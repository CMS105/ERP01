package com.example.appforlpg.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface UserDao {
    @Query("SELECT * FROM users WHERE isLoggedIn = 1 LIMIT 1")
    fun getLoggedInUserFlow(): Flow<UserEntity?>

    @Query("SELECT * FROM users WHERE isLoggedIn = 1 LIMIT 1")
    suspend fun getLoggedInUser(): UserEntity?

    @Query("SELECT * FROM users WHERE username = :username LIMIT 1")
    suspend fun getUserByUsername(username: String): UserEntity?

    @Query("SELECT * FROM users WHERE id = :id LIMIT 1")
    suspend fun getUserById(id: String): UserEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertUser(user: UserEntity)

    @Query("UPDATE users SET isLoggedIn = 0")
    suspend fun clearSession(): Int
}

@Dao
interface BookingDao {
    @Query("SELECT * FROM bookings WHERE customerId = :customerId ORDER BY bookingDate DESC")
    fun getBookingsForCustomerFlow(customerId: String): Flow<List<BookingEntity>>

    @Query("SELECT * FROM bookings ORDER BY bookingDate DESC")
    fun getAllBookingsFlow(): Flow<List<BookingEntity>>

    @Query("SELECT * FROM bookings WHERE customerId = :customerId ORDER BY bookingDate DESC")
    suspend fun getBookingsForCustomer(customerId: String): List<BookingEntity>

    @Query("SELECT * FROM bookings WHERE customerId = :customerId AND (bookingStatus = 'PENDING' OR deliveryStatus IN ('UNASSIGNED', 'ASSIGNED', 'OUT_FOR_DELIVERY')) LIMIT 1")
    suspend fun getPendingBookingForCustomer(customerId: String): BookingEntity?

    @Query("SELECT * FROM bookings WHERE bookingId = :bookingId LIMIT 1")
    suspend fun getBookingById(bookingId: String): BookingEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertBooking(booking: BookingEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertBookings(bookings: List<BookingEntity>)

    @Query("UPDATE bookings SET deliveryStatus = :deliveryStatus, bookingStatus = :bookingStatus WHERE bookingId = :bookingId")
    suspend fun updateBookingStatus(bookingId: String, deliveryStatus: String, bookingStatus: String): Int
}

@Dao
interface DeliveryDao {
    @Query("SELECT * FROM deliveries WHERE deliveryBoyId = :deliveryBoyId ORDER BY deliveryTimestamp DESC")
    fun getDeliveriesForDeliveryBoyFlow(deliveryBoyId: String): Flow<List<DeliveryEntity>>

    @Query("SELECT * FROM deliveries WHERE deliveryBoyId = :deliveryBoyId ORDER BY deliveryTimestamp DESC")
    suspend fun getDeliveriesForDeliveryBoy(deliveryBoyId: String): List<DeliveryEntity>

    @Query("SELECT * FROM deliveries WHERE customerId = :customerId ORDER BY deliveryTimestamp DESC")
    fun getDeliveriesForCustomerFlow(customerId: String): Flow<List<DeliveryEntity>>

    @Query("SELECT * FROM deliveries WHERE deliveryId = :deliveryId LIMIT 1")
    suspend fun getDeliveryById(deliveryId: String): DeliveryEntity?

    @Query("SELECT * FROM deliveries WHERE bookingId = :bookingId LIMIT 1")
    suspend fun getDeliveryByBookingId(bookingId: String): DeliveryEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertDelivery(delivery: DeliveryEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertDeliveries(deliveries: List<DeliveryEntity>)

    @Query("UPDATE deliveries SET syncStatus = :syncStatus, isServerConfirmed = :isConfirmed WHERE deliveryId = :deliveryId")
    suspend fun updateSyncStatus(deliveryId: String, syncStatus: String, isConfirmed: Boolean): Int
}

@Dao
interface PaymentDao {
    @Query("SELECT * FROM payments WHERE customerId = :customerId ORDER BY collectionTimestamp DESC")
    fun getPaymentsForCustomerFlow(customerId: String): Flow<List<PaymentEntity>>

    @Query("SELECT * FROM payments WHERE deliveryBoyId = :deliveryBoyId ORDER BY collectionTimestamp DESC")
    fun getPaymentsForDeliveryBoyFlow(deliveryBoyId: String): Flow<List<PaymentEntity>>

    @Query("SELECT * FROM payments WHERE paymentId = :paymentId LIMIT 1")
    suspend fun getPaymentById(paymentId: String): PaymentEntity?

    @Query("SELECT * FROM payments WHERE bookingId = :bookingId LIMIT 1")
    suspend fun getPaymentByBookingId(bookingId: String): PaymentEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPayment(payment: PaymentEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPayments(payments: List<PaymentEntity>)
}

@Dao
interface PendingSyncDao {
    @Query("SELECT * FROM pending_sync_operations ORDER BY createdAt ASC")
    fun getPendingOperationsFlow(): Flow<List<PendingSyncEntity>>

    @Query("SELECT * FROM pending_sync_operations ORDER BY createdAt ASC")
    suspend fun getAllPendingOperations(): List<PendingSyncEntity>

    @Query("SELECT COUNT(*) FROM pending_sync_operations")
    fun getPendingCountFlow(): Flow<Int>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertOperation(operation: PendingSyncEntity)

    @Query("DELETE FROM pending_sync_operations WHERE operationId = :operationId")
    suspend fun deleteOperation(operationId: String): Int

    @Query("UPDATE pending_sync_operations SET retryCount = retryCount + 1, lastError = :error WHERE operationId = :operationId")
    suspend fun incrementRetryCount(operationId: String, error: String): Int
}

@Dao
interface BluetoothTransferDao {
    @Query("SELECT * FROM bluetooth_transfers ORDER BY timestamp DESC")
    fun getTransferRecordsFlow(): Flow<List<BluetoothTransferEntity>>

    @Query("SELECT * FROM bluetooth_transfers WHERE bookingId = :bookingId OR deliveryId = :deliveryId LIMIT 1")
    suspend fun getTransferRecordByRef(bookingId: String, deliveryId: String): BluetoothTransferEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertTransferRecord(record: BluetoothTransferEntity)
}

@Dao
interface SupportTicketDao {
    @Query("SELECT * FROM support_tickets WHERE customerId = :customerId ORDER BY id DESC")
    fun getTicketsForCustomerFlow(customerId: String): Flow<List<SupportTicketEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertTicket(ticket: SupportTicketEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertTickets(tickets: List<SupportTicketEntity>)
}
