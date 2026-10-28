package com.example.appforlpg.data.repository

import com.example.appforlpg.domain.model.BluetoothPayload
import com.example.appforlpg.domain.model.BluetoothTransferRecord
import com.example.appforlpg.domain.model.Booking
import com.example.appforlpg.domain.model.Delivery
import com.example.appforlpg.domain.model.Payment
import com.example.appforlpg.domain.model.PendingSyncOperation
import com.example.appforlpg.domain.model.User
import com.example.appforlpg.domain.model.UserRole
import kotlinx.coroutines.flow.Flow

interface LpgRepository {
    // Auth
    fun getLoggedInUserFlow(): Flow<User?>
    suspend fun getLoggedInUser(): User?
    suspend fun login(username: String, password: String, role: UserRole): Result<User>
    suspend fun logout()

    // Customer
    fun getBookingsForCustomerFlow(customerId: String): Flow<List<Booking>>
    fun getDeliveriesForCustomerFlow(customerId: String): Flow<List<Delivery>>
    fun getPaymentsForCustomerFlow(customerId: String): Flow<List<Payment>>
    suspend fun createBooking(
        customerId: String,
        cylinderType: String,
        quantity: Int
    ): Result<Booking>

    // Delivery Boy
    fun getAssignedDeliveriesFlow(deliveryBoyId: String): Flow<List<Booking>>
    fun getDeliveriesForDeliveryBoyFlow(deliveryBoyId: String): Flow<List<Delivery>>
    fun getPaymentsForDeliveryBoyFlow(deliveryBoyId: String): Flow<List<Payment>>
    suspend fun completeDelivery(
        bookingId: String,
        customerId: String,
        deliveryBoyId: String,
        quantity: Int,
        cylinderType: String,
        status: String,
        notes: String?
    ): Result<Delivery>

    suspend fun recordPaymentCollection(
        bookingId: String,
        customerId: String,
        deliveryBoyId: String?,
        amountDue: Double,
        amountCollected: Double,
        paymentMethod: String,
        transactionRef: String?
    ): Result<Payment>

    // Bluetooth
    fun getBluetoothTransfersFlow(): Flow<List<BluetoothTransferRecord>>
    suspend fun saveBluetoothTransferRecord(record: BluetoothTransferRecord)
    suspend fun processReceivedBluetoothPayload(payload: BluetoothPayload): Result<Delivery>

    // Offline Sync
    fun getPendingSyncCountFlow(): Flow<Int>
    fun getPendingOperationsFlow(): Flow<List<PendingSyncOperation>>
    suspend fun syncPendingOperations(): Result<Int>
    suspend fun refreshDataFromServer()

    // Support
    fun getSupportTicketsFlow(customerId: String): Flow<List<com.example.appforlpg.domain.model.SupportTicket>>
    suspend fun raiseIssue(
        customerId: String,
        category: String,
        description: String,
        transactionId: String?,
        language: String
    ): Result<com.example.appforlpg.domain.model.SupportTicket>
    
    suspend fun escalateIssue(ticketId: Int, customerId: String, reason: String): Result<com.example.appforlpg.domain.model.SupportTicket>
}
