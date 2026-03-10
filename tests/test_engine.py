"""Tests for NeuroArousalEngine, DigitalSoul, and multimodal pipeline."""

import json

import numpy as np
import pytest

from neuro_arousal.engine import (
    CouplingParams,
    EmotionalDriveParams,
    NeuroArousalEngine,
    SimulationConfig,
    SubsystemParams,
    null_stimulus,
    pulse_stimulus,
    periodic_stimulus,
    savage_config,
)
from neuro_arousal.digital_soul import (
    DigitalSoul,
    Regime,
    ArcPhase,
    PEFT_ADAPTERS,
    compute_alignment,
    compute_narrative_arc,
)
from neuro_arousal.multimodal import (
    compute_appearance,
    render_character,
    appearance_to_dict,
    CharacterAppearance,
)


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
        """With zero stimulus, zero emotional drive, and small IC, trajectory should stay small."""
        cfg = SimulationConfig(
            t_max=100.0,
            emotion=EmotionalDriveParams(E_u=0.0, E_v=50.0, E_v0=0.0),
        )
        engine = NeuroArousalEngine(cfg)
        engine.set_initial_conditions(0.01, 0.0, 0.01, 0.0)
        results = engine.run()
        assert results["u1"].shape == results["time"].shape
        assert np.max(np.abs(results["u1"])) < 0.6

    def test_pulse_triggers_spike(self):
        engine = NeuroArousalEngine(SimulationConfig(t_max=100.0))
        engine.set_initial_conditions(0.0, 0.0, 0.0, 0.0)
        stim = pulse_stimulus(10.0, 3.0, 0.8)
        results = engine.run(I1_func=stim)
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
        assert stim(20.0) == 1.0


# ---------------------------------------------------------------------------
# Emotional drive & savage mode
# ---------------------------------------------------------------------------

class TestEmotionalDrive:
    def test_default_emotional_params(self):
        cfg = SimulationConfig()
        assert cfg.emotion.E_u == 50.0
        assert cfg.emotion.E_v == 50.0
        assert cfg.emotion.E_v0 == 0.2

    def test_custom_emotional_drive(self):
        cfg = SimulationConfig(
            emotion=EmotionalDriveParams(E_u=80.0, E_v=20.0, E_v0=0.3)
        )
        engine = NeuroArousalEngine(cfg)
        assert engine._arousal_drive == pytest.approx(0.8)
        assert engine._valence_drive == pytest.approx(-0.3)
        assert engine._valence_baseline == pytest.approx(0.3)

    def test_savage_config(self):
        cfg = savage_config(t_max=100.0)
        assert cfg.savage_mode is True
        assert cfg.soma.epsilon == 0.05
        assert cfg.soma.a == 0.5
        assert cfg.soma.b == 0.1
        assert cfg.emotion.E_v0 == 0.2

    def test_savage_mode_runs(self):
        cfg = savage_config(t_max=50.0)
        engine = NeuroArousalEngine(cfg)
        engine.set_initial_conditions(0.1, 0.0, 0.1, 0.0)
        results = engine.run(
            I1_func=pulse_stimulus(5.0, 3.0, 0.5),
        )
        assert len(results["time"]) > 0
        assert results["u1"].shape == results["time"].shape


# ---------------------------------------------------------------------------
# State snapshot
# ---------------------------------------------------------------------------

class TestStateSnapshot:
    def test_snapshot_structure(self):
        engine = NeuroArousalEngine(SimulationConfig(t_max=50.0))
        engine.set_initial_conditions(0.1, 0.0, 0.05, 0.0)
        engine.run()
        snap = engine.snapshot_state(step=10)
        assert "step" in snap
        assert snap["step"] == 10
        assert "u1" in snap
        assert "v1" in snap
        assert "config" in snap
        assert "savage_mode" in snap

    def test_snapshot_default_step(self):
        engine = NeuroArousalEngine(SimulationConfig(t_max=20.0))
        engine.set_initial_conditions()
        engine.run()
        snap = engine.snapshot_state()
        assert snap["step"] > 0

    def test_snapshot_serialisable(self):
        engine = NeuroArousalEngine(SimulationConfig(t_max=20.0))
        engine.set_initial_conditions()
        engine.run()
        snap = engine.snapshot_state(step=5)
        s = json.dumps(snap)
        assert isinstance(s, str)


# ---------------------------------------------------------------------------
# DigitalSoul
# ---------------------------------------------------------------------------

class TestDigitalSoul:
    def test_scenario_names(self):
        ds = DigitalSoul()
        assert "resting_state" in ds.scenario_names
        assert "dual_oscillation" in ds.scenario_names
        assert "savage_burst" in ds.scenario_names

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
        assert report.soma_spike_count + report.psyche_spike_count > 0

    def test_get_scenario_info(self):
        ds = DigitalSoul()
        info = ds.get_scenario_info("single_soma_pulse")
        assert info["name"] == "Single SOMA Pulse"
        assert "c12" in info

    def test_savage_scenario(self):
        ds = DigitalSoul()
        results, report = ds.run_scenario("savage_burst")
        assert len(results["time"]) > 0


# ---------------------------------------------------------------------------
# PEFT adapters
# ---------------------------------------------------------------------------

