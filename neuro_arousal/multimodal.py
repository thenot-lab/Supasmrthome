"""
Multimodal injection pipeline — generates character visualisations from
simulation state.

Produces procedural character images that reflect the current dynamical
regime:  colour, expression, particle effects, and body-language are all
driven by the SOMA/PSYCHE state vector.

This module is intentionally dependency-light: it uses only numpy and
Pillow (PIL) so it can run on any museum kiosk without a GPU.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

try:
    from PIL import Image, ImageDraw, ImageFont
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


# ---------------------------------------------------------------------------
# Character appearance parameters driven by simulation state
# ---------------------------------------------------------------------------

@dataclass
class CharacterAppearance:
    """Visual parameters extracted from a simulation snapshot."""
    # Core colours (RGB tuples)
    body_colour: tuple[int, int, int]
    aura_colour: tuple[int, int, int]
    eye_colour: tuple[int, int, int]

    # Expression
    expression: str        # "calm", "alert", "excited", "chaotic", "tense"
    mouth_curve: float     # -1 (frown) to 1 (smile)
    eye_openness: float    # 0 (closed) to 1 (wide)
    pupil_dilation: float  # 0.3 to 1.0

    # Particle / aura effects
    aura_intensity: float  # 0 to 1
    particle_count: int
    particle_speed: float

    # Body language
    posture_angle: float   # degrees, 0 = upright
    breathing_rate: float  # Hz
    tremor: float          # 0 to 1


def compute_appearance(
    snapshot: dict,
    regime: str = "QUIESCENT",
) -> CharacterAppearance:
    """Map simulation state → character visual parameters."""
    u1 = snapshot.get("u1", 0.0)
    v1 = snapshot.get("v1", 0.0)
    u2 = snapshot.get("u2", 0.0)
    v2 = snapshot.get("v2", 0.0)
    se = snapshot.get("soma_energy", 0.0)
    pe = snapshot.get("psyche_energy", 0.0)
    flux = snapshot.get("coupling_flux", 0.0)
    savage = snapshot.get("savage_mode", False)

    total_energy = se + pe
    arousal = min(1.0, total_energy * 4.0)

    # Colour mapping
    r = int(min(255, 80 + arousal * 175))
    g = int(max(0, 200 - arousal * 150))
    b = int(min(255, 120 + abs(u2) * 200))
    body_colour = (r, g, b)

    # Aura — flux-driven
    af = min(1.0, abs(flux) * 5.0)
    aura_colour = (
        int(40 + af * 180),
        int(220 - af * 120),
        int(200 + af * 55),
    )

    # Eyes — PSYCHE drives openness, SOMA drives pupil
    eye_openness = min(1.0, 0.3 + abs(u2) * 1.5)
    pupil_dilation = min(1.0, max(0.3, 0.3 + abs(u1) * 1.2))

    # Expression mapping by regime
    expression_map = {
        "QUIESCENT": ("calm", 0.3, 0.4),
        "EXCITABLE": ("alert", 0.0, 0.7),
        "OSCILLATORY": ("excited", 0.6, 0.8),
        "BISTABLE": ("tense", -0.3, 0.9),
        "CHAOTIC": ("chaotic", -0.5, 1.0),
    }
    expression, mouth_curve, _ = expression_map.get(
        regime, ("calm", 0.0, 0.5)
    )

    if savage:
        expression = "chaotic"
        mouth_curve = -0.7
        eye_openness = 1.0

    # Particles
    particle_count = int(min(50, arousal * 60))
    particle_speed = arousal * 3.0

    # Body language
    posture_angle = arousal * 15.0 * math.sin(flux * 10.0)
    breathing_rate = 0.2 + arousal * 0.8
    tremor = arousal * 0.5 + (0.3 if savage else 0.0)

    return CharacterAppearance(
        body_colour=body_colour,
        aura_colour=aura_colour,
        eye_colour=(int(100 + abs(u2) * 155), 80, int(100 + abs(u1) * 155)),
        expression=expression,
        mouth_curve=mouth_curve,
        eye_openness=eye_openness,
        pupil_dilation=pupil_dilation,
        aura_intensity=af,
        particle_count=particle_count,
        particle_speed=particle_speed,
        posture_angle=posture_angle,
        breathing_rate=breathing_rate,
        tremor=tremor,
    )


# ---------------------------------------------------------------------------
# Procedural character rendering
# ---------------------------------------------------------------------------

def render_character(
    appearance: CharacterAppearance,
    width: int = 400,
    height: int = 500,
    background: tuple[int, int, int] = (15, 15, 25),
) -> bytes:
    """Render a character PNG from appearance parameters.

    Returns PNG bytes.  Falls back to a minimal numpy-only renderer if
    Pillow is not installed.
    """
    if not _HAS_PIL:
        return _render_fallback(appearance, width, height, background)

    img = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(img)

    cx, cy = width // 2, height // 2 + 20

    # --- Aura ---
    if appearance.aura_intensity > 0.05:
        for r_offset in range(3):
            radius = 120 + r_offset * 25
            alpha_scale = max(0, 1.0 - r_offset * 0.3)
            ac = appearance.aura_colour
            c = (
                int(ac[0] * alpha_scale * appearance.aura_intensity),
                int(ac[1] * alpha_scale * appearance.aura_intensity),
                int(ac[2] * alpha_scale * appearance.aura_intensity),
            )
            draw.ellipse(
                [cx - radius, cy - radius, cx + radius, cy + radius],
                outline=c, width=2,
            )

    # --- Particles ---
    rng = np.random.RandomState(42)
    for _ in range(appearance.particle_count):
        px = int(cx + rng.randint(-140, 140))
        py = int(cy + rng.randint(-160, 160))
        pr = rng.randint(1, 4)
        pc = appearance.aura_colour
        draw.ellipse([px - pr, py - pr, px + pr, py + pr], fill=pc)

    # --- Body (oval) ---
    body_rx, body_ry = 55, 85
    bx_off = int(math.sin(math.radians(appearance.posture_angle)) * 15)
    draw.ellipse(
        [cx - body_rx + bx_off, cy - body_ry + 30,
         cx + body_rx + bx_off, cy + body_ry + 30],
        fill=appearance.body_colour,
        outline=(255, 255, 255),
        width=2,
    )

    # --- Head ---
    head_r = 42
    hx = cx + bx_off
    hy = cy - 60
    draw.ellipse(
        [hx - head_r, hy - head_r, hx + head_r, hy + head_r],
        fill=appearance.body_colour,
        outline=(255, 255, 255),
        width=2,
    )

    # --- Eyes ---
    eye_h = int(8 * appearance.eye_openness)
    eye_w = 12
    for ex_off in [-18, 18]:
        # Eye white
        draw.ellipse(
            [hx + ex_off - eye_w, hy - 5 - eye_h,
             hx + ex_off + eye_w, hy - 5 + eye_h],
            fill=(240, 240, 240),
        )
        # Pupil
        pr = int(5 * appearance.pupil_dilation)
        draw.ellipse(
            [hx + ex_off - pr, hy - 5 - pr,
             hx + ex_off + pr, hy - 5 + pr],
            fill=appearance.eye_colour,
        )

    # --- Mouth ---
    mouth_y = hy + 18
    mc = appearance.mouth_curve
    if abs(mc) < 0.15:
        draw.line([(hx - 12, mouth_y), (hx + 12, mouth_y)],
                  fill=(200, 200, 200), width=2)
    else:
        arc_h = int(mc * 10)
        draw.arc(
            [hx - 12, mouth_y - abs(arc_h), hx + 12, mouth_y + abs(arc_h)],
            start=0 if mc > 0 else 180,
            end=180 if mc > 0 else 360,
            fill=(200, 200, 200), width=2,
        )

    # --- Status label ---
    label = appearance.expression.upper()
    if appearance.tremor > 0.5:
        label += " !"
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    draw.text((10, height - 30), label, fill=(200, 200, 200), font=font)

    # --- Tremor shake indicator ---
    if appearance.tremor > 0.3:
        for _ in range(int(appearance.tremor * 8)):
            sx = int(cx + rng.randint(-80, 80))
            sy = int(cy + rng.randint(-100, 100))
            draw.line([(sx, sy), (sx + rng.randint(-5, 5), sy + rng.randint(-5, 5))],
                      fill=(255, 255, 255), width=1)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _render_fallback(
    appearance: CharacterAppearance,
    width: int, height: int,
    background: tuple[int, int, int],
) -> bytes:
    """Minimal numpy-only PNG stub when Pillow is unavailable."""
    # Create a simple gradient image as placeholder
    img = np.full((height, width, 3), background, dtype=np.uint8)

    # Draw a coloured circle for the body
    cy, cx = height // 2, width // 2
    Y, X = np.ogrid[:height, :width]
    mask = ((X - cx) ** 2 + (Y - cy) ** 2) < 60 ** 2
    img[mask] = appearance.body_colour

    # Encode as raw PPM (universally readable, no Pillow needed)
    header = f"P6\n{width} {height}\n255\n".encode()
    return header + img.tobytes()


# ---------------------------------------------------------------------------
# Appearance-to-dict for JSON serialisation
# ---------------------------------------------------------------------------

def appearance_to_dict(app: CharacterAppearance) -> dict:
    return {
        "body_colour": list(app.body_colour),
        "aura_colour": list(app.aura_colour),
        "eye_colour": list(app.eye_colour),
        "expression": app.expression,
        "mouth_curve": round(app.mouth_curve, 3),
        "eye_openness": round(app.eye_openness, 3),
        "pupil_dilation": round(app.pupil_dilation, 3),
        "aura_intensity": round(app.aura_intensity, 3),
        "particle_count": app.particle_count,
        "particle_speed": round(app.particle_speed, 3),
        "posture_angle": round(app.posture_angle, 3),
        "breathing_rate": round(app.breathing_rate, 3),
        "tremor": round(app.tremor, 3),
    }
