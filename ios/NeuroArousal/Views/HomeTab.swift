import SwiftUI

struct HomeTab: View {
    @EnvironmentObject var api: APIClient

    @State private var scenarios: [String] = []
    @State private var serverStatus = "Checking..."
    @State private var selectedQuickScenario = "resting_state"
    @State private var quickResult: SimulationOut?
    @State private var errorMsg: String?

    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                // Header
                VStack(spacing: 4) {
                    Text("NeuroArousal")
                        .font(.largeTitle)
                        .fontWeight(.bold)
                    Text("Coupled Excitable System")
                        .font(.title3)
                        .foregroundColor(.secondary)
                }
                .padding(.top)

                // Status card
                GroupBox("System Status") {
                    VStack(alignment: .leading, spacing: 8) {
                        StatusRow(label: "Server", value: serverStatus,
                                  color: serverStatus.contains("Connected") ? .green : .orange)
                        StatusRow(label: "Scenarios", value: "\(scenarios.count) loaded",
                                  color: scenarios.isEmpty ? .red : .green)
                        StatusRow(label: "Auth", value: "Personal mode",
                                  color: .green)
                    }
                }
                .padding(.horizontal)

                // Quick launch
                GroupBox("Quick Launch") {
                    VStack(spacing: 12) {
                        Picker("Scenario", selection: $selectedQuickScenario) {
                            ForEach(scenarios, id: \.self) { s in
                                Text(s.replacingOccurrences(of: "_", with: " ").capitalized)
                                    .tag(s)
                            }
                        }
                        .pickerStyle(.menu)

                        Button(action: { Task { await quickRun() } }) {
                            HStack {
                                if api.isLoading { ProgressView().tint(.white) }
                                Text("Run Now")
                                    .fontWeight(.semibold)
                            }
                            .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(api.isLoading || scenarios.isEmpty)
                    }
                }
                .padding(.horizontal)

                if let err = errorMsg {
                    Text(err).foregroundColor(.red).font(.caption).padding(.horizontal)
                }

                if let r = quickResult {
                    GroupBox("Result") {
                        VStack(alignment: .leading, spacing: 6) {
                            HStack {
                                Text("Coupled:").fontWeight(.medium)
                                Text(r.report.coupled_regime)
                                    .fontWeight(.bold)
                                    .foregroundColor(regimeColor(r.report.coupled_regime))
                            }
                            .font(.subheadline)
                            Text("SOMA: \(r.report.soma_regime) (\(r.report.soma_spike_count) spikes)")
                                .font(.caption).foregroundColor(.secondary)
                            Text("PSYCHE: \(r.report.psyche_regime) (\(r.report.psyche_spike_count) spikes)")
                                .font(.caption).foregroundColor(.secondary)
                            Text(r.report.description)
                                .font(.caption2).foregroundColor(.secondary)
                                .lineLimit(4)
                        }
                    }
                    .padding(.horizontal)
                }

                // Navigation hints
                GroupBox("Explore") {
                    VStack(alignment: .leading, spacing: 10) {
                        NavHint(icon: "list.star", title: "Presets",
                                desc: "Run pre-configured scenarios with full analysis")
                        NavHint(icon: "slider.horizontal.3", title: "Custom",
                                desc: "Tune every parameter of the coupled system")
                        NavHint(icon: "cpu", title: "State Explorer",
                                desc: "Scrub through integration steps, inspect internals")
                        NavHint(icon: "info.circle", title: "About",
                                desc: "Mathematical background and references")
                    }
                }
                .padding(.horizontal)
            }
            .padding(.bottom)
        }
        .task {
            await checkStatus()
        }
    }

    private func checkStatus() async {
        do {
            scenarios = try await api.listScenarios()
            serverStatus = "Connected"
        } catch {
            serverStatus = "Offline"
            errorMsg = error.localizedDescription
        }
    }

    private func quickRun() async {
        errorMsg = nil
        do {
            quickResult = try await api.runScenario(selectedQuickScenario)
        } catch {
            errorMsg = error.localizedDescription
        }
    }

    private func regimeColor(_ regime: String) -> Color {
        switch regime {
        case "QUIESCENT": return .green
        case "EXCITABLE": return .orange
        case "OSCILLATORY": return .blue
        case "BISTABLE": return .purple
        case "CHAOTIC": return .red
        default: return .primary
        }
    }
}

struct StatusRow: View {
    let label: String
    let value: String
    let color: Color

    var body: some View {
        HStack {
            Circle()
                .fill(color)
                .frame(width: 8, height: 8)
            Text(label)
                .font(.caption)
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
                .font(.caption)
                .fontWeight(.medium)
        }
    }
}

struct NavHint: View {
    let icon: String
    let title: String
    let desc: String

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundColor(.accentColor)
                .frame(width: 28)
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(.subheadline).fontWeight(.medium)
                Text(desc).font(.caption).foregroundColor(.secondary)
            }
        }
    }
}
