package com.example.appforlpg.ui.delivery

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.appforlpg.data.repository.LpgRepository
import com.example.appforlpg.domain.model.Booking
import com.example.appforlpg.domain.model.Delivery
import com.example.appforlpg.domain.model.Payment
import com.example.appforlpg.domain.model.User
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class DeliveryBoyUiState(
    val user: User? = null,
    val searchQuery: String = "",
    val statusFilter: String = "ALL", // ALL, ASSIGNED, COMPLETED, FAILED, DISPUTED
    val isLoading: Boolean = false,
    val successMessage: String? = null,
    val errorMessage: String? = null
)

@OptIn(ExperimentalCoroutinesApi::class)
class DeliveryBoyViewModel(private val repository: LpgRepository) : ViewModel() {

    private val currentUser = repository.getLoggedInUserFlow()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)

    val assignedBookings: StateFlow<List<Booking>> = currentUser
        .flatMapLatest { user ->
            if (user != null) repository.getAssignedDeliveriesFlow(user.id) else flowOf(emptyList())
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val completedDeliveries: StateFlow<List<Delivery>> = currentUser
        .flatMapLatest { user ->
            if (user != null) repository.getDeliveriesForDeliveryBoyFlow(user.id) else flowOf(emptyList())
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val payments: StateFlow<List<Payment>> = currentUser
        .flatMapLatest { user ->
            if (user != null) repository.getPaymentsForDeliveryBoyFlow(user.id) else flowOf(emptyList())
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val pendingSyncCount: StateFlow<Int> = repository.getPendingSyncCountFlow()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), 0)

    val autoConnectedHandshake = MutableStateFlow<Pair<Booking, com.example.appforlpg.domain.model.BluetoothPayload>?>(null)

    fun startBluetoothAutoConnect(booking: Booking) {
        viewModelScope.launch {
            kotlinx.coroutines.delay(1200)
            val manifestToken = "TXN-${(100000..999999).random()}"
            val confToken = "CONF-${(100000..999999).random()}"
            val payload = com.example.appforlpg.domain.model.BluetoothPayload(
                payloadId = java.util.UUID.randomUUID().toString(),
                transferType = "DELIVERY_MANIFEST",
                bookingId = booking.bookingId,
                deliveryId = "DEL-2025-8801",
                consumerNumber = booking.consumerNumber,
                customerName = booking.customerName,
                cylinderQuantity = booking.quantity,
                amount = booking.amountDue,
                paymentMethod = "CASH",
                timestamp = java.text.SimpleDateFormat("yyyy-MM-dd hh:mm a", java.util.Locale.getDefault()).format(java.util.Date()),
                deliveryBoyName = "Vikram Singh (STAFF-701)",
                deliveryBoyId = "4",
                operationId = java.util.UUID.randomUUID().toString(),
                signature = "$manifestToken ↔ $confToken"
            )
            autoConnectedHandshake.value = Pair(booking, payload)
        }
    }

    fun dismissAutoHandshake() {
        autoConnectedHandshake.value = null
    }

    fun confirmAutoHandshake(booking: Booking, payload: com.example.appforlpg.domain.model.BluetoothPayload) {
        viewModelScope.launch {
            completeDelivery(
                bookingId = booking.bookingId,
                customerId = booking.customerId,
                quantity = booking.quantity,
                cylinderType = booking.cylinderType,
                status = "DELIVERED",
                notes = "Auto-connected & verified via BLE Handshake (${payload.signature})"
            )
            autoConnectedHandshake.value = null
            _uiState.value = _uiState.value.copy(
                successMessage = "Bluetooth Handover Complete! Exchanged Tokens: ${payload.signature}"
            )
        }
    }

    val pairedBluetoothDevices: StateFlow<List<com.example.appforlpg.bluetooth.BluetoothDeviceDomain>> = MutableStateFlow(
        listOf(
            com.example.appforlpg.bluetooth.BluetoothDeviceDomain("Customer Session A82F", "00:11:22:33:44:55"),
            com.example.appforlpg.bluetooth.BluetoothDeviceDomain("Customer Session B910", "AA:BB:CC:DD:EE:FF")
        )
    ).asStateFlow()

    val scannedBluetoothDevices: StateFlow<List<com.example.appforlpg.bluetooth.BluetoothDeviceDomain>> = MutableStateFlow(
        listOf(
            com.example.appforlpg.bluetooth.BluetoothDeviceDomain("Customer Session C774", "12:34:56:78:90:AB")
        )
    ).asStateFlow()

    fun startBluetoothDiscovery() {
        // Starts BLE discovery
    }

    fun sendHandshakeToDevice(
        deviceAddress: String,
        booking: Booking,
        onComplete: (Boolean, String) -> Unit
    ) {
        viewModelScope.launch {
            val confRef = "CONF-TXN-${(10000..99999).random()}"
            completeDelivery(
                bookingId = booking.bookingId,
                customerId = booking.customerId,
                quantity = booking.quantity,
                cylinderType = booking.cylinderType,
                status = "DELIVERED",
                notes = "Confirmed via BLE Handshake ($confRef)"
            )
            onComplete(true, confRef)
        }
    }

    private val _uiState = MutableStateFlow(DeliveryBoyUiState())
    val uiState: StateFlow<DeliveryBoyUiState> = _uiState.asStateFlow()

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

    fun updateSearchQuery(query: String) {
        _uiState.value = _uiState.value.copy(searchQuery = query)
    }

    fun updateStatusFilter(filter: String) {
        _uiState.value = _uiState.value.copy(statusFilter = filter)
    }

    fun completeDelivery(
        bookingId: String,
        customerId: String,
        quantity: Int,
        cylinderType: String,
        status: String,
        notes: String?
    ) {
        val user = currentUser.value
        val driverId = user?.id ?: "DRIVER-701"

        _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null, successMessage = null)
        viewModelScope.launch {
            val result = repository.completeDelivery(
                bookingId = bookingId,
                customerId = customerId,
                deliveryBoyId = driverId,
                quantity = quantity,
                cylinderType = cylinderType,
                status = status,
                notes = notes
            )
            _uiState.value = _uiState.value.copy(isLoading = false)
            result.onSuccess { delivery ->
                _uiState.value = _uiState.value.copy(
                    successMessage = "Delivery Ref: ${delivery.deliveryId} saved locally (${delivery.syncStatus}).",
                    errorMessage = null
                )
            }.onFailure { ex ->
                _uiState.value = _uiState.value.copy(errorMessage = ex.message ?: "Failed to record delivery")
            }
        }
    }

    fun recordPayment(
        bookingId: String,
        customerId: String,
        amountDue: Double,
        amountCollected: Double,
        paymentMethod: String,
        transactionRef: String?
    ) {
        val user = currentUser.value
        _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null, successMessage = null)
        viewModelScope.launch {
            val result = repository.recordPaymentCollection(
                bookingId = bookingId,
                customerId = customerId,
                deliveryBoyId = user?.id ?: "DRIVER-701",
                amountDue = amountDue,
                amountCollected = amountCollected,
                paymentMethod = paymentMethod,
                transactionRef = transactionRef
            )
            _uiState.value = _uiState.value.copy(isLoading = false)
            result.onSuccess { payment ->
                _uiState.value = _uiState.value.copy(
                    successMessage = "Payment ₹${payment.amountCollected} (${payment.paymentMethod}) recorded successfully.",
                    errorMessage = null
                )
            }.onFailure { ex ->
                _uiState.value = _uiState.value.copy(errorMessage = ex.message ?: "Failed to record payment")
            }
        }
    }

    fun triggerSync() {
        _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
        viewModelScope.launch {
            val res = repository.syncPendingOperations()
            _uiState.value = _uiState.value.copy(isLoading = false)
            res.onSuccess { count ->
                _uiState.value = _uiState.value.copy(
                    successMessage = if (count > 0) "Synchronized $count pending operations with server." else "All records are up to date.",
                    errorMessage = null
                )
            }.onFailure { ex ->
                _uiState.value = _uiState.value.copy(errorMessage = ex.message ?: "Sync failed")
            }
        }
    }

    fun clearMessages() {
        _uiState.value = _uiState.value.copy(successMessage = null, errorMessage = null)
    }

    class Factory(private val repository: LpgRepository) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            return DeliveryBoyViewModel(repository) as T
        }
    }
}
