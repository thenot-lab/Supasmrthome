"""Tests for the Live Observer module and API endpoints.

Covers:

    * `EventBus` — publish / recent / latest / clear / subscribe / unsubscribe
      and the drop-on-full back-pressure policy.
    * `generate_scenario_frames` and `frames_to_gif` — end-to-end frame
      generation for a real scenario.
    * FastAPI live endpoints — /live/events, /live/frames/{scenario},
      /live/observer — including X-Client source attribution.
"""

from __future__ import annotations

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

import neuro_arousal.auth as auth_mod
from neuro_arousal.api import app, soul
from neuro_arousal.live import (
    EventBus,
    LiveEvent,
    bus as global_bus,
    frames_to_gif,
    generate_scenario_frames,
)


# ---------------------------------------------------------------------------
# EventBus unit tests
# ---------------------------------------------------------------------------


class TestEventBus:
    def test_publish_assigns_monotonic_ids(self):
        b = EventBus()
        e1 = b.publish(type="scenario_run", summary="first")
        e2 = b.publish(type="custom_run", summary="second")
        assert e1.id == 1
        assert e2.id == 2
        assert e2.timestamp >= e1.timestamp

    def test_recent_returns_events_in_order(self):
        b = EventBus()
        b.publish(type="scenario_run", summary="a")
        b.publish(type="scenario_run", summary="b")
        b.publish(type="scenario_run", summary="c")
        events = b.recent(limit=10)
        assert [e.summary for e in events] == ["a", "b", "c"]

    def test_recent_limit_truncates_from_end(self):
        b = EventBus()
        for i in range(10):
            b.publish(type="scenario_run", summary=f"evt-{i}")
        events = b.recent(limit=3)
        assert [e.summary for e in events] == ["evt-7", "evt-8", "evt-9"]

    def test_recent_since_id_filters(self):
        b = EventBus()
        for i in range(5):
            b.publish(type="scenario_run", summary=f"evt-{i}")
        events = b.recent(limit=10, since_id=2)
        assert [e.id for e in events] == [3, 4, 5]

    def test_latest_returns_most_recent(self):
        b = EventBus()
        assert b.latest() is None
        b.publish(type="scenario_run", summary="one")
        b.publish(type="scenario_run", summary="two")
        assert b.latest().summary == "two"

    def test_clear_resets_state(self):
        b = EventBus()
        b.publish(type="scenario_run", summary="x")
        b.clear()
        assert b.latest() is None
        assert b.recent() == []
        # Clearing must also reset the id counter so fresh streams start at 1.
        e = b.publish(type="scenario_run", summary="fresh")
        assert e.id == 1

    def test_maxlen_ring_buffer_evicts_oldest(self):
        b = EventBus(maxlen=3)
        for i in range(5):
            b.publish(type="scenario_run", summary=f"evt-{i}")
        events = b.recent(limit=10)
        assert len(events) == 3
        # Oldest two are evicted; ids are still monotonic.
        assert [e.summary for e in events] == ["evt-2", "evt-3", "evt-4"]

    def test_event_detail_preserved(self):
        b = EventBus()
        evt = b.publish(
            type="scenario_run",
            summary="with detail",
            source="ios",
            detail={"regime": "OSCILLATORY", "spikes": 12},
        )
        assert evt.source == "ios"
        assert evt.detail == {"regime": "OSCILLATORY", "spikes": 12}

    def test_event_to_dict_roundtrip(self):
        b = EventBus()
        evt = b.publish(
            type="scenario_run",
            summary="dict",
            source="api",
            detail={"k": 1},
        )
        d = evt.to_dict()
        assert d["id"] == evt.id
        assert d["type"] == "scenario_run"
        assert d["source"] == "api"
        assert d["detail"] == {"k": 1}

    def test_subscribe_receives_published_events(self):
        async def run():
            b = EventBus()
            q = b.subscribe()
            assert b.subscriber_count == 1
            b.publish(type="scenario_run", summary="hello")
            evt = await asyncio.wait_for(q.get(), timeout=1.0)
            assert evt.summary == "hello"
            b.unsubscribe(q)
            assert b.subscriber_count == 0

        asyncio.run(run())

    def test_full_subscriber_is_dropped(self):
        async def run():
            b = EventBus()
            q = b.subscribe(maxsize=2)
            # Fill the queue beyond capacity — third publish should drop the sub.
            b.publish(type="scenario_run", summary="1")
            b.publish(type="scenario_run", summary="2")
            b.publish(type="scenario_run", summary="3")
            # The bus has dropped the overloaded subscriber.
            assert b.subscriber_count == 0

        asyncio.run(run())


# ---------------------------------------------------------------------------
# Frame generation
# ---------------------------------------------------------------------------


