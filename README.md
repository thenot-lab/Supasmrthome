# NeuroArousal — Coupled Excitable System Exhibit

Interactive simulation of a **Blyuss-Kyrychko-type coupled excitable system**
with SOMA-PSYCHE delay coupling, built for university museum demonstration.

## Architecture

```
neuro_arousal/
├── engine.py        # NeuroArousalEngine — DDE numerical integrator
├── digital_soul.py  # DigitalSoul agent — regime analysis & narration
├── api.py           # FastAPI REST endpoints
└── ui.py            # Gradio interactive frontend
main.py              # Entry point (serves both API + UI)
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

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

Then open:
- **Gradio UI**: http://localhost:7860/ui
- **API docs**: http://localhost:7860/docs

## API-only mode

```bash
python main.py --api-only --port 8000
```

## Preset Scenarios

| Scenario | Description |
|----------|-------------|
| Resting State | Stable fixed point, sub-threshold dynamics |
| Single SOMA Pulse | Pulse injection triggers spike + cross-coupling |
| Dual Oscillation | Sustained limit-cycle in both channels |
| Periodic Drive | Entrainment and sub-harmonic responses |
| PSYCHE Perturbation | Emotional pulse back-propagates to somatic channel |

## Running Tests

```bash
python -m pytest tests/ -v
```

## License

MIT — see [LICENSE](LICENSE).
