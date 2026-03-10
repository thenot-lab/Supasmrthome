package com.neuroarousal.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import kotlin.math.roundToInt

@Composable
fun LabeledSlider(
    label: String,
    value: Float,
    range: ClosedFloatingPointRange<Float>,
    step: Float,
    onValueChange: (Float) -> Unit
) {
    Column {
        Row(modifier = Modifier.fillMaxWidth()) {
            Text(label, style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.weight(1f))
            Text(
                formatSliderValue(value, step),
                style = MaterialTheme.typography.bodySmall,
                fontFamily = FontFamily.Monospace
            )
        }
        Slider(
            value = value,
            onValueChange = {
                // Snap to step
                val snapped = (it / step).roundToInt() * step
                onValueChange(snapped.coerceIn(range.start, range.endInclusive))
            },
            valueRange = range
        )
    }
}

private fun formatSliderValue(value: Float, step: Float): String {
    return when {
        step >= 1f -> "%.0f".format(value)
        step >= 0.01f -> "%.2f".format(value)
        else -> "%.3f".format(value)
    }
}
