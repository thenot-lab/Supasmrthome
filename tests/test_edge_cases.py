"""Edge-case and robustness tests for the NeuroArousal system.

Covers:
  * Extreme parameter values
  * Zero-length stimulus
  * Near-boundary thresholds
  * Pillow fallback rendering path
  * NaN propagation guard
  * Alignment on flat signals
  * Narrative arc on very short simulations
"""

import json
import math
from unittest.mock import patch

import numpy as np
import pytest

from neuro_arousal.engine import (
    EmotionalDriveParams,
    NeuroArousalEngine,
    SimulationConfig,
    SubsystemParams,
    CouplingParams,
    null_stimulus,
    pulse_stimulus,
    periodic_stimulus,
    savage_config,
)
from neuro_arousal.digital_soul import (
    DigitalSoul,
    Regime,
    compute_alignment,
    compute_narrative_arc,
)
from neuro_arousal.multimodal import (
    compute_appearance,
    render_character,
    _render_fallback,
    CharacterAppearance,
    _HAS_PIL,
)


# ---------------------------------------------------------------------------
# Extreme parameter values
# ---------------------------------------------------------------------------

class TestExtremeParameters:
    def test_very_small_epsilon(self):
        """Very small epsilon → very slow recovery; should not blow up."""
        cfg = SimulationConfig(
            t_max=50.0,
            soma=SubsystemParams(a=0.25, epsilon=0.0001, b=0.5),
            psyche=SubsystemParams(a=0.20, epsilon=0.0001, b=0.45),
        )
        engine = NeuroArousalEngine(cfg)
        engine.set_initial_conditions(0.1, 0.0, 0.1, 0.0)
        results = engine.run()
        assert not np.any(np.isnan(results["u1"]))
        assert not np.any(np.isnan(results["v1"]))

    def test_very_large_coupling(self):
        """Large coupling strengths; trajectory should remain finite."""
        cfg = SimulationConfig(
            t_max=30.0,
            coupling=CouplingParams(c12=0.9, c21=0.9, kappa=50.0),
        )
        engine = NeuroArousalEngine(cfg)
        engine.set_initial_conditions(0.5, 0.0, 0.5, 0.0)
        results = engine.run()
        assert np.all(np.isfinite(results["u1"]))
        assert np.all(np.isfinite(results["u2"]))

    def test_threshold_near_zero(self):
        """a close to 0 (very excitable system)."""
        cfg = SimulationConfig(
            t_max=50.0,
            soma=SubsystemParams(a=0.01, epsilon=0.01, b=0.5),
        )
        engine = NeuroArousalEngine(cfg)
        engine.set_initial_conditions(0.05, 0.0, 0.0, 0.0)
        results = engine.run()
        assert np.all(np.isfinite(results["u1"]))

    def test_threshold_near_one(self):
        """a close to 1 (barely excitable)."""
        cfg = SimulationConfig(
            t_max=50.0,
            soma=SubsystemParams(a=0.99, epsilon=0.01, b=0.5),
        )
        engine = NeuroArousalEngine(cfg)
        engine.set_initial_conditions(0.0, 0.0, 0.0, 0.0)
        results = engine.run()
        assert np.all(np.isfinite(results["u1"]))

    def test_zero_coupling_delay(self):
        """tau close to zero (minimal delay)."""
        cfg = SimulationConfig(
            t_max=50.0,
            coupling=CouplingParams(tau=0.05),
        )
        engine = NeuroArousalEngine(cfg)
        engine.set_initial_conditions(0.1, 0.0, 0.1, 0.0)
        results = engine.run()
        assert np.all(np.isfinite(results["u1"]))

    def test_very_large_delay(self):
        """Large delay; ring buffer handles gracefully."""
        cfg = SimulationConfig(
            t_max=100.0,
            coupling=CouplingParams(tau=50.0),
        )
        engine = NeuroArousalEngine(cfg)
        engine.set_initial_conditions(0.1, 0.0, 0.1, 0.0)
        results = engine.run()
        assert np.all(np.isfinite(results["u1"]))

    def test_max_emotional_drive(self):
        """E_u=100, E_v=100 — maximum emotional drive."""
        cfg = SimulationConfig(
            t_max=50.0,
            emotion=EmotionalDriveParams(E_u=100.0, E_v=100.0, E_v0=0.5),
        )
        engine = NeuroArousalEngine(cfg)
        engine.set_initial_conditions(0.0, 0.0, 0.0, 0.0)
        results = engine.run()
        assert np.all(np.isfinite(results["u1"]))
        assert np.all(np.isfinite(results["u2"]))

    def test_zero_emotional_drive(self):
        """E_u=0, E_v=0 — no emotional modulation."""
        cfg = SimulationConfig(
            t_max=50.0,
            emotion=EmotionalDriveParams(E_u=0.0, E_v=0.0, E_v0=0.0),
        )
        engine = NeuroArousalEngine(cfg)
        engine.set_initial_conditions(0.0, 0.0, 0.0, 0.0)
        results = engine.run()
        assert np.all(np.isfinite(results["u1"]))


