"""
FastAPI backend for the NeuroArousal interactive exhibit.

Provides REST endpoints for:
  * listing / describing preset scenarios
  * running simulations (preset or custom)
  * retrieving nullcline data for phase-plane plots
  * computational state inspection at any timestep
  * alignment scoring between SOMA and PSYCHE
  * narrative arc decomposition (climax detection, tension curve)
  * PEFT adapter selection and listing
  * multimodal character image generation
"""

from __future__ import annotations

import asyncio
import json
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from neuro_arousal.digital_soul import (
    DigitalSoul,
    Regime,
    ArcPhase,
    PEFT_ADAPTERS,
)
from neuro_arousal.engine import (
    CouplingParams,
    EmotionalDriveParams,
    SimulationConfig,
    SubsystemParams,
    null_stimulus,
    pulse_stimulus,
    periodic_stimulus,
    savage_config,
)
from neuro_arousal.multimodal import (
    compute_appearance,
    render_character,
    appearance_to_dict,
)
from neuro_arousal.live import (
    bus as live_bus,
    frames_to_gif,
    generate_scenario_frames,
)
from neuro_arousal.auth import (
    UserCreate,
    UserOut,
    TokenOut,
    get_current_user,
    register_user,
    authenticate_user,
)

# ---------------------------------------------------------------------------
# App and shared state
# ---------------------------------------------------------------------------

app = FastAPI(
    title="NeuroArousal Exhibit API",
    description=(
        "Interactive Blyuss-Kyrychko coupled excitable system simulation "
        "for museum demonstration.  Full state inspection, narrative arc "
        "analysis, alignment scoring, and multimodal character generation."
    ),
    version="2.0.0",
)

# Enable CORS for local development and mobile apps.
# In production, replace with specific allowed origins.
CORS_ORIGINS = [
    "http://localhost:7860",
    "http://localhost:3000",
    "http://127.0.0.1:7860",
    "http://127.0.0.1:3000",
    "http://10.0.2.2:7860",     # Android emulator → host
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|10\.0\.2\.2)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

soul = DigitalSoul()


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@app.post("/auth/register", response_model=UserOut, status_code=201)
def auth_register(data: UserCreate):
    """Register a new user account."""
    return register_user(data)


@app.post("/auth/login", response_model=TokenOut)
def auth_login(form: OAuth2PasswordRequestForm = Depends()):
    """Log in with username/password. Returns a bearer token."""
    return authenticate_user(form.username, form.password)


