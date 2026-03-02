# NeuroArousal — Coupled Excitable System Exhibit

Interactive simulation of a **Blyuss-Kyrychko-type coupled excitable system**
with SOMA-PSYCHE delay coupling, built for university museum demonstration.

**Mobile-first responsive UI** — works on phones, tablets, kiosks, and desktops.

## Architecture

```
neuro_arousal/
├── engine.py        # NeuroArousalEngine — DDE numerical integrator
├── digital_soul.py  # DigitalSoul agent — regime analysis, alignment, arcs
├── multimodal.py    # Character image generation from simulation state
├── api.py           # FastAPI REST endpoints (v2.0)
└── ui.py            # Gradio interactive frontend (mobile-first)
main.py              # Entry point (serves both API + UI)
tests/
└── test_engine.py   # Comprehensive test suite
```

## Mathematical Model

Two coupled FitzHugh-Nagumo oscillators with sigmoidal delay coupling:

**SOMA** (physiological arousal):

    du₁/dt = u₁(1-u₁)(u₁-a₁) - v₁ + c₁₂·S(u₂(t-τ)) + I₁(t)
    dv₁/dt = ε₁(b₁·u₁ - v₁)

**PSYCHE** (cognitive/emotional arousal):

    du₂/dt = u₂(1-u₂)(u₂-a₂) - v₂ + c₂₁·S(u₁(t-τ)) + I₂(t)
    dv₂/dt = ε₂(b₂·u₂ - v₂)

where S(x) = 1/(1 + exp(-κ(x-θ))) is the sigmoidal coupling function.

### Emotional Drive Mapping

| Slider      | Internal Variable          | Effect                     |
|-------------|----------------------------|----------------------------|
| E_u (0–100) | arousal_drive = E_u / 100  | Tonic SOMA boost (×0.3)   |
| E_v (0–100) | valence_drive = E_v/100−0.5| PSYCHE shift (×0.2)       |
| E_v0        | baseline = 0.2             | Resting valence offset     |

### Savage Mode Parameters

Engages high-excitability regime: ε=0.05, a=0.5, b=0.1, E_v0=0.2,
amplified coupling (c₁₂=0.35, c₂₁=0.30, κ=20).

## Features

- **6 preset scenarios** including Savage Burst
- **E_u / E_v sliders** (0–100) for exhibit-facing arousal/valence control
- **Savage Mode toggle** for chaotic regime exploration
- **4 PEFT adapters** (Museum Default, Poetic, Clinical, Dramatic)
- **Alignment scoring** — cross-correlation, phase lag, coherence index
- **Narrative arc** — exposition → rising action → climax → falling → resolution
- **Climax detection** via tension-curve peak analysis
- **Full state inspector** — scrub through every integration step
- **Multimodal character** — procedural character visualisation from state
- **Mobile-first responsive** CSS for phone/tablet/kiosk displays
- **REST API** with Swagger/ReDoc documentation

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the server

```bash
python main.py
```

### 3. Open in browser

- **Gradio UI**: http://localhost:7860/ui
- **API docs**: http://localhost:7860/docs

### Mobile access

Open the Gradio UI URL on any phone or tablet on the same network.
The interface is fully responsive with touch-friendly controls.

## API-only mode

```bash
python main.py --api-only --port 8000
```

## API Endpoints (v2.0)

| Method | Path                    | Description                           |
|--------|-------------------------|---------------------------------------|
| GET    | /                       | Service info                          |
| GET    | /scenarios              | List preset scenario keys             |
| GET    | /scenarios/{name}       | Scenario description and parameters   |
| POST   | /run/scenario/{name}    | Run preset, return full results       |
| POST   | /run/custom             | Run with custom parameters            |
| GET    | /nullclines             | Compute nullclines                    |
| GET    | /state                  | Current computational state           |
| GET    | /state/{step}           | State at specific integration step    |
| GET    | /alignment              | SOMA-PSYCHE alignment score           |
| GET    | /arc                    | Narrative arc decomposition           |
| GET    | /adapters               | List PEFT adapters                    |
| POST   | /adapters/{name}        | Set active adapter                    |
| GET    | /character/appearance   | Character visual parameters           |
| GET    | /character/image        | Rendered character PNG                |

## Preset Scenarios

| Scenario             | Description                                     |
|----------------------|-------------------------------------------------|
| Resting State        | Stable fixed point, sub-threshold dynamics       |
| Single SOMA Pulse    | Pulse injection triggers spike + cross-coupling  |
| Dual Oscillation     | Sustained limit-cycle in both channels           |
| Periodic Drive       | Entrainment and sub-harmonic responses           |
| PSYCHE Perturbation  | Emotional pulse back-propagates to somatic       |
| Savage Burst         | Chaotic bursting with high-excitability params   |

## PEFT Adapters

| Adapter          | Tone     | Coupling Scale | Arousal Bias |
|------------------|----------|----------------|--------------|
| Museum Default   | measured | ×1.0           | +0           |
| Poetic Narrator  | lyrical  | ×1.1           | +5           |
| Clinical Observer| precise  | ×1.0           | +0           |
| Dramatic Storyteller | vivid | ×1.2          | +10          |

## Running Tests

```bash
python -m pytest tests/ -v
```

## Deployment (Production)

### Docker (recommended for museum kiosks)

```bash
docker build -t neuroarousal .
docker run -p 7860:7860 neuroarousal
```

### Systemd service

```ini
[Unit]
Description=NeuroArousal Exhibit
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/neuroarousal
ExecStart=/opt/neuroarousal/venv/bin/python main.py --port 7860
Restart=always

[Install]
WantedBy=multi-user.target
```

### Windows (future)

A Windows UI version using tkinter/PyQt is planned for standalone kiosk
deployment. The API and engine modules are platform-independent.

## License

MIT — see [LICENSE](LICENSE).
