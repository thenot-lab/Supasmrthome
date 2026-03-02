"""
FastAPI backend for the NeuroArousal interactive exhibit.

Provides REST endpoints for:
  * listing / describing preset scenarios
  * running simulations (preset or custom)
  * retrieving nullcline data for phase-plane plots
"""

from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from neuro_arousal.digital_soul import DigitalSoul, Regime
from neuro_arousal.engine import (
    CouplingParams,
    SimulationConfig,
    SubsystemParams,
    null_stimulus,
    pulse_stimulus,
    periodic_stimulus,
)

# ---------------------------------------------------------------------------
# App and shared state
# ---------------------------------------------------------------------------

app = FastAPI(
    title="NeuroArousal Exhibit API",
    description=(
        "Interactive Blyuss-Kyrychko coupled excitable system simulation "
        "for museum demonstration."
    ),
    version="1.0.0",
)

soul = DigitalSoul()


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
    ic_u1: float = 0.0
    ic_v1: float = 0.0
    ic_u2: float = 0.0
    ic_v2: float = 0.0
    soma_stimulus: StimulusIn = Field(default_factory=StimulusIn)
    psyche_stimulus: StimulusIn = Field(default_factory=StimulusIn)


class RegimeOut(BaseModel):
    soma_regime: str
    psyche_regime: str
    coupled_regime: str
    soma_spike_count: int
    psyche_spike_count: int
    mean_coupling_flux: float
    description: str


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
    """Downsample a numpy array to at most *max_points* for JSON transfer."""
    if len(arr) <= max_points:
        return arr.tolist()
    step = max(1, len(arr) // max_points)
    return arr[::step].tolist()


def _results_to_out(results, report) -> SimulationOut:
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
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "service": "NeuroArousal Exhibit API",
        "docs": "/docs",
        "scenarios": soul.scenario_names,
    }


@app.get("/scenarios", response_model=list[str])
def list_scenarios():
    """List available preset scenario keys."""
    return soul.scenario_names


@app.get("/scenarios/{name}", response_model=ScenarioInfoOut)
def get_scenario(name: str):
    """Describe a preset scenario."""
    if name not in soul.scenarios:
        raise HTTPException(404, f"Unknown scenario: {name}")
    return ScenarioInfoOut(**soul.get_scenario_info(name))


@app.post("/run/scenario/{name}", response_model=SimulationOut)
def run_scenario(name: str):
    """Run a preset scenario and return full time-series + report."""
    try:
        results, report = soul.run_scenario(name)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    return _results_to_out(results, report)


@app.post("/run/custom", response_model=SimulationOut)
def run_custom(req: CustomRunRequest):
    """Run a simulation with fully custom parameters."""
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
    return _results_to_out(results, report)


@app.get("/nullclines", response_model=NullclineOut)
def get_nullclines(
    soma_a: Annotated[float, Query(gt=0, lt=1)] = 0.25,
    soma_b: float = 0.5,
    psyche_a: Annotated[float, Query(gt=0, lt=1)] = 0.20,
    psyche_b: float = 0.45,
):
    """Compute nullclines for the given parameters (for phase-plane overlay)."""
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
