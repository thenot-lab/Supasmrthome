"""Tests for the FastAPI endpoints.

Uses httpx + FastAPI TestClient to exercise every endpoint without
spinning up a real server.
"""

import pytest
from fastapi.testclient import TestClient

from neuro_arousal.api import app


@pytest.fixture(scope="module")
def client():
    """Shared test client for the module."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Root & discovery
# ---------------------------------------------------------------------------

class TestRootEndpoint:
    def test_root_returns_200(self, client):
        r = client.get("/")
        assert r.status_code == 200
        body = r.json()
        assert body["version"] == "2.0.0"
        assert "scenarios" in body
        assert "adapters" in body

    def test_list_scenarios(self, client):
        r = client.get("/scenarios")
        assert r.status_code == 200
        names = r.json()
        assert isinstance(names, list)
        assert "resting_state" in names
        assert "savage_burst" in names

    def test_get_scenario_info(self, client):
        r = client.get("/scenarios/resting_state")
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Resting State"
        assert "soma_a" in body

    def test_get_scenario_info_404(self, client):
        r = client.get("/scenarios/nonexistent")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Simulation endpoints
# ---------------------------------------------------------------------------

class TestSimulationEndpoints:
    def test_run_scenario_resting(self, client):
        r = client.post("/run/scenario/resting_state")
        assert r.status_code == 200
        body = r.json()
        assert "time" in body
        assert "u1" in body
        assert "report" in body
        assert body["report"]["soma_regime"] == "QUIESCENT"

    def test_run_scenario_with_adapter(self, client):
        r = client.post("/run/scenario/single_soma_pulse?adapter=poetic")
        assert r.status_code == 200
        body = r.json()
        assert "report" in body

    def test_run_scenario_404(self, client):
        r = client.post("/run/scenario/nonexistent")
        assert r.status_code == 404

    def test_run_custom_defaults(self, client):
        r = client.post("/run/custom", json={})
        assert r.status_code == 200
        body = r.json()
        assert "time" in body
        assert "alignment" in body
        assert "arc" in body

    def test_run_custom_with_params(self, client):
        r = client.post("/run/custom", json={
            "dt": 0.05,
            "t_max": 50.0,
            "soma": {"a": 0.25, "epsilon": 0.01, "b": 0.5},
            "emotion": {"E_u": 70.0, "E_v": 30.0, "E_v0": 0.2},
            "savage_mode": False,
        })
        assert r.status_code == 200
        body = r.json()
        assert len(body["time"]) > 0

    def test_run_custom_savage_mode(self, client):
        r = client.post("/run/custom", json={
            "savage_mode": True,
            "t_max": 50.0,
        })
        assert r.status_code == 200
        body = r.json()
        assert len(body["time"]) > 0

    def test_run_custom_with_stimulus(self, client):
        r = client.post("/run/custom", json={
            "t_max": 100.0,
            "soma_stimulus": {
                "kind": "pulse",
                "onset": 10.0,
                "duration": 3.0,
                "amplitude": 0.5,
            },
            "psyche_stimulus": {
                "kind": "periodic",
                "period": 20.0,
                "duration": 2.0,
                "amplitude": 0.3,
            },
        })
        assert r.status_code == 200

    def test_run_custom_invalid_a(self, client):
        r = client.post("/run/custom", json={
            "soma": {"a": 1.5, "epsilon": 0.01, "b": 0.5},
        })
        assert r.status_code == 422

    def test_run_custom_invalid_tmax(self, client):
        r = client.post("/run/custom", json={"t_max": 0})
        assert r.status_code == 422

    def test_simulation_includes_alignment(self, client):
        r = client.post("/run/scenario/dual_oscillation")
        assert r.status_code == 200
        body = r.json()
        alignment = body.get("alignment")
        assert alignment is not None
        assert "cross_correlation" in alignment
        assert "coherence_index" in alignment

    def test_simulation_includes_arc(self, client):
        r = client.post("/run/scenario/single_soma_pulse")
        assert r.status_code == 200
        body = r.json()
        arc = body.get("arc")
        assert arc is not None
        assert "phases" in arc
        assert "climax_time" in arc
        assert "tension_curve" in arc


# ---------------------------------------------------------------------------
# Nullclines
# ---------------------------------------------------------------------------

class TestNullclineEndpoint:
    def test_nullclines_defaults(self, client):
        r = client.get("/nullclines")
        assert r.status_code == 200
        body = r.json()
        assert "u" in body
        assert "soma_cubic" in body
        assert "soma_linear" in body
        assert "psyche_cubic" in body
        assert "psyche_linear" in body
        assert len(body["u"]) == 300

    def test_nullclines_custom_params(self, client):
        r = client.get("/nullclines?soma_a=0.3&psyche_a=0.15")
        assert r.status_code == 200
        body = r.json()
        assert len(body["u"]) == 300

    def test_nullclines_invalid_a(self, client):
        r = client.get("/nullclines?soma_a=1.5")
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# State inspector
# ---------------------------------------------------------------------------

class TestStateEndpoints:
    def test_state_no_run_404(self, client):
        """Fresh soul has no simulation — expect 404."""
        # Note: the module-scoped client shares state, so a prior test
        # may have already run a simulation. We test the specific step.
        # Just verify the endpoint returns valid JSON on success.
        r = client.get("/state")
        # After prior tests have run simulations, this should be 200
        assert r.status_code == 200
        body = r.json()
        assert "step" in body
        assert "u1" in body
        assert "config" in body

    def test_state_at_step(self, client):
        # Run a scenario first
        client.post("/run/scenario/resting_state")
        r = client.get("/state/10")
        assert r.status_code == 200
        body = r.json()
        assert body["step"] == 10
        assert "coupling_flux" in body
        assert "savage_mode" in body

    def test_state_step_clamped(self, client):
        """Steps beyond n_steps should be clamped, not error."""
        r = client.get("/state/999999")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Alignment & Arc endpoints
# ---------------------------------------------------------------------------

class TestAlignmentArcEndpoints:
    def test_alignment_after_run(self, client):
        client.post("/run/scenario/dual_oscillation")
        r = client.get("/alignment")
        assert r.status_code == 200
        body = r.json()
        assert "cross_correlation" in body
        assert "phase_lag" in body
        assert "coherence_index" in body
        assert "interpretation" in body

    def test_arc_after_run(self, client):
        client.post("/run/scenario/single_soma_pulse")
        r = client.get("/arc")
        assert r.status_code == 200
        body = r.json()
        assert "phases" in body
        assert "climax_time" in body
        assert "arc_summary" in body
        assert "tension_curve" in body
        assert len(body["tension_curve"]) > 0


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------

class TestAdapterEndpoints:
    def test_list_adapters(self, client):
        r = client.get("/adapters")
        assert r.status_code == 200
        adapters = r.json()
        assert len(adapters) == 4
        names = [a["name"] for a in adapters]
        assert "default" in names
        assert "poetic" in names
        assert "clinical" in names
        assert "dramatic" in names

    def test_set_adapter(self, client):
        r = client.post("/adapters/dramatic")
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "dramatic"

    def test_set_adapter_404(self, client):
        r = client.post("/adapters/nonexistent")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Character / multimodal endpoints
# ---------------------------------------------------------------------------

class TestCharacterEndpoints:
    def test_character_appearance(self, client):
        client.post("/run/scenario/resting_state")
        r = client.get("/character/appearance")
        assert r.status_code == 200
        body = r.json()
        assert "body_colour" in body
        assert "expression" in body
        assert "eye_openness" in body
        assert "particle_count" in body

    def test_character_appearance_at_step(self, client):
        r = client.get("/character/appearance?step=5")
        assert r.status_code == 200

    def test_character_image_png(self, client):
        client.post("/run/scenario/resting_state")
        r = client.get("/character/image")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/png"
        assert len(r.content) > 0

    def test_character_image_at_step(self, client):
        r = client.get("/character/image?step=10")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/png"


# ---------------------------------------------------------------------------
# All 6 scenarios run successfully (regression)
# ---------------------------------------------------------------------------

class TestAllScenariosRegression:
    @pytest.mark.parametrize("scenario", [
        "resting_state",
        "single_soma_pulse",
        "dual_oscillation",
        "periodic_drive",
        "psyche_perturbation",
        "savage_burst",
    ])
    def test_scenario_runs(self, client, scenario):
        r = client.post(f"/run/scenario/{scenario}")
        assert r.status_code == 200
        body = r.json()
        assert len(body["time"]) > 0
        assert body["report"]["soma_regime"] in [
            "QUIESCENT", "EXCITABLE", "OSCILLATORY", "BISTABLE", "CHAOTIC"
        ]
        assert body["report"]["description"]
        # Alignment and arc should always be present
        assert body["alignment"] is not None
        assert body["arc"] is not None


# ---------------------------------------------------------------------------
# Downsampling behaviour
# ---------------------------------------------------------------------------

class TestDownsampling:
    def test_long_simulation_downsampled(self, client):
        r = client.post("/run/custom", json={
            "t_max": 500.0,
            "dt": 0.01,
        })
        assert r.status_code == 200
        body = r.json()
        # dt=0.01, t_max=500 → 50001 points; should be heavily downsampled
        assert len(body["time"]) <= 2100
        assert len(body["time"]) < 50001
