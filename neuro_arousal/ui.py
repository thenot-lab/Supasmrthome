"""
Gradio interactive UI for the NeuroArousal museum exhibit.

Mobile-first responsive layout with:
  * Preset scenario selector with explanatory cards
  * Custom parameter sliders — including E_u (0–100), E_v (0–100)
  * Savage Mode toggle
  * PEFT adapter dropdown for persona switching
  * Time-series, phase-plane, energy/flux, and tension-curve plots
  * Full computational state inspector at any timestep
  * Alignment score display
  * Narrative arc with climax annotation
  * Character visualisation panel (multimodal pipeline)
  * Regime classification and narrative panel
"""

from __future__ import annotations

import io
import json

import gradio as gr
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from neuro_arousal.digital_soul import (
    DigitalSoul,
    RegimeReport,
    AlignmentScore,
    NarrativeArc,
    ArcPhase,
    PEFT_ADAPTERS,
)
from neuro_arousal.engine import (
    CouplingParams,
    EmotionalDriveParams,
    SimulationConfig,
    SubsystemParams,
    null_stimulus,
    pulse_stimulus,
    periodic_stimulus,
    savage_config,
)
from neuro_arousal.multimodal import (
    compute_appearance,
    render_character,
    _HAS_PIL,
)

# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

soul = DigitalSoul()

# Consistent colour scheme
C_SOMA_U = "#e63946"
C_SOMA_V = "#f4a261"
C_PSYCHE_U = "#457b9d"
C_PSYCHE_V = "#a8dadc"
C_FLUX = "#2a9d8f"
C_TENSION = "#e9c46a"
C_CLIMAX = "#ff006e"

# Mobile-friendly CSS
MOBILE_CSS = """
/* Mobile-first responsive overhaul */
.gradio-container {
    max-width: 100% !important;
    padding: 8px !important;
}
@media (max-width: 768px) {
    .gradio-container { padding: 4px !important; }
    .gr-block { padding: 6px !important; }
    .gr-box { padding: 4px !important; }
    .gr-padded { padding: 8px !important; }
    .gr-form { gap: 4px !important; }
    .plot-container { min-height: 250px; }
    .gr-button { min-height: 44px !important; font-size: 16px !important; }
    .gr-input, .gr-slider input { font-size: 16px !important; }
    h1 { font-size: 1.4rem !important; }
    h2 { font-size: 1.2rem !important; }
    h3 { font-size: 1.05rem !important; }
}
@media (min-width: 769px) and (max-width: 1024px) {
    .gradio-container { max-width: 960px !important; }
}
/* State inspector styling */
.state-json {
    font-family: 'SF Mono', 'Fira Code', monospace !important;
    font-size: 12px !important;
    background: #1a1a2e !important;
    color: #e0e0e0 !important;
    border-radius: 8px !important;
    padding: 12px !important;
}
/* Savage mode indicator */
.savage-active {
    border: 2px solid #ff006e !important;
    box-shadow: 0 0 15px rgba(255, 0, 110, 0.3) !important;
}
/* Character panel */
.character-panel {
    text-align: center;
    padding: 8px;
}
"""


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

def _plot_timeseries(results: dict) -> Figure:
    t = results["time"]
    fig, axes = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
    fig.suptitle("Time Series — SOMA & PSYCHE Activators", fontsize=13)

    axes[0].plot(t, results["u1"], color=C_SOMA_U, lw=1.2, label="u₁ (SOMA)")
    axes[0].plot(t, results["v1"], color=C_SOMA_V, lw=0.9, ls="--",
                 label="v₁ (recovery)")
    axes[0].set_ylabel("SOMA")
    axes[0].legend(loc="upper right", fontsize=8)
    axes[0].grid(alpha=0.3)

    axes[1].plot(t, results["u2"], color=C_PSYCHE_U, lw=1.2,
                 label="u₂ (PSYCHE)")
    axes[1].plot(t, results["v2"], color=C_PSYCHE_V, lw=0.9, ls="--",
                 label="v₂ (recovery)")
    axes[1].set_ylabel("PSYCHE")
    axes[1].set_xlabel("Time")
    axes[1].legend(loc="upper right", fontsize=8)
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    return fig


