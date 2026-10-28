package com.example.appforlpg.ui

import androidx.compose.animation.Crossfade
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.appforlpg.LpgApplication
import com.example.appforlpg.domain.model.UserRole
import com.example.appforlpg.ui.auth.AuthScreen
import com.example.appforlpg.ui.auth.AuthViewModel
import com.example.appforlpg.ui.customer.CustomerScreen
import com.example.appforlpg.ui.customer.CustomerViewModel
import com.example.appforlpg.ui.delivery.DeliveryBoyScreen
import com.example.appforlpg.ui.delivery.DeliveryBoyViewModel
import com.example.appforlpg.ui.theme.APPFORLPGTheme

@Composable
fun MainAppScreen() {
    val context = LocalContext.current
    val app = context.applicationContext as LpgApplication

    val authViewModel: AuthViewModel = viewModel(factory = AuthViewModel.Factory(app.repository))
    val customerViewModel: CustomerViewModel = viewModel(factory = CustomerViewModel.Factory(app.repository))
    val deliveryBoyViewModel: DeliveryBoyViewModel = viewModel(factory = DeliveryBoyViewModel.Factory(app.repository))

    val currentUser by authViewModel.currentUser.collectAsState()
    
    val prefs = context.getSharedPreferences("lpg_app_prefs", android.content.Context.MODE_PRIVATE)
    var isKannada by rememberSaveable { mutableStateOf(prefs.getBoolean("is_kannada", false)) }

    val updateLanguage: (Boolean) -> Unit = { selected ->
        isKannada = selected
        prefs.edit().putBoolean("is_kannada", selected).apply()
    }

    APPFORLPGTheme {
        Surface(
            modifier = Modifier.fillMaxSize(),
            color = MaterialTheme.colorScheme.background
        ) {
            Crossfade(targetState = currentUser, label = "UserAuthCrossfade") { user ->
                when {
                    user == null -> {
                        AuthScreen(
                            authViewModel = authViewModel,
                            isKannada = isKannada,
                            onLanguageToggle = { updateLanguage(it) }
                        )
                    }
                    user.role == UserRole.CUSTOMER -> {
                        CustomerScreen(
                            user = user,
                            customerViewModel = customerViewModel,
                            isKannada = isKannada,
                            onLanguageToggle = { updateLanguage(it) },
                            onLogout = { authViewModel.logout() }
                        )
                    }
                    user.role == UserRole.DELIVERY_BOY -> {
                        DeliveryBoyScreen(
                            user = user,
                            deliveryBoyViewModel = deliveryBoyViewModel,
                            isKannada = isKannada,
                            onLanguageToggle = { updateLanguage(it) },
                            onLogout = { authViewModel.logout() }
                        )
                    }
                }
            }
        }
    }
}
