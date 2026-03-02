"""Tests for the Gradio UI callbacks.

Exercises the callback functions (run_preset, run_custom, inspect_state)
directly — no Gradio server needed.
"""

import json
from unittest.mock import patch

import numpy as np
import pytest
import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure

from neuro_arousal.ui import (
    run_preset,
    run_custom,
    inspect_state,
    _build_regime_text,
    _build_alignment_text,
    _plot_timeseries,
    _plot_phase_planes,
    _plot_energy_flux,
    _plot_tension_arc,
    _render_character_image,
    soul,
)
from neuro_arousal.digital_soul import Regime, AlignmentScore, RegimeReport


# ---------------------------------------------------------------------------
# Preset scenario callback
# ---------------------------------------------------------------------------

class TestRunPreset:
    def test_resting_state_returns_10_outputs(self):
        result = run_preset("resting_state", "default")
        assert len(result) == 10
        # First 4 outputs are matplotlib figures
        for i in range(4):
            assert isinstance(result[i], Figure)
        # scenario header is markdown string
        assert isinstance(result[4], str)
        assert "Resting State" in result[4]
        # regime text
        assert "QUIESCENT" in result[5]
        # alignment text
        assert isinstance(result[6], str)
        # arc text
        assert isinstance(result[7], str)
        # state JSON
        state = json.loads(result[8])
        assert "u1" in state
        assert "step" in state

    def test_savage_burst_scenario(self):
        result = run_preset("savage_burst", "default")
        assert len(result) == 10
        # Should contain savage_mode info in state JSON
        state = json.loads(result[8])
        assert state["savage_mode"] is True

    def test_preset_with_poetic_adapter(self):
        result = run_preset("single_soma_pulse", "poetic")
        assert len(result) == 10
        # Poetic adapter uses "lyrical" tone modifier
        desc = result[5]
        assert isinstance(desc, str)

    def test_preset_with_dramatic_adapter(self):
        result = run_preset("single_soma_pulse", "dramatic")
        assert len(result) == 10

    def test_all_presets_succeed(self):
        for scenario in soul.scenario_names:
            result = run_preset(scenario, "default")
            assert len(result) == 10
            for i in range(4):
                assert isinstance(result[i], Figure)


# ---------------------------------------------------------------------------
# Custom run callback
# ---------------------------------------------------------------------------

class TestRunCustom:
    def test_custom_defaults(self):
        result = run_custom(
            0.25, 0.01, 0.5,      # soma a, eps, b
            0.20, 0.008, 0.45,    # psyche a, eps, b
            0.15, 0.12, 10.0, 0.3, 5.0,  # coupling c12, c21, kappa, theta, tau
            100.0,                  # t_max
            50, 50,                 # E_u, E_v
            False,                  # savage
            "default",              # adapter
            "none", "SOMA", 20, 3, 0.5, 40,  # stimulus
        )
        assert len(result) == 9
        for i in range(4):
            assert isinstance(result[i], Figure)

    def test_custom_with_pulse(self):
        result = run_custom(
            0.25, 0.01, 0.5,
            0.20, 0.008, 0.45,
            0.15, 0.12, 10.0, 0.3, 5.0,
            100.0,
            50, 50,
            False,
            "default",
            "pulse", "SOMA", 10, 3, 0.5, 40,
        )
        assert len(result) == 9

    def test_custom_periodic_both(self):
        result = run_custom(
            0.25, 0.01, 0.5,
            0.20, 0.008, 0.45,
            0.15, 0.12, 10.0, 0.3, 5.0,
            100.0,
            50, 50,
            False,
            "default",
            "periodic", "Both", 10, 3, 0.3, 30,
        )
        assert len(result) == 9

    def test_custom_savage_mode(self):
        result = run_custom(
            0.25, 0.01, 0.5,
            0.20, 0.008, 0.45,
            0.15, 0.12, 10.0, 0.3, 5.0,
            50.0,
            80, 70,
            True,        # savage mode ON
            "default",
            "none", "SOMA", 20, 3, 0.5, 40,
        )
        assert len(result) == 9
        state = json.loads(result[7])
        assert state["savage_mode"] is True

    def test_custom_psyche_target(self):
        result = run_custom(
            0.25, 0.01, 0.5,
            0.20, 0.008, 0.45,
            0.15, 0.12, 10.0, 0.3, 5.0,
            80.0,
            50, 50,
            False,
            "clinical",
            "pulse", "PSYCHE", 15, 5, 0.6, 40,
        )
        assert len(result) == 9