def _plot_phase_planes(results: dict, nullclines: dict) -> Figure:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    fig.suptitle("Phase-Plane Portraits", fontsize=13)

    u_nc = nullclines["u"]

    ax = axes[0]
    ax.plot(u_nc, nullclines["soma_cubic"], "k-", lw=0.8, alpha=0.5,
            label="u-nullcline")
    ax.plot(u_nc, nullclines["soma_linear"], "k--", lw=0.8, alpha=0.5,
            label="v-nullcline")
    ax.plot(results["u1"], results["v1"], color=C_SOMA_U, lw=0.6, alpha=0.7)
    ax.plot(results["u1"][0], results["v1"][0], "o", color=C_SOMA_U, ms=5)
    ax.set_title("SOMA (u₁, v₁)", fontsize=10)
    ax.set_xlabel("u₁"); ax.set_ylabel("v₁")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)

    ax = axes[1]
    ax.plot(u_nc, nullclines["psyche_cubic"], "k-", lw=0.8, alpha=0.5,
            label="u-nullcline")
    ax.plot(u_nc, nullclines["psyche_linear"], "k--", lw=0.8, alpha=0.5,
            label="v-nullcline")
    ax.plot(results["u2"], results["v2"], color=C_PSYCHE_U, lw=0.6, alpha=0.7)
    ax.plot(results["u2"][0], results["v2"][0], "o", color=C_PSYCHE_U, ms=5)
    ax.set_title("PSYCHE (u₂, v₂)", fontsize=10)
    ax.set_xlabel("u₂"); ax.set_ylabel("v₂")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)

    plt.tight_layout()
    return fig


def _plot_energy_flux(results: dict) -> Figure:
    t = results["time"]
    fig, axes = plt.subplots(2, 1, figsize=(10, 4.5), sharex=True)
    fig.suptitle("Energy & Coupling Flux", fontsize=13)

    axes[0].plot(t, results["soma_energy"], color=C_SOMA_U, lw=1,
                 label="SOMA ½(u₁²+v₁²)")
    axes[0].plot(t, results["psyche_energy"], color=C_PSYCHE_U, lw=1,
                 label="PSYCHE ½(u₂²+v₂²)")
    axes[0].set_ylabel("Energy proxy")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.3)

    axes[1].fill_between(t, results["coupling_flux"], 0,
                         color=C_FLUX, alpha=0.4)
    axes[1].plot(t, results["coupling_flux"], color=C_FLUX, lw=0.8)
    axes[1].axhline(0, color="grey", lw=0.5)
    axes[1].set_ylabel("Net coupling flux")
    axes[1].set_xlabel("Time")
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    return fig


def _plot_tension_arc(results: dict, arc: NarrativeArc | None) -> Figure:
    """Plot the tension curve with narrative arc phase annotations."""
    t = results["time"]
    fig, ax = plt.subplots(figsize=(10, 3.5))
    fig.suptitle("Narrative Tension Arc", fontsize=13)

    if arc is not None:
        ax.plot(t, arc.tension_curve, color=C_TENSION, lw=1.5, label="Tension")
        ax.axvline(arc.climax_time, color=C_CLIMAX, lw=1.5, ls="--",
                    label=f"Climax (t={arc.climax_time:.1f})")

        phase_colors = {
            ArcPhase.EXPOSITION: "#264653",
            ArcPhase.RISING_ACTION: "#e9c46a",
            ArcPhase.CLIMAX: "#ff006e",
            ArcPhase.FALLING_ACTION: "#2a9d8f",
            ArcPhase.RESOLUTION: "#457b9d",
        }
        for t_start, t_end, phase in arc.phases:
            c = phase_colors.get(phase, "#888888")
            ax.axvspan(t_start, t_end, alpha=0.12, color=c)
            mid = (t_start + t_end) / 2
            ax.text(mid, ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else 0.01,
                    phase.name.replace("_", "\n"),
                    ha="center", va="top", fontsize=7, alpha=0.7)
    else:
        ax.text(0.5, 0.5, "Run a simulation first",
                ha="center", va="center", transform=ax.transAxes)

    ax.set_xlabel("Time")
    ax.set_ylabel("Tension")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    return fig


