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

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
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

@app.post("/run/scenario/{name}", response_model=SimulationOut)
def run_scenario(
    name: str, adapter: str = "default",
    _user: str = Depends(get_current_user),
):
    soul.set_adapter(adapter)
    try:
        results, report = soul.run_scenario(name)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return _results_to_out(
        results, report, soul.get_alignment(), soul.get_arc()
    )


@app.post("/run/custom", response_model=SimulationOut)
def run_custom(req: CustomRunRequest, _user: str = Depends(get_current_user)):
    soul.set_adapter(req.adapter)

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
def set_adapter(name: str, _user: str = Depends(get_current_user)):
    if name not in PEFT_ADAPTERS:
        raise HTTPException(404, f"Unknown adapter: {name}")
    a = soul.set_adapter(name)
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
    return Response(content=png_bytes, media_type="image/png")
