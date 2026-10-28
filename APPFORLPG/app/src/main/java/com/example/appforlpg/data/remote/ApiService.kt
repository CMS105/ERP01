package com.example.appforlpg.data.remote

import com.google.gson.annotations.SerializedName
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path

// Data Transfer Objects matching FastAPI backend schemas (/api/v1/)

data class AuthRequest(
    val email: String,
    val password: String
)

data class AuthResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String,
    @SerializedName("role") val role: String,
    @SerializedName("user_id") val userId: Int,
    @SerializedName("full_name") val fullName: String
)

data class CustomerProfileDto(
    val id: Int,
    @SerializedName("user_id") val userId: Int,
    @SerializedName("consumer_number") val consumerNumber: String,
    val address: String,
    val city: String,
    val pincode: String,
    @SerializedName("cylinder_quota_limit") val cylinderQuotaLimit: Int,
    @SerializedName("quota_used_this_year") val quotaUsedThisYear: Int,
    @SerializedName("connection_type") val connectionType: String
)

data class BookingRequestDto(
    @SerializedName("cylinder_type") val cylinderType: String = "14.2kg",
    val quantity: Int = 1,
    @SerializedName("scheduled_date") val scheduledDate: String
)

data class BookingResponseDto(
    val id: Int,
    @SerializedName("booking_number") val bookingNumber: String,
    @SerializedName("customer_id") val customerId: Int,
    @SerializedName("cylinder_type") val cylinderType: String,
    val quantity: Int,
    @SerializedName("unit_price") val unitPrice: Double,
    @SerializedName("total_amount") val totalAmount: Double,
    @SerializedName("subsidy_amount") val subsidyAmount: Double,
    @SerializedName("net_payable") val netPayable: Double,
    val status: String,
    @SerializedName("scheduled_date") val scheduledDate: String,
    @SerializedName("created_at") val createdAt: String,
    val assignment: DeliveryAssignmentDto? = null,
    val payment: PaymentRecordDto? = null
)

data class DeliveryAssignmentDto(
    val id: Int,
    @SerializedName("booking_id") val bookingId: Int,
    @SerializedName("delivery_boy_id") val deliveryBoyId: Int,
    @SerializedName("cylinder_id") val cylinderId: Int? = null,
    @SerializedName("assigned_at") val assignedAt: String,
    val status: String,
    val notes: String? = null,
    val execution: DeliveryExecutionDto? = null
)

data class DeliveryExecutionDto(
    val id: Int,
    @SerializedName("assignment_id") val assignmentId: Int,
    @SerializedName("booking_id") val bookingId: Int,
    @SerializedName("delivery_boy_id") val deliveryBoyId: Int,
    val outcome: String,
    @SerializedName("outcome_timestamp") val outcomeTimestamp: String,
    @SerializedName("offline_sync_id") val offlineSyncId: String? = null,
    @SerializedName("synced_at") val syncedAt: String,
    @SerializedName("empty_cylinder_returned_serial") val emptyCylinderReturnedSerial: String? = null,
    @SerializedName("failure_reason") val failureReason: String? = null
)

data class DeliveryOutcomeRequestDto(
    val outcome: String, // DELIVERED_SUCCESS, CANCELLED_CUSTOMER_REFUSED, FAILED_CUSTOMER_ABSENT
    @SerializedName("empty_cylinder_returned_serial") val emptyCylinderReturnedSerial: String? = null,
    @SerializedName("failure_reason") val failureReason: String? = null,
    @SerializedName("offline_sync_id") val offlineSyncId: String? = null
)

data class PaymentCollectRequestDto(
    val amount: Double,
    @SerializedName("payment_method") val paymentMethod: String, // CASH, UPI
    @SerializedName("transaction_reference") val transactionReference: String? = null
)

data class PaymentRecordDto(
    val id: Int,
    @SerializedName("booking_id") val bookingId: Int,
    @SerializedName("customer_id") val customerId: Int,
    @SerializedName("delivery_boy_id") val deliveryBoyId: Int? = null,
    val amount: Double,
    @SerializedName("payment_method") val paymentMethod: String,
    @SerializedName("payment_status") val paymentStatus: String,
    @SerializedName("transaction_reference") val transactionReference: String? = null,
    @SerializedName("collected_at") val collectedAt: String? = null,
    @SerializedName("created_at") val createdAt: String
)

