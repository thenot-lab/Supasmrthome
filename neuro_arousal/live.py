"""
Live Observer module — event bus and animated-frame generator.

Enables a "live feed" view of the NeuroArousal exhibit:

    * `EventBus` — a thread-safe, bounded in-memory append-only log of
      simulation events (scenario runs, custom runs, adapter changes).
      Readers can poll for recent events or subscribe via an async queue
      for Server-Sent Events (SSE).

    * `generate_scenario_frames` — run a scenario and turn each K-th
      integration snapshot into a character PNG. Bundles them into an
      animated GIF when Pillow is available.

The bus is process-local and intentionally lightweight — suitable for a
single kiosk or the personal-use deployment. It is *not* a replacement
for an external broker; it exists so that observers (a curator on a
second device, a teacher monitoring a classroom) can see what visitors
are doing in real time without modifying the simulation path.
"""

from __future__ import annotations

import asyncio
import io
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from threading import Lock
from typing import Iterable

try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


# ---------------------------------------------------------------------------
# Event model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LiveEvent:
    """A single observable event in the exhibit's activity feed."""
    id: int
    timestamp: float
    type: str           # "scenario_run" | "custom_run" | "adapter_change"
    source: str         # "api" | "gradio" | "ios" | "android" | "internal"
    summary: str        # human-readable one-liner
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Event bus
# ---------------------------------------------------------------------------

class EventBus:
    """Thread-safe bounded ring buffer + async fan-out for live events.

    Use `publish(...)` from any context (sync or async). Poll recent
    history with `recent(...)`. For SSE/WS fan-out, acquire a fresh
    `asyncio.Queue` via `subscribe()` — the bus enqueues every new event
    to every active subscriber and drops subscribers whose queues are
    full (back-pressure strategy: "observer must keep up or miss frames").
    """

    def __init__(self, maxlen: int = 200) -> None:
        self._events: deque[LiveEvent] = deque(maxlen=maxlen)
        self._lock = Lock()
        self._next_id = 1
        self._subscribers: list[asyncio.Queue[LiveEvent]] = []

    # ----- publish path -----

    def publish(
        self,
        type: str,
        summary: str,
        source: str = "internal",
        detail: dict | None = None,
    ) -> LiveEvent:
        with self._lock:
            evt = LiveEvent(
                id=self._next_id,
                timestamp=time.time(),
                type=type,
                source=source,
                summary=summary,
                detail=detail or {},
            )
            self._next_id += 1
            self._events.append(evt)
            subscribers = list(self._subscribers)

        # Fan-out outside the lock so a slow subscriber can't block publish.
        for q in subscribers:
            try:
                q.put_nowait(evt)
            except asyncio.QueueFull:
                # Drop the subscriber — they fell behind.
                self._drop_subscriber(q)
        return evt

    # ----- read path -----

    def recent(self, limit: int = 50, since_id: int = 0) -> list[LiveEvent]:
        with self._lock:
            if since_id > 0:
                filtered = [e for e in self._events if e.id > since_id]
            else:
                filtered = list(self._events)
        return filtered[-limit:]

    def latest(self) -> LiveEvent | None:
        with self._lock:
            return self._events[-1] if self._events else None

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._next_id = 1

    # ----- subscribe / unsubscribe for SSE -----

    def subscribe(self, maxsize: int = 64) -> asyncio.Queue[LiveEvent]:
        q: asyncio.Queue[LiveEvent] = asyncio.Queue(maxsize=maxsize)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[LiveEvent]) -> None:
        self._drop_subscriber(q)

    def _drop_subscriber(self, q: asyncio.Queue[LiveEvent]) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)


# Module-level singleton — shared between DigitalSoul and the FastAPI layer.
bus = EventBus()


# ---------------------------------------------------------------------------
# Animated frame generation
# ---------------------------------------------------------------------------

def generate_scenario_frames(
    soul,
    scenario_name: str,
    frame_count: int = 24,
    frame_width: int = 300,
    frame_height: int = 380,
) -> tuple[list[bytes], dict]:
    """Run a scenario and render `frame_count` character PNGs across time.

    Returns (list_of_png_bytes, metadata). Metadata includes the scenario
    name, frame indices, regime, and total steps.

    The scenario is run through the given DigitalSoul instance. Frames
    are sampled at evenly-spaced integration steps so the resulting GIF
    traces the full arc from exposition to resolution.
    """
    from neuro_arousal.multimodal import compute_appearance, render_character

    results, report = soul.run_scenario(scenario_name)
    u1 = results["u1"]
    total_steps = len(u1)

    if total_steps == 0:
        return [], {"scenario": scenario_name, "frames": 0}

    frame_count = max(1, min(frame_count, total_steps))
    step_indices = [
        int(round(i * (total_steps - 1) / max(1, frame_count - 1)))
        for i in range(frame_count)
    ]
    # Deduplicate while preserving order (relevant if frame_count > total_steps)
    seen: set[int] = set()
    unique_steps: list[int] = []
    for s in step_indices:
        if s not in seen:
            unique_steps.append(s)
            seen.add(s)

    regime_name = report.coupled_regime.name
    png_frames: list[bytes] = []
    for step in unique_steps:
        snap = soul.get_state_snapshot(step)
        if snap is None:
            continue
        appearance = compute_appearance(snap, regime_name)
        png_frames.append(
            render_character(
                appearance,
                width=frame_width,
                height=frame_height,
            )
        )

    return png_frames, {
        "scenario": scenario_name,
        "regime": regime_name,
        "frames": len(png_frames),
        "total_steps": total_steps,
        "step_indices": unique_steps,
        "soma_regime": report.soma_regime.name,
        "psyche_regime": report.psyche_regime.name,
        "soma_spikes": report.soma_spike_count,
        "psyche_spikes": report.psyche_spike_count,
    }


def frames_to_gif(
    png_frames: Iterable[bytes],
    duration_ms: int = 120,
    loop: int = 0,
) -> bytes | None:
    """Combine PNG frames into an animated GIF. Returns None if Pillow is
    unavailable or no frames are provided."""
    if not _HAS_PIL:
        return None
    frames = [Image.open(io.BytesIO(p)).convert("P", palette=Image.ADAPTIVE)
              for p in png_frames]
    if not frames:
        return None
    buf = io.BytesIO()
    frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=loop,
        optimize=True,
        disposal=2,
    )
    return buf.getvalue()
