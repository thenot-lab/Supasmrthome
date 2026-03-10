package com.neuroarousal.api

import com.google.gson.annotations.SerializedName

// ── Auth Models ────────────────────────────────────────────

data class RegisterRequest(
    val username: String,
    val password: String,
    @SerializedName("display_name") val displayName: String = ""
)

data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String,
    @SerializedName("expires_in") val expiresIn: Int
)

data class UserResponse(
    val username: String,
    @SerializedName("display_name") val displayName: String,
    @SerializedName("created_at") val createdAt: Double
)

// ── Request Models ──────────────────────────────────────────

data class SubsystemIn(
    val a: Double = 0.25,
    val epsilon: Double = 0.01,
    val b: Double = 0.5
)

data class CouplingIn(
    val c12: Double = 0.15,
    val c21: Double = 0.12,
    val kappa: Double = 10.0,
    val theta: Double = 0.3,
    val tau: Double = 5.0
)

data class EmotionIn(
    @SerializedName("E_u") val eU: Double = 50.0,
    @SerializedName("E_v") val eV: Double = 50.0,
    @SerializedName("E_v0") val eV0: Double = 0.2
)

data class StimulusIn(
    val kind: String = "none",
    val onset: Double = 20.0,
    val duration: Double = 3.0,
    val amplitude: Double = 0.5,
    val period: Double = 40.0
)

data class CustomRunRequest(
    val dt: Double = 0.05,
    @SerializedName("t_max") val tMax: Double = 200.0,
    val soma: SubsystemIn = SubsystemIn(),
    val psyche: SubsystemIn = SubsystemIn(a = 0.20, epsilon = 0.008, b = 0.45),
    val coupling: CouplingIn = CouplingIn(),
    val emotion: EmotionIn = EmotionIn(),
    @SerializedName("savage_mode") val savageMode: Boolean = false,
    @SerializedName("ic_u1") val icU1: Double = 0.0,
    @SerializedName("ic_v1") val icV1: Double = 0.0,
    @SerializedName("ic_u2") val icU2: Double = 0.0,
    @SerializedName("ic_v2") val icV2: Double = 0.0,
    @SerializedName("soma_stimulus") val somaStimulus: StimulusIn = StimulusIn(),
    @SerializedName("psyche_stimulus") val psycheStimulus: StimulusIn = StimulusIn(),
    val adapter: String = "default"
)

// ── Response Models ─────────────────────────────────────────

data class RegimeOut(
    @SerializedName("soma_regime") val somaRegime: String,
    @SerializedName("psyche_regime") val psycheRegime: String,
    @SerializedName("coupled_regime") val coupledRegime: String,
    @SerializedName("soma_spike_count") val somaSpikeCount: Int,
    @SerializedName("psyche_spike_count") val psycheSpikeCount: Int,
    @SerializedName("mean_coupling_flux") val meanCouplingFlux: Double,
    val description: String
)

data class AlignmentOut(
    @SerializedName("cross_correlation") val crossCorrelation: Double,
    @SerializedName("phase_lag") val phaseLag: Double,
    @SerializedName("coherence_index") val coherenceIndex: Double,
    val interpretation: String
)

data class ArcPhaseOut(
    @SerializedName("t_start") val tStart: Double,
    @SerializedName("t_end") val tEnd: Double,
    val phase: String
)

data class NarrativeArcOut(
    val phases: List<ArcPhaseOut>,
    @SerializedName("climax_time") val climaxTime: Double,
    @SerializedName("climax_energy") val climaxEnergy: Double,
    @SerializedName("peak_spike_rate") val peakSpikeRate: Double,
    @SerializedName("arc_summary") val arcSummary: String,
    @SerializedName("tension_curve") val tensionCurve: List<Double>
)

data class SimulationOut(
    val time: List<Double>,
    val u1: List<Double>,
    val v1: List<Double>,
    val u2: List<Double>,
    val v2: List<Double>,
    @SerializedName("soma_energy") val somaEnergy: List<Double>,
    @SerializedName("psyche_energy") val psycheEnergy: List<Double>,
    @SerializedName("coupling_flux") val couplingFlux: List<Double>,
    val report: RegimeOut,
    val alignment: AlignmentOut?,
    val arc: NarrativeArcOut?
)

data class ScenarioInfoOut(
    val name: String,
    val description: String,
    @SerializedName("soma_a") val somaA: String,
    @SerializedName("psyche_a") val psycheA: String,
    val c12: String,
    val c21: String,
    val tau: String
)

data class AdapterOut(
    val name: String,
    val label: String,
    val description: String
)

data class StateSnapshot(
    val step: Int,
    val t: Double,
    val u1: Double,
    val v1: Double,
    val u2: Double,
    val v2: Double,
    @SerializedName("delayed_u1") val delayedU1: Double,
    @SerializedName("delayed_u2") val delayedU2: Double,
    @SerializedName("sigmoid_psyche_to_soma") val sigmoidPsycheToSoma: Double,
    @SerializedName("sigmoid_soma_to_psyche") val sigmoidSomaToPsyche: Double,
    @SerializedName("coupling_flux") val couplingFlux: Double,
    @SerializedName("soma_energy") val somaEnergy: Double,
    @SerializedName("psyche_energy") val psycheEnergy: Double,
    @SerializedName("arousal_drive") val arousalDrive: Double,
    @SerializedName("valence_drive") val valenceDrive: Double,
    @SerializedName("valence_baseline") val valenceBaseline: Double,
    @SerializedName("savage_mode") val savageMode: Boolean,
    val config: StateConfig
)

data class NullclineOut(
    val u: List<Double>,
    @SerializedName("soma_cubic") val somaCubic: List<Double>,
    @SerializedName("soma_linear") val somaLinear: List<Double>,
    @SerializedName("psyche_cubic") val psycheCubic: List<Double>,
    @SerializedName("psyche_linear") val psycheLinear: List<Double>
)

data class CharacterAppearanceOut(
    @SerializedName("body_colour") val bodyColour: List<Int>,
    @SerializedName("aura_colour") val auraColour: List<Int>,
    @SerializedName("eye_colour") val eyeColour: List<Int>,
    val expression: String,
    @SerializedName("mouth_curve") val mouthCurve: Double,
    @SerializedName("eye_openness") val eyeOpenness: Double,
    @SerializedName("pupil_dilation") val pupilDilation: Double,
    @SerializedName("aura_intensity") val auraIntensity: Double,
    @SerializedName("particle_count") val particleCount: Int,
    @SerializedName("particle_speed") val particleSpeed: Double,
    @SerializedName("posture_angle") val postureAngle: Double,
    @SerializedName("breathing_rate") val breathingRate: Double,
    val tremor: Double
)

data class StateConfig(
    val dt: Double,
    @SerializedName("soma_a") val somaA: Double,
    @SerializedName("soma_epsilon") val somaEpsilon: Double,
    @SerializedName("soma_b") val somaB: Double,
    @SerializedName("psyche_a") val psycheA: Double,
    @SerializedName("psyche_epsilon") val psycheEpsilon: Double,
    @SerializedName("psyche_b") val psycheB: Double,
    val c12: Double,
    val c21: Double,
    val kappa: Double,
    val theta: Double,
    val tau: Double,
    @SerializedName("E_u") val eU: Double,
    @SerializedName("E_v") val eV: Double,
    @SerializedName("E_v0") val eV0: Double
)