@app.get("/auth/me", response_model=UserOut)
def auth_me(username: str = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    from neuro_arousal.auth import _load_users
    users = _load_users()
    user = users[username]
    return UserOut(
        username=username,
        display_name=user["display_name"],
        created_at=user["created_at"],
    )


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class SubsystemIn(BaseModel):
    a: float = Field(0.25, gt=0, lt=1, description="Excitability threshold")
    epsilon: float = Field(0.01, gt=0, description="Timescale separation")
    b: float = Field(0.5, description="Recovery gain")


class CouplingIn(BaseModel):
    c12: float = Field(0.15, description="PSYCHE → SOMA strength")
    c21: float = Field(0.12, description="SOMA → PSYCHE strength")
    kappa: float = Field(10.0, ge=0, description="Sigmoid steepness")
    theta: float = Field(0.3, description="Sigmoid midpoint")
    tau: float = Field(5.0, ge=0, description="Coupling delay")


class EmotionIn(BaseModel):
    E_u: float = Field(50.0, ge=0, le=100, description="Arousal drive 0–100")
    E_v: float = Field(50.0, ge=0, le=100, description="Valence drive 0–100")
    E_v0: float = Field(0.2, description="Baseline valence offset")


class StimulusIn(BaseModel):
    kind: str = Field("none", description="'none', 'pulse', or 'periodic'")
    onset: float = Field(20.0, ge=0)
    duration: float = Field(3.0, ge=0)
    amplitude: float = Field(0.5)
    period: float = Field(40.0, gt=0, description="Only used for periodic")


class CustomRunRequest(BaseModel):
    dt: float = Field(0.05, gt=0)
    t_max: float = Field(200.0, gt=0, le=1000.0)
    soma: SubsystemIn = Field(default_factory=SubsystemIn)
    psyche: SubsystemIn = Field(default_factory=SubsystemIn)
    coupling: CouplingIn = Field(default_factory=CouplingIn)
    emotion: EmotionIn = Field(default_factory=EmotionIn)
    savage_mode: bool = False
    ic_u1: float = 0.0
    ic_v1: float = 0.0
    ic_u2: float = 0.0
    ic_v2: float = 0.0
    soma_stimulus: StimulusIn = Field(default_factory=StimulusIn)
    psyche_stimulus: StimulusIn = Field(default_factory=StimulusIn)
    adapter: str = "default"


class RegimeOut(BaseModel):
    soma_regime: str
    psyche_regime: str
    coupled_regime: str
    soma_spike_count: int
    psyche_spike_count: int
    mean_coupling_flux: float
    description: str


class AlignmentOut(BaseModel):
    cross_correlation: float
    phase_lag: float
    coherence_index: float
    interpretation: str


class ArcPhaseOut(BaseModel):
    t_start: float
    t_end: float
    phase: str


class NarrativeArcOut(BaseModel):
    phases: list[ArcPhaseOut]
    climax_time: float
    climax_energy: float
    peak_spike_rate: float
    arc_summary: str
    tension_curve: list[float]


class SimulationOut(BaseModel):
    time: list[float]
    u1: list[float]
    v1: list[float]
    u2: list[float]
    v2: list[float]
    soma_energy: list[float]
    psyche_energy: list[float]
    coupling_flux: list[float]
    report: RegimeOut
    alignment: AlignmentOut | None = None
    arc: NarrativeArcOut | None = None


class NullclineOut(BaseModel):
    u: list[float]
    soma_cubic: list[float]
    soma_linear: list[float]
    psyche_cubic: list[float]
    psyche_linear: list[float]


class ScenarioInfoOut(BaseModel):
    name: str
    description: str
    soma_a: str
    psyche_a: str
    c12: str
    c21: str
    tau: str


class AdapterOut(BaseModel):
    name: str
    label: str
    description: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stimulus(s: StimulusIn):
    if s.kind == "pulse":
        return pulse_stimulus(s.onset, s.duration, s.amplitude)
    if s.kind == "periodic":
        return periodic_stimulus(s.period, s.duration, s.amplitude)
    return null_stimulus


def _downsample(arr, max_points: int = 2000) -> list[float]:
    if len(arr) <= max_points:
        return arr.tolist()
    step = max(1, len(arr) // max_points)
    return arr[::step].tolist()


def _results_to_out(results, report, alignment=None, arc=None) -> SimulationOut:
    alignment_out = None
    if alignment is not None:
        alignment_out = AlignmentOut(
            cross_correlation=alignment.cross_correlation,
            phase_lag=alignment.phase_lag,
            coherence_index=alignment.coherence_index,
            interpretation=alignment.interpretation,
        )

    arc_out = None
    if arc is not None:
        arc_out = NarrativeArcOut(
            phases=[
                ArcPhaseOut(t_start=p[0], t_end=p[1], phase=p[2].name)
                for p in arc.phases
            ],
            climax_time=arc.climax_time,
            climax_energy=arc.climax_energy,
            peak_spike_rate=arc.peak_spike_rate,
            arc_summary=arc.arc_summary,
            tension_curve=_downsample(arc.tension_curve),
        )

    return SimulationOut(
        time=_downsample(results["time"]),
        u1=_downsample(results["u1"]),
        v1=_downsample(results["v1"]),
        u2=_downsample(results["u2"]),
        v2=_downsample(results["v2"]),
        soma_energy=_downsample(results["soma_energy"]),
        psyche_energy=_downsample(results["psyche_energy"]),
        coupling_flux=_downsample(results["coupling_flux"]),
        report=RegimeOut(
            soma_regime=report.soma_regime.name,
            psyche_regime=report.psyche_regime.name,
            coupled_regime=report.coupled_regime.name,
            soma_spike_count=report.soma_spike_count,
            psyche_spike_count=report.psyche_spike_count,
            mean_coupling_flux=round(report.mean_coupling_flux, 6),
            description=report.description,
        ),
        alignment=alignment_out,
        arc=arc_out,
    )


# ---------------------------------------------------------------------------
# Endpoints — scenarios
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "service": "NeuroArousal Exhibit API",
        "version": "2.0.0",
        "docs": "/docs",
        "scenarios": soul.scenario_names,
        "adapters": list(PEFT_ADAPTERS.keys()),
    }


@app.get("/scenarios", response_model=list[str])
def list_scenarios():
    return soul.scenario_names


@app.get("/scenarios/{name}", response_model=ScenarioInfoOut)
def get_scenario(name: str):
    if name not in soul.scenarios:
        raise HTTPException(404, f"Unknown scenario: {name}")
    return ScenarioInfoOut(**soul.get_scenario_info(name))


# ---------------------------------------------------------------------------
# Endpoints — simulation
# ---------------------------------------------------------------------------

def _resolve_source(x_client: str | None) -> str:
    """Map the X-Client header to a normalised source label for the event bus."""
    if not x_client:
        return "api"
    c = x_client.strip().lower()
    if c in ("gradio", "ios", "android", "api", "internal", "observer"):
        return c
    return "api"


@app.post("/run/scenario/{name}", response_model=SimulationOut)
def run_scenario(
    name: str, adapter: str = "default",
    _user: str = Depends(get_current_user),
    x_client: str | None = Header(default=None, alias="X-Client"),
):
    source = _resolve_source(x_client)
    soul.set_adapter(adapter, source=source)
    try:
        results, report = soul.run_scenario(name, source=source)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return _results_to_out(
        results, report, soul.get_alignment(), soul.get_arc()
    )


@app.post("/run/custom", response_model=SimulationOut)
def run_custom(
    req: CustomRunRequest,
    _user: str = Depends(get_current_user),
    x_client: str | None = Header(default=None, alias="X-Client"),
):
    source = _resolve_source(x_client)
    soul.set_adapter(req.adapter, source=source)

    if req.savage_mode:
        config = savage_config(t_max=req.t_max)
    else:
        config = SimulationConfig(
            dt=req.dt,
            t_max=req.t_max,
            soma=SubsystemParams(
                a=req.soma.a, epsilon=req.soma.epsilon, b=req.soma.b
            ),
            psyche=SubsystemParams(
                a=req.psyche.a, epsilon=req.psyche.epsilon, b=req.psyche.b
            ),
            coupling=CouplingParams(
                c12=req.coupling.c12, c21=req.coupling.c21,
                kappa=req.coupling.kappa, theta=req.coupling.theta,
                tau=req.coupling.tau,
            ),
            emotion=EmotionalDriveParams(
                E_u=req.emotion.E_u,
                E_v=req.emotion.E_v,
                E_v0=req.emotion.E_v0,
            ),
            savage_mode=False,
        )
    try:
        results, report = soul.run_custom(
            config=config,
            ic=(req.ic_u1, req.ic_v1, req.ic_u2, req.ic_v2),
            I1_func=_make_stimulus(req.soma_stimulus),
            I2_func=_make_stimulus(req.psyche_stimulus),
            source=source,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return _results_to_out(
        results, report, soul.get_alignment(), soul.get_arc()
    )


# ---------------------------------------------------------------------------
# Endpoints — nullclines
# ---------------------------------------------------------------------------

@app.get("/nullclines", response_model=NullclineOut)
def get_nullclines(
    soma_a: Annotated[float, Query(gt=0, lt=1)] = 0.25,
    soma_b: float = 0.5,
    psyche_a: Annotated[float, Query(gt=0, lt=1)] = 0.20,
    psyche_b: float = 0.45,
):
    config = SimulationConfig(
        soma=SubsystemParams(a=soma_a, b=soma_b),
        psyche=SubsystemParams(a=psyche_a, b=psyche_b),
    )
    nc = soul.get_nullclines(config)
    return NullclineOut(
        u=nc["u"].tolist(),
        soma_cubic=nc["soma_cubic"].tolist(),
        soma_linear=nc["soma_linear"].tolist(),
        psyche_cubic=nc["psyche_cubic"].tolist(),
        psyche_linear=nc["psyche_linear"].tolist(),
    )


# ---------------------------------------------------------------------------
# Endpoints — state inspector
# ---------------------------------------------------------------------------

@app.get("/state/{step}")
def get_state_snapshot(step: int):
    """Return full computational state at a given integration step."""
    snap = soul.get_state_snapshot(step)
    if snap is None:
        raise HTTPException(404, "No simulation has been run yet.")
    return snap


@app.get("/state")
def get_state_current():
    """Return computational state at the final step of the last run."""
    snap = soul.get_state_snapshot()
    if snap is None:
        raise HTTPException(404, "No simulation has been run yet.")
    return snap


# ---------------------------------------------------------------------------
# Endpoints — alignment
# ---------------------------------------------------------------------------

@app.get("/alignment", response_model=AlignmentOut)
def get_alignment():
    a = soul.get_alignment()
    if a is None:
        raise HTTPException(404, "No simulation has been run yet.")
    return AlignmentOut(
        cross_correlation=a.cross_correlation,
        phase_lag=a.phase_lag,
        coherence_index=a.coherence_index,
        interpretation=a.interpretation,
    )


# ---------------------------------------------------------------------------
# Endpoints — narrative arc
# ---------------------------------------------------------------------------

@app.get("/arc", response_model=NarrativeArcOut)
def get_narrative_arc():
    arc = soul.get_arc()
    if arc is None:
        raise HTTPException(404, "No simulation has been run yet.")
    return NarrativeArcOut(
        phases=[
            ArcPhaseOut(t_start=p[0], t_end=p[1], phase=p[2].name)
            for p in arc.phases
        ],
        climax_time=arc.climax_time,
        climax_energy=arc.climax_energy,
        peak_spike_rate=arc.peak_spike_rate,
        arc_summary=arc.arc_summary,
        tension_curve=_downsample(arc.tension_curve),
    )


# ---------------------------------------------------------------------------
# Endpoints — PEFT adapters
# ---------------------------------------------------------------------------

@app.get("/adapters", response_model=list[AdapterOut])
def list_adapters():
    return [
        AdapterOut(**a) for a in soul.available_adapters()
    ]


@app.post("/adapters/{name}")
def set_adapter(
    name: str,
    _user: str = Depends(get_current_user),
    x_client: str | None = Header(default=None, alias="X-Client"),
):
    if name not in PEFT_ADAPTERS:
        raise HTTPException(404, f"Unknown adapter: {name}")
    a = soul.set_adapter(name, source=_resolve_source(x_client))
    return {"name": a.name, "label": a.label}


# ---------------------------------------------------------------------------
# Endpoints — multimodal character
# ---------------------------------------------------------------------------

@app.get("/character/appearance")
def get_character_appearance(step: int | None = None):
    """Get character visual parameters derived from simulation state."""
    snap = soul.get_state_snapshot(step)
    if snap is None:
        raise HTTPException(404, "No simulation has been run yet.")
    report = soul._last_report
    regime_name = report.coupled_regime.name if report else "QUIESCENT"
    appearance = compute_appearance(snap, regime_name)
    return appearance_to_dict(appearance)


@app.get("/character/image")
def get_character_image(step: int | None = None):
    """Render character PNG from current simulation state."""
    snap = soul.get_state_snapshot(step)
    if snap is None:
        raise HTTPException(404, "No simulation has been run yet.")
    report = soul._last_report
    regime_name = report.coupled_regime.name if report else "QUIESCENT"
    appearance = compute_appearance(snap, regime_name)
    png_bytes = render_character(appearance)
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


# ---------------------------------------------------------------------------
# Endpoints — Live Observer
# ---------------------------------------------------------------------------

class LiveEventOut(BaseModel):
    id: int
    timestamp: float
    type: str
    source: str
    summary: str
    detail: dict


class LiveFeedOut(BaseModel):
    events: list[LiveEventOut]
    subscriber_count: int
    latest_id: int


@app.get("/live/events", response_model=LiveFeedOut)
def live_events(
    limit: int = Query(50, ge=1, le=200),
    since_id: int = Query(0, ge=0),
):
    """Poll-based activity feed of recent simulation events.

    Read-only and unauthenticated so a passive observer can watch the
    exhibit without needing credentials. Clients can pass `since_id`
    for efficient incremental polling.
    """
    events = live_bus.recent(limit=limit, since_id=since_id)
    latest = live_bus.latest()
    return LiveFeedOut(
        events=[LiveEventOut(**e.to_dict()) for e in events],
        subscriber_count=live_bus.subscriber_count,
        latest_id=latest.id if latest else 0,
    )


@app.get("/live/stream")
async def live_stream(request: Request):
    """Server-Sent Events stream of live observer events.

    Each event is emitted as `data: <json>\\n\\n`. A heartbeat comment
    is sent every 15 seconds to keep intermediate proxies from closing
    the connection. Unauthenticated for observer use.
    """
    queue = live_bus.subscribe()

    async def event_generator():
        try:
            # Send a small init event so clients know the stream is alive.
            init = {
                "type": "stream_opened",
                "summary": "Live observer stream connected",
                "timestamp": __import__("time").time(),
            }
            yield f"event: open\ndata: {json.dumps(init)}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    evt = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(evt.to_dict())}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            live_bus.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",  # disable nginx buffering if present
            "Connection": "keep-alive",
        },
    )


