"""
DigitalSoul — High-level agent that interprets excitable system dynamics.

Wraps the NeuroArousalEngine to provide:
  * regime classification (quiescent, excitable, oscillatory, bistable, chaotic)
  * narrative descriptions for museum exhibit visitors
  * alignment scoring (coherence between SOMA and PSYCHE channels)
  * narrative arc progression (tension → rising → climax → falling → resolution)
  * climax detection via energy / spike-rate peak analysis
  * preset scenario management
  * PEFT adapter catalogue for persona switching
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
    EmotionalDriveParams,
    NeuroArousalEngine,
    SimulationConfig,
    SubsystemParams,
    null_stimulus,
    periodic_stimulus,
    pulse_stimulus,
    savage_config,
)


# ---------------------------------------------------------------------------
# Regime classification
# ---------------------------------------------------------------------------

class Regime(Enum):
    QUIESCENT = auto()
    EXCITABLE = auto()
    OSCILLATORY = auto()
    BISTABLE = auto()
    CHAOTIC = auto()


# ---------------------------------------------------------------------------
# Narrative arc phases
# ---------------------------------------------------------------------------

class ArcPhase(Enum):
    EXPOSITION = auto()      # initial calm / sub-threshold
    RISING_ACTION = auto()   # energy building
    CLIMAX = auto()          # peak energy / spike burst
    FALLING_ACTION = auto()  # energy dissipating
    RESOLUTION = auto()      # return toward equilibrium


# ---------------------------------------------------------------------------
# PEFT adapter catalogue
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PEFTAdapter:
    """Describes a personality adapter that modulates narrative style."""
    name: str
    label: str
    description: str
    narrative_tone: str        # adjective for narrative colouring
    coupling_scale: float      # multiplier on coupling strengths
    arousal_bias: float        # added to arousal drive


PEFT_ADAPTERS: dict[str, PEFTAdapter] = {
    "default": PEFTAdapter(
        name="default",
        label="Museum Default",
        description="Balanced, educational tone for general audiences.",
        narrative_tone="measured",
        coupling_scale=1.0,
        arousal_bias=0.0,
    ),
    "poetic": PEFTAdapter(
        name="poetic",
        label="Poetic Narrator",
        description="Lyrical language with metaphorical descriptions.",
        narrative_tone="lyrical",
        coupling_scale=1.1,
        arousal_bias=5.0,
    ),
    "clinical": PEFTAdapter(
        name="clinical",
        label="Clinical Observer",
        description="Precise, technical language for advanced visitors.",
        narrative_tone="precise",
        coupling_scale=1.0,
        arousal_bias=0.0,
    ),
    "dramatic": PEFTAdapter(
        name="dramatic",
        label="Dramatic Storyteller",
        description="Heightened emotional language with narrative suspense.",
        narrative_tone="vivid",
        coupling_scale=1.2,
        arousal_bias=10.0,
    ),
}


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

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


@dataclass(frozen=True)
class AlignmentScore:
    """Quantifies coherence between SOMA and PSYCHE channels."""
    cross_correlation: float   # peak normalised cross-correlation [-1, 1]
    phase_lag: float           # time-lag at peak cross-correlation
    coherence_index: float     # 0–1 index (1 = perfectly synchronised)
    interpretation: str


@dataclass(frozen=True)
class NarrativeArc:
    """Full narrative arc decomposition of a simulation run."""
    phases: list[tuple[float, float, ArcPhase]]   # (t_start, t_end, phase)
    climax_time: float
    climax_energy: float
    peak_spike_rate: float
    arc_summary: str
    tension_curve: NDArray[np.float64]  # same length as time array


# ---------------------------------------------------------------------------
# Preset scenarios
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Scenario:
    """A named parameter + stimulus configuration for exhibit use."""
    name: str
    description: str
    config: SimulationConfig
    ic: tuple[float, float, float, float]
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
            config=SimulationConfig(
                emotion=EmotionalDriveParams(E_u=0.0, E_v=50.0, E_v0=0.0),
            ),
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
        "savage_burst": Scenario(
            name="Savage Burst",
            description=(
                "Savage Mode engaged — high excitability (ε=0.05, a=0.5, b=0.1) "
                "with amplified coupling drives the system into chaotic bursting. "
                "E_v0=0.2 biases the PSYCHE channel toward sustained activation."
            ),
            config=savage_config(t_max=300.0),
            ic=(0.1, 0.0, 0.15, 0.0),
            soma_stimulus_factory=lambda: pulse_stimulus(10.0, 5.0, 0.7),
            psyche_stimulus_factory=lambda: pulse_stimulus(15.0, 5.0, 0.6),
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

    if spikes == 0:
        return Regime.QUIESCENT
    if spikes == 1:
        return Regime.EXCITABLE

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

_TONE_MODIFIERS: dict[str, dict[Regime, str]] = {
    "lyrical": {
        Regime.QUIESCENT: "A whisper of stillness, the pond's mirror unbroken.",
        Regime.EXCITABLE: "A single bolt of lightning — then silence returns.",
        Regime.OSCILLATORY: "A heartbeat in code: rise, fall, rise, fall — eternal.",
        Regime.BISTABLE: "Two worlds coexist, the system dancing between realities.",
        Regime.CHAOTIC: "A tempest of numbers, beautiful in its unpredictability.",
    },
    "precise": {
        Regime.QUIESCENT: "Sub-threshold dynamics; asymptotically stable fixed point.",
        Regime.EXCITABLE: "Single excitable excursion; Type II excitability.",
        Regime.OSCILLATORY: "Stable limit-cycle oscillation; Hopf bifurcation regime.",
        Regime.BISTABLE: "Coexisting attractors; hysteretic switching observed.",
        Regime.CHAOTIC: "Positive Lyapunov exponent regime; deterministic chaos.",
    },
    "vivid": {
        Regime.QUIESCENT: "DEAD CALM. Not a ripple. The beast sleeps.",
        Regime.EXCITABLE: "ONE MASSIVE SPIKE erupts — then crashes to silence!",
        Regime.OSCILLATORY: "RELENTLESS RHYTHM — the system is ALIVE and pumping!",
        Regime.BISTABLE: "TWO FATES hang in the balance — which will dominate?",
        Regime.CHAOTIC: "PURE CHAOS — the system has gone FERAL!",
    },
}


def _build_narrative(
    soma_regime: Regime,
    psyche_regime: Regime,
    mean_flux: float,
    tone: str = "measured",
) -> str:
    parts: list[str] = []

    if tone in _TONE_MODIFIERS:
        parts.append(f"SOMA channel: {_TONE_MODIFIERS[tone][soma_regime]}")
        parts.append(f"PSYCHE channel: {_TONE_MODIFIERS[tone][psyche_regime]}")
    else:
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
# Alignment scoring
# ---------------------------------------------------------------------------

def compute_alignment(
    results: dict[str, NDArray[np.float64]],
) -> AlignmentScore:
    """Compute coherence / alignment between SOMA and PSYCHE channels."""
    u1 = results["u1"]
    u2 = results["u2"]
    dt_idx = 1  # we work in index space

    # Normalise
    u1_n = u1 - np.mean(u1)
    u2_n = u2 - np.mean(u2)

    norm1 = np.linalg.norm(u1_n)
    norm2 = np.linalg.norm(u2_n)

    if norm1 < 1e-12 or norm2 < 1e-12:
        return AlignmentScore(
            cross_correlation=0.0,
            phase_lag=0.0,
            coherence_index=0.0,
            interpretation="Both channels are quiescent — no meaningful alignment.",
        )

    # Cross-correlation via FFT
    n = len(u1_n)
    fft1 = np.fft.fft(u1_n, n=2 * n)
    fft2 = np.fft.fft(u2_n, n=2 * n)
    xcorr = np.fft.ifft(fft1 * np.conj(fft2)).real
    xcorr = xcorr / (norm1 * norm2)

    # Find peak
    peak_idx = int(np.argmax(np.abs(xcorr[:n])))
    peak_val = float(xcorr[peak_idx])
    phase_lag = float(peak_idx) * dt_idx

    # Coherence index: abs of peak cross-correlation, clamped to [0, 1]
    coherence = min(1.0, abs(peak_val))

    if coherence > 0.7:
        interp = (
            f"Strong alignment (coherence={coherence:.2f}). "
            f"SOMA and PSYCHE are highly synchronised with "
            f"a phase lag of ~{phase_lag:.0f} steps."
        )
    elif coherence > 0.3:
        interp = (
            f"Moderate alignment (coherence={coherence:.2f}). "
            f"Partial coupling effects visible."
        )
    else:
        interp = (
            f"Weak alignment (coherence={coherence:.2f}). "
            f"Channels are largely independent or in different regimes."
        )

    return AlignmentScore(
        cross_correlation=round(peak_val, 4),
        phase_lag=round(phase_lag, 2),
        coherence_index=round(coherence, 4),
        interpretation=interp,
    )


# ---------------------------------------------------------------------------
# Narrative arc analysis
# ---------------------------------------------------------------------------

def _compute_tension_curve(results: dict[str, NDArray[np.float64]]) -> NDArray[np.float64]:
    """Compute a tension curve from combined energy and flux."""
    se = results["soma_energy"]
    pe = results["psyche_energy"]
    flux = np.abs(results["coupling_flux"])
    # Tension = total energy + coupling activity
    raw = se + pe + flux
    # Smooth with a moving average
    window = min(51, len(raw) // 10)
    if window < 3:
        return raw
    kernel = np.ones(window) / window
    return np.convolve(raw, kernel, mode="same")


def compute_narrative_arc(
    results: dict[str, NDArray[np.float64]],
) -> NarrativeArc:
    """Decompose a simulation into narrative arc phases."""
    t = results["time"]
    tension = _compute_tension_curve(results)
    n = len(t)

    # Climax = peak of tension curve
    climax_idx = int(np.argmax(tension))
    climax_time = float(t[climax_idx])
    climax_energy = float(tension[climax_idx])

    # Spike rate in a rolling window
    u_combined = results["u1"] + results["u2"]
    window_size = max(1, n // 20)
    spike_rate = np.zeros(n)
    for i in range(n):
        lo = max(0, i - window_size // 2)
        hi = min(n, i + window_size // 2)
        segment = u_combined[lo:hi]
        above = segment > 0.5
        crossings = np.diff(above.astype(int))
        spike_rate[i] = float(np.sum(crossings == 1))
    peak_spike_rate = float(np.max(spike_rate))

    # Partition into 5 phases based on tension curve quartiles
    tension_max = float(np.max(tension)) if np.max(tension) > 1e-12 else 1.0
    normalised = tension / tension_max

    phases: list[tuple[float, float, ArcPhase]] = []

    # Find exposition: from start until tension exceeds 20% of peak
    rise_start = 0
    for i in range(n):
        if normalised[i] > 0.2:
            rise_start = i
            break

    # Rising action: from rise_start to climax
    # Falling action: from climax until tension drops below 20%
    fall_end = n - 1
    for i in range(climax_idx, n):
        if normalised[i] < 0.2:
            fall_end = i
            break

    # Build phase list
    if rise_start > 0:
        phases.append((float(t[0]), float(t[rise_start]), ArcPhase.EXPOSITION))

    if rise_start < climax_idx:
        phases.append((float(t[rise_start]), float(t[climax_idx]), ArcPhase.RISING_ACTION))

    # Climax is a point neighbourhood
    climax_lo = max(0, climax_idx - n // 40)
    climax_hi = min(n - 1, climax_idx + n // 40)
    phases.append((float(t[climax_lo]), float(t[climax_hi]), ArcPhase.CLIMAX))

    if climax_idx < fall_end:
        phases.append((float(t[climax_idx]), float(t[fall_end]), ArcPhase.FALLING_ACTION))

    if fall_end < n - 1:
        phases.append((float(t[fall_end]), float(t[-1]), ArcPhase.RESOLUTION))

    # Summary
    phase_names = [p[2].name.replace("_", " ").title() for p in phases]
    arc_summary = (
        f"Narrative arc: {' → '.join(phase_names)}. "
        f"Climax at t={climax_time:.1f} with peak tension {climax_energy:.4f}. "
        f"Peak spike rate: {peak_spike_rate:.0f} spikes/window."
    )

    return NarrativeArc(
        phases=phases,
        climax_time=round(climax_time, 2),
        climax_energy=round(climax_energy, 6),
        peak_spike_rate=round(peak_spike_rate, 2),
        arc_summary=arc_summary,
        tension_curve=tension,
    )


# ---------------------------------------------------------------------------
# DigitalSoul agent
# ---------------------------------------------------------------------------

class DigitalSoul:
    """Orchestrating agent: runs simulations, classifies regimes, narrates.

    Designed to power both the FastAPI endpoints and the Gradio UI.
    Now includes alignment scoring, narrative arc tracking, and PEFT
    adapter persona switching.
    """

    def __init__(self, adapter: str = "default") -> None:
        self.scenarios = _default_scenarios()
        self._last_results: dict[str, NDArray[np.float64]] | None = None
        self._last_config: SimulationConfig | None = None
        self._last_engine: NeuroArousalEngine | None = None
        self._last_report: RegimeReport | None = None
        self._last_alignment: AlignmentScore | None = None
        self._last_arc: NarrativeArc | None = None
        self.set_adapter(adapter)

    # ----- PEFT adapter -----

    def set_adapter(self, name: str) -> PEFTAdapter:
        if name not in PEFT_ADAPTERS:
            name = "default"
        self._adapter = PEFT_ADAPTERS[name]
        return self._adapter

    @property
    def adapter(self) -> PEFTAdapter:
        return self._adapter

    @staticmethod
    def available_adapters() -> list[dict[str, str]]:
        return [
            {"name": a.name, "label": a.label, "description": a.description}
            for a in PEFT_ADAPTERS.values()
        ]

    # ----- scenario listing -----

    @property
    def scenario_names(self) -> list[str]:
        return list(self.scenarios.keys())

    # ----- run preset -----

    def run_scenario(
        self, name: str
    ) -> tuple[dict[str, NDArray[np.float64]], RegimeReport]:
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
        self._store(engine, results, sc.config, report)
        return results, report

    # ----- run custom -----

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
        self._store(engine, results, config, report)
        return results, report

    # ----- accessors for last-run computed data -----

    def get_alignment(self) -> AlignmentScore | None:
        return self._last_alignment

    def get_arc(self) -> NarrativeArc | None:
        return self._last_arc

    def get_state_snapshot(self, step: int | None = None) -> dict | None:
        if self._last_engine is None:
            return None
        return self._last_engine.snapshot_state(step)

    def get_nullclines(
        self, config: SimulationConfig | None = None
    ) -> dict[str, NDArray[np.float64]]:
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

    # ----- internal helpers -----

    def _store(
        self,
        engine: NeuroArousalEngine,
        results: dict[str, NDArray[np.float64]],
        config: SimulationConfig,
        report: RegimeReport,
    ) -> None:
        self._last_engine = engine
        self._last_results = results
        self._last_config = config
        self._last_report = report
        self._last_alignment = compute_alignment(results)
        self._last_arc = compute_narrative_arc(results)

    def _analyse(self, results: dict[str, NDArray[np.float64]]) -> RegimeReport:
        u1 = results["u1"]
        u2 = results["u2"]
        flux = results["coupling_flux"]

        soma_r = _classify_trace(u1)
        psyche_r = _classify_trace(u2)

        hierarchy = [
            Regime.QUIESCENT, Regime.EXCITABLE,
            Regime.OSCILLATORY, Regime.BISTABLE, Regime.CHAOTIC,
        ]
        coupled_r = hierarchy[max(
            hierarchy.index(soma_r), hierarchy.index(psyche_r)
        )]

        mean_flux = float(np.mean(flux))
        tone = self._adapter.narrative_tone
        description = _build_narrative(soma_r, psyche_r, mean_flux, tone)

        return RegimeReport(
            soma_regime=soma_r,
            psyche_regime=psyche_r,
            coupled_regime=coupled_r,
            soma_spike_count=_count_spikes(u1),
            psyche_spike_count=_count_spikes(u2),
            mean_coupling_flux=mean_flux,
            description=description,
        )
