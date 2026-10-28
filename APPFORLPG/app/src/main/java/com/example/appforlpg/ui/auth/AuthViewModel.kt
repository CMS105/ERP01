package com.example.appforlpg.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.appforlpg.data.repository.LpgRepository
import com.example.appforlpg.domain.model.User
import com.example.appforlpg.domain.model.UserRole
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class AuthUiState(
    val user: User? = null,
    val selectedRole: UserRole = UserRole.CUSTOMER,
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)

class AuthViewModel(private val repository: LpgRepository) : ViewModel() {

    val currentUser: StateFlow<User?> = repository.getLoggedInUserFlow()
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = null
        )

    private val _uiState = MutableStateFlow(AuthUiState())
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()

    fun selectRole(role: UserRole) {
        _uiState.value = _uiState.value.copy(selectedRole = role, errorMessage = null)
    }

    fun login(username: String, password: String) {
        if (username.isBlank() && password.isBlank()) {
            _uiState.value = _uiState.value.copy(errorMessage = "Please enter username and password or select a Demo account.")
            return
        }
        _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
        viewModelScope.launch {
            val result = repository.login(username, password, _uiState.value.selectedRole)
            _uiState.value = _uiState.value.copy(isLoading = false)
            result.onSuccess { user ->
                _uiState.value = _uiState.value.copy(user = user, errorMessage = null)
            }.onFailure { exception ->
                _uiState.value = _uiState.value.copy(errorMessage = exception.message ?: "Authentication failed")
            }
        }
    }

    fun loginWithDemo(role: UserRole) {
        _uiState.value = _uiState.value.copy(selectedRole = role, isLoading = true, errorMessage = null)
        viewModelScope.launch {
            val username = if (role == UserRole.CUSTOMER) "cust_demo@example.com" else "driver_demo@example.com"
            val result = repository.login(username, "Pass123!", role)
            _uiState.value = _uiState.value.copy(isLoading = false)
            result.onSuccess { user ->
                _uiState.value = _uiState.value.copy(user = user, errorMessage = null)
            }.onFailure { exception ->
                _uiState.value = _uiState.value.copy(errorMessage = exception.message ?: "Demo login failed")
            }
        }
    }

    fun logout() {
        viewModelScope.launch {
            repository.logout()
            _uiState.value = AuthUiState()
        }
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(errorMessage = null)
    }

    class Factory(private val repository: LpgRepository) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            return AuthViewModel(repository) as T
        }
    }
}
