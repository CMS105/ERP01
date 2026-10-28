package com.example.appforlpg

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.example.appforlpg.ui.MainAppScreen
import com.example.appforlpg.ui.theme.APPFORLPGTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            APPFORLPGTheme {
                MainAppScreen()
            }
        }
    }
}
