import SwiftUI

struct ContentView: View {
    @EnvironmentObject var api: APIClient
    @State private var selectedTab = 0
    @State private var showSettings = false

    var body: some View {
        NavigationStack {
            TabView(selection: $selectedTab) {
                PresetsTab()
                    .tabItem {
                        Label("Presets", systemImage: "list.star")
                    }
                    .tag(0)

                CustomTab()
                    .tabItem {
                        Label("Custom", systemImage: "slider.horizontal.3")
                    }
                    .tag(1)

                StateExplorerTab()
                    .tabItem {
                        Label("State", systemImage: "cpu")
                    }
                    .tag(2)

                AboutTab()
                    .tabItem {
                        Label("About", systemImage: "info.circle")
                    }
                    .tag(3)
            }
            .navigationTitle("NeuroArousal")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: { showSettings = true }) {
                        Image(systemName: "gear")
                    }
                }
            }
            .sheet(isPresented: $showSettings) {
                ServerSettingsView()
            }
        }
    }
}

struct ServerSettingsView: View {
    @EnvironmentObject var api: APIClient
    @Environment(\.dismiss) var dismiss
    @State private var urlText = ""
    @State private var connectionStatus = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("Server URL") {
                    TextField("http://host:port", text: $urlText)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                }

                Section {
                    Button("Test Connection") {
                        Task { await testConnection() }
                    }
                    if !connectionStatus.isEmpty {
                        Text(connectionStatus)
                            .font(.caption)
                            .foregroundColor(connectionStatus.contains("OK") ? .green : .red)
                    }
                }

                Section {
                    Button("Save") {
                        api.baseURL = urlText.trimmingCharacters(in: .whitespacesAndNewlines)
                        dismiss()
                    }
                    .disabled(urlText.isEmpty)
                }
            }
            .navigationTitle("Server Settings")
            .onAppear { urlText = api.baseURL }
        }
    }

    private func testConnection() async {
        let saved = api.baseURL
        api.baseURL = urlText.trimmingCharacters(in: .whitespacesAndNewlines)
        do {
            let _ = try await api.listScenarios()
            connectionStatus = "OK — connected"
        } catch {
            connectionStatus = "Error: \(error.localizedDescription)"
        }
        api.baseURL = saved
    }
}
