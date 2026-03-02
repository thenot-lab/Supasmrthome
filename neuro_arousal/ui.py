"""
Gradio interactive UI for the NeuroArousal museum exhibit.

Provides:
  * Preset scenario selector with explanatory cards
  * Custom parameter sliders for all model parameters
  * Time-series plots (u, v for both SOMA and PSYCHE)
  * Phase-plane portraits with nullcline overlays
  * Energy and coupling-flux visualisations
  * Regime classification and narrative panel
"""

from __future__ import annotations

import gradio as gr
import numpy as np
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for server use
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from neuro_arousal.digital_soul import DigitalSoul, RegimeReport
from neuro_arousal.engine import (
    CouplingParams,
    SimulationConfig,
    SubsystemParams,
    null_stimulus,
    pulse_stimulus,
    periodic_stimulus,
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

    # SOMA phase plane
    ax = axes[0]
    ax.plot(u_nc, nullclines["soma_cubic"], "k-", lw=0.8, alpha=0.5,
            label="u-nullcline")
    ax.plot(u_nc, nullclines["soma_linear"], "k--", lw=0.8, alpha=0.5,
            label="v-nullcline")
    ax.plot(results["u1"], results["v1"], color=C_SOMA_U, lw=0.6, alpha=0.7)
    ax.plot(results["u1"][0], results["v1"][0], "o", color=C_SOMA_U, ms=5)
    ax.set_title("SOMA (u₁, v₁)", fontsize=10)
    ax.set_xlabel("u₁")
    ax.set_ylabel("v₁")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)

    # PSYCHE phase plane
    ax = axes[1]
    ax.plot(u_nc, nullclines["psyche_cubic"], "k-", lw=0.8, alpha=0.5,
            label="u-nullcline")
    ax.plot(u_nc, nullclines["psyche_linear"], "k--", lw=0.8, alpha=0.5,
            label="v-nullcline")
    ax.plot(results["u2"], results["v2"], color=C_PSYCHE_U, lw=0.6, alpha=0.7)
    ax.plot(results["u2"][0], results["v2"][0], "o", color=C_PSYCHE_U, ms=5)
    ax.set_title("PSYCHE (u₂, v₂)", fontsize=10)
    ax.set_xlabel("u₂")
    ax.set_ylabel("v₂")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)

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


# ---------------------------------------------------------------------------
# Scenario callback
# ---------------------------------------------------------------------------

def run_preset(scenario_key: str):
    results, report = soul.run_scenario(scenario_key)
    nc = soul.get_nullclines()

    info = soul.get_scenario_info(scenario_key)
    header = f"### {info['name']}\n\n{info['description']}"

    regime_text = (
        f"**SOMA regime:** {report.soma_regime.name} "
        f"({report.soma_spike_count} spikes)\n\n"
        f"**PSYCHE regime:** {report.psyche_regime.name} "
        f"({report.psyche_spike_count} spikes)\n\n"
        f"**Coupled regime:** {report.coupled_regime.name}\n\n"
        f"**Mean coupling flux:** {report.mean_coupling_flux:.4f}\n\n"
        f"---\n\n{report.description}"
    )

    return (
        _plot_timeseries(results),
        _plot_phase_planes(results, nc),
        _plot_energy_flux(results),
        header,
        regime_text,
    )


# ---------------------------------------------------------------------------
# Custom run callback
# ---------------------------------------------------------------------------

def run_custom(
    soma_a, soma_eps, soma_b,
    psyche_a, psyche_eps, psyche_b,
    c12, c21, kappa, theta, tau,
    t_max,
    stim_kind, stim_target, stim_onset, stim_dur, stim_amp, stim_period,
):
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

    regime_text = (
        f"**SOMA regime:** {report.soma_regime.name} "
        f"({report.soma_spike_count} spikes)\n\n"
        f"**PSYCHE regime:** {report.psyche_regime.name} "
        f"({report.psyche_spike_count} spikes)\n\n"
        f"**Coupled regime:** {report.coupled_regime.name}\n\n"
        f"**Mean coupling flux:** {report.mean_coupling_flux:.4f}\n\n"
        f"---\n\n{report.description}"
    )

    return (
        _plot_timeseries(results),
        _plot_phase_planes(results, nc),
        _plot_energy_flux(results),
        regime_text,
    )


# ---------------------------------------------------------------------------
# Build the Gradio interface
# ---------------------------------------------------------------------------

def build_ui() -> gr.Blocks:
    scenario_choices = {
        soul.scenarios[k].name: k for k in soul.scenario_names
    }

    with gr.Blocks(
        title="NeuroArousal — Coupled Excitable System Exhibit",
        theme=gr.themes.Soft(),
    ) as demo:
        gr.Markdown(
            "# NeuroArousal — Coupled Excitable System Exhibit\n\n"
            "Interactive demonstration of **Blyuss-Kyrychko-type SOMA-PSYCHE "
            "coupling** — a pair of FitzHugh-Nagumo oscillators linked by "
            "sigmoidal delay coupling.  Explore how physiological and "
            "cognitive arousal channels interact through preset scenarios "
            "or custom parameter tuning."
        )

        # ---- Preset tab ----
        with gr.Tab("Preset Scenarios"):
            with gr.Row():
                with gr.Column(scale=1):
                    scenario_dd = gr.Dropdown(
                        choices=list(scenario_choices.keys()),
                        value="Resting State",
                        label="Choose scenario",
                    )
                    run_preset_btn = gr.Button("Run Scenario", variant="primary")
                    scenario_info = gr.Markdown()
                    regime_md = gr.Markdown(label="Regime Analysis")

                with gr.Column(scale=2):
                    ts_plot = gr.Plot(label="Time Series")
                    pp_plot = gr.Plot(label="Phase Planes")
                    ef_plot = gr.Plot(label="Energy & Flux")

            def _run_preset(display_name):
                key = scenario_choices[display_name]
                return run_preset(key)

            run_preset_btn.click(
                fn=_run_preset,
                inputs=[scenario_dd],
                outputs=[ts_plot, pp_plot, ef_plot, scenario_info, regime_md],
            )

        # ---- Custom tab ----
        with gr.Tab("Custom Parameters"):
            with gr.Row():
                with gr.Column(scale=1):
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

                    run_custom_btn = gr.Button("Run Custom", variant="primary")

                with gr.Column(scale=2):
                    c_ts = gr.Plot(label="Time Series")
                    c_pp = gr.Plot(label="Phase Planes")
                    c_ef = gr.Plot(label="Energy & Flux")
                    c_regime = gr.Markdown(label="Regime Analysis")

            run_custom_btn.click(
                fn=run_custom,
                inputs=[
                    soma_a, soma_eps, soma_b,
                    psyche_a, psyche_eps, psyche_b,
                    c12, c21, kappa, theta, tau,
                    t_max,
                    stim_kind, stim_target, stim_onset, stim_dur,
                    stim_amp, stim_period,
                ],
                outputs=[c_ts, c_pp, c_ef, c_regime],
            )

        # ---- About tab ----
        with gr.Tab("About the Model"):
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
