package com.neuroarousal.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import com.google.gson.GsonBuilder

@Composable
fun StateExplorerScreen(vm: MainViewModel) {
    var step by remember { mutableFloatStateOf(0f) }
    val gson = remember { GsonBuilder().setPrettyPrinting().create() }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(
            "Full Computational State Viewer",
            style = MaterialTheme.typography.titleMedium
        )
        Text(
            "Scrub through every integration step to inspect the complete " +
            "internal state of the Blyuss-Kyrychko system.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Card {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row {
                    Text("Step: ${step.toInt()}", style = MaterialTheme.typography.titleSmall)
                    Spacer(Modifier.weight(1f))
                    vm.stateSnapshot?.let {
                        Text("t = ${"%.2f".format(it.t)}",
                            style = MaterialTheme.typography.bodySmall,
                            fontFamily = FontFamily.Monospace)
                    }
                }

                Slider(
                    value = step,
                    onValueChange = { step = it },
                    valueRange = 0f..10000f,
                    steps = 0,
                    onValueChangeFinished = { vm.inspectState(step.toInt()) }
                )

                Button(
                    onClick = { vm.inspectState(step.toInt()) },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Inspect")
                }
            }
        }

        vm.errorMessage?.let {
            Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
        }

        vm.stateSnapshot?.let { snap ->
            // State Variables
            StateCard("State Variables") {
                StateRow("u1 (SOMA)", "%.6f".format(snap.u1))
                StateRow("v1 (recovery)", "%.6f".format(snap.v1))
                StateRow("u2 (PSYCHE)", "%.6f".format(snap.u2))
                StateRow("v2 (recovery)", "%.6f".format(snap.v2))
            }

            StateCard("Delayed State") {
                StateRow("delayed u1", "%.6f".format(snap.delayedU1))
                StateRow("delayed u2", "%.6f".format(snap.delayedU2))
            }

            StateCard("Coupling") {
                StateRow("S(PSY->SOMA)", "%.6f".format(snap.sigmoidPsycheToSoma))
                StateRow("S(SOMA->PSY)", "%.6f".format(snap.sigmoidSomaToPsyche))
                StateRow("net flux", "%.6f".format(snap.couplingFlux))
            }

            StateCard("Energy") {
                StateRow("SOMA energy", "%.6f".format(snap.somaEnergy))
                StateRow("PSYCHE energy", "%.6f".format(snap.psycheEnergy))
            }

            StateCard("Emotional Drive") {
                StateRow("arousal drive", "%.4f".format(snap.arousalDrive))
                StateRow("valence drive", "%.4f".format(snap.valenceDrive))
                StateRow("valence base", "%.4f".format(snap.valenceBaseline))
                StateRow("savage", if (snap.savageMode) "ON" else "OFF")
            }

            StateCard("Configuration") {
                StateRow("dt", "%.4f".format(snap.config.dt))
                StateRow("SOMA a", "%.3f".format(snap.config.somaA))
                StateRow("SOMA eps", "%.4f".format(snap.config.somaEpsilon))
                StateRow("PSY a", "%.3f".format(snap.config.psycheA))
                StateRow("c12", "%.3f".format(snap.config.c12))
                StateRow("c21", "%.3f".format(snap.config.c21))
                StateRow("kappa", "%.1f".format(snap.config.kappa))
                StateRow("theta", "%.2f".format(snap.config.theta))
                StateRow("tau", "%.1f".format(snap.config.tau))
                StateRow("E_u", "%.1f".format(snap.config.eU))
                StateRow("E_v", "%.1f".format(snap.config.eV))
            }

            // Raw JSON
            Card {
                Column(Modifier.padding(12.dp)) {
                    Text("Raw JSON", style = MaterialTheme.typography.titleSmall)
                    Spacer(Modifier.height(4.dp))
                    Text(
                        gson.toJson(snap),
                        style = MaterialTheme.typography.bodySmall,
                        fontFamily = FontFamily.Monospace
                    )
                }
            }
        }
    }
}

@Composable
fun StateCard(title: String, content: @Composable ColumnScope.() -> Unit) {
    Card {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall)
            content()
        }
    }
}

@Composable
fun StateRow(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth()) {
        Text(label, style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.weight(1f))
        Text(value, style = MaterialTheme.typography.bodySmall,
            fontFamily = FontFamily.Monospace)
    }
}