# ---------------------------------------------------------------------------
# Zero-length and edge-case stimuli
# ---------------------------------------------------------------------------

class TestStimulusEdgeCases:
    def test_zero_duration_pulse(self):
        """A pulse with zero duration should have no effect."""
        stim = pulse_stimulus(10.0, 0.0, 1.0)
        assert stim(10.0) == 0.0
        assert stim(9.99) == 0.0

    def test_zero_amplitude_pulse(self):
        """Zero amplitude pulse is equivalent to no stimulus."""
        stim = pulse_stimulus(10.0, 5.0, 0.0)
        assert stim(12.0) == 0.0

    def test_zero_amplitude_periodic(self):
        """Zero amplitude periodic is equivalent to no stimulus."""
        stim = periodic_stimulus(20.0, 3.0, 0.0)
        assert stim(1.0) == 0.0

    def test_very_short_period_periodic(self):
        """Very short period should still function."""
        stim = periodic_stimulus(0.1, 0.05, 1.0)
        # Should alternate rapidly
        assert isinstance(stim(0.01), float)

    def test_negative_amplitude_pulse(self):
        """Negative amplitude (inhibitory) should work."""
        stim = pulse_stimulus(5.0, 2.0, -0.5)
        assert stim(6.0) == -0.5

    def test_stimulus_runs_in_engine(self):
        """Engine handles zero-duration stimulus without error."""
        cfg = SimulationConfig(t_max=30.0)
        engine = NeuroArousalEngine(cfg)
        engine.set_initial_conditions()
        stim = pulse_stimulus(10.0, 0.0, 1.0)
        results = engine.run(I1_func=stim)
        assert np.all(np.isfinite(results["u1"]))


# ---------------------------------------------------------------------------
# Alignment edge cases
# ---------------------------------------------------------------------------

class TestAlignmentEdgeCases:
    def test_alignment_flat_signals(self):
        """Both channels constant → coherence should be 0."""
        n = 500
        results = {
            "time": np.linspace(0, 10, n),
            "u1": np.zeros(n),
            "u2": np.zeros(n),
            "v1": np.zeros(n),
            "v2": np.zeros(n),
            "soma_energy": np.zeros(n),
            "psyche_energy": np.zeros(n),
            "coupling_flux": np.zeros(n),
        }
        alignment = compute_alignment(results)
        assert alignment.coherence_index == 0.0
        assert alignment.cross_correlation == 0.0
        assert "quiescent" in alignment.interpretation.lower()

    def test_alignment_identical_signals(self):
        """Identical channels → perfect correlation."""
        n = 500
        t = np.linspace(0, 20, n)
        sig = np.sin(t * 2)
        results = {
            "time": t,
            "u1": sig,
            "u2": sig.copy(),
            "v1": np.zeros(n),
            "v2": np.zeros(n),
            "soma_energy": sig ** 2 * 0.5,
            "psyche_energy": sig ** 2 * 0.5,
            "coupling_flux": np.zeros(n),
        }
        alignment = compute_alignment(results)
        assert alignment.coherence_index > 0.9

    def test_alignment_anticorrelated(self):
        """Opposite channels."""
        n = 500
        t = np.linspace(0, 20, n)
        sig = np.sin(t * 2)
        results = {
            "time": t,
            "u1": sig,
            "u2": -sig,
            "v1": np.zeros(n),
            "v2": np.zeros(n),
            "soma_energy": sig ** 2 * 0.5,
            "psyche_energy": sig ** 2 * 0.5,
            "coupling_flux": np.zeros(n),
        }
        alignment = compute_alignment(results)
        # Should detect anti-correlation
        assert alignment.coherence_index > 0.9
        assert alignment.cross_correlation < 0


