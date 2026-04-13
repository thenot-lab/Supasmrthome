package com.neuroarousal.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(vm: MainViewModel, onNavigate: (Int) -> Unit = {}) {
    var selectedScenario by remember { mutableStateOf("resting_state") }
    var scenarioExpanded by remember { mutableStateOf(false) }
    var serverStatus by remember { mutableStateOf("Checking...") }
    var statusColor by remember { mutableStateOf(Color(0xFFFF9800)) }

    LaunchedEffect(vm.scenarios) {
        if (vm.scenarios.isNotEmpty()) {
            serverStatus = "Connected"
            statusColor = Color(0xFF4CAF50)
        } else if (vm.errorMessage != null) {
            serverStatus = "Offline"
            statusColor = Color(0xFFF44336)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Header
        Column(
            modifier = Modifier.fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text("NeuroArousal", style = MaterialTheme.typography.headlineLarge)
            Text("Coupled Excitable System",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
        }

        // Status card
        Card {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("System Status", style = MaterialTheme.typography.titleMedium)
                StatusItem("Server", serverStatus, statusColor)
                StatusItem("Scenarios", "${vm.scenarios.size} loaded",
                    if (vm.scenarios.isNotEmpty()) Color(0xFF4CAF50) else Color(0xFFF44336))
                StatusItem("Adapters", "${vm.adapters.size} personas",
                    if (vm.adapters.isNotEmpty()) Color(0xFF4CAF50) else Color(0xFFFF9800))
                StatusItem("Auth", "Personal mode", Color(0xFF4CAF50))
            }
        }

        // Quick launch
        Card {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Quick Launch", style = MaterialTheme.typography.titleMedium)

                ExposedDropdownMenuBox(
                    expanded = scenarioExpanded,
                    onExpandedChange = { scenarioExpanded = it }
                ) {
                    OutlinedTextField(
                        value = selectedScenario.replace("_", " ").replaceFirstChar { it.uppercase() },
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Scenario") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(scenarioExpanded) },
                        modifier = Modifier.menuAnchor().fillMaxWidth()
                    )
                    ExposedDropdownMenu(scenarioExpanded, { scenarioExpanded = false }) {
                        vm.scenarios.forEach { s ->
                            DropdownMenuItem(
                                text = { Text(s.replace("_", " ").replaceFirstChar { it.uppercase() }) },
                                onClick = { selectedScenario = s; scenarioExpanded = false }
                            )
                        }
                    }
                }

                Button(
                    onClick = { vm.runScenario(selectedScenario) },
                    modifier = Modifier.fillMaxWidth().height(48.dp),
                    enabled = !vm.isLoading && vm.scenarios.isNotEmpty()
                ) {
                    if (vm.isLoading) CircularProgressIndicator(modifier = Modifier.size(20.dp))
                    else Text("Run Now")
                }
            }
        }

        // Quick result
        vm.result?.let { result ->
            Card {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("Result", style = MaterialTheme.typography.titleMedium)
                    Row {
                        Text("Coupled: ", style = MaterialTheme.typography.bodyMedium)
                        Text(result.report.coupledRegime,
                            style = MaterialTheme.typography.bodyMedium,
                            color = regimeColor(result.report.coupledRegime))
                    }
                    Text("SOMA: ${result.report.somaRegime} (${result.report.somaSpikeCount} spikes)",
                        style = MaterialTheme.typography.bodySmall)
                    Text("PSYCHE: ${result.report.psycheRegime} (${result.report.psycheSpikeCount} spikes)",
                        style = MaterialTheme.typography.bodySmall)
                    Text(result.report.description, style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 4)
                }
            }
        }

        vm.errorMessage?.let {
            Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
        }

        // Navigation cards
        Card {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("Explore", style = MaterialTheme.typography.titleMedium)
                NavItem(Icons.Default.Star, "Presets", "Run pre-configured scenarios") { onNavigate(1) }
                NavItem(Icons.Default.Tune, "Custom", "Tune every parameter") { onNavigate(2) }
                NavItem(Icons.Default.Memory, "State Explorer", "Inspect integration steps") { onNavigate(3) }
                NavItem(Icons.Default.Visibility, "Live Observer",
                    "Watch the exhibit react to every client in real time") { onNavigate(4) }
                NavItem(Icons.Default.Info, "About", "Math & references") { onNavigate(5) }
            }
        }
    }
}

@Composable
private fun StatusItem(label: String, value: String, color: Color) {
    Row(verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.fillMaxWidth()) {
        Surface(
            shape = MaterialTheme.shapes.extraSmall,
            color = color,
            modifier = Modifier.size(8.dp)
        ) {}
        Spacer(Modifier.width(8.dp))
        Text(label, style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.weight(1f))
        Text(value, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun NavItem(icon: ImageVector, title: String, desc: String, onClick: () -> Unit) {
    Surface(onClick = onClick) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)
        ) {
            Icon(icon, null, tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(24.dp))
            Spacer(Modifier.width(12.dp))
            Column {
                Text(title, style = MaterialTheme.typography.bodyMedium)
                Text(desc, style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
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
