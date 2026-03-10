package com.neuroarousal.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp

@Composable
fun AboutScreen() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text("NeuroArousal", style = MaterialTheme.typography.headlineLarge)
        Text("Coupled Excitable System Exhibit",
            style = MaterialTheme.typography.titleMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant)

        HorizontalDivider()

        SectionTitle("Mathematical Model")
        Text(
            """
            Two coupled FitzHugh-Nagumo oscillators with sigmoidal delay coupling:

            SOMA (physiological arousal):
              du1/dt = u1(1-u1)(u1-a1) - v1 + c12*S(u2(t-tau)) + I1(t)
              dv1/dt = e1*(b1*u1 - v1)

            PSYCHE (cognitive/emotional arousal):
              du2/dt = u2(1-u2)(u2-a2) - v2 + c21*S(u1(t-tau)) + I2(t)
              dv2/dt = e2*(b2*u2 - v2)

            where S(x) = 1/(1 + exp(-kappa*(x-theta)))
            """.trimIndent(),
            fontFamily = FontFamily.Monospace,
            style = MaterialTheme.typography.bodySmall
        )

        HorizontalDivider()

        SectionTitle("Emotional Drive Mapping")
        InfoItem("E_u (0-100)", "Arousal drive -> SOMA boost")
        InfoItem("E_v (0-100)", "Valence drive -> PSYCHE shift")
        InfoItem("E_v0 = 0.2", "Resting valence baseline")

        HorizontalDivider()

        SectionTitle("Savage Mode Parameters")
        Text("epsilon=0.05, a=0.5, b=0.1, E_v0=0.2\nc12=0.35, c21=0.30, kappa=20",
            style = MaterialTheme.typography.bodySmall,
            fontFamily = FontFamily.Monospace)

        HorizontalDivider()

        SectionTitle("PEFT Adapters")
        InfoItem("Museum Default", "Measured, educational")
        InfoItem("Poetic Narrator", "Lyrical, metaphorical")
        InfoItem("Clinical Observer", "Precise, technical")
        InfoItem("Dramatic Storyteller", "Vivid, suspenseful")

        HorizontalDivider()

        SectionTitle("Key Parameters")
        InfoItem("a", "Excitability threshold (0 < a < 1)")
        InfoItem("epsilon", "Timescale separation")
        InfoItem("b", "Recovery gain")
        InfoItem("c12, c21", "Inter-population coupling strengths")
        InfoItem("kappa", "Sigmoid steepness")
        InfoItem("theta", "Sigmoid midpoint")
        InfoItem("tau", "Coupling delay")

        HorizontalDivider()

        SectionTitle("References")
        Text(
            "- Blyuss, K.B. & Kyrychko, Y.N. (2010). Bull. Math. Biol., 72, 490-505.\n" +
            "- FitzHugh, R. (1961). Biophys. J., 1(6), 445-466.\n" +
            "- Nagumo, J. et al. (1962). Proc. IRE, 50(10), 2061-2070.",
            style = MaterialTheme.typography.bodySmall
        )

        Text("v2.0.0",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun SectionTitle(text: String) {
    Text(text, style = MaterialTheme.typography.titleMedium)
}

@Composable
private fun InfoItem(label: String, description: String) {
    Row(modifier = Modifier.fillMaxWidth()) {
        Text(label, style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.weight(1f))
        Text(description, style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.weight(1.5f))
    }
}
