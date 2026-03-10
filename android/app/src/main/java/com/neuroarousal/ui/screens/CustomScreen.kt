package com.neuroarousal.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.neuroarousal.api.*
import com.neuroarousal.ui.components.LabeledSlider
import com.neuroarousal.ui.components.SimulationResultPanel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CustomScreen(vm: MainViewModel) {
    // Emotional drive
    var eU by remember { mutableFloatStateOf(50f) }
    var eV by remember { mutableFloatStateOf(50f) }
    var savageMode by remember { mutableStateOf(false) }
    var selectedAdapter by remember { mutableStateOf("default") }
    var adapterExpanded by remember { mutableStateOf(false) }

    // SOMA
    var somaA by remember { mutableFloatStateOf(0.25f) }
    var somaEps by remember { mutableFloatStateOf(0.01f) }
    var somaB by remember { mutableFloatStateOf(0.5f) }

    // PSYCHE
    var psycheA by remember { mutableFloatStateOf(0.20f) }
    var psycheEps by remember { mutableFloatStateOf(0.008f) }
    var psycheB by remember { mutableFloatStateOf(0.45f) }

    // Coupling
    var c12 by remember { mutableFloatStateOf(0.15f) }
    var c21 by remember { mutableFloatStateOf(0.12f) }
    var kappa by remember { mutableFloatStateOf(10f) }
    var theta by remember { mutableFloatStateOf(0.3f) }
    var tau by remember { mutableFloatStateOf(5f) }

    // Simulation
    var tMax by remember { mutableFloatStateOf(200f) }

    // Stimulus
    var stimKind by remember { mutableStateOf("none") }
    var stimTarget by remember { mutableStateOf("SOMA") }
    var stimOnset by remember { mutableFloatStateOf(20f) }
    var stimDur by remember { mutableFloatStateOf(3f) }
    var stimAmp by remember { mutableFloatStateOf(0.5f) }
    var stimPeriod by remember { mutableFloatStateOf(40f) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Emotional Drive
        Card(
            colors = if (savageMode) CardDefaults.cardColors(containerColor = Color(0xFF2D0011))
                     else CardDefaults.cardColors()
        ) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Emotional Drive", style = MaterialTheme.typography.titleMedium)
                LabeledSlider("E_u (Arousal)", eU, 0f..100f, 1f) { eU = it }
                LabeledSlider("E_v (Valence)", eV, 0f..100f, 1f) { eV = it }

                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("SAVAGE MODE", color = if (savageMode) Color.Red else Color.Unspecified)
                    Spacer(Modifier.weight(1f))
                    Switch(checked = savageMode, onCheckedChange = { savageMode = it })
                }

                ExposedDropdownMenuBox(
                    expanded = adapterExpanded,
                    onExpandedChange = { adapterExpanded = it }
                ) {
                    OutlinedTextField(
                        value = vm.adapters.find { it.name == selectedAdapter }?.label ?: "Default",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Persona (PEFT)") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(adapterExpanded) },
                        modifier = Modifier.menuAnchor().fillMaxWidth()
                    )
                    ExposedDropdownMenu(adapterExpanded, { adapterExpanded = false }) {
                        vm.adapters.forEach { a ->
                            DropdownMenuItem(
                                text = { Text(a.label) },
                                onClick = { selectedAdapter = a.name; adapterExpanded = false }
                            )
                        }
                    }
                }
            }
        }

        // SOMA
        Card {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("SOMA Subsystem", style = MaterialTheme.typography.titleSmall)
                LabeledSlider("a1 (threshold)", somaA, 0.01f..0.99f, 0.01f) { somaA = it }
                LabeledSlider("e1 (timescale)", somaEps, 0.001f..0.1f, 0.001f) { somaEps = it }
                LabeledSlider("b1 (recovery)", somaB, 0.1f..2f, 0.05f) { somaB = it }
            }
        }

        // PSYCHE
        Card {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("PSYCHE Subsystem", style = MaterialTheme.typography.titleSmall)
                LabeledSlider("a2 (threshold)", psycheA, 0.01f..0.99f, 0.01f) { psycheA = it }
                LabeledSlider("e2 (timescale)", psycheEps, 0.001f..0.1f, 0.001f) { psycheEps = it }
                LabeledSlider("b2 (recovery)", psycheB, 0.1f..2f, 0.05f) { psycheB = it }
            }
        }

        // Coupling
        Card {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("Coupling", style = MaterialTheme.typography.titleSmall)
                LabeledSlider("c12 (PSY->SOMA)", c12, 0f..1f, 0.01f) { c12 = it }
                LabeledSlider("c21 (SOMA->PSY)", c21, 0f..1f, 0.01f) { c21 = it }
                LabeledSlider("kappa (steep)", kappa, 1f..50f, 1f) { kappa = it }
                LabeledSlider("theta (mid)", theta, -0.5f..1f, 0.05f) { theta = it }
                LabeledSlider("tau (delay)", tau, 0f..30f, 0.5f) { tau = it }
            }
        }

        // Simulation & Stimulus
        Card {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("Simulation", style = MaterialTheme.typography.titleSmall)
                LabeledSlider("T_max", tMax, 50f..500f, 10f) { tMax = it }

                Spacer(Modifier.height(8.dp))
                Text("Stimulus", style = MaterialTheme.typography.titleSmall)

                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    listOf("none", "pulse", "periodic").forEach { kind ->
                        FilterChip(
                            selected = stimKind == kind,
                            onClick = { stimKind = kind },
                            label = { Text(kind.replaceFirstChar { it.uppercase() }) }
                        )
                    }
                }

                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    listOf("SOMA", "PSYCHE", "Both").forEach { target ->
                        FilterChip(
                            selected = stimTarget == target,
                            onClick = { stimTarget = target },
                            label = { Text(target) }
                        )
                    }
                }

                if (stimKind != "none") {
                    LabeledSlider("Onset", stimOnset, 0f..200f, 1f) { stimOnset = it }
                    LabeledSlider("Duration", stimDur, 0.5f..20f, 0.5f) { stimDur = it }
                    LabeledSlider("Amplitude", stimAmp, 0f..2f, 0.05f) { stimAmp = it }
                }
                if (stimKind == "periodic") {
                    LabeledSlider("Period", stimPeriod, 5f..100f, 1f) { stimPeriod = it }
                }
            }
        }

        // Run button
        Button(
            onClick = {
                val req = CustomRunRequest(
                    tMax = tMax.toDouble(),
                    soma = SubsystemIn(somaA.toDouble(), somaEps.toDouble(), somaB.toDouble()),
                    psyche = SubsystemIn(psycheA.toDouble(), psycheEps.toDouble(), psycheB.toDouble()),
                    coupling = CouplingIn(c12.toDouble(), c21.toDouble(), kappa.toDouble(), theta.toDouble(), tau.toDouble()),
                    emotion = EmotionIn(eU.toDouble(), eV.toDouble(), 0.2),
                    savageMode = savageMode,
                    somaStimulus = StimulusIn(stimKind, stimOnset.toDouble(), stimDur.toDouble(), stimAmp.toDouble(), stimPeriod.toDouble()),
                    adapter = selectedAdapter
                )
                vm.runCustom(req)
            },
            modifier = Modifier.fillMaxWidth().height(48.dp),
            enabled = !vm.isLoading,
            colors = if (savageMode) ButtonDefaults.buttonColors(containerColor = Color.Red)
                     else ButtonDefaults.buttonColors()
        ) {
            if (vm.isLoading) CircularProgressIndicator(modifier = Modifier.size(20.dp))
            else Text(if (savageMode) "UNLEASH SAVAGE" else "Run Custom")
        }

        vm.errorMessage?.let {
            Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
        }

        vm.result?.let { result ->
            SimulationResultPanel(result)
        }
    }
}
