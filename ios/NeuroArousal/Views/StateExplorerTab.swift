import SwiftUI

struct StateExplorerTab: View {
    @EnvironmentObject var api: APIClient
    @State private var step: Double = 0
    @State private var snapshot: StateSnapshot?
    @State private var characterImage: Data?
    @State private var errorMsg: String?

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                GroupBox("Integration Step") {
                    VStack(spacing: 8) {
                        HStack {
                            Text("Step: \(Int(step))")
                                .font(.headline)
                                .monospacedDigit()
                            Spacer()
                            if let s = snapshot {
                                Text("t = \(s.t, specifier: "%.2f")")
                                    .font(.subheadline)
                                    .foregroundColor(.secondary)
                                    .monospacedDigit()
                            }
                        }

                        Slider(value: $step, in: 0...10000, step: 1)
                            .onChange(of: step) { _ in
                                Task { await loadState() }
                            }

                        Button("Inspect") {
                            Task { await loadState() }
                        }
                        .buttonStyle(.bordered)
                    }
                }
                .padding(.horizontal)

                if let err = errorMsg {
                    Text(err).foregroundColor(.red).font(.caption).padding(.horizontal)
                }

                if let s = snapshot {
                    // State variables
                    GroupBox("State Variables") {
                        StateGrid(items: [
                            ("u1 (SOMA)", String(format: "%.6f", s.u1)),
                            ("v1 (recovery)", String(format: "%.6f", s.v1)),
                            ("u2 (PSYCHE)", String(format: "%.6f", s.u2)),
                            ("v2 (recovery)", String(format: "%.6f", s.v2)),
                        ])
                    }
                    .padding(.horizontal)

                    // Delayed state
                    GroupBox("Delayed State") {
                        StateGrid(items: [
                            ("delayed u1", String(format: "%.6f", s.delayed_u1)),
                            ("delayed u2", String(format: "%.6f", s.delayed_u2)),
                        ])
                    }
                    .padding(.horizontal)

                    // Coupling
                    GroupBox("Coupling") {
                        StateGrid(items: [
                            ("S(PSY->SOMA)", String(format: "%.6f", s.sigmoid_psyche_to_soma)),
                            ("S(SOMA->PSY)", String(format: "%.6f", s.sigmoid_soma_to_psyche)),
                            ("net flux", String(format: "%.6f", s.coupling_flux)),
                        ])
                    }
                    .padding(.horizontal)

                    // Energy
                    GroupBox("Energy") {
                        StateGrid(items: [
                            ("SOMA energy", String(format: "%.6f", s.soma_energy)),
                            ("PSYCHE energy", String(format: "%.6f", s.psyche_energy)),
                        ])
                    }
                    .padding(.horizontal)

                    // Drive
                    GroupBox("Emotional Drive") {
                        StateGrid(items: [
                            ("arousal drive", String(format: "%.4f", s.arousal_drive)),
                            ("valence drive", String(format: "%.4f", s.valence_drive)),
                            ("valence base", String(format: "%.4f", s.valence_baseline)),
                            ("savage", s.savage_mode ? "ON" : "OFF"),
                        ])
                    }
                    .padding(.horizontal)

                    // Config
                    GroupBox("Configuration") {
                        StateGrid(items: [
                            ("dt", String(format: "%.4f", s.config.dt)),
                            ("SOMA a", String(format: "%.3f", s.config.soma_a)),
                            ("SOMA eps", String(format: "%.4f", s.config.soma_epsilon)),
                            ("PSY a", String(format: "%.3f", s.config.psyche_a)),
                            ("c12", String(format: "%.3f", s.config.c12)),
                            ("c21", String(format: "%.3f", s.config.c21)),
                            ("kappa", String(format: "%.1f", s.config.kappa)),
                            ("theta", String(format: "%.2f", s.config.theta)),
                            ("tau", String(format: "%.1f", s.config.tau)),
                            ("E_u", String(format: "%.1f", s.config.E_u)),
                            ("E_v", String(format: "%.1f", s.config.E_v)),
                        ])
                    }
                    .padding(.horizontal)

                    // Character
                    if let imgData = characterImage, let uiImage = UIImage(data: imgData) {
                        GroupBox("Character") {
                            Image(uiImage: uiImage)
                                .resizable()
                                .aspectRatio(contentMode: .fit)
                                .frame(maxHeight: 300)
                                .clipShape(RoundedRectangle(cornerRadius: 12))
                        }
                        .padding(.horizontal)
                    }
                }
            }
            .padding(.vertical)
        }
    }

    private func loadState() async {
        errorMsg = nil
        do {
            snapshot = try await api.getState(step: Int(step))
            characterImage = try? await api.getCharacterImage(step: Int(step))
        } catch {
            errorMsg = error.localizedDescription
        }
    }
}

struct StateGrid: View {
    let items: [(String, String)]

    var body: some View {
        LazyVGrid(columns: [
            GridItem(.flexible(), alignment: .leading),
            GridItem(.flexible(), alignment: .trailing),
        ], spacing: 6) {
            ForEach(items, id: \.0) { label, value in
                Text(label)
                    .font(.caption)
                    .foregroundColor(.secondary)
                Text(value)
                    .font(.system(.caption, design: .monospaced))
                    .fontWeight(.medium)
            }
        }
    }
}