def _render_character_image(snap: dict | None, regime: str) -> np.ndarray | None:
    """Render character as numpy array for Gradio Image component."""
    if snap is None:
        return None
    appearance = compute_appearance(snap, regime)
    if _HAS_PIL:
        from PIL import Image as PILImage
        png = render_character(appearance, width=300, height=380)
        img = PILImage.open(io.BytesIO(png))
        return np.array(img)
    return None


# ---------------------------------------------------------------------------
# Preset scenario callback
# ---------------------------------------------------------------------------

def run_preset(scenario_key: str, adapter_name: str):
    soul.set_adapter(adapter_name)
    results, report = soul.run_scenario(scenario_key)
    nc = soul.get_nullclines()
    alignment = soul.get_alignment()
    arc = soul.get_arc()

    info = soul.get_scenario_info(scenario_key)
    header = f"### {info['name']}\n\n{info['description']}"

    regime_text = _build_regime_text(report)
    align_text = _build_alignment_text(alignment)
    arc_text = arc.arc_summary if arc else "N/A"

    snap = soul.get_state_snapshot()
    state_json = json.dumps(snap, indent=2) if snap else "{}"
    regime_name = report.coupled_regime.name
    char_img = _render_character_image(snap, regime_name)

    return (
        _plot_timeseries(results),
        _plot_phase_planes(results, nc),
        _plot_energy_flux(results),
        _plot_tension_arc(results, arc),
        header,
        regime_text,
        align_text,
        arc_text,
        state_json,
        char_img,
    )


# ---------------------------------------------------------------------------
# Custom run callback
# ---------------------------------------------------------------------------

def run_custom(
    soma_a, soma_eps, soma_b,
    psyche_a, psyche_eps, psyche_b,
    c12, c21, kappa, theta, tau,
    t_max,
    E_u, E_v,
    savage_mode,
    adapter_name,
    stim_kind, stim_target, stim_onset, stim_dur, stim_amp, stim_period,
):
    soul.set_adapter(adapter_name)

    if savage_mode:
        config = savage_config(t_max=float(t_max))
        # Override E_u/E_v with slider values even in savage mode
        config.emotion.E_u = float(E_u)
        config.emotion.E_v = float(E_v)
    else:
        config = SimulationConfig(
            t_max=float(t_max),
            soma=SubsystemParams(a=float(soma_a), epsilon=float(soma_eps),
                                 b=float(soma_b)),
            psyche=SubsystemParams(a=float(psyche_a), epsilon=float(psyche_eps),
                                   b=float(psyche_b)),
            coupling=CouplingParams(
                c12=float(c12), c21=float(c21),
                kappa=float(kappa), theta=float(theta), tau=float(tau),
            ),
            emotion=EmotionalDriveParams(
                E_u=float(E_u), E_v=float(E_v), E_v0=0.2,
            ),
        )

    # Build stimulus functions
    if stim_kind == "pulse":
        stim_fn = pulse_stimulus(float(stim_onset), float(stim_dur),
                                 float(stim_amp))
    elif stim_kind == "periodic":
        stim_fn = periodic_stimulus(float(stim_period), float(stim_dur),
                                    float(stim_amp))
    else:
        stim_fn = null_stimulus

    I1 = stim_fn if stim_target in ("SOMA", "Both") else null_stimulus
    I2 = stim_fn if stim_target in ("PSYCHE", "Both") else null_stimulus

    results, report = soul.run_custom(config, I1_func=I1, I2_func=I2)
    nc = soul.get_nullclines(config)
    alignment = soul.get_alignment()
    arc = soul.get_arc()

    regime_text = _build_regime_text(report)
    align_text = _build_alignment_text(alignment)
    arc_text = arc.arc_summary if arc else "N/A"

    snap = soul.get_state_snapshot()
    state_json = json.dumps(snap, indent=2) if snap else "{}"
    regime_name = report.coupled_regime.name
    char_img = _render_character_image(snap, regime_name)

    return (
        _plot_timeseries(results),
        _plot_phase_planes(results, nc),
        _plot_energy_flux(results),
        _plot_tension_arc(results, arc),
        regime_text,
        align_text,
        arc_text,
        state_json,
        char_img,
    )


