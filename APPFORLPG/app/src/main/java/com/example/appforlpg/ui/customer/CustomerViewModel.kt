package com.example.appforlpg.ui.customer

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.appforlpg.data.repository.LpgRepository
import com.example.appforlpg.domain.model.Booking
import com.example.appforlpg.domain.model.Delivery
import com.example.appforlpg.domain.model.Payment
import com.example.appforlpg.domain.model.User
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class CustomerUiState(
    val user: User? = null,
    val bookings: List<Booking> = emptyList(),
    val deliveries: List<Delivery> = emptyList(),
    val payments: List<Payment> = emptyList(),
    val pendingSyncCount: Int = 0,
    val isLoading: Boolean = false,
    val successMessage: String? = null,
    val errorMessage: String? = null
)

@OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
class CustomerViewModel(private val repository: LpgRepository) : ViewModel() {

    private val currentUser = repository.getLoggedInUserFlow()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)

    val bookings: StateFlow<List<Booking>> = currentUser
        .flatMapLatest { user ->
            if (user != null) repository.getBookingsForCustomerFlow(user.id) else flowOf(emptyList())
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val deliveries: StateFlow<List<Delivery>> = currentUser
        .flatMapLatest { user ->
            if (user != null) repository.getDeliveriesForCustomerFlow(user.id) else flowOf(emptyList())
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val payments: StateFlow<List<Payment>> = currentUser
        .flatMapLatest { user ->
            if (user != null) repository.getPaymentsForCustomerFlow(user.id) else flowOf(emptyList())
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val supportTickets: StateFlow<List<com.example.appforlpg.domain.model.SupportTicket>> = currentUser
        .flatMapLatest { user ->
            if (user != null) repository.getSupportTicketsFlow(user.id) else flowOf(emptyList())
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val pendingSyncCount: StateFlow<Int> = repository.getPendingSyncCountFlow()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), 0)

    private val _uiState = MutableStateFlow(CustomerUiState())
    val uiState: StateFlow<CustomerUiState> = _uiState.asStateFlow()

    init {
        // Live Updates (Polling every 10 seconds)
        viewModelScope.launch {
            currentUser.collect { user ->
                if (user != null) {
                    while (true) {
                        repository.refreshDataFromServer()
                        kotlinx.coroutines.delay(10000L)
                    }
                }
            }
        }
    }

    fun createBooking(cylinderType: String = "14.2 kg Domestic", quantity: Int = 1) {
        val user = currentUser.value
        if (user == null) {
            _uiState.value = _uiState.value.copy(errorMessage = "Customer session not found. Please log in.")
            return
        }

        _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null, successMessage = null)
        viewModelScope.launch {
            val result = repository.createBooking(
                customerId = user.id,
                cylinderType = cylinderType,
                quantity = quantity
            )
            _uiState.value = _uiState.value.copy(isLoading = false)
            result.onSuccess { booking ->
                val statusText = if (booking.isServerConfirmed) "Server Confirmed" else "Locally Pending Sync"
                _uiState.value = _uiState.value.copy(
                    successMessage = "Booking Ref: ${booking.bookingId} submitted successfully ($statusText).",
                    errorMessage = null
                )
            }.onFailure { exception ->
                _uiState.value = _uiState.value.copy(
                    errorMessage = exception.message ?: "Failed to submit booking"
                )
            }
        }
    }

    fun refreshData() {
        viewModelScope.launch {
            repository.refreshDataFromServer()
        }
    }

    fun raiseIssue(category: String, description: String, transactionId: String?, language: String) {
        val user = currentUser.value
        if (user == null) {
            _uiState.value = _uiState.value.copy(errorMessage = "Customer session not found.")
            return
        }

        _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null, successMessage = null)
        viewModelScope.launch {
            val result = repository.raiseIssue(user.id, category, description, transactionId, language)
            _uiState.value = _uiState.value.copy(isLoading = false)
            result.onSuccess {
                _uiState.value = _uiState.value.copy(successMessage = "Issue submitted successfully. Our AI Assistant has replied!")
            }.onFailure { ex ->
                _uiState.value = _uiState.value.copy(errorMessage = ex.message ?: "Failed to raise issue")
            }
        }
    }

    fun escalateIssue(ticketId: Int, reason: String) {
        val user = currentUser.value ?: return
        _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
        viewModelScope.launch {
            val result = repository.escalateIssue(ticketId, user.id, reason)
            _uiState.value = _uiState.value.copy(isLoading = false)
            result.onSuccess {
                _uiState.value = _uiState.value.copy(successMessage = "Issue escalated to human staff.")
            }.onFailure { ex ->
                _uiState.value = _uiState.value.copy(errorMessage = ex.message ?: "Failed to escalate")
            }
        }
    }

    fun clearMessages() {
        _uiState.value = _uiState.value.copy(successMessage = null, errorMessage = null)
    }

    class Factory(private val repository: LpgRepository) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            return CustomerViewModel(repository) as T
        }
    }
}