# ---------------------------------------------------------------------------
# Narrative arc edge cases
# ---------------------------------------------------------------------------

class TestArcEdgeCases:
    def test_arc_very_short_simulation(self):
        """Short simulation should still produce a valid arc."""
        cfg = SimulationConfig(t_max=5.0, dt=0.05)
        engine = NeuroArousalEngine(cfg)
        engine.set_initial_conditions(0.1, 0.0, 0.1, 0.0)
        results = engine.run(I1_func=pulse_stimulus(1.0, 1.0, 0.5))
        arc = compute_narrative_arc(results)
        assert arc is not None
        assert arc.climax_time >= 0
        assert len(arc.tension_curve) == len(results["time"])

    def test_arc_flat_simulation(self):
        """Flat (no activity) simulation should produce valid arc."""
        cfg = SimulationConfig(
            t_max=20.0,
            emotion=EmotionalDriveParams(E_u=0.0, E_v=50.0, E_v0=0.0),
        )
        engine = NeuroArousalEngine(cfg)
        engine.set_initial_conditions(0.0, 0.0, 0.0, 0.0)
        results = engine.run()
        arc = compute_narrative_arc(results)
        assert arc is not None
        assert isinstance(arc.arc_summary, str)


# ---------------------------------------------------------------------------
# Snapshot serialisation edge cases
# ---------------------------------------------------------------------------

class TestSnapshotEdgeCases:
    def test_snapshot_step_negative_clamped(self):
        """Negative step should be clamped to 0."""
        engine = NeuroArousalEngine(SimulationConfig(t_max=20.0))
        engine.set_initial_conditions()
        engine.run()
        snap = engine.snapshot_state(step=-10)
        assert snap["step"] == 0

    def test_snapshot_all_fields_serialisable(self):
        """Every field should be JSON-serialisable."""
        engine = NeuroArousalEngine(SimulationConfig(t_max=20.0))
        engine.set_initial_conditions(0.1, 0.0, 0.1, 0.0)
        engine.run()
        for step in [0, 5, 10, 100]:
            snap = engine.snapshot_state(step)
            s = json.dumps(snap)
            assert isinstance(s, str)
            parsed = json.loads(s)
            assert parsed["step"] == snap["step"]


# ---------------------------------------------------------------------------
# Multimodal / character edge cases
# ---------------------------------------------------------------------------

