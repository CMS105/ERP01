package com.example.appforlpg.domain.model

enum class UserRole {
    CUSTOMER,
    DELIVERY_BOY
}

data class User(
    val id: String,
    val username: String,
    val fullName: String,
    val phone: String,
    val address: String,
    val consumerNumber: String,
    val role: UserRole,
    val token: String? = null
)

data class Booking(
    val bookingId: String,
    val customerId: String,
    val customerName: String,
    val consumerNumber: String,
    val customerPhone: String,
    val deliveryAddress: String,
    val bookingDate: String,
    val cylinderType: String = "14.2 kg Domestic",
    val quantity: Int = 1,
    val amountDue: Double = 950.0,
    val bookingStatus: String = "PENDING", // PENDING, CONFIRMED, CANCELLED, COMPLETED
    val deliveryStatus: String = "UNASSIGNED", // UNASSIGNED, ASSIGNED, OUT_FOR_DELIVERY, DELIVERED, FAILED, DISPUTED
    val assignedDeliveryBoyId: String? = null,
    val assignedDeliveryBoyName: String? = null,
    val isLocallyCreated: Boolean = false,
    val isServerConfirmed: Boolean = false,
    val operationId: String = ""
)

data class Delivery(
    val deliveryId: String,
    val bookingId: String,
    val customerId: String,
    val customerName: String,
    val customerPhone: String,
    val deliveryAddress: String,
    val deliveryBoyId: String,
    val cylinderQuantity: Int = 1,
    val cylinderType: String = "14.2 kg Domestic",
    val deliveryTimestamp: String,
    val status: String = "DELIVERED", // DELIVERED, FAILED, DISPUTED
    val notes: String? = null,
    val operationId: String,
    val syncStatus: String = "LOCALLY_SAVED", // LOCALLY_SAVED, SYNC_PENDING, SYNCED, SYNC_FAILED
    val confirmationReference: String = "",
    val isServerConfirmed: Boolean = false
)

data class Payment(
    val paymentId: String,
    val bookingId: String,
    val customerId: String,
    val deliveryBoyId: String? = null,
    val amountDue: Double,
    val amountCollected: Double,
    val paymentMethod: String, // CASH, UPI
    val transactionReference: String? = null,
    val collectionTimestamp: String,
    val status: String = "RECORDED", // RECORDED, PENDING_VERIFICATION, VERIFIED, DISPUTED
    val isServerVerified: Boolean = false,
    val syncStatus: String = "LOCALLY_SAVED"
)

data class BluetoothPayload(
    val payloadId: String,
    val transferType: String = "DELIVERY_CONFIRMATION",
    val bookingId: String,
    val deliveryId: String,
    val consumerNumber: String,
    val customerName: String,
    val cylinderQuantity: Int,
    val amount: Double,
    val paymentMethod: String,
    val timestamp: String,
    val deliveryBoyName: String,
    val deliveryBoyId: String,
    val operationId: String,
    val signature: String = ""
)

data class BluetoothTransferRecord(
    val id: String,
    val deviceName: String,
    val deviceAddress: String,
    val transferType: String, // SENT, RECEIVED
    val bookingId: String,
    val deliveryId: String,
    val timestamp: String,
    val status: String, // SUCCESS, FAILED, REJECTED
    val rawJson: String
)

data class PendingSyncOperation(
    val operationId: String,
    val entityType: String, // BOOKING, DELIVERY, PAYMENT, BLUETOOTH_CONFIRMATION, SUPPORT_TICKET
    val entityId: String,
    val payloadJson: String,
    val createdAt: Long = System.currentTimeMillis(),
    val retryCount: Int = 0,
    val lastError: String? = null
)

data class SupportTicket(
    val id: Int,
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
