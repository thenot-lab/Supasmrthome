"""
DigitalSoul — High-level agent that interprets excitable system dynamics.

Wraps the NeuroArousalEngine to provide:
  * regime classification (quiescent, excitable, oscillatory, bistable)
  * narrative descriptions for museum exhibit visitors
  * preset scenario management
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable

import numpy as np
from numpy.typing import NDArray

from neuro_arousal.engine import (
    CouplingParams,
    NeuroArousalEngine,
    SimulationConfig,
    SubsystemParams,
    null_stimulus,
    periodic_stimulus,
    pulse_stimulus,
)


# ---------------------------------------------------------------------------
# Regime classification
# ---------------------------------------------------------------------------

class Regime(Enum):
    QUIESCENT = auto()      # resting, sub-threshold activity
    EXCITABLE = auto()      # single spike then return to rest
    OSCILLATORY = auto()    # sustained limit-cycle oscillations
    BISTABLE = auto()       # coexisting rest and oscillatory attractors
    CHAOTIC = auto()        # irregular, sensitive to initial conditions


@dataclass(frozen=True)
class RegimeReport:
    """Summary of dynamical regime for a simulation run."""
    soma_regime: Regime
    psyche_regime: Regime
    coupled_regime: Regime
    soma_spike_count: int
    psyche_spike_count: int
    mean_coupling_flux: float
    description: str


# ---------------------------------------------------------------------------
# Preset scenarios
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Scenario:
    """A named parameter + stimulus configuration for exhibit use."""
    name: str
    description: str
    config: SimulationConfig
    ic: tuple[float, float, float, float]   # (u1, v1, u2, v2)
    soma_stimulus_factory: Callable[[], Callable[[float], float]]
    psyche_stimulus_factory: Callable[[], Callable[[float], float]]


def _default_scenarios() -> dict[str, Scenario]:
    return {
        "resting_state": Scenario(
            name="Resting State",
            description=(
                "Both subsystems sit at a stable fixed point. "
                "Small perturbations decay — the system is excitable but quiet."
            ),
            config=SimulationConfig(),
            ic=(0.05, 0.0, 0.05, 0.0),
            soma_stimulus_factory=lambda: null_stimulus,
            psyche_stimulus_factory=lambda: null_stimulus,
        ),
        "single_soma_pulse": Scenario(
            name="Single SOMA Pulse",
            description=(
                "A brief current injection into the somatic subsystem triggers "
                "a single action-potential-like excursion. Watch how the pulse "
                "propagates through the coupling into the PSYCHE channel."
            ),
            config=SimulationConfig(t_max=150.0),
            ic=(0.0, 0.0, 0.0, 0.0),
            soma_stimulus_factory=lambda: pulse_stimulus(20.0, 3.0, 0.5),
            psyche_stimulus_factory=lambda: null_stimulus,
        ),
        "dual_oscillation": Scenario(
            name="Dual Oscillation",
            description=(
                "Stronger coupling and a lower excitability threshold push "
                "both populations into sustained oscillation — a limit cycle. "
                "Notice the phase lag introduced by the coupling delay τ."
            ),
            config=SimulationConfig(
                t_max=300.0,
                soma=SubsystemParams(a=0.13, epsilon=0.01, b=0.5),
                psyche=SubsystemParams(a=0.10, epsilon=0.008, b=0.45),
                coupling=CouplingParams(c12=0.25, c21=0.20, tau=8.0),
            ),
            ic=(0.1, 0.0, 0.05, 0.0),
            soma_stimulus_factory=lambda: null_stimulus,
            psyche_stimulus_factory=lambda: null_stimulus,
        ),
        "periodic_drive": Scenario(
            name="Periodic Drive",
            description=(
                "A periodic stimulus is applied to the SOMA channel. "
                "Depending on the drive frequency, the coupled system may "
                "entrain 1:1, show sub-harmonic responses, or exhibit "
                "complex intermittent dynamics."
            ),
            config=SimulationConfig(
                t_max=400.0,
                coupling=CouplingParams(c12=0.18, c21=0.15, tau=6.0),
            ),
            ic=(0.0, 0.0, 0.0, 0.0),
            soma_stimulus_factory=lambda: periodic_stimulus(40.0, 3.0, 0.45),
            psyche_stimulus_factory=lambda: null_stimulus,
        ),
        "psyche_perturbation": Scenario(
            name="PSYCHE Perturbation",
            description=(
                "A strong pulse hits the cognitive/emotional subsystem. "
                "Observe the back-propagation into the somatic channel — "
                "an analogy for how sudden emotional events manifest as "
                "physiological arousal."
            ),
            config=SimulationConfig(t_max=200.0),
            ic=(0.0, 0.0, 0.0, 0.0),
            soma_stimulus_factory=lambda: null_stimulus,
            psyche_stimulus_factory=lambda: pulse_stimulus(30.0, 5.0, 0.6),
        ),
    }


# ---------------------------------------------------------------------------
# Spike detection utility
# ---------------------------------------------------------------------------

def _count_spikes(
    u: NDArray[np.float64], threshold: float = 0.5
) -> int:
    """Count upward threshold crossings in a fast-variable trace."""
    above = u > threshold
    crossings = np.diff(above.astype(int))
    return int(np.sum(crossings == 1))


def _classify_trace(u: NDArray[np.float64], threshold: float = 0.5) -> Regime:
    """Heuristic regime classification from a single trace."""
    spikes = _count_spikes(u, threshold)
    amp = float(np.max(u) - np.min(u))

    if spikes == 0:
        return Regime.QUIESCENT
    if spikes == 1:
        return Regime.EXCITABLE

    # Check regularity for oscillatory vs chaotic
    above = u > threshold
    crossings = np.where(np.diff(above.astype(int)) == 1)[0]
    if len(crossings) >= 3:
        intervals = np.diff(crossings)
        cv = float(np.std(intervals) / (np.mean(intervals) + 1e-12))
        if cv < 0.15:
            return Regime.OSCILLATORY
        if cv < 0.4:
            return Regime.BISTABLE
        return Regime.CHAOTIC

    return Regime.OSCILLATORY if spikes >= 2 else Regime.EXCITABLE


# ---------------------------------------------------------------------------
# Narrative generation
# ---------------------------------------------------------------------------

_REGIME_NARRATIVES: dict[Regime, str] = {
    Regime.QUIESCENT: (
        "The system rests at a stable equilibrium — like a calm pond. "
        "All perturbations fade away."
    ),
    Regime.EXCITABLE: (
        "A threshold-crossing stimulus triggers a single large excursion — "
        "an all-or-nothing spike, analogous to a single heartbeat or startle "
        "response."
    ),
    Regime.OSCILLATORY: (
        "Sustained rhythmic oscillations emerge — a limit cycle. This mirrors "
        "biological rhythms such as breathing, circadian cycles, or neural "
        "oscillations in sleep."
    ),
    Regime.BISTABLE: (
        "The system can sit in either of two stable states and switch between "
        "them. This bistability underlies phenomena like perceptual rivalry "
        "and decision-making hysteresis."
    ),
    Regime.CHAOTIC: (
        "Irregular, seemingly random dynamics arise despite the deterministic "
        "equations. Small differences in starting conditions lead to "
        "dramatically different trajectories — sensitive dependence."
    ),
}


def _build_narrative(
    soma_regime: Regime,
    psyche_regime: Regime,
    mean_flux: float,
) -> str:
    parts: list[str] = []
    parts.append(f"SOMA channel: {_REGIME_NARRATIVES[soma_regime]}")
    parts.append(f"PSYCHE channel: {_REGIME_NARRATIVES[psyche_regime]}")

    if abs(mean_flux) < 0.01:
        parts.append(
            "The coupling flux is near zero — the two subsystems are "
            "roughly balanced in their mutual influence."
        )
    elif mean_flux > 0:
        parts.append(
            "Net coupling flux flows PSYCHE → SOMA, meaning the emotional/"
            "cognitive channel is currently driving physiological arousal."
        )
    else:
        parts.append(
            "Net coupling flux flows SOMA → PSYCHE, meaning physiological "
            "activation is feeding back into the cognitive/emotional channel."
        )

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# DigitalSoul agent
# ---------------------------------------------------------------------------

class DigitalSoul:
    """Orchestrating agent: runs simulations, classifies regimes, narrates.

    Designed to power both the FastAPI endpoints and the Gradio UI.
    """

    def __init__(self) -> None:
        self.scenarios = _default_scenarios()
        self._last_results: dict[str, NDArray[np.float64]] | None = None
        self._last_config: SimulationConfig | None = None

    @property
    def scenario_names(self) -> list[str]:
        return list(self.scenarios.keys())

    def run_scenario(self, name: str) -> tuple[dict[str, NDArray[np.float64]], RegimeReport]:
        """Run a named preset scenario and return (results, report)."""
        if name not in self.scenarios:
            raise ValueError(
                f"Unknown scenario '{name}'. "
                f"Available: {', '.join(self.scenarios.keys())}"
            )
        sc = self.scenarios[name]
        engine = NeuroArousalEngine(sc.config)
        engine.set_initial_conditions(*sc.ic)
        results = engine.run(
            I1_func=sc.soma_stimulus_factory(),
            I2_func=sc.psyche_stimulus_factory(),
        )
        report = self._analyse(results)
        self._last_results = results
        self._last_config = sc.config
        return results, report

    def run_custom(
        self,
        config: SimulationConfig,
        ic: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
        I1_func: Callable[[float], float] = null_stimulus,
        I2_func: Callable[[float], float] = null_stimulus,
    ) -> tuple[dict[str, NDArray[np.float64]], RegimeReport]:
        """Run with fully custom parameters and return (results, report)."""
        engine = NeuroArousalEngine(config)
        engine.set_initial_conditions(*ic)
        results = engine.run(I1_func, I2_func)
        report = self._analyse(results)
        self._last_results = results
        self._last_config = config
        return results, report

    def get_nullclines(
        self, config: SimulationConfig | None = None
    ) -> dict[str, NDArray[np.float64]]:
        """Compute nullclines for phase-plane display."""
        cfg = config or self._last_config or SimulationConfig()
        engine = NeuroArousalEngine(cfg)
        return engine.compute_nullclines()

    def get_scenario_info(self, name: str) -> dict[str, str]:
        sc = self.scenarios[name]
        cfg = sc.config
        return {
            "name": sc.name,
            "description": sc.description,
            "soma_a": str(cfg.soma.a),
            "psyche_a": str(cfg.psyche.a),
            "c12": str(cfg.coupling.c12),
            "c21": str(cfg.coupling.c21),
            "tau": str(cfg.coupling.tau),
        }

    # ----- internal analysis -----

    @staticmethod
    def _analyse(results: dict[str, NDArray[np.float64]]) -> RegimeReport:
        u1 = results["u1"]
        u2 = results["u2"]
        flux = results["coupling_flux"]

        soma_r = _classify_trace(u1)
        psyche_r = _classify_trace(u2)

        # Combined regime: take the "most dynamic" of the two
        hierarchy = [
            Regime.QUIESCENT, Regime.EXCITABLE,
            Regime.OSCILLATORY, Regime.BISTABLE, Regime.CHAOTIC,
        ]
        coupled_r = hierarchy[max(
            hierarchy.index(soma_r), hierarchy.index(psyche_r)
        )]

        mean_flux = float(np.mean(flux))
        description = _build_narrative(soma_r, psyche_r, mean_flux)

        return RegimeReport(
            soma_regime=soma_r,
            psyche_regime=psyche_r,
            coupled_regime=coupled_r,
            soma_spike_count=_count_spikes(u1),
            psyche_spike_count=_count_spikes(u2),
            mean_coupling_flux=mean_flux,
            description=description,
        )
