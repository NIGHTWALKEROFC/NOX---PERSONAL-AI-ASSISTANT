package com.nox.assistant

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Colors inspired by Claude's warm dark theme: charcoal background, terracotta accent.
val NoxBackground = Color(0xFF262624)
val NoxSurface = Color(0xFF30302E)
val NoxSurfaceVariant = Color(0xFF3A3A38)
val NoxAccent = Color(0xFFCC785C)
val NoxAccentDim = Color(0xFF8A5240)
val NoxTextPrimary = Color(0xFFECECE6)
val NoxTextSecondary = Color(0xFFA8A8A0)

private val NoxColorScheme = darkColorScheme(
    primary = NoxAccent,
    onPrimary = NoxTextPrimary,
    secondary = NoxAccentDim,
    background = NoxBackground,
    onBackground = NoxTextPrimary,
    surface = NoxSurface,
    onSurface = NoxTextPrimary,
    surfaceVariant = NoxSurfaceVariant,
    onSurfaceVariant = NoxTextSecondary,
)

@Composable
fun NoxTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = NoxColorScheme, content = content)
}