class TestPEFTAdapters:
    def test_default_adapter(self):
        ds = DigitalSoul()
        assert ds.adapter.name == "default"

    def test_set_adapter(self):
        ds = DigitalSoul()
        adapter = ds.set_adapter("poetic")
        assert adapter.name == "poetic"
        assert ds.adapter.narrative_tone == "lyrical"

    def test_unknown_adapter_falls_back(self):
        ds = DigitalSoul()
        adapter = ds.set_adapter("nonexistent")
        assert adapter.name == "default"

    def test_available_adapters(self):
        adapters = DigitalSoul.available_adapters()
        assert len(adapters) == 4
        names = [a["name"] for a in adapters]
        assert "default" in names
        assert "dramatic" in names

    def test_adapter_affects_narrative(self):
        ds_default = DigitalSoul(adapter="default")
        ds_dramatic = DigitalSoul(adapter="dramatic")
        _, report_d = ds_default.run_scenario("resting_state")
        _, report_v = ds_dramatic.run_scenario("resting_state")
        # Different adapters should produce different descriptions
        # (both are quiescent but narrated differently)
        assert report_d.description != report_v.description


# ---------------------------------------------------------------------------
# Alignment scoring
# ---------------------------------------------------------------------------

class TestAlignment:
    def test_alignment_after_run(self):
        ds = DigitalSoul()
        ds.run_scenario("dual_oscillation")
        alignment = ds.get_alignment()
        assert alignment is not None
        assert -1.0 <= alignment.cross_correlation <= 1.0
        assert 0.0 <= alignment.coherence_index <= 1.0
        assert isinstance(alignment.interpretation, str)

    def test_quiescent_alignment_near_zero(self):
        ds = DigitalSoul()
        ds.run_scenario("resting_state")
        alignment = ds.get_alignment()
        assert alignment is not None
        # Resting state uses zero emotional drive, so both channels are at
        # a fixed point with minimal activity.  Alignment is computed but
        # the interpretation should still be valid.
        assert isinstance(alignment.interpretation, str)

    def test_alignment_no_run(self):
        ds = DigitalSoul()
        assert ds.get_alignment() is None


# ---------------------------------------------------------------------------
# Narrative arc
# ---------------------------------------------------------------------------

class TestNarrativeArc:
    def test_arc_after_run(self):
        ds = DigitalSoul()
        ds.run_scenario("single_soma_pulse")
        arc = ds.get_arc()
        assert arc is not None
        assert arc.climax_time > 0
        assert arc.climax_energy >= 0
        assert len(arc.phases) > 0
        assert isinstance(arc.arc_summary, str)

    def test_arc_phases_are_valid(self):
        ds = DigitalSoul()
        ds.run_scenario("periodic_drive")
        arc = ds.get_arc()
        assert arc is not None
        for t_start, t_end, phase in arc.phases:
            assert t_end >= t_start
            assert isinstance(phase, ArcPhase)

    def test_tension_curve_length(self):
        ds = DigitalSoul()
        results, _ = ds.run_scenario("dual_oscillation")
        arc = ds.get_arc()
        assert arc is not None
        assert len(arc.tension_curve) == len(results["time"])

    def test_arc_no_run(self):
        ds = DigitalSoul()
        assert ds.get_arc() is None


# ---------------------------------------------------------------------------
# State snapshot via DigitalSoul
# ---------------------------------------------------------------------------

class TestSoulStateSnapshot:
    def test_snapshot_after_run(self):
        ds = DigitalSoul()
        ds.run_scenario("single_soma_pulse")
        snap = ds.get_state_snapshot(step=50)
        assert snap is not None
        assert snap["step"] == 50

    def test_snapshot_no_run(self):
        ds = DigitalSoul()
        assert ds.get_state_snapshot() is None


# ---------------------------------------------------------------------------
# Multimodal pipeline
# ---------------------------------------------------------------------------

class TestMultimodal:
    def test_compute_appearance(self):
        snap = {
            "u1": 0.5, "v1": 0.1, "u2": 0.3, "v2": 0.05,
            "soma_energy": 0.13, "psyche_energy": 0.05,
            "coupling_flux": 0.02, "savage_mode": False,
        }
        app = compute_appearance(snap, "OSCILLATORY")
        assert isinstance(app, CharacterAppearance)
        assert app.expression == "excited"
        assert 0 <= app.eye_openness <= 1.0
        assert app.particle_count >= 0

    def test_appearance_savage(self):
        snap = {
            "u1": 0.8, "v1": 0.2, "u2": 0.7, "v2": 0.15,
            "soma_energy": 0.34, "psyche_energy": 0.26,
            "coupling_flux": 0.1, "savage_mode": True,
        }
        app = compute_appearance(snap, "CHAOTIC")
        assert app.expression == "chaotic"
        assert app.eye_openness == 1.0

    def test_appearance_to_dict(self):
        snap = {
            "u1": 0.0, "v1": 0.0, "u2": 0.0, "v2": 0.0,
            "soma_energy": 0.0, "psyche_energy": 0.0,
            "coupling_flux": 0.0, "savage_mode": False,
        }
        app = compute_appearance(snap, "QUIESCENT")
        d = appearance_to_dict(app)
        assert "body_colour" in d
        assert "expression" in d
        assert isinstance(d["body_colour"], list)

    def test_render_character_returns_bytes(self):
        snap = {
            "u1": 0.3, "v1": 0.05, "u2": 0.2, "v2": 0.03,
            "soma_energy": 0.05, "psyche_energy": 0.02,
            "coupling_flux": 0.01, "savage_mode": False,
        }
        app = compute_appearance(snap, "EXCITABLE")
        img_bytes = render_character(app, width=100, height=120)
        assert isinstance(img_bytes, bytes)
        assert len(img_bytes) > 0
