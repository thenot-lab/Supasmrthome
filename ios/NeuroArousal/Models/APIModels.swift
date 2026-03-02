import Foundation

// MARK: - Request Models

struct SubsystemIn: Codable {
    var a: Double = 0.25
    var epsilon: Double = 0.01
    var b: Double = 0.5
}

struct CouplingIn: Codable {
    var c12: Double = 0.15
    var c21: Double = 0.12
    var kappa: Double = 10.0
    var theta: Double = 0.3
    var tau: Double = 5.0
}

struct EmotionIn: Codable {
    var E_u: Double = 50.0
    var E_v: Double = 50.0
    var E_v0: Double = 0.2
}

struct StimulusIn: Codable {
    var kind: String = "none"
    var onset: Double = 20.0
    var duration: Double = 3.0
    var amplitude: Double = 0.5
    var period: Double = 40.0
}

struct CustomRunRequest: Codable {
    var dt: Double = 0.05
    var t_max: Double = 200.0
    var soma: SubsystemIn = SubsystemIn()
    var psyche: SubsystemIn = SubsystemIn(a: 0.20, epsilon: 0.008, b: 0.45)
    var coupling: CouplingIn = CouplingIn()
    var emotion: EmotionIn = EmotionIn()
    var savage_mode: Bool = false
    var ic_u1: Double = 0.0
    var ic_v1: Double = 0.0
    var ic_u2: Double = 0.0
    var ic_v2: Double = 0.0
    var soma_stimulus: StimulusIn = StimulusIn()
    var psyche_stimulus: StimulusIn = StimulusIn()
    var adapter: String = "default"
}

// MARK: - Response Models

struct RegimeOut: Codable {
    let soma_regime: String
    let psyche_regime: String
    let coupled_regime: String
    let soma_spike_count: Int
    let psyche_spike_count: Int
    let mean_coupling_flux: Double
    let description: String
}

struct AlignmentOut: Codable {
    let cross_correlation: Double
    let phase_lag: Double
    let coherence_index: Double
    let interpretation: String
}

struct ArcPhaseOut: Codable {
    let t_start: Double
    let t_end: Double
    let phase: String
}

struct NarrativeArcOut: Codable {
    let phases: [ArcPhaseOut]
    let climax_time: Double
    let climax_energy: Double
    let peak_spike_rate: Double
    let arc_summary: String
    let tension_curve: [Double]
}

struct SimulationOut: Codable {
    let time: [Double]
    let u1: [Double]
    let v1: [Double]
    let u2: [Double]
    let v2: [Double]
    let soma_energy: [Double]
    let psyche_energy: [Double]
    let coupling_flux: [Double]
    let report: RegimeOut
    let alignment: AlignmentOut?
    let arc: NarrativeArcOut?
}

struct ScenarioInfoOut: Codable {
    let name: String
    let description: String
    let soma_a: String
    let psyche_a: String
    let c12: String
    let c21: String
    let tau: String
}

struct AdapterOut: Codable {
    let name: String
    let label: String
    let description: String
}

struct CharacterAppearance: Codable {
    let body_colour: [Int]
    let aura_colour: [Int]
    let eye_colour: [Int]
    let expression: String
    let mouth_curve: Double
    let eye_openness: Double
    let pupil_dilation: Double
    let aura_intensity: Double
    let particle_count: Int
    let particle_speed: Double
    let posture_angle: Double
    let breathing_rate: Double
    let tremor: Double
}

struct StateSnapshot: Codable {
    let step: Int
    let t: Double
    let u1: Double
    let v1: Double
    let u2: Double
    let v2: Double
    let delayed_u1: Double
    let delayed_u2: Double
    let sigmoid_psyche_to_soma: Double
    let sigmoid_soma_to_psyche: Double
    let coupling_flux: Double
    let soma_energy: Double
    let psyche_energy: Double
    let arousal_drive: Double
    let valence_drive: Double
    let valence_baseline: Double
    let savage_mode: Bool
    let config: StateConfig
}

struct StateConfig: Codable {
    let dt: Double
    let soma_a: Double
    let soma_epsilon: Double
    let soma_b: Double
    let psyche_a: Double
    let psyche_epsilon: Double
    let psyche_b: Double
    let c12: Double
    let c21: Double
    let kappa: Double
    let theta: Double
    let tau: Double
    let E_u: Double
    let E_v: Double
    let E_v0: Double
}
