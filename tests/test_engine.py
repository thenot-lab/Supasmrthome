"""Tests for NeuroArousalEngine and DigitalSoul."""

import numpy as np
import pytest

from neuro_arousal.engine import (
    CouplingParams,
    NeuroArousalEngine,
    SimulationConfig,
    SubsystemParams,
    null_stimulus,
    pulse_stimulus,
    periodic_stimulus,
)
from neuro_arousal.digital_soul import DigitalSoul, Regime


# ---------------------------------------------------------------------------
# Engine basics
# ---------------------------------------------------------------------------

class TestEngineConstruction:
    def test_default_config(self):
        engine = NeuroArousalEngine()
        assert engine.config.dt == 0.05
        assert engine.config.t_max == 200.0

    def test_custom_config(self):
        cfg = SimulationConfig(dt=0.01, t_max=50.0)
        engine = NeuroArousalEngine(cfg)
        assert engine.config.dt == 0.01
        assert len(engine.time) > 0

    def test_invalid_dt_raises(self):
        with pytest.raises(ValueError, match="dt must be positive"):
            NeuroArousalEngine(SimulationConfig(dt=-1))

    def test_invalid_threshold_raises(self):
        with pytest.raises(ValueError, match="soma.a must be in"):
            NeuroArousalEngine(SimulationConfig(
                soma=SubsystemParams(a=1.5)
            ))


class TestEngineRun:
    def test_resting_state_stays_near_zero(self):
        """With zero stimulus and small IC, trajectory should stay small."""
        engine = NeuroArousalEngine(SimulationConfig(t_max=100.0))
        engine.set_initial_conditions(0.01, 0.0, 0.01, 0.0)
        results = engine.run()

        assert results["u1"].shape == results["time"].shape
        # In resting state, u1 should not spike above 0.5
        assert np.max(np.abs(results["u1"])) < 0.6

    def test_pulse_triggers_spike(self):
        """A strong pulse should kick the activator above threshold."""
        engine = NeuroArousalEngine(SimulationConfig(t_max=100.0))
        engine.set_initial_conditions(0.0, 0.0, 0.0, 0.0)
        stim = pulse_stimulus(10.0, 3.0, 0.8)
        results = engine.run(I1_func=stim)

        # u1 should exhibit a spike
        assert np.max(results["u1"]) > 0.3

    def test_result_keys(self):
        engine = NeuroArousalEngine(SimulationConfig(t_max=50.0))
        engine.set_initial_conditions()
        results = engine.run()

        expected_keys = {
            "time", "u1", "v1", "u2", "v2",
            "soma_energy", "psyche_energy", "coupling_flux",
        }
        assert set(results.keys()) == expected_keys

    def test_energy_non_negative(self):
        engine = NeuroArousalEngine(SimulationConfig(t_max=50.0))
        engine.set_initial_conditions(0.1, 0.0, 0.1, 0.0)
        results = engine.run()

        assert np.all(results["soma_energy"] >= 0)
        assert np.all(results["psyche_energy"] >= 0)


class TestNullclines:
    def test_nullcline_shapes(self):
        engine = NeuroArousalEngine()
        nc = engine.compute_nullclines(n_points=100)
        assert nc["u"].shape == (100,)
        assert nc["soma_cubic"].shape == (100,)
        assert nc["soma_linear"].shape == (100,)

    def test_cubic_at_threshold(self):
        """At u=a, the cubic u(1-u)(u-a) should be zero."""
        cfg = SimulationConfig(soma=SubsystemParams(a=0.25))
        engine = NeuroArousalEngine(cfg)
        val = engine._cubic(0.25, 0.25)
        assert abs(val) < 1e-12


# ---------------------------------------------------------------------------
# Stimulus helpers
# ---------------------------------------------------------------------------

class TestStimuli:
    def test_null_stimulus(self):
        assert null_stimulus(0.0) == 0.0
        assert null_stimulus(999.0) == 0.0

    def test_pulse_stimulus(self):
        stim = pulse_stimulus(10.0, 5.0, 0.5)
        assert stim(9.9) == 0.0
        assert stim(10.0) == 0.5
        assert stim(14.9) == 0.5
        assert stim(15.0) == 0.0

    def test_periodic_stimulus(self):
        stim = periodic_stimulus(20.0, 3.0, 1.0)
        assert stim(0.0) == 1.0
        assert stim(2.9) == 1.0
        assert stim(3.1) == 0.0
        assert stim(20.0) == 1.0  # next period


# ---------------------------------------------------------------------------
# DigitalSoul
# ---------------------------------------------------------------------------

class TestDigitalSoul:
    def test_scenario_names(self):
        ds = DigitalSoul()
        assert "resting_state" in ds.scenario_names
        assert "dual_oscillation" in ds.scenario_names

    def test_run_scenario(self):
        ds = DigitalSoul()
        results, report = ds.run_scenario("resting_state")
        assert "time" in results
        assert report.soma_regime in Regime
        assert isinstance(report.description, str)
        assert len(report.description) > 0

    def test_unknown_scenario_raises(self):
        ds = DigitalSoul()
        with pytest.raises(ValueError, match="Unknown scenario"):
            ds.run_scenario("nonexistent")

    def test_custom_run(self):
        ds = DigitalSoul()
        results, report = ds.run_custom(
            config=SimulationConfig(t_max=50.0),
            ic=(0.0, 0.0, 0.0, 0.0),
        )
        assert results["u1"].shape == results["time"].shape
        assert report.coupled_regime in Regime

    def test_resting_state_is_quiescent(self):
        ds = DigitalSoul()
        _, report = ds.run_scenario("resting_state")
        assert report.soma_regime == Regime.QUIESCENT

    def test_dual_oscillation_oscillates(self):
        ds = DigitalSoul()
        _, report = ds.run_scenario("dual_oscillation")
        # Should have spikes in at least one channel
        assert report.soma_spike_count + report.psyche_spike_count > 0

    def test_get_scenario_info(self):
        ds = DigitalSoul()
        info = ds.get_scenario_info("single_soma_pulse")
        assert info["name"] == "Single SOMA Pulse"
        assert "c12" in info
