import SwiftUI

struct CustomTab: View {
    @EnvironmentObject var api: APIClient

    // Emotional drive
    @State private var eU: Double = 50
    @State private var eV: Double = 50
    @State private var savageMode = false
    @State private var selectedAdapter = "default"
    @State private var adapters: [AdapterOut] = []

    // SOMA
    @State private var somaA: Double = 0.25
    @State private var somaEps: Double = 0.01
    @State private var somaB: Double = 0.5

    // PSYCHE
    @State private var psycheA: Double = 0.20
    @State private var psycheEps: Double = 0.008
    @State private var psycheB: Double = 0.45

    // Coupling
    @State private var c12: Double = 0.15
    @State private var c21: Double = 0.12
    @State private var kappa: Double = 10.0
    @State private var theta: Double = 0.3
    @State private var tau: Double = 5.0

    // Simulation
    @State private var tMax: Double = 200

    // Stimulus
    @State private var stimKind = "none"
    @State private var stimTarget = "SOMA"
    @State private var stimOnset: Double = 20
    @State private var stimDur: Double = 3
    @State private var stimAmp: Double = 0.5
    @State private var stimPeriod: Double = 40

    @State private var result: SimulationOut?
    @State private var characterImage: Data?
    @State private var errorMsg: String?

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                // Emotional Drive
                GroupBox("Emotional Drive") {
                    VStack(spacing: 8) {
                        SliderRow(label: "E_u (Arousal)", value: $eU, range: 0...100, step: 1)
                        SliderRow(label: "E_v (Valence)", value: $eV, range: 0...100, step: 1)
                        Toggle("SAVAGE MODE", isOn: $savageMode)
                            .tint(.red)
                            .fontWeight(savageMode ? .bold : .regular)
                        Picker("Persona (PEFT)", selection: $selectedAdapter) {
                            ForEach(adapters, id: \.name) { a in
                                Text(a.label).tag(a.name)
                            }
                        }
                        .pickerStyle(.menu)
                    }
                }
                .padding(.horizontal)
                .overlay(
                    savageMode ?
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(Color.red, lineWidth: 2)
                        .padding(.horizontal)
                    : nil
                )

                // SOMA
                GroupBox("SOMA Subsystem") {
                    VStack(spacing: 6) {
                        SliderRow(label: "a1 (threshold)", value: $somaA, range: 0.01...0.99, step: 0.01)
                        SliderRow(label: "e1 (timescale)", value: $somaEps, range: 0.001...0.1, step: 0.001)
                        SliderRow(label: "b1 (recovery)", value: $somaB, range: 0.1...2.0, step: 0.05)
                    }
                }
                .padding(.horizontal)

                // PSYCHE
                GroupBox("PSYCHE Subsystem") {
                    VStack(spacing: 6) {
                        SliderRow(label: "a2 (threshold)", value: $psycheA, range: 0.01...0.99, step: 0.01)
                        SliderRow(label: "e2 (timescale)", value: $psycheEps, range: 0.001...0.1, step: 0.001)
                        SliderRow(label: "b2 (recovery)", value: $psycheB, range: 0.1...2.0, step: 0.05)
                    }
                }
                .padding(.horizontal)

                // Coupling
                GroupBox("Coupling") {
                    VStack(spacing: 6) {
                        SliderRow(label: "c12 (PSY->SOMA)", value: $c12, range: 0...1, step: 0.01)
                        SliderRow(label: "c21 (SOMA->PSY)", value: $c21, range: 0...1, step: 0.01)
                        SliderRow(label: "kappa (steepness)", value: $kappa, range: 1...50, step: 1)
                        SliderRow(label: "theta (midpoint)", value: $theta, range: -0.5...1, step: 0.05)
                        SliderRow(label: "tau (delay)", value: $tau, range: 0...30, step: 0.5)
                    }
                }
                .padding(.horizontal)

                // Simulation
                GroupBox("Simulation") {
                    SliderRow(label: "T_max", value: $tMax, range: 50...500, step: 10)
                }
                .padding(.horizontal)

                // Stimulus
                GroupBox("Stimulus") {
                    VStack(spacing: 8) {
                        Picker("Type", selection: $stimKind) {
                            Text("None").tag("none")
                            Text("Pulse").tag("pulse")
                            Text("Periodic").tag("periodic")
                        }
                        .pickerStyle(.segmented)

                        Picker("Target", selection: $stimTarget) {
                            Text("SOMA").tag("SOMA")
                            Text("PSYCHE").tag("PSYCHE")
                            Text("Both").tag("Both")
                        }
                        .pickerStyle(.segmented)

                        if stimKind != "none" {
                            SliderRow(label: "Onset", value: $stimOnset, range: 0...200, step: 1)
                            SliderRow(label: "Duration", value: $stimDur, range: 0.5...20, step: 0.5)
                            SliderRow(label: "Amplitude", value: $stimAmp, range: 0...2, step: 0.05)
                        }
                        if stimKind == "periodic" {
                            SliderRow(label: "Period", value: $stimPeriod, range: 5...100, step: 1)
                        }
                    }
                }
                .padding(.horizontal)

                // Run button
                Button(action: { Task { await runCustom() } }) {
                    HStack {
                        if api.isLoading { ProgressView().tint(.white) }
                        Text(savageMode ? "UNLEASH SAVAGE" : "Run Custom")
                            .fontWeight(.semibold)
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(savageMode ? .red : .blue)
                .padding(.horizontal)
                .disabled(api.isLoading)

                if let err = errorMsg {
                    Text(err).foregroundColor(.red).font(.caption).padding(.horizontal)
                }

                if let r = result {
                    SimulationResultView(result: r, characterImage: characterImage)
                }
            }
            .padding(.vertical)
        }
        .task {
            adapters = (try? await api.listAdapters()) ?? []
        }
    }

    private func runCustom() async {
        errorMsg = nil
        let req = CustomRunRequest(
            dt: 0.05,
            t_max: tMax,
            soma: SubsystemIn(a: somaA, epsilon: somaEps, b: somaB),
            psyche: SubsystemIn(a: psycheA, epsilon: psycheEps, b: psycheB),
            coupling: CouplingIn(c12: c12, c21: c21, kappa: kappa, theta: theta, tau: tau),
            emotion: EmotionIn(E_u: eU, E_v: eV, E_v0: 0.2),
            savage_mode: savageMode,
            soma_stimulus: StimulusIn(kind: stimKind, onset: stimOnset, duration: stimDur,
                                       amplitude: stimAmp, period: stimPeriod),
            psyche_stimulus: StimulusIn(),
            adapter: selectedAdapter
        )
        do {
            result = try await api.runCustom(req)
            characterImage = try? await api.getCharacterImage()
        } catch {
            errorMsg = error.localizedDescription
        }
    }
}

// MARK: - Slider Row

struct SliderRow: View {
    let label: String
    @Binding var value: Double
    let range: ClosedRange<Double>
    let step: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack {
                Text(label).font(.caption).foregroundColor(.secondary)
                Spacer()
                Text(formatValue(value)).font(.caption).monospacedDigit()
            }
            Slider(value: $value, in: range, step: step)
        }
    }

    private func formatValue(_ v: Double) -> String {
        if step >= 1 { return String(format: "%.0f", v) }
        if step >= 0.01 { return String(format: "%.2f", v) }
        return String(format: "%.3f", v)
    }
}
