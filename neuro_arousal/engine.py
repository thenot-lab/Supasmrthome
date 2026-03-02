"""
NeuroArousalEngine — Mathematical core for coupled excitable system simulation.

Implements a Blyuss-Kyrychko-type coupled excitable system with two interacting
subsystems (SOMA and PSYCHE), each modelled as a FitzHugh-Nagumo oscillator
with sigmoidal inter-population delay coupling.

Model equations
===============

SOMA subsystem (physiological arousal):
    du₁/dt = u₁(1 - u₁)(u₁ - a₁) - v₁ + c₁₂·S(u₂(t - τ)) + I₁(t)
    dv₁/dt = ε₁(b₁·u₁ - v₁)

PSYCHE subsystem (cognitive/emotional arousal):
    du₂/dt = u₂(1 - u₂)(u₂ - a₂) - v₂ + c₂₁·S(u₁(t - τ)) + I₂(t)
    dv₂/dt = ε₂(b₂·u₂ - v₂)

where:
    u — fast activator variable (membrane-potential analogue)
    v — slow recovery variable (adaptation analogue)
    a — excitability threshold (0 < a < 1)
    ε — timescale separation (small ε → slow recovery)
    b — recovery gain
    c₁₂, c₂₁ — inter-population coupling strengths
    S(x) = 1 / (1 + exp(-κ(x - θ))) — sigmoidal coupling function
    τ — coupling delay
    I₁, I₂ — external stimulus currents

References
----------
Blyuss, K. B. & Kyrychko, Y. N. (2010). Stability and bifurcations in an
    epidemic model with varying immunity period. *Bull. Math. Biol.*, 72, 490–505.
FitzHugh, R. (1961). Impulses and physiological states in theoretical models of
    nerve membrane. *Biophys. J.*, 1(6), 445–466.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from numpy.typing import NDArray


# ---------------------------------------------------------------------------
# Parameter containers
# ---------------------------------------------------------------------------

@dataclass
class SubsystemParams:
    """Parameters for a single FitzHugh-Nagumo subsystem."""
    a: float = 0.25          # excitability threshold
    epsilon: float = 0.01    # timescale separation
    b: float = 0.5           # recovery gain


@dataclass
class CouplingParams:
    """Parameters for sigmoidal inter-population coupling."""
    c12: float = 0.15        # PSYCHE → SOMA coupling strength
    c21: float = 0.12        # SOMA → PSYCHE coupling strength
    kappa: float = 10.0      # sigmoid steepness
    theta: float = 0.3       # sigmoid midpoint
    tau: float = 5.0         # coupling delay (time units)


@dataclass
class SimulationConfig:
    """Top-level simulation configuration."""
    dt: float = 0.05         # integration timestep
    t_max: float = 200.0     # total simulation time
    soma: SubsystemParams = field(default_factory=SubsystemParams)
    psyche: SubsystemParams = field(default_factory=lambda: SubsystemParams(
        a=0.20, epsilon=0.008, b=0.45
    ))
    coupling: CouplingParams = field(default_factory=CouplingParams)


# ---------------------------------------------------------------------------
# Stimulus helpers
# ---------------------------------------------------------------------------

def null_stimulus(t: float) -> float:
    """Zero external stimulus."""
    return 0.0


def pulse_stimulus(
    onset: float, duration: float, amplitude: float
) -> Callable[[float], float]:
    """Return a rectangular pulse stimulus function."""
    def _stim(t: float) -> float:
        return amplitude if onset <= t < onset + duration else 0.0
    return _stim


def periodic_stimulus(
    period: float, duration: float, amplitude: float
) -> Callable[[float], float]:
    """Return a periodic rectangular pulse stimulus function."""
    def _stim(t: float) -> float:
        phase = t % period
        return amplitude if phase < duration else 0.0
    return _stim


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

class NeuroArousalEngine:
    """Numerical integrator for the coupled SOMA-PSYCHE excitable system.

    Uses Euler integration with a ring-buffer history for delay coupling,
    chosen for clarity and suitability in interactive museum demonstrations.
    """

    # State vector layout: [u1, v1, u2, v2]
    _U1, _V1, _U2, _V2 = 0, 1, 2, 3

    def __init__(self, config: SimulationConfig | None = None) -> None:
        self.config = config or SimulationConfig()
        self._validate_config()

        self._n_steps = int(np.ceil(self.config.t_max / self.config.dt))
        self._delay_steps = max(1, int(round(
            self.config.coupling.tau / self.config.dt
        )))

        # Pre-allocate trajectory storage
        self.time: NDArray[np.float64] = np.linspace(
            0, self.config.t_max, self._n_steps + 1
        )
        self.trajectory: NDArray[np.float64] = np.zeros(
            (self._n_steps + 1, 4), dtype=np.float64
        )

        # Ring buffer for delay look-up (stores full state vectors)
        self._ring_size = self._delay_steps + 1
        self._ring: NDArray[np.float64] = np.zeros(
            (self._ring_size, 4), dtype=np.float64
        )
        self._ring_idx = 0

    # ----- validation -----

    def _validate_config(self) -> None:
        cfg = self.config
        if cfg.dt <= 0:
            raise ValueError("dt must be positive")
        if cfg.t_max <= 0:
            raise ValueError("t_max must be positive")
        for label, sub in [("soma", cfg.soma), ("psyche", cfg.psyche)]:
            if not (0 < sub.a < 1):
                raise ValueError(f"{label}.a must be in (0, 1), got {sub.a}")
            if sub.epsilon <= 0:
                raise ValueError(f"{label}.epsilon must be positive")

    # ----- sigmoid -----

    def _sigmoid(self, x: float) -> float:
        cp = self.config.coupling
        z = cp.kappa * (x - cp.theta)
        # Clip to avoid overflow in exp
        z = np.clip(z, -500.0, 500.0)
        return 1.0 / (1.0 + np.exp(-z))

    # ----- FHN cubic nullcline -----

    @staticmethod
    def _cubic(u: float, a: float) -> float:
        """Cubic reaction term: u(1-u)(u-a)."""
        return u * (1.0 - u) * (u - a)

    # ----- delayed state look-up -----

    def _delayed_state(self) -> NDArray[np.float64]:
        idx = (self._ring_idx - self._delay_steps) % self._ring_size
        return self._ring[idx]

    # ----- right-hand side -----

    def _rhs(
        self,
        state: NDArray[np.float64],
        delayed: NDArray[np.float64],
        I1: float,
        I2: float,
    ) -> NDArray[np.float64]:
        u1, v1, u2, v2 = state
        s = self.config.soma
        p = self.config.psyche
        cp = self.config.coupling

        du1 = (self._cubic(u1, s.a) - v1
               + cp.c12 * self._sigmoid(delayed[self._U2]) + I1)
        dv1 = s.epsilon * (s.b * u1 - v1)

        du2 = (self._cubic(u2, p.a) - v2
               + cp.c21 * self._sigmoid(delayed[self._U1]) + I2)
        dv2 = p.epsilon * (p.b * u2 - v2)

        return np.array([du1, dv1, du2, dv2])

    # ----- public interface -----

    def set_initial_conditions(
        self, u1: float = 0.0, v1: float = 0.0,
        u2: float = 0.0, v2: float = 0.0,
    ) -> None:
        """Set the state at t = 0 and fill the delay buffer."""
        ic = np.array([u1, v1, u2, v2], dtype=np.float64)
        self.trajectory[0] = ic
        self._ring[:] = ic
        self._ring_idx = 0

    def run(
        self,
        I1_func: Callable[[float], float] = null_stimulus,
        I2_func: Callable[[float], float] = null_stimulus,
    ) -> dict[str, NDArray[np.float64]]:
        """Integrate the full system and return results.

        Parameters
        ----------
        I1_func : callable
            External stimulus current for SOMA as a function of time.
        I2_func : callable
            External stimulus current for PSYCHE as a function of time.

        Returns
        -------
        dict with keys:
            "time", "u1", "v1", "u2", "v2",
            "soma_energy", "psyche_energy", "coupling_flux"
        """
        dt = self.config.dt

        for i in range(self._n_steps):
            t = self.time[i]
            state = self.trajectory[i]

            # Write current state into ring buffer
            self._ring[self._ring_idx % self._ring_size] = state
            delayed = self._delayed_state()

            I1 = I1_func(t)
            I2 = I2_func(t)

            # Euler step
            deriv = self._rhs(state, delayed, I1, I2)
            self.trajectory[i + 1] = state + dt * deriv

            self._ring_idx += 1

        return self._pack_results()

    def _pack_results(self) -> dict[str, NDArray[np.float64]]:
        t = self.time
        u1 = self.trajectory[:, self._U1]
        v1 = self.trajectory[:, self._V1]
        u2 = self.trajectory[:, self._U2]
        v2 = self.trajectory[:, self._V2]

        # Derived quantities for visualization
        soma_energy = 0.5 * (u1**2 + v1**2)
        psyche_energy = 0.5 * (u2**2 + v2**2)
        coupling_flux = np.array([
            self.config.coupling.c12 * self._sigmoid(u2_val)
            - self.config.coupling.c21 * self._sigmoid(u1_val)
            for u1_val, u2_val in zip(u1, u2)
        ])

        return {
            "time": t,
            "u1": u1, "v1": v1,
            "u2": u2, "v2": v2,
            "soma_energy": soma_energy,
            "psyche_energy": psyche_energy,
            "coupling_flux": coupling_flux,
        }

    def compute_nullclines(
        self, u_range: tuple[float, float] = (-0.5, 1.5), n_points: int = 300
    ) -> dict[str, NDArray[np.float64]]:
        """Compute cubic and linear nullclines for both subsystems.

        Useful for phase-plane overlays in the UI.
        """
        u = np.linspace(u_range[0], u_range[1], n_points)
        s = self.config.soma
        p = self.config.psyche

        return {
            "u": u,
            "soma_cubic": np.array([self._cubic(ui, s.a) for ui in u]),
            "soma_linear": s.b * u,
            "psyche_cubic": np.array([self._cubic(ui, p.a) for ui in u]),
            "psyche_linear": p.b * u,
        }