# ---------------------------------------------------------------------------
# State inspector callback
# ---------------------------------------------------------------------------

def inspect_state(step: int):
    snap = soul.get_state_snapshot(int(step))
    if snap is None:
        return "{}", None
    regime_name = "QUIESCENT"
    if soul._last_report:
        regime_name = soul._last_report.coupled_regime.name
    char_img = _render_character_image(snap, regime_name)
    return json.dumps(snap, indent=2), char_img


# ---------------------------------------------------------------------------
# Text formatters
# ---------------------------------------------------------------------------

def _build_regime_text(report: RegimeReport) -> str:
    return (
        f"**SOMA regime:** {report.soma_regime.name} "
        f"({report.soma_spike_count} spikes)\n\n"
        f"**PSYCHE regime:** {report.psyche_regime.name} "
        f"({report.psyche_spike_count} spikes)\n\n"
        f"**Coupled regime:** {report.coupled_regime.name}\n\n"
        f"**Mean coupling flux:** {report.mean_coupling_flux:.4f}\n\n"
        f"---\n\n{report.description}"
    )


def _build_alignment_text(alignment: AlignmentScore | None) -> str:
    if alignment is None:
        return "N/A"
    return (
        f"**Cross-correlation:** {alignment.cross_correlation:.4f}\n\n"
        f"**Phase lag:** {alignment.phase_lag:.1f} steps\n\n"
        f"**Coherence index:** {alignment.coherence_index:.4f}\n\n"
        f"---\n\n{alignment.interpretation}"
    )


# ---------------------------------------------------------------------------
# Build the Gradio interface
# ---------------------------------------------------------------------------

