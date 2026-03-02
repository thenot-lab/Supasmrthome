package com.neuroarousal.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.neuroarousal.ui.components.SimulationResultPanel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PresetsScreen(vm: MainViewModel) {
    var selectedScenario by remember { mutableStateOf("resting_state") }
    var selectedAdapter by remember { mutableStateOf("default") }
    var scenarioExpanded by remember { mutableStateOf(false) }
    var adapterExpanded by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Scenario picker
        Card {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Scenario", style = MaterialTheme.typography.titleMedium)

                ExposedDropdownMenuBox(
                    expanded = scenarioExpanded,
                    onExpandedChange = { scenarioExpanded = it }
                ) {
                    OutlinedTextField(
                        value = selectedScenario.replace("_", " ").replaceFirstChar { it.uppercase() },
                        onValueChange = {},
                        readOnly = true,
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(scenarioExpanded) },
                        modifier = Modifier.menuAnchor().fillMaxWidth()
                    )
                    ExposedDropdownMenu(
                        expanded = scenarioExpanded,
                        onDismissRequest = { scenarioExpanded = false }
                    ) {
                        vm.scenarios.forEach { s ->
                            DropdownMenuItem(
                                text = { Text(s.replace("_", " ").replaceFirstChar { it.uppercase() }) },
                                onClick = {
                                    selectedScenario = s
                                    scenarioExpanded = false
                                }
                            )
                        }
                    }
                }

                // Adapter picker
                ExposedDropdownMenuBox(
                    expanded = adapterExpanded,
                    onExpandedChange = { adapterExpanded = it }
                ) {
                    OutlinedTextField(
                        value = vm.adapters.find { it.name == selectedAdapter }?.label ?: "Default",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Narrative Persona") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(adapterExpanded) },
                        modifier = Modifier.menuAnchor().fillMaxWidth()
                    )
                    ExposedDropdownMenu(
                        expanded = adapterExpanded,
                        onDismissRequest = { adapterExpanded = false }
                    ) {
                        vm.adapters.forEach { a ->
                            DropdownMenuItem(
                                text = { Text(a.label) },
                                onClick = {
                                    selectedAdapter = a.name
                                    adapterExpanded = false
                                }
                            )
                        }
                    }
                }

                Button(
                    onClick = { vm.runScenario(selectedScenario, selectedAdapter) },
                    modifier = Modifier.fillMaxWidth().height(48.dp),
                    enabled = !vm.isLoading
                ) {
                    if (vm.isLoading) CircularProgressIndicator(modifier = Modifier.size(20.dp))
                    else Text("Run Scenario")
                }
            }
        }

        // Scenario info
        vm.scenarioInfo?.let { info ->
            Card {
                Column(Modifier.padding(16.dp)) {
                    Text(info.name, style = MaterialTheme.typography.titleSmall)
                    Spacer(Modifier.height(4.dp))
                    Text(info.description, style = MaterialTheme.typography.bodySmall)
                }
            }
        }

        // Error
        vm.errorMessage?.let { err ->
            Text(err, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
        }

        // Results
        vm.result?.let { result ->
            SimulationResultPanel(result)
        }
    }
}
