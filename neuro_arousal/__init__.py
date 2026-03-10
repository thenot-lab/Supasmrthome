"""
NeuroArousal — Interactive Blyuss-Kyrychko excitable system simulation.

A computational neuroscience demonstration of coupled SOMA-PSYCHE dynamics
for university museum exhibition use.
"""

from neuro_arousal.engine import NeuroArousalEngine, SimulationConfig, savage_config
from neuro_arousal.digital_soul import DigitalSoul, Regime, ArcPhase, PEFT_ADAPTERS
from neuro_arousal.multimodal import compute_appearance, render_character

__all__ = [
    "NeuroArousalEngine",
    "SimulationConfig",
    "savage_config",
    "DigitalSoul",
    "Regime",
    "ArcPhase",
    "PEFT_ADAPTERS",
    "compute_appearance",
    "render_character",
]