@app.get("/live/frames/{scenario}")
def live_frames(
    scenario: str,
    frames: int = Query(24, ge=2, le=60),
    width: int = Query(300, ge=100, le=800),
    height: int = Query(380, ge=100, le=1000),
    duration_ms: int = Query(120, ge=20, le=1000),
    x_client: str | None = Header(default=None, alias="X-Client"),
):
    """Run a scenario and return an animated GIF of the character across time.

    This is the "video generation" path — each frame is a procedural render
    of the character at an evenly-spaced simulation step. Observers can
    embed the returned GIF in any `<img>` tag.
    """
    if scenario not in soul.scenarios:
        raise HTTPException(404, f"Unknown scenario: {scenario}")
    source = _resolve_source(x_client)
    soul.set_adapter(soul.adapter.name, source=source)
    png_frames, meta = generate_scenario_frames(
        soul,
        scenario_name=scenario,
        frame_count=frames,
        frame_width=width,
        frame_height=height,
    )
    gif = frames_to_gif(png_frames, duration_ms=duration_ms)
    if gif is None:
        # Fallback: return the last rendered frame as a static PNG so the
        # caller always gets an image back.
        if not png_frames:
            raise HTTPException(500, "Frame generation produced no output.")
        return Response(
            content=png_frames[-1],
            media_type="image/png",
            headers={
                "Cache-Control": "no-store",
                "X-Live-Frames-Meta": json.dumps(meta),
            },
        )
    live_bus.publish(
        type="frames_generated",
        summary=f"Rendered {meta['frames']} frames for '{meta['scenario']}'",
        source=source,
        detail=meta,
    )
    return Response(
        content=gif,
        media_type="image/gif",
        headers={
            "Cache-Control": "no-store",
            "X-Live-Frames-Meta": json.dumps(meta),
        },
    )


