import SwiftUI
import Charts

// MARK: - Data point for charts

struct TSPoint: Identifiable {
    let id = UUID()
    let t: Double
    let value: Double
    let series: String
}

// MARK: - Time Series Chart

struct TimeSeriesChart: View {
    let result: SimulationOut

    var body: some View {
        let points = buildPoints()
        Chart(points) { p in
            LineMark(
                x: .value("t", p.t),
                y: .value("val", p.value)
            )
            .foregroundStyle(by: .value("Series", p.series))
            .lineStyle(StrokeStyle(lineWidth: 1.2))
        }
        .chartForegroundStyleScale([
            "u1 SOMA": .red,
            "v1 SOMA": .orange,
            "u2 PSYCHE": .blue,
            "v2 PSYCHE": .teal,
        ])
        .chartLegend(.visible)
        .chartXAxisLabel("Time")
    }

    private func buildPoints() -> [TSPoint] {
        let step = max(1, result.time.count / 500)
        var pts: [TSPoint] = []
        for i in stride(from: 0, to: result.time.count, by: step) {
            let t = result.time[i]
            pts.append(TSPoint(t: t, value: result.u1[i], series: "u1 SOMA"))
            pts.append(TSPoint(t: t, value: result.v1[i], series: "v1 SOMA"))
            pts.append(TSPoint(t: t, value: result.u2[i], series: "u2 PSYCHE"))
            pts.append(TSPoint(t: t, value: result.v2[i], series: "v2 PSYCHE"))
        }
        return pts
    }
}

// MARK: - Phase Chart

struct PhasePoint: Identifiable {
    let id = UUID()
    let u: Double
    let v: Double
}

struct PhaseChart: View {
    let u: [Double]
    let v: [Double]
    let label: String
    let color: Color

    var body: some View {
        let points = buildPhasePoints()
        Chart(points) { p in
            LineMark(
                x: .value("u", p.u),
                y: .value("v", p.v)
            )
            .foregroundStyle(color.opacity(0.6))
            .lineStyle(StrokeStyle(lineWidth: 0.8))
        }
        .chartXAxisLabel("u")
        .chartYAxisLabel("v")
        .overlay(alignment: .topLeading) {
            Text(label)
                .font(.caption2)
                .fontWeight(.bold)
                .padding(4)
                .background(.ultraThinMaterial)
                .cornerRadius(4)
                .padding(4)
        }
    }

    private func buildPhasePoints() -> [PhasePoint] {
        let step = max(1, u.count / 400)
        var pts: [PhasePoint] = []
        for i in stride(from: 0, to: u.count, by: step) {
            pts.append(PhasePoint(u: u[i], v: v[i]))
        }
        return pts
    }
}

// MARK: - Energy / Flux Chart

struct EnergyFluxChart: View {
    let result: SimulationOut

    var body: some View {
        let points = buildEnergyPoints()
        Chart(points) { p in
            LineMark(
                x: .value("t", p.t),
                y: .value("val", p.value)
            )
            .foregroundStyle(by: .value("Series", p.series))
            .lineStyle(StrokeStyle(lineWidth: 1))
        }
        .chartForegroundStyleScale([
            "SOMA energy": .red,
            "PSYCHE energy": .blue,
            "Coupling flux": .teal,
        ])
        .chartLegend(.visible)
        .chartXAxisLabel("Time")
    }

    private func buildEnergyPoints() -> [TSPoint] {
        let step = max(1, result.time.count / 400)
        var pts: [TSPoint] = []
        for i in stride(from: 0, to: result.time.count, by: step) {
            let t = result.time[i]
            pts.append(TSPoint(t: t, value: result.soma_energy[i], series: "SOMA energy"))
            pts.append(TSPoint(t: t, value: result.psyche_energy[i], series: "PSYCHE energy"))
            pts.append(TSPoint(t: t, value: result.coupling_flux[i], series: "Coupling flux"))
        }
        return pts
    }
}

// MARK: - Tension Arc Chart

struct TensionChart: View {
    let time: [Double]
    let tension: [Double]
    let climaxTime: Double

    var body: some View {
        let points = buildTensionPoints()
        Chart {
            ForEach(points) { p in
                LineMark(
                    x: .value("t", p.t),
                    y: .value("tension", p.value)
                )
                .foregroundStyle(Color.yellow)
                .lineStyle(StrokeStyle(lineWidth: 1.5))
            }
            RuleMark(x: .value("climax", climaxTime))
                .foregroundStyle(.pink)
                .lineStyle(StrokeStyle(lineWidth: 1.5, dash: [5, 3]))
                .annotation(position: .top, alignment: .trailing) {
                    Text("Climax")
                        .font(.caption2)
                        .foregroundColor(.pink)
                }
        }
        .chartXAxisLabel("Time")
        .chartYAxisLabel("Tension")
    }

    private func buildTensionPoints() -> [TSPoint] {
        let step = max(1, time.count / 400)
        var pts: [TSPoint] = []
        let n = min(time.count, tension.count)
        for i in stride(from: 0, to: n, by: step) {
            pts.append(TSPoint(t: time[i], value: tension[i], series: "tension"))
        }
        return pts
    }
}
