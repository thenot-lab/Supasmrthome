package com.neuroarousal.ui.theme

import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val SomaU = Color(0xFFE63946)
val SomaV = Color(0xFFF4A261)
val PsycheU = Color(0xFF457B9D)
val PsycheV = Color(0xFFA8DADC)
val Flux = Color(0xFF2A9D8F)
val Tension = Color(0xFFE9C46A)
val Climax = Color(0xFFFF006E)
val BgDark = Color(0xFF1A1A2E)

private val DarkColorScheme = darkColorScheme(
    primary = PsycheU,
    secondary = SomaU,
    tertiary = Flux,
    background = BgDark,
    surface = Color(0xFF16213E),
    onPrimary = Color.White,
    onSecondary = Color.White,
    onBackground = Color(0xFFE0E0E0),
    onSurface = Color(0xFFE0E0E0),
)

private val LightColorScheme = lightColorScheme(
    primary = PsycheU,
    secondary = SomaU,
    tertiary = Flux,
    background = Color(0xFFF8F9FA),
    surface = Color.White,
    onPrimary = Color.White,
    onSecondary = Color.White,
)

@Composable
fun NeuroArousalTheme(
    darkTheme: Boolean = true,
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme
    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography(),
        content = content
    )
}
