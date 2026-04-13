import SwiftUI

/// Live Observer tab — polls the server's /live/events feed and the
/// /character/image endpoint so a curator or remote viewer can watch the
/// exhibit respond to visitor interactions in real time.
struct LiveTab: View {
    @EnvironmentObject var api: APIClient

    @State private var events: [LiveEventOut] = []
    @State private var characterImage: UIImage?
    @State private var latestId: Int = 0
    @State private var errorMsg: String?
    @State private var isGenerating = false
    @State private var animationImage: UIImage?
    @State private var selectedScenario = "savage_burst"
    @State private var scenarios: [String] = []
    @State private var pollTimer: Timer?

    private let pollInterval: TimeInterval = 2.0

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                header

                characterCard

                animationCard

                activityCard
            }
            .padding()
        }
        .task {
            scenarios = (try? await api.listScenarios()) ?? []
            if !scenarios.isEmpty && !scenarios.contains(selectedScenario) {
                selectedScenario = scenarios.first!
            }
            await pollOnce()
            startPolling()
        }
        .onDisappear {
            pollTimer?.invalidate()
            pollTimer = nil
        }
    }

    // MARK: - Components

    private var header: some View {
        VStack(spacing: 4) {
            Text("Live Observer")
                .font(.largeTitle)
                .fontWeight(.bold)
            Text("Streaming interactions from every client")
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
    }

    private var characterCard: some View {
        GroupBox("Character") {
            VStack(spacing: 12) {
                if let img = characterImage {
                    Image(uiImage: img)
                        .resizable()
                        .scaledToFit()
                        .frame(maxHeight: 320)
                        .cornerRadius(8)
                } else {
                    RoundedRectangle(cornerRadius: 8)
                        .fill(Color.black.opacity(0.2))
                        .frame(height: 240)
                        .overlay(
                            Text("Run a scenario on any client to populate.")
                                .foregroundColor(.secondary)
                                .font(.caption)
                                .multilineTextAlignment(.center)
                                .padding()
                        )
                }
                if let latest = events.last {
                    VStack(spacing: 2) {
                        Text(latest.summary)
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .multilineTextAlignment(.center)
                        Text("source: \(latest.source)")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                    }
                }
            }
            .frame(maxWidth: .infinity)
        }
    }

    private var animationCard: some View {
        GroupBox("Generate Animation") {
            VStack(spacing: 12) {
                Picker("Scenario", selection: $selectedScenario) {
                    ForEach(scenarios, id: \.self) { s in
                        Text(s.replacingOccurrences(of: "_", with: " ").capitalized)
                            .tag(s)
                    }
                }
                .pickerStyle(.menu)

                Button(action: { Task { await generateAnimation() } }) {
                    HStack {
                        if isGenerating { ProgressView().tint(.white) }
                        Text(isGenerating ? "Generating..." : "Generate Animation")
                            .fontWeight(.semibold)
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .disabled(isGenerating || scenarios.isEmpty)

                if let anim = animationImage {
                    Image(uiImage: anim)
                        .resizable()
                        .scaledToFit()
                        .frame(maxHeight: 300)
                        .cornerRadius(8)
                }
            }
        }
    }

    private var activityCard: some View {
        GroupBox("Activity Feed") {
            VStack(alignment: .leading, spacing: 8) {
                if events.isEmpty {
                    Text("No activity yet. Run a scenario from any tab.")
                        .font(.caption)
                        .foregroundColor(.secondary)
                } else {
                    ForEach(events.reversed().prefix(20)) { evt in
                        EventRow(event: evt)
                    }
                }
                if let err = errorMsg {
                    Text(err)
                        .font(.caption)
                        .foregroundColor(.red)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    // MARK: - Polling

    private func startPolling() {
        pollTimer?.invalidate()
        pollTimer = Timer.scheduledTimer(withTimeInterval: pollInterval, repeats: true) { _ in
            Task { await pollOnce() }
        }
    }

    private func pollOnce() async {
        do {
            let feed = try await api.listLiveEvents(limit: 40, sinceId: 0)
            let newEvents = feed.events
            let hadNewRun = newEvents.last?.id ?? 0 > latestId &&
                (newEvents.last?.type == "scenario_run" ||
                 newEvents.last?.type == "custom_run")
            events = newEvents
            if let newest = newEvents.last {
                latestId = newest.id
            }
            if hadNewRun || characterImage == nil {
                await refreshCharacter()
            }
            errorMsg = nil
        } catch {
            errorMsg = error.localizedDescription
        }
    }

    private func refreshCharacter() async {
        do {
            let data = try await api.getCharacterImage()
            if let img = UIImage(data: data) {
                characterImage = img
            }
        } catch {
            // Non-fatal — may be no simulation yet.
        }
    }

    private func generateAnimation() async {
        isGenerating = true
        defer { isGenerating = false }
        do {
            let data = try await api.getLiveFrames(
                scenario: selectedScenario, frames: 24,
            )
            if let img = UIImage(data: data) {
                animationImage = img
            }
            await pollOnce()
        } catch {
            errorMsg = error.localizedDescription
        }
    }
}

struct EventRow: View {
    let event: LiveEventOut

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Circle()
                .fill(color(for: event.type))
                .frame(width: 8, height: 8)
                .padding(.top, 6)
            VStack(alignment: .leading, spacing: 2) {
                Text(event.summary)
                    .font(.caption)
                Text("\(formattedTime) · \(event.source)")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
            Spacer(minLength: 0)
        }
    }

    private var formattedTime: String {
        let d = Date(timeIntervalSince1970: event.timestamp)
        let f = DateFormatter()
        f.dateFormat = "HH:mm:ss"
        return f.string(from: d)
    }

    private func color(for type: String) -> Color {
        switch type {
        case "scenario_run": return .green
        case "custom_run": return .blue
        case "adapter_change": return .purple
        case "frames_generated": return .orange
        default: return .gray
        }
    }
}
