import SwiftUI
import Charts

struct PresetsTab: View {
    @EnvironmentObject var api: APIClient

    @State private var scenarios: [String] = []
    @State private var selectedScenario = "resting_state"
    @State private var selectedAdapter = "default"
    @State private var adapters: [AdapterOut] = []
    @State private var result: SimulationOut?
    @State private var scenarioInfo: ScenarioInfoOut?
    @State private var characterImage: Data?
    @State private var errorMsg: String?

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                // Controls
                GroupBox("Scenario") {
                    VStack(spacing: 12) {
                        Picker("Preset", selection: $selectedScenario) {
                            ForEach(scenarios, id: \.self) { s in
                                Text(s.replacingOccurrences(of: "_", with: " ").capitalized)
                                    .tag(s)
                            }
                        }
                        .pickerStyle(.menu)

                        Picker("Narrative Persona", selection: $selectedAdapter) {
                            ForEach(adapters, id: \.name) { a in
                                Text(a.label).tag(a.name)
                            }
                        }
                        .pickerStyle(.menu)

                        Button(action: { Task { await runPreset() } }) {
                            HStack {
                                if api.isLoading {
                                    ProgressView()
                                        .tint(.white)
                                }
                                Text("Run Scenario")
                                    .fontWeight(.semibold)
                            }
                            .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(api.isLoading)
                    }
                }
                .padding(.horizontal)

                if let err = errorMsg {
                    Text(err).foregroundColor(.red).font(.caption).padding(.horizontal)
                }

                if let info = scenarioInfo {
                    GroupBox("Info") {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(info.name).font(.headline)
                            Text(info.description).font(.caption).foregroundColor(.secondary)
                        }
                    }
                    .padding(.horizontal)
                }

                if let r = result {
                    SimulationResultView(result: r, characterImage: characterImage)
                }
            }
            .padding(.vertical)
        }
        .task {
            await loadInitial()
        }
    }

    private func loadInitial() async {
        do {
            scenarios = try await api.listScenarios()
            adapters = try await api.listAdapters()
        } catch {
            errorMsg = error.localizedDescription
        }
    }

    private func runPreset() async {
        errorMsg = nil
        do {
            result = try await api.runScenario(selectedScenario, adapter: selectedAdapter)
            scenarioInfo = try? await api.getScenarioInfo(selectedScenario)
            characterImage = try? await api.getCharacterImage()
        } catch {
            errorMsg = error.localizedDescription
        }
    }
}
