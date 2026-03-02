package com.neuroarousal.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import com.neuroarousal.api.SimulationOut
import com.neuroarousal.ui.theme.*

@Composable
fun SimulationResultPanel(result: SimulationOut) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {

        // Regime report
        Card {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("Regime Analysis", style = MaterialTheme.typography.titleSmall)
                RegimeRow("SOMA", result.report.somaRegime, result.report.somaSpikeCount)
                RegimeRow("PSYCHE", result.report.psycheRegime, result.report.psycheSpikeCount)
                HorizontalDivider()
                Row {
                    Text("Coupled: ", style = MaterialTheme.typography.bodySmall)
                    Text(
                        result.report.coupledRegime,
                        style = MaterialTheme.typography.bodySmall,
                        color = regimeColor(result.report.coupledRegime)
                    )
                }
                Text("Flux: ${"%.4f".format(result.report.meanCouplingFlux)}",
                    style = MaterialTheme.typography.bodySmall, fontFamily = FontFamily.Monospace)
                Text(result.report.description, style = MaterialTheme.typography.bodySmall)
            }
        }

        // Time series chart
        Card {
            Column(Modifier.padding(12.dp)) {
                Text("Time Series", style = MaterialTheme.typography.titleSmall)
                Spacer(Modifier.height(8.dp))
                LineChart(
                    series = listOf(
                        ChartSeries("u1", result.u1, SomaU),
                        ChartSeries("u2", result.u2, PsycheU),
                    ),
                    modifier = Modifier.fillMaxWidth().height(180.dp)
                )
                Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                    ChartLegendItem("u1 SOMA", SomaU)
                    ChartLegendItem("u2 PSYCHE", PsycheU)
                }
            }
        }

        // Energy & Flux
        Card {
            Column(Modifier.padding(12.dp)) {
                Text("Energy & Flux", style = MaterialTheme.typography.titleSmall)
                Spacer(Modifier.height(8.dp))
                LineChart(
                    series = listOf(
                        ChartSeries("SOMA E", result.somaEnergy, SomaU),
                        ChartSeries("PSY E", result.psycheEnergy, PsycheU),
                        ChartSeries("Flux", result.couplingFlux, Flux),
                    ),
                    modifier = Modifier.fillMaxWidth().height(150.dp)
                )
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    ChartLegendItem("SOMA", SomaU)
                    ChartLegendItem("PSYCHE", PsycheU)
                    ChartLegendItem("Flux", Flux)
                }
            }
        }

        // Tension Arc
        result.arc?.let { arc ->
            Card {
                Column(Modifier.padding(12.dp)) {
                    Text("Narrative Arc", style = MaterialTheme.typography.titleSmall)
                    Spacer(Modifier.height(8.dp))
                    LineChart(
                        series = listOf(ChartSeries("Tension", arc.tensionCurve, Tension)),
                        modifier = Modifier.fillMaxWidth().height(120.dp)
                    )
                    Text(arc.arcSummary, style = MaterialTheme.typography.bodySmall)
                }
            }
        }

        // Alignment
        result.alignment?.let { align ->
            Card {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("Alignment", style = MaterialTheme.typography.titleSmall)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                        StatBadge("Corr", "%.3f".format(align.crossCorrelation))
                        StatBadge("Lag", "%.0f".format(align.phaseLag))
                        StatBadge("Coh", "%.3f".format(align.coherenceIndex))
                    }
                    Text(align.interpretation, style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}

@Composable
private fun RegimeRow(label: String, regime: String, spikes: Int) {
    Row(Modifier.fillMaxWidth()) {
        Text(label, style = MaterialTheme.typography.bodySmall, modifier = Modifier.width(60.dp))
        Text(regime, style = MaterialTheme.typography.bodySmall, color = regimeColor(regime))
        Spacer(Modifier.weight(1f))
        Text("$spikes spikes", style = MaterialTheme.typography.bodySmall,
            fontFamily = FontFamily.Monospace)
    }
}

@Composable
private fun StatBadge(label: String, value: String) {
    Column(horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally) {
        Text(value, style = MaterialTheme.typography.titleSmall, fontFamily = FontFamily.Monospace)
        Text(label, style = MaterialTheme.typography.labelSmall)
    }
}

@Composable
private fun ChartLegendItem(label: String, color: Color) {
    Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        Canvas(Modifier.size(8.dp)) { drawCircle(color) }
        Text(label, style = MaterialTheme.typography.labelSmall)
    }
}

private fun regimeColor(regime: String): Color = when (regime) {
    "QUIESCENT" -> Color(0xFF4CAF50)
    "EXCITABLE" -> Color(0xFFFF9800)
    "OSCILLATORY" -> Color(0xFF2196F3)
    "BISTABLE" -> Color(0xFF9C27B0)
    "CHAOTIC" -> Color(0xFFF44336)
    else -> Color.Gray
}

// ── Simple Canvas Line Chart ────────────────────────────────

data class ChartSeries(val label: String, val data: List<Double>, val color: Color)

@Composable
fun LineChart(
    series: List<ChartSeries>,
    modifier: Modifier = Modifier
) {
    Canvas(modifier = modifier) {
        if (series.isEmpty() || series.first().data.isEmpty()) return@Canvas

        val allValues = series.flatMap { it.data }
        val yMin = allValues.min()
        val yMax = allValues.max()
        val yRange = (yMax - yMin).let { if (it < 1e-10) 1.0 else it }
        val w = size.width
        val h = size.height
        val padding = 4f

        for (s in series) {
            val n = s.data.size
            if (n < 2) continue
            val step = maxOf(1, n / 600)

            val path = Path()
            var first = true
            for (i in 0 until n step step) {
                val x = padding + (i.toFloat() / (n - 1)) * (w - 2 * padding)
                val y = h - padding - ((s.data[i] - yMin) / yRange).toFloat() * (h - 2 * padding)
                if (first) {
                    path.moveTo(x, y)
                    first = false
                } else {
                    path.lineTo(x, y)
                }
            }
            drawPath(path, s.color, style = Stroke(width = 2f))
        }
    }
}