class TestMultimodalEdgeCases:
    def test_appearance_all_zeros(self):
        snap = {
            "u1": 0.0, "v1": 0.0, "u2": 0.0, "v2": 0.0,
            "soma_energy": 0.0, "psyche_energy": 0.0,
            "coupling_flux": 0.0, "savage_mode": False,
        }
        app = compute_appearance(snap, "QUIESCENT")
        assert app.expression == "calm"
        assert app.particle_count == 0
        assert app.tremor < 0.1

    def test_appearance_extreme_values(self):
        snap = {
            "u1": 10.0, "v1": 5.0, "u2": 10.0, "v2": 5.0,
            "soma_energy": 62.5, "psyche_energy": 62.5,
            "coupling_flux": 5.0, "savage_mode": True,
        }
        app = compute_appearance(snap, "CHAOTIC")
        assert app.expression == "chaotic"
        assert app.eye_openness == 1.0
        # Colours should be clamped to valid RGB
        for c in app.body_colour:
            assert 0 <= c <= 255
        for c in app.aura_colour:
            assert 0 <= c <= 255

    def test_appearance_unknown_regime(self):
        """Unknown regime string falls back gracefully."""
        snap = {
            "u1": 0.3, "v1": 0.1, "u2": 0.2, "v2": 0.05,
            "soma_energy": 0.05, "psyche_energy": 0.02,
            "coupling_flux": 0.01, "savage_mode": False,
        }
        app = compute_appearance(snap, "UNKNOWN_REGIME")
        assert isinstance(app.expression, str)
        assert 0 <= app.eye_openness <= 1.0

    def test_render_character_small_size(self):
        """Rendering at very small dimensions should not crash."""
        snap = {
            "u1": 0.1, "v1": 0.0, "u2": 0.1, "v2": 0.0,
            "soma_energy": 0.005, "psyche_energy": 0.005,
            "coupling_flux": 0.0, "savage_mode": False,
        }
        app = compute_appearance(snap, "QUIESCENT")
        img_bytes = render_character(app, width=10, height=10)
        assert isinstance(img_bytes, bytes)
        assert len(img_bytes) > 0

    def test_render_fallback(self):
        """The numpy-only fallback renderer should produce valid PPM bytes."""
        snap = {
            "u1": 0.5, "v1": 0.1, "u2": 0.3, "v2": 0.05,
            "soma_energy": 0.13, "psyche_energy": 0.05,
            "coupling_flux": 0.02, "savage_mode": False,
        }
        app = compute_appearance(snap, "OSCILLATORY")
        ppm_bytes = _render_fallback(app, 50, 60, (15, 15, 25))
        assert isinstance(ppm_bytes, bytes)
        # PPM header should be present
        assert ppm_bytes.startswith(b"P6\n")
        assert b"50 60" in ppm_bytes[:30]

    def test_render_fallback_forced(self):
        """Simulate Pillow not being available."""
        snap = {
            "u1": 0.2, "v1": 0.0, "u2": 0.1, "v2": 0.0,
            "soma_energy": 0.02, "psyche_energy": 0.005,
            "coupling_flux": 0.0, "savage_mode": False,
        }
        app = compute_appearance(snap, "QUIESCENT")

        with patch("neuro_arousal.multimodal._HAS_PIL", False):
            img_bytes = render_character(app, width=80, height=100)
            assert isinstance(img_bytes, bytes)
            assert img_bytes.startswith(b"P6\n")


# ---------------------------------------------------------------------------
# Config validation edge cases
# ---------------------------------------------------------------------------

class TestValidationEdgeCases:
    def test_zero_tmax_raises(self):
        with pytest.raises(ValueError, match="t_max must be positive"):
            NeuroArousalEngine(SimulationConfig(t_max=0))

    def test_negative_tmax_raises(self):
        with pytest.raises(ValueError, match="t_max must be positive"):
            NeuroArousalEngine(SimulationConfig(t_max=-10))

    def test_zero_dt_raises(self):
        with pytest.raises(ValueError, match="dt must be positive"):
            NeuroArousalEngine(SimulationConfig(dt=0))

    def test_a_at_boundary_zero_raises(self):
        with pytest.raises(ValueError, match="soma.a must be in"):
            NeuroArousalEngine(SimulationConfig(
                soma=SubsystemParams(a=0.0)
            ))

    def test_a_at_boundary_one_raises(self):
        with pytest.raises(ValueError, match="soma.a must be in"):
            NeuroArousalEngine(SimulationConfig(
                soma=SubsystemParams(a=1.0)
            ))

    def test_negative_epsilon_raises(self):
        with pytest.raises(ValueError, match="soma.epsilon must be positive"):
            NeuroArousalEngine(SimulationConfig(
                soma=SubsystemParams(epsilon=-0.01)
            ))