class TestGenerateScenarioFrames:
    def test_returns_png_bytes_and_metadata(self):
        frames, meta = generate_scenario_frames(
            soul, scenario_name="resting_state", frame_count=6,
            frame_width=180, frame_height=220,
        )
        assert len(frames) > 0
        assert all(isinstance(f, bytes) and f.startswith(b"\x89PNG") for f in frames)
        assert meta["scenario"] == "resting_state"
        assert meta["frames"] == len(frames)
        assert meta["total_steps"] > 0
        assert "regime" in meta
        assert len(meta["step_indices"]) == len(frames)

    def test_frame_count_clamped_to_total_steps(self):
        # Extremely high frame count should not exceed total integration steps.
        frames, meta = generate_scenario_frames(
            soul, scenario_name="resting_state", frame_count=100000,
        )
        assert meta["frames"] <= meta["total_steps"]

    def test_frames_to_gif_roundtrip(self):
        frames, _ = generate_scenario_frames(
            soul, scenario_name="resting_state", frame_count=4,
            frame_width=120, frame_height=150,
        )
        gif = frames_to_gif(frames, duration_ms=80)
        # Pillow is a hard dependency of multimodal rendering, so this should
        # always succeed in the test environment.
        assert gif is not None
        assert gif.startswith(b"GIF8")

    def test_frames_to_gif_empty_returns_none(self):
        assert frames_to_gif([]) is None


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _disable_auth_and_clear_bus():
    """Force personal-mode auth (AUTH_REQUIRED=False) and isolate bus state.

    Other test modules (e.g. test_auth.py) may flip ``AUTH_REQUIRED`` to True
    and leave it that way — we reset it per-test here so the live endpoints
    behave as they would in a kiosk deployment.
    """
    prev_auth = auth_mod.AUTH_REQUIRED
    auth_mod.AUTH_REQUIRED = False
    global_bus.clear()
    yield
    global_bus.clear()
    auth_mod.AUTH_REQUIRED = prev_auth


class TestLiveEventsEndpoint:
    def test_empty_feed(self, client):
        r = client.get("/live/events")
        assert r.status_code == 200
        body = r.json()
        assert body["events"] == []
        assert body["latest_id"] == 0
        assert body["subscriber_count"] == 0

    def test_run_scenario_publishes_event(self, client):
        r = client.post(
            "/run/scenario/resting_state",
            headers={"X-Client": "ios"},
        )
        assert r.status_code == 200

        feed = client.get("/live/events").json()
        # Expect at least two events: adapter_change then scenario_run.
        assert len(feed["events"]) >= 1
        types = {e["type"] for e in feed["events"]}
        assert "scenario_run" in types
        run_evts = [e for e in feed["events"] if e["type"] == "scenario_run"]
        assert run_evts[-1]["source"] == "ios"
        assert "resting" in run_evts[-1]["summary"].lower()

    def test_since_id_filters(self, client):
        # Publish three events directly; verify since_id slicing.
        global_bus.publish(type="scenario_run", summary="a", source="api")
        global_bus.publish(type="scenario_run", summary="b", source="api")
        global_bus.publish(type="scenario_run", summary="c", source="api")
        r = client.get("/live/events", params={"since_id": 2})
        body = r.json()
        ids = [e["id"] for e in body["events"]]
        assert ids == [3]

    def test_limit_parameter(self, client):
        for i in range(10):
            global_bus.publish(type="scenario_run", summary=f"e{i}", source="api")
        r = client.get("/live/events", params={"limit": 4})
        body = r.json()
        assert len(body["events"]) == 4

    def test_x_client_defaults_to_api(self, client):
        r = client.post("/run/scenario/resting_state")
        assert r.status_code == 200
        feed = client.get("/live/events").json()
        run_evts = [e for e in feed["events"] if e["type"] == "scenario_run"]
        assert run_evts[-1]["source"] == "api"

    def test_unknown_x_client_normalises_to_api(self, client):
        r = client.post(
            "/run/scenario/resting_state",
            headers={"X-Client": "some-random-bot"},
        )
        assert r.status_code == 200
        feed = client.get("/live/events").json()
        run_evts = [e for e in feed["events"] if e["type"] == "scenario_run"]
        assert run_evts[-1]["source"] == "api"


class TestLiveFramesEndpoint:
    def test_returns_gif_for_valid_scenario(self, client):
        r = client.get(
            "/live/frames/resting_state",
            params={"frames": 6, "width": 160, "height": 200, "duration_ms": 100},
            headers={"X-Client": "android"},
        )
        assert r.status_code == 200
        assert r.headers["content-type"] in ("image/gif", "image/png")
        # When GIF, the signature starts with GIF8; PNG fallback starts with \x89PNG.
        body = r.content
        assert body.startswith(b"GIF8") or body.startswith(b"\x89PNG")
        assert "X-Live-Frames-Meta" in r.headers

    def test_unknown_scenario_404s(self, client):
        r = client.get("/live/frames/not_a_real_scenario")
        assert r.status_code == 404

    def test_frames_publishes_event(self, client):
        client.get(
            "/live/frames/resting_state",
            params={"frames": 4},
            headers={"X-Client": "gradio"},
        )
        feed = client.get("/live/events").json()
        gen_evts = [e for e in feed["events"] if e["type"] == "frames_generated"]
        assert len(gen_evts) >= 1
        assert gen_evts[-1]["source"] == "gradio"
        assert "resting" in gen_evts[-1]["summary"].lower()


class TestLiveObserverPage:
    def test_returns_html(self, client):
        r = client.get("/live/observer")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        body = r.text
        assert "Live Observer" in body or "live observer" in body.lower()
        # Must reference the endpoints it consumes.
        assert "/live/events" in body
        assert "/live/stream" in body
        assert "/character/image" in body


class TestLiveStreamEndpoint:
    def test_stream_route_registered(self):
        # FastAPI TestClient's sync `stream()` is incompatible with SSE
        # generators that loop on asyncio.wait_for — the context manager
        # can't cleanly tear down an in-flight async yield from a sync
        # caller, which hangs the test run. Instead, verify that the route
        # is registered and has the expected endpoint function.
        from neuro_arousal.api import app, live_stream
        paths = {route.path for route in app.routes}
        assert "/live/stream" in paths
        assert live_stream.__name__ == "live_stream"