def build_ui() -> gr.Blocks:
    scenario_choices = {
        soul.scenarios[k].name: k for k in soul.scenario_names
    }
    adapter_choices = [a.label for a in PEFT_ADAPTERS.values()]
    adapter_name_map = {a.label: a.name for a in PEFT_ADAPTERS.values()}

    with gr.Blocks(
        title="NeuroArousal — Coupled Excitable System Exhibit",
        theme=gr.themes.Soft(),
        css=MOBILE_CSS,
    ) as demo:
        gr.Markdown(
            "# NeuroArousal — Coupled Excitable System\n\n"
            "Interactive **Blyuss-Kyrychko SOMA-PSYCHE coupling** exhibit.  "
            "Explore how physiological and cognitive arousal channels interact."
        )

        # ================================================================
        # TAB 1 — Preset Scenarios
        # ================================================================
        with gr.Tab("Presets"):
            with gr.Row():
                with gr.Column(scale=1, min_width=280):
                    scenario_dd = gr.Dropdown(
                        choices=list(scenario_choices.keys()),
                        value="Resting State",
                        label="Scenario",
                    )
                    adapter_dd_preset = gr.Dropdown(
                        choices=adapter_choices,
                        value="Museum Default",
                        label="Narrative Persona (PEFT)",
                    )
                    run_preset_btn = gr.Button(
                        "Run Scenario", variant="primary", size="lg",
                    )
                    scenario_info = gr.Markdown()
                    regime_md = gr.Markdown(label="Regime Analysis")
                    align_md_preset = gr.Markdown(label="Alignment")
                    arc_md_preset = gr.Markdown(label="Narrative Arc")

                with gr.Column(scale=2, min_width=300):
                    ts_plot = gr.Plot(label="Time Series")
                    pp_plot = gr.Plot(label="Phase Planes")
                    ef_plot = gr.Plot(label="Energy & Flux")
                    ta_plot_preset = gr.Plot(label="Tension Arc")

            with gr.Accordion("State Inspector & Character", open=False):
                with gr.Row():
                    with gr.Column(scale=1):
                        state_json_preset = gr.Code(
                            label="Computational State (JSON)",
                            language="json",
                            lines=18,
                        )
                    with gr.Column(scale=1):
                        char_img_preset = gr.Image(
                            label="Character Visualisation",
                            type="numpy",
                            height=380,
                        )

            def _run_preset(display_name, adapter_label):
                key = scenario_choices[display_name]
                adapter_key = adapter_name_map.get(adapter_label, "default")
                return run_preset(key, adapter_key)

            run_preset_btn.click(
                fn=_run_preset,
                inputs=[scenario_dd, adapter_dd_preset],
                outputs=[
                    ts_plot, pp_plot, ef_plot, ta_plot_preset,
                    scenario_info, regime_md, align_md_preset, arc_md_preset,
                    state_json_preset, char_img_preset,
                ],
            )

        # ================================================================
        # TAB 2 — Custom Parameters
        # ================================================================
        with gr.Tab("Custom"):
            with gr.Row():
                with gr.Column(scale=1, min_width=280):
                    # --- Emotional drive sliders (exhibit-facing) ---
                    gr.Markdown("### Emotional Drive")
                    E_u_slider = gr.Slider(
                        0, 100, 50, step=1,
                        label="E_u — Arousal Drive (0–100)",
                    )
                    E_v_slider = gr.Slider(
                        0, 100, 50, step=1,
                        label="E_v — Valence Drive (0–100)",
                    )
                    savage_toggle = gr.Checkbox(
                        label="SAVAGE MODE",
                        value=False,
                    )
                    adapter_dd_custom = gr.Dropdown(
                        choices=adapter_choices,
                        value="Museum Default",
                        label="Narrative Persona (PEFT)",
                    )

                    gr.Markdown("### SOMA subsystem")
                    soma_a = gr.Slider(0.01, 0.99, 0.25, step=0.01,
                                       label="a₁ (threshold)")
                    soma_eps = gr.Slider(0.001, 0.1, 0.01, step=0.001,
                                         label="ε₁ (timescale)")
                    soma_b = gr.Slider(0.1, 2.0, 0.5, step=0.05,
                                       label="b₁ (recovery)")

                    gr.Markdown("### PSYCHE subsystem")
                    psyche_a = gr.Slider(0.01, 0.99, 0.20, step=0.01,
                                         label="a₂ (threshold)")
                    psyche_eps = gr.Slider(0.001, 0.1, 0.008, step=0.001,
                                           label="ε₂ (timescale)")
                    psyche_b = gr.Slider(0.1, 2.0, 0.45, step=0.05,
                                         label="b₂ (recovery)")

                    gr.Markdown("### Coupling")
                    c12 = gr.Slider(0.0, 1.0, 0.15, step=0.01,
                                    label="c₁₂ (PSYCHE→SOMA)")
                    c21 = gr.Slider(0.0, 1.0, 0.12, step=0.01,
                                    label="c₂₁ (SOMA→PSYCHE)")
                    kappa = gr.Slider(1.0, 50.0, 10.0, step=1.0,
                                      label="κ (sigmoid steepness)")
                    theta = gr.Slider(-0.5, 1.0, 0.3, step=0.05,
                                      label="θ (sigmoid midpoint)")
                    tau = gr.Slider(0.0, 30.0, 5.0, step=0.5,
                                    label="τ (delay)")

                    gr.Markdown("### Simulation")
                    t_max = gr.Slider(50, 500, 200, step=10, label="T_max")

                    gr.Markdown("### Stimulus")
                    stim_kind = gr.Radio(
                        ["none", "pulse", "periodic"],
                        value="none", label="Stimulus type",
                    )
                    stim_target = gr.Radio(
                        ["SOMA", "PSYCHE", "Both"],
                        value="SOMA", label="Target",
                    )
                    stim_onset = gr.Slider(0, 200, 20, step=1,
                                           label="Onset (pulse)")
                    stim_dur = gr.Slider(0.5, 20, 3, step=0.5,
                                         label="Duration")
                    stim_amp = gr.Slider(0.0, 2.0, 0.5, step=0.05,
                                         label="Amplitude")
                    stim_period = gr.Slider(5, 100, 40, step=1,
                                            label="Period (periodic)")

                    run_custom_btn = gr.Button(
                        "Run Custom", variant="primary", size="lg",
                    )

                with gr.Column(scale=2, min_width=300):
                    c_ts = gr.Plot(label="Time Series")
                    c_pp = gr.Plot(label="Phase Planes")
                    c_ef = gr.Plot(label="Energy & Flux")
                    c_ta = gr.Plot(label="Tension Arc")
                    c_regime = gr.Markdown(label="Regime Analysis")
                    c_align = gr.Markdown(label="Alignment")
                    c_arc = gr.Markdown(label="Narrative Arc")

            with gr.Accordion("State Inspector & Character", open=False):
                with gr.Row():
                    step_slider = gr.Slider(
                        0, 10000, 0, step=1,
                        label="Inspect Step (scrub through simulation)",
                    )
                with gr.Row():
                    with gr.Column(scale=1):
                        c_state_json = gr.Code(
                            label="Computational State (JSON)",
                            language="json",
                            lines=18,
                        )
                    with gr.Column(scale=1):
                        c_char_img = gr.Image(
                            label="Character Visualisation",
                            type="numpy",
                            height=380,
                        )

            def _run_custom_wrapper(
                sa, se, sb, pa, pe, pb,
                _c12, _c21, _kappa, _theta, _tau,
                _tmax, _eu, _ev, _savage, _adapter_label,
                _sk, _st, _so, _sd, _sa2, _sp,
            ):
                adapter_key = adapter_name_map.get(_adapter_label, "default")
                return run_custom(
                    sa, se, sb, pa, pe, pb,
                    _c12, _c21, _kappa, _theta, _tau,
                    _tmax, _eu, _ev, _savage, adapter_key,
                    _sk, _st, _so, _sd, _sa2, _sp,
                )

            run_custom_btn.click(
                fn=_run_custom_wrapper,
                inputs=[
                    soma_a, soma_eps, soma_b,
                    psyche_a, psyche_eps, psyche_b,
                    c12, c21, kappa, theta, tau,
                    t_max, E_u_slider, E_v_slider,
                    savage_toggle, adapter_dd_custom,
                    stim_kind, stim_target, stim_onset, stim_dur,
                    stim_amp, stim_period,
                ],
                outputs=[
                    c_ts, c_pp, c_ef, c_ta,
                    c_regime, c_align, c_arc,
                    c_state_json, c_char_img,
                ],
            )

            step_slider.release(
                fn=inspect_state,
                inputs=[step_slider],
                outputs=[c_state_json, c_char_img],
            )

        # ================================================================
        # TAB 3 — State Explorer (dedicated full-screen state view)
        # ================================================================
        with gr.Tab("State Explorer"):
            gr.Markdown(
                "### Full Computational State Viewer\n\n"
                "Scrub through every integration step to inspect the complete "
                "internal state of the Blyuss-Kyrychko system: activator / "
                "recovery variables, delayed states, sigmoid coupling values, "
                "energy proxies, emotional drive offsets, and config."
            )
            with gr.Row():
                explore_step = gr.Slider(
                    0, 10000, 0, step=1,
                    label="Integration Step",
                )
                explore_btn = gr.Button("Inspect", variant="secondary")

            with gr.Row():
                with gr.Column(scale=2):
                    explore_json = gr.Code(
                        label="Full State Snapshot",
                        language="json",
                        lines=30,
                    )
                with gr.Column(scale=1):
                    explore_char = gr.Image(
                        label="Character at Step",
                        type="numpy",
                        height=380,
                    )

            explore_btn.click(
                fn=inspect_state,
                inputs=[explore_step],
                outputs=[explore_json, explore_char],
            )
            explore_step.release(
                fn=inspect_state,
                inputs=[explore_step],
                outputs=[explore_json, explore_char],
            )

        # ================================================================
        # TAB 4 — About
        # ================================================================
        with gr.Tab("About"):
            gr.Markdown(
                "## Mathematical Background\n\n"
                "This exhibit simulates a **coupled excitable system** "
                "inspired by the Blyuss-Kyrychko framework for interacting "
                "populations with delay coupling.\n\n"
                "### Governing equations\n\n"
                "**SOMA** (physiological arousal):\n"
                "$$\\frac{du_1}{dt} = u_1(1-u_1)(u_1-a_1) - v_1 "
                "+ c_{12}\\,S\\bigl(u_2(t-\\tau)\\bigr) + I_1(t)$$\n"
                "$$\\frac{dv_1}{dt} = \\varepsilon_1\\,(b_1 u_1 - v_1)$$\n\n"
                "**PSYCHE** (cognitive/emotional arousal):\n"
                "$$\\frac{du_2}{dt} = u_2(1-u_2)(u_2-a_2) - v_2 "
                "+ c_{21}\\,S\\bigl(u_1(t-\\tau)\\bigr) + I_2(t)$$\n"
                "$$\\frac{dv_2}{dt} = \\varepsilon_2\\,(b_2 u_2 - v_2)$$\n\n"
                "where $S(x) = \\frac{1}{1+e^{-\\kappa(x-\\theta)}}$ is a "
                "sigmoidal coupling function and $\\tau$ is the coupling delay.\n\n"
                "### Emotional Drive Mapping\n\n"
                "| Slider | Internal | Effect |\n"
                "|--------|----------|--------|\n"
                "| E_u (0–100) | arousal_drive = E_u/100 | Tonic SOMA boost |\n"
                "| E_v (0–100) | valence_drive = E_v/100 − 0.5 | PSYCHE shift |\n"
                "| E_v0 | baseline = 0.2 | Resting valence offset |\n\n"
                "### Savage Mode Parameters\n\n"
                "| Parameter | Value |\n"
                "|-----------|-------|\n"
                "| ε (both) | 0.05 |\n"
                "| a (both) | 0.5 |\n"
                "| b (both) | 0.1 |\n"
                "| E_v0 | 0.2 |\n"
                "| c₁₂ | 0.35 |\n"
                "| c₂₁ | 0.30 |\n"
                "| κ | 20.0 |\n\n"
                "### PEFT Adapters\n\n"
                "Persona adapters modulate narrative tone and subtly adjust "
                "coupling/arousal to match the storytelling style.\n\n"
                "| Adapter | Tone | Coupling Scale | Arousal Bias |\n"
                "|---------|------|---------------|-------------|\n"
                + "".join(
                    f"| {a.label} | {a.narrative_tone} | "
                    f"×{a.coupling_scale} | +{a.arousal_bias} |\n"
                    for a in PEFT_ADAPTERS.values()
                )
                + "\n"
                "### Key parameters\n\n"
                "| Symbol | Meaning |\n"
                "|--------|---------|\n"
                "| $a$ | Excitability threshold (0 < a < 1) |\n"
                "| $\\varepsilon$ | Timescale separation (smaller → slower recovery) |\n"
                "| $b$ | Recovery gain |\n"
                "| $c_{12}, c_{21}$ | Inter-population coupling strengths |\n"
                "| $\\kappa$ | Sigmoid steepness |\n"
                "| $\\theta$ | Sigmoid midpoint |\n"
                "| $\\tau$ | Coupling delay |\n\n"
                "### References\n\n"
                "- Blyuss, K. B. & Kyrychko, Y. N. (2010). *Bull. Math. Biol.*, "
                "72, 490-505.\n"
                "- FitzHugh, R. (1961). *Biophys. J.*, 1(6), 445-466.\n"
                "- Nagumo, J. et al. (1962). *Proc. IRE*, 50(10), 2061-2070.\n"
            )

    return demo