@app.get("/live/observer", response_class=HTMLResponse)
def live_observer():
    """Standalone HTML observer page — zero-config live feed for a second screen.

    Shows the current character, the latest simulation result, and an
    activity feed that updates in real time via the SSE stream. Designed
    to be opened on a curator's phone or a second kiosk display.
    """
    return HTMLResponse(_OBSERVER_HTML)


_OBSERVER_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>NeuroArousal — Live Observer</title>
<style>
  :root {
    color-scheme: dark;
    --bg: #0f0f1a;
    --panel: #1a1a2e;
    --ink: #e7e7f2;
    --muted: #8c8ca5;
    --accent: #ff006e;
    --ok: #4caf50;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro", "Segoe UI",
                 Roboto, sans-serif;
    background: var(--bg);
    color: var(--ink);
    padding: 16px;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }
  h1 { margin: 0; font-size: 1.2rem; }
  .status {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 0.85rem;
    color: var(--muted);
  }
  .dot {
    width: 10px; height: 10px; border-radius: 50%;
    background: var(--muted);
    box-shadow: 0 0 8px currentColor;
  }
  .dot.live { background: var(--ok); }
  .grid {
    display: grid;
    grid-template-columns: minmax(280px, 1fr) 1fr;
    gap: 16px;
  }
  @media (max-width: 720px) {
    .grid { grid-template-columns: 1fr; }
  }
  .panel {
    background: var(--panel);
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.25);
  }
  .panel h2 {
    margin: 0 0 12px 0;
    font-size: 0.95rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  #character {
    width: 100%; max-width: 360px; height: auto;
    border-radius: 8px;
    display: block;
    margin: 0 auto;
    background: #000;
  }
  .regime {
    margin-top: 12px;
    font-size: 1.1rem;
    font-weight: 600;
    text-align: center;
  }
  .regime .label { color: var(--muted); font-weight: 400; font-size: 0.85rem; }
  ul#feed {
    list-style: none;
    padding: 0;
    margin: 0;
    max-height: 60vh;
    overflow-y: auto;
  }
  ul#feed li {
    padding: 10px 12px;
    border-left: 3px solid var(--accent);
    margin-bottom: 8px;
    background: rgba(255,255,255,0.03);
    border-radius: 0 8px 8px 0;
    font-size: 0.9rem;
  }
  ul#feed li .meta {
    display: block;
    color: var(--muted);
    font-size: 0.75rem;
    margin-top: 4px;
  }
