package com.example.appforlpg.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val LightColorScheme = lightColorScheme(
    primary = TerracottaPrimary,
    onPrimary = OnTerracottaPrimary,
    primaryContainer = TerracottaContainer,
    onPrimaryContainer = OnTerracottaContainer,
    secondary = TerracottaSecondary,
    onSecondary = OnTerracottaSecondary,
    secondaryContainer = TerracottaSecondaryContainer,
    onSecondaryContainer = OnTerracottaSecondaryContainer,
    background = CreamBackground,
    onBackground = Color(0xFF231A16),
    surface = CreamSurface,
    onSurface = Color(0xFF231A16),
    surfaceVariant = CreamSurfaceVariant,
    onSurfaceVariant = Color(0xFF53433C)
)

private val DarkColorScheme = darkColorScheme(
    primary = DarkTerracottaPrimary,
    onPrimary = Color(0xFF511D0A),
    primaryContainer = Color(0xFF722D16),
    onPrimaryContainer = TerracottaContainer,
    secondary = Color(0xFFE58066),
    onSecondary = Color(0xFF4A1A0C),
    background = DarkTerracottaBackground,
    onBackground = Color(0xFFEDE0D8),
    surface = DarkTerracottaSurface,
    onSurface = Color(0xFFEDE0D8),
    surfaceVariant = DarkTerracottaSurfaceVariant,
    onSurfaceVariant = Color(0xFFD8C2B8)
)

@Composable
fun APPFORLPGTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    // Set dynamicColor to false to preserve cream-and-terracotta design language
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.primary.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = darkTheme
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