data class OfflineSyncOutcomeItemDto(
    @SerializedName("offline_sync_id") val offlineSyncId: String,
    @SerializedName("assignment_id") val assignmentId: Int,
    val outcome: String,
    @SerializedName("outcome_timestamp") val outcomeTimestamp: String,
    @SerializedName("empty_cylinder_returned_serial") val emptyCylinderReturnedSerial: String? = null,
    @SerializedName("failure_reason") val failureReason: String? = null
)

data class OfflineSyncPaymentItemDto(
    @SerializedName("booking_id") val bookingId: Int,
    val amount: Double,
    @SerializedName("payment_method") val paymentMethod: String,
    @SerializedName("transaction_reference") val transactionReference: String? = null,
    @SerializedName("collected_at") val collectedAt: String
)

data class OfflineSyncBatchRequestDto(
    val outcomes: List<OfflineSyncOutcomeItemDto> = emptyList(),
    val payments: List<OfflineSyncPaymentItemDto> = emptyList()
)

data class OfflineSyncBatchResponseDto(
    @SerializedName("synced_outcomes_count") val syncedOutcomesCount: Int,
    @SerializedName("synced_payments_count") val syncedPaymentsCount: Int,
    val errors: List<String> = emptyList()
)

data class SupportTicketCreateDto(
    val category: String,
    val description: String,
    @SerializedName("transaction_id") val transactionId: String? = null,
    val language: String = "English"
)

data class SupportTicketOutDto(
    val id: Int,
    @SerializedName("ticket_number") val ticketNumber: String,
    val category: String,
    val description: String,
    val language: String,
    val status: String,
    @SerializedName("ai_response") val aiResponse: String? = null,
    @SerializedName("escalation_reason") val escalationReason: String? = null
)

data class SupportTicketEscalateDto(
    @SerializedName("escalation_reason") val escalationReason: String
)

interface ApiService {
    @POST("api/v1/auth/login")
    suspend fun login(@Body request: AuthRequest): Response<AuthResponse>

    @GET("api/v1/customer/profile")
    suspend fun getCustomerProfile(
        @Header("Authorization") token: String
    ): Response<CustomerProfileDto>

    @POST("api/v1/customer/bookings")
    suspend fun createBooking(
        @Header("Authorization") token: String,
        @Body bookingRequest: BookingRequestDto
    ): Response<BookingResponseDto>

    @GET("api/v1/customer/bookings")
    suspend fun getCustomerBookings(
        @Header("Authorization") token: String
    ): Response<List<BookingResponseDto>>

    @GET("api/v1/customer/deliveries")
    suspend fun getCustomerDeliveries(
        @Header("Authorization") token: String
    ): Response<List<DeliveryAssignmentDto>>

    @GET("api/v1/customer/payments")
    suspend fun getCustomerPayments(
        @Header("Authorization") token: String
    ): Response<List<PaymentRecordDto>>

    @POST("api/v1/customer/tickets")
    suspend fun createSupportTicket(
        @Header("Authorization") token: String,
        @Body payload: SupportTicketCreateDto
    ): Response<SupportTicketOutDto>

    @GET("api/v1/customer/tickets")
    suspend fun getSupportTickets(
        @Header("Authorization") token: String
    ): Response<List<SupportTicketOutDto>>

    @POST("api/v1/customer/tickets/{ticket_id}/escalate")
    suspend fun escalateSupportTicket(
        @Header("Authorization") token: String,
        @Path("ticket_id") ticketId: Int,
        @Body payload: SupportTicketEscalateDto
    ): Response<SupportTicketOutDto>

    @GET("api/v1/delivery-boy/deliveries/assigned")
    suspend fun getAssignedDeliveries(
        @Header("Authorization") token: String
    ): Response<List<DeliveryAssignmentDto>>

    @POST("api/v1/delivery-boy/deliveries/{assignment_id}/outcome")
    suspend fun recordDeliveryOutcome(
        @Header("Authorization") token: String,
        @Path("assignment_id") assignmentId: Int,
        @Body payload: DeliveryOutcomeRequestDto
    ): Response<DeliveryExecutionDto>

    @POST("api/v1/delivery-boy/deliveries/{assignment_id}/collect-payment")
    suspend fun collectDeliveryPayment(
        @Header("Authorization") token: String,
        @Path("assignment_id") assignmentId: Int,
        @Body payload: PaymentCollectRequestDto
    ): Response<PaymentRecordDto>

    @POST("api/v1/delivery-boy/sync-offline")
    suspend fun syncOffline(
        @Header("Authorization") token: String,
        @Body batchRequest: OfflineSyncBatchRequestDto
    ): Response<OfflineSyncBatchResponseDto>
}
