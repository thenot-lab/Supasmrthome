package com.neuroarousal.ui.screens

import android.graphics.BitmapFactory
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.neuroarousal.api.LiveEventOut
import kotlinx.coroutines.delay

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LiveScreen(vm: MainViewModel) {
    var selectedScenario by remember { mutableStateOf("resting_state") }
    var scenarioExpanded by remember { mutableStateOf(false) }
    var frameCount by remember { mutableIntStateOf(24) }

    // Poll every 2 seconds while this screen is on-screen.
    LaunchedEffect(Unit) {
        while (true) {
            vm.pollLiveFeed()
            delay(2000)
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
            Text("Live Observer", style = MaterialTheme.typography.headlineMedium)
            Text(
                "Watching the exhibit react to every client in real time",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        // Character image card
        Card {
            Column(
                Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    "Current State",
                    style = MaterialTheme.typography.titleMedium,
                    modifier = Modifier.align(Alignment.Start)
                )
                val bytes = vm.liveCharacterBytes
                if (bytes != null && bytes.isNotEmpty()) {
                    val bitmap = remember(bytes) {
                        BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                    }
                    if (bitmap != null) {
                        Image(
                            bitmap = bitmap.asImageBitmap(),
                            contentDescription = "Live character render",
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(360.dp)
                                .clip(RoundedCornerShape(12.dp))
                                .background(Color(0xFF0F0F1A))
                        )
                    }
                } else {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(240.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .background(Color(0xFF0F0F1A)),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            "Waiting for first simulation…",
                            color = Color.White.copy(alpha = 0.6f)
                        )
                    }
                }
            }
        }

        // Animation generator card
        Card {
            Column(
                Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text("Generate Animation", style = MaterialTheme.typography.titleMedium)

                ExposedDropdownMenuBox(
                    expanded = scenarioExpanded,
                    onExpandedChange = { scenarioExpanded = it }
                ) {
                    OutlinedTextField(
                        value = selectedScenario
                            .replace("_", " ")
                            .replaceFirstChar { it.uppercase() },
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Scenario") },
                        trailingIcon = {
                            ExposedDropdownMenuDefaults.TrailingIcon(scenarioExpanded)
                        },
                        modifier = Modifier.menuAnchor().fillMaxWidth()
                    )
                    ExposedDropdownMenu(
                        scenarioExpanded,
                        { scenarioExpanded = false }
                    ) {
                        vm.scenarios.forEach { s ->
                            DropdownMenuItem(
                                text = {
                                    Text(s.replace("_", " ").replaceFirstChar { it.uppercase() })
                                },
                                onClick = {
                                    selectedScenario = s
                                    scenarioExpanded = false
                                }
                            )
                        }
                    }
                }

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text("Frames:", style = MaterialTheme.typography.bodySmall)
                    Slider(
                        value = frameCount.toFloat(),
                        onValueChange = { frameCount = it.toInt() },
                        valueRange = 8f..48f,
                        steps = 39,
                        modifier = Modifier.weight(1f)
                    )
                    Text("$frameCount", style = MaterialTheme.typography.bodySmall)
                }

                Button(
                    onClick = { vm.generateAnimation(selectedScenario, frameCount) },
                    modifier = Modifier.fillMaxWidth().height(48.dp),
                    enabled = !vm.liveGenerating && vm.scenarios.isNotEmpty()
                ) {
                    if (vm.liveGenerating) {
                        CircularProgressIndicator(modifier = Modifier.size(20.dp))
                    } else {
                        Text("Generate Animation")
                    }
                }

                val animBytes = vm.liveAnimationBytes
                if (animBytes != null && animBytes.isNotEmpty()) {
                    val animBitmap = remember(animBytes) {
                        BitmapFactory.decodeByteArray(animBytes, 0, animBytes.size)
                    }
                    if (animBitmap != null) {
                        Image(
                            bitmap = animBitmap.asImageBitmap(),
                            contentDescription = "Generated animation first frame",
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(320.dp)
                                .clip(RoundedCornerShape(12.dp))
                                .background(Color(0xFF0F0F1A))
                        )
                    }
                    Text(
                        "GIF saved to memory (${animBytes.size / 1024} KB) — Android preview " +
                            "shows the first frame only. Full animation plays in Gradio and iOS.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        // Activity feed card
        Card {
            Column(
                Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text("Activity Feed", style = MaterialTheme.typography.titleMedium)
                if (vm.liveEvents.isEmpty()) {
                    Text(
                        "No events yet. Run a scenario from any client (Gradio, iOS, " +
                            "Android, API) to see it land here.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                } else {
                    vm.liveEvents.asReversed().take(30).forEach { event ->
                        EventRow(event)
                        Divider()
                    }
                }
            }
        }

        vm.errorMessage?.let {
            Text(
                it,
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodySmall
            )
        }
    }
}

@Composable
private fun EventRow(event: LiveEventOut) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Surface(
            shape = RoundedCornerShape(4.dp),
            color = eventColor(event.type),
            modifier = Modifier.size(width = 4.dp, height = 36.dp)
        ) {}
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f)) {
            Text(
                event.summary,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Medium
            )
            Text(
                "${event.type} · ${event.source}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

private fun eventColor(type: String): Color = when (type) {
    "scenario_run" -> Color(0xFF4CAF50)
    "custom_run" -> Color(0xFF2196F3)
    "adapter_change" -> Color(0xFF9C27B0)
    "frames_generated" -> Color(0xFFFF9800)
    else -> Color.Gray
}
