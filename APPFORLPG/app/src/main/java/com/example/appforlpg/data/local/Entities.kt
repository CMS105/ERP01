package com.example.appforlpg.data.local

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(tableName = "users")
data class UserEntity(
    @PrimaryKey val id: String,
    val username: String,
    val fullName: String,
    val phone: String,
    val address: String,
    val consumerNumber: String,
    val role: String, // CUSTOMER or DELIVERY_BOY
    val token: String? = null,
    val isLoggedIn: Boolean = false
)

@Entity(
    tableName = "bookings",
    indices = [
        Index(value = ["customerId"]),
        Index(value = ["assignedDeliveryBoyId"]),
        Index(value = ["bookingStatus"]),
        Index(value = ["deliveryStatus"])
    ]
)
data class BookingEntity(
    @PrimaryKey val bookingId: String,
    val customerId: String,
    val customerName: String,
    val consumerNumber: String,
    val customerPhone: String,
    val deliveryAddress: String,
    val bookingDate: String,
    val cylinderType: String,
    val quantity: Int,
    val amountDue: Double,
    val bookingStatus: String,
    val deliveryStatus: String,
    val assignedDeliveryBoyId: String?,
    val assignedDeliveryBoyName: String?,
    val isLocallyCreated: Boolean,
    val isServerConfirmed: Boolean,
    val operationId: String
)

@Entity(
    tableName = "deliveries",
    indices = [
        Index(value = ["bookingId"]),
        Index(value = ["customerId"]),
        Index(value = ["deliveryBoyId"]),
        Index(value = ["status"]),
        Index(value = ["syncStatus"])
    ]
)
data class DeliveryEntity(
    @PrimaryKey val deliveryId: String,
    val bookingId: String,
    val customerId: String,
    val customerName: String,
    val customerPhone: String,
    val deliveryAddress: String,
    val deliveryBoyId: String,
    val cylinderQuantity: Int,
    val cylinderType: String,
    val deliveryTimestamp: String,
    val status: String,
    val notes: String?,
    val operationId: String,
    val syncStatus: String,
    val confirmationReference: String,
    val isServerConfirmed: Boolean
)

@Entity(
    tableName = "payments",
    indices = [
        Index(value = ["bookingId"]),
        Index(value = ["customerId"]),
        Index(value = ["deliveryBoyId"])
    ]
)
data class PaymentEntity(
    @PrimaryKey val paymentId: String,
    val bookingId: String,
    val customerId: String,
    val deliveryBoyId: String?,
    val amountDue: Double,
    val amountCollected: Double,
    val paymentMethod: String,
    val transactionReference: String?,
    val collectionTimestamp: String,
    val status: String,
    val isServerVerified: Boolean,
    val syncStatus: String
)

@Entity(tableName = "pending_sync_operations")
data class PendingSyncEntity(
    @PrimaryKey val operationId: String,
    val entityType: String,
    val entityId: String,
    val payloadJson: String,
    val createdAt: Long,
    val retryCount: Int,
    val lastError: String?
)

@Entity(tableName = "bluetooth_transfers")
data class BluetoothTransferEntity(
    @PrimaryKey val id: String,
    val deviceName: String,
    val deviceAddress: String,
    val transferType: String,
    val bookingId: String,
    val deliveryId: String,
    val timestamp: String,
    val status: String,
    val rawJson: String
)

@Entity(
    tableName = "support_tickets",
    indices = [
        Index(value = ["customerId"])
    ]
)
data class SupportTicketEntity(
    @PrimaryKey val id: Int,
    val ticketNumber: String,
    val customerId: String,
    val transactionId: String?,
    val category: String,
    val description: String,
    val language: String,
    val status: String,
    val aiResponse: String?,
    val escalationReason: String?,
    val isLocallyCreated: Boolean,
    val operationId: String
)
