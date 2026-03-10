import SwiftUI
import Charts

struct SimulationResultView: View {
    let result: SimulationOut
    let characterImage: Data?

    @State private var expandedSection: String?

    var body: some View {
        VStack(spacing: 12) {
            // Regime report
            GroupBox("Regime Analysis") {
                VStack(alignment: .leading, spacing: 6) {
                    RegimeRow(label: "SOMA", regime: result.report.soma_regime,
                              spikes: result.report.soma_spike_count)
                    RegimeRow(label: "PSYCHE", regime: result.report.psyche_regime,
                              spikes: result.report.psyche_spike_count)
                    Divider()
                    HStack {
                        Text("Coupled:").fontWeight(.medium)
                        Text(result.report.coupled_regime)
                            .foregroundColor(regimeColor(result.report.coupled_regime))
                            .fontWeight(.bold)
                    }
                    .font(.subheadline)
                    Text("Flux: \(result.report.mean_coupling_flux, specifier: "%.4f")")
                        .font(.caption).foregroundColor(.secondary)
                    Text(result.report.description)
                        .font(.caption2).foregroundColor(.secondary)
                        .lineLimit(6)
                }
            }
            .padding(.horizontal)

            // Time Series Chart
            GroupBox("Time Series") {
                TimeSeriesChart(result: result)
                    .frame(height: 220)
            }
            .padding(.horizontal)

            // Phase Planes
            GroupBox("Phase Planes") {
                HStack(spacing: 8) {
                    PhaseChart(u: result.u1, v: result.v1, label: "SOMA",
                               color: .red)
                        .frame(height: 180)
                    PhaseChart(u: result.u2, v: result.v2, label: "PSYCHE",
                               color: .blue)
                        .frame(height: 180)
                }
            }
            .padding(.horizontal)

            // Energy & Flux
            GroupBox("Energy & Flux") {
                EnergyFluxChart(result: result)
                    .frame(height: 200)
            }
            .padding(.horizontal)

            // Tension Arc
            if let arc = result.arc {
                GroupBox("Narrative Arc") {
                    VStack(alignment: .leading, spacing: 6) {
                        TensionChart(time: result.time, tension: arc.tension_curve,
                                     climaxTime: arc.climax_time)
                            .frame(height: 150)
                        Text(arc.arc_summary)
                            .font(.caption).foregroundColor(.secondary)
                    }
                }
                .padding(.horizontal)
            }

            // Alignment
            if let align = result.alignment {
                GroupBox("Alignment") {
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            StatBadge(label: "Corr", value: String(format: "%.3f", align.cross_correlation))
                            StatBadge(label: "Lag", value: String(format: "%.0f", align.phase_lag))
                            StatBadge(label: "Coh", value: String(format: "%.3f", align.coherence_index))
                        }
                        Text(align.interpretation)
                            .font(.caption).foregroundColor(.secondary)
                    }
                }
                .padding(.horizontal)
            }

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

struct RegimeRow: View {
    let label: String
    let regime: String
    let spikes: Int

    var body: some View {
        HStack {
            Text(label).font(.caption).frame(width: 60, alignment: .leading)
            Text(regime).font(.caption).fontWeight(.semibold)
            Spacer()
            Text("\(spikes) spikes").font(.caption2).foregroundColor(.secondary)
        }
    }
}

struct StatBadge: View {
    let label: String
    let value: String

    var body: some View {
        VStack(spacing: 2) {
            Text(value)
                .font(.system(.caption, design: .monospaced))
                .fontWeight(.bold)
            Text(label)
                .font(.caption2)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(6)
        .background(Color(.systemGray6))
        .cornerRadius(8)
    }
}