# ---------------------------------------------------------------------------
# State inspector callback
# ---------------------------------------------------------------------------

class TestInspectState:
    def test_inspect_after_run(self):
        run_preset("single_soma_pulse", "default")
        state_json, char_img = inspect_state(50)
        state = json.loads(state_json)
        assert state["step"] == 50
        assert "u1" in state
        assert "config" in state

    def test_inspect_step_zero(self):
        run_preset("resting_state", "default")
        state_json, char_img = inspect_state(0)
        state = json.loads(state_json)
        assert state["step"] == 0

    def test_inspect_high_step_clamped(self):
        run_preset("resting_state", "default")
        state_json, char_img = inspect_state(999999)
        state = json.loads(state_json)
        # Should be clamped to max step, not error
        assert "step" in state


# ---------------------------------------------------------------------------
# Text formatters
# ---------------------------------------------------------------------------

class TestTextFormatters:
    def test_build_regime_text(self):
        report = RegimeReport(
            soma_regime=Regime.OSCILLATORY,
            psyche_regime=Regime.EXCITABLE,
            coupled_regime=Regime.OSCILLATORY,
            soma_spike_count=5,
            psyche_spike_count=1,
            mean_coupling_flux=0.023,
            description="Test description.",
        )
        text = _build_regime_text(report)
        assert "OSCILLATORY" in text
        assert "5 spikes" in text
        assert "0.0230" in text

    def test_build_alignment_text_none(self):
        text = _build_alignment_text(None)
        assert text == "N/A"

    def test_build_alignment_text(self):
        alignment = AlignmentScore(
            cross_correlation=0.85,
            phase_lag=3.0,
            coherence_index=0.85,
            interpretation="Strong alignment.",
        )
        text = _build_alignment_text(alignment)
        assert "0.8500" in text
        assert "3.0" in text
        assert "Strong alignment" in text


# ---------------------------------------------------------------------------
# Plotting functions return Figure objects
# ---------------------------------------------------------------------------

class TestPlotFunctions:
    @pytest.fixture
    def results(self):
        """Minimal simulation results dict."""
        n = 100
        t = np.linspace(0, 10, n)
        return {
            "time": t,
            "u1": np.sin(t),
            "v1": np.cos(t) * 0.3,
            "u2": np.sin(t + 1),
            "v2": np.cos(t + 1) * 0.3,
            "soma_energy": np.sin(t) ** 2 * 0.5,
            "psyche_energy": np.sin(t + 1) ** 2 * 0.5,
            "coupling_flux": np.sin(t) * 0.1,
        }

    @pytest.fixture
    def nullclines(self):
        u = np.linspace(-0.5, 1.5, 100)
        return {
            "u": u,
            "soma_cubic": u * (1 - u) * (u - 0.25),
            "soma_linear": 0.5 * u,
            "psyche_cubic": u * (1 - u) * (u - 0.20),
            "psyche_linear": 0.45 * u,
        }

    def test_plot_timeseries(self, results):
        fig = _plot_timeseries(results)
        assert isinstance(fig, Figure)

    def test_plot_phase_planes(self, results, nullclines):
        fig = _plot_phase_planes(results, nullclines)
        assert isinstance(fig, Figure)

    def test_plot_energy_flux(self, results):
        fig = _plot_energy_flux(results)
        assert isinstance(fig, Figure)

    def test_plot_tension_arc_none(self, results):
        fig = _plot_tension_arc(results, None)
        assert isinstance(fig, Figure)

    def test_plot_tension_arc_with_arc(self):
        soul_obj = soul
        soul_obj.run_scenario("single_soma_pulse")
        results = soul_obj._last_results
        arc = soul_obj.get_arc()
        fig = _plot_tension_arc(results, arc)
        assert isinstance(fig, Figure)


# ---------------------------------------------------------------------------
# Character rendering via UI helper
# ---------------------------------------------------------------------------

class TestCharacterRendering:
    def test_render_character_image_none_snapshot(self):
        result = _render_character_image(None, "QUIESCENT")
        assert result is None

    def test_render_character_image_valid(self):
        snap = {
            "u1": 0.3, "v1": 0.05, "u2": 0.2, "v2": 0.03,
            "soma_energy": 0.05, "psyche_energy": 0.02,
            "coupling_flux": 0.01, "savage_mode": False,
        }
        result = _render_character_image(snap, "EXCITABLE")
        # If Pillow is available, should return numpy array
        if result is not None:
            assert isinstance(result, np.ndarray)
            assert result.ndim == 3