</style>
</head>
<body>
  <header>
    <h1>NeuroArousal — Live Observer</h1>
    <span class="status"><span class="dot" id="dot"></span><span id="stat">Connecting...</span></span>
  </header>
  <div class="grid">
    <section class="panel">
      <h2>Character</h2>
      <img id="character" alt="Character visualisation" />
      <div class="regime">
        <span class="label">Coupled regime</span><br/>
        <span id="regime">—</span>
      </div>
    </section>
    <section class="panel">
      <h2>Activity feed</h2>
      <ul id="feed"></ul>
    </section>
  </div>
<script>
(function(){
  var img = document.getElementById("character");
  var feed = document.getElementById("feed");
  var regime = document.getElementById("regime");
  var stat = document.getElementById("stat");
  var dot = document.getElementById("dot");

  function refreshCharacter() {
    img.src = "/character/image?t=" + Date.now();
  }

  function addEvent(evt) {
    var li = document.createElement("li");
    var d = new Date((evt.timestamp || Date.now()/1000) * 1000);
    li.innerHTML =
      "<strong>" + (evt.summary || evt.type || "event") + "</strong>" +
      "<span class=\\"meta\\">" + d.toLocaleTimeString() +
      " · " + (evt.source || "internal") + "</span>";
    feed.insertBefore(li, feed.firstChild);
    while (feed.children.length > 30) feed.removeChild(feed.lastChild);
    if (evt.detail && evt.detail.coupled_regime) {
      regime.textContent = evt.detail.coupled_regime;
    }
    if (evt.type === "scenario_run" || evt.type === "custom_run") {
      refreshCharacter();
    }
  }

  // Prime the feed with recent history.
  fetch("/live/events?limit=20").then(function(r){ return r.json(); })
    .then(function(data){
      (data.events || []).forEach(addEvent);
      refreshCharacter();
    });

  // Open the SSE stream for live updates.
  try {
    var es = new EventSource("/live/stream");
    es.addEventListener("open", function(){
      stat.textContent = "Live"; dot.classList.add("live");
    });
    es.onmessage = function(e){
      try { addEvent(JSON.parse(e.data)); } catch (err) {}
    };
    es.onerror = function(){
      stat.textContent = "Reconnecting..."; dot.classList.remove("live");
    };
  } catch (e) {
    stat.textContent = "SSE unavailable";
  }

  // Safety: poll every 5s for character refresh even if no events fired.
  setInterval(refreshCharacter, 5000);
})();
</script>
</body>
</html>
"""
