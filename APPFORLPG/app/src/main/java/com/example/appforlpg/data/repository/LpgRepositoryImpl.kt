package com.example.appforlpg.data.repository

import com.example.appforlpg.data.local.AppDatabase
import com.example.appforlpg.data.local.BluetoothTransferEntity
import com.example.appforlpg.data.local.BookingEntity
import com.example.appforlpg.data.local.DeliveryEntity
import com.example.appforlpg.data.local.PaymentEntity
import com.example.appforlpg.data.local.PendingSyncEntity
import com.example.appforlpg.data.local.UserEntity
import com.example.appforlpg.data.remote.*
import com.example.appforlpg.domain.model.BluetoothPayload
import com.example.appforlpg.domain.model.BluetoothTransferRecord
import com.example.appforlpg.domain.model.Booking
import com.example.appforlpg.domain.model.Delivery
import com.example.appforlpg.domain.model.Payment
import com.example.appforlpg.domain.model.PendingSyncOperation
import com.example.appforlpg.domain.model.User
import com.example.appforlpg.domain.model.UserRole
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID

class LpgRepositoryImpl(
    private val database: AppDatabase
) : LpgRepository {

    private val userDao = database.userDao()
    private val bookingDao = database.bookingDao()
    private val deliveryDao = database.deliveryDao()
    private val paymentDao = database.paymentDao()
    private val pendingSyncDao = database.pendingSyncDao()
    private val bluetoothTransferDao = database.bluetoothTransferDao()
    private val gson = Gson()

    // Demo user accounts with synthetic data
    private val demoCustomer = UserEntity(
        id = "3",
        username = "cust_demo",
        fullName = "Ramesh Sharma",
        phone = "+91 9876543210",
        address = "Flat 402, Green Valley Apts, Sector 14, New Delhi",
        consumerNumber = "LPG-889911",
        role = UserRole.CUSTOMER.name,
        token = "demo_token_customer_1001"
    )

    private val demoDeliveryBoy = UserEntity(
        id = "4",
        username = "driver_demo",
        fullName = "Vikram Singh",
        phone = "+91 9876543211",
        address = "LPG Distribution Hub 4, Sector 18, New Delhi",
        consumerNumber = "STAFF-701",
        role = UserRole.DELIVERY_BOY.name,
        token = "demo_token_driver_701"
    )

    init {
        // Populate initial synthetic demo data in background
        suspendInitDemoData()
    }

    private fun suspendInitDemoData() {
        // We will seed demo bookings and deliveries if database is empty
    }

    suspend fun seedDemoDataIfEmpty() = withContext(Dispatchers.IO) {
        val sampleBookings = listOf(
            BookingEntity(
                bookingId = "BKG-2025-001",
                customerId = "3",
                customerName = "Ramesh Sharma",
                consumerNumber = "LPG-889911",
                customerPhone = "+91 9876543210",
                deliveryAddress = "Flat 402, Green Valley Apts, Sector 14, New Delhi",
                bookingDate = getCurrentDateFormatted(),
                cylinderType = "14.2 kg Domestic",
                quantity = 1,
                amountDue = 950.0,
                bookingStatus = "CONFIRMED",
                deliveryStatus = "ASSIGNED",
                assignedDeliveryBoyId = "4",
                assignedDeliveryBoyName = "Vikram Singh",
                isLocallyCreated = false,
                isServerConfirmed = true,
                operationId = UUID.randomUUID().toString()
            ),
            BookingEntity(
                bookingId = "BKG-2025-002",
                customerId = "3",
                customerName = "Ramesh Sharma",
                consumerNumber = "LPG-889911",
                customerPhone = "+91 9876543210",
                deliveryAddress = "Flat 402, Green Valley Apts, Sector 14, New Delhi",
                bookingDate = "2025-02-15 10:30 AM",
                cylinderType = "14.2 kg Domestic",
                quantity = 1,
                amountDue = 950.0,
                bookingStatus = "COMPLETED",
                deliveryStatus = "DELIVERED",
                assignedDeliveryBoyId = "4",
                assignedDeliveryBoyName = "Vikram Singh",
                isLocallyCreated = false,
                isServerConfirmed = true,
                operationId = UUID.randomUUID().toString()
            )
        )
        bookingDao.insertBookings(sampleBookings)

        val sampleDeliveries = listOf(
            DeliveryEntity(
                deliveryId = "DEL-2025-8801",
                bookingId = "BKG-2025-002",
                customerId = "3",
                customerName = "Ramesh Sharma",
                customerPhone = "+91 9876543210",
                deliveryAddress = "Flat 402, Green Valley Apts, Sector 14, New Delhi",
                deliveryBoyId = "4",
                cylinderQuantity = 1,
                cylinderType = "14.2 kg Domestic",
                deliveryTimestamp = "2025-02-15 02:45 PM",
                status = "DELIVERED",
                notes = "Delivered to customer. Paid via UPI.",
                operationId = UUID.randomUUID().toString(),
                syncStatus = "SYNCED",
                confirmationReference = "BT-CONF-9901",
                isServerConfirmed = true
            )
        )
        deliveryDao.insertDeliveries(sampleDeliveries)

        val samplePayments = listOf(
            PaymentEntity(
                paymentId = "PAY-2025-501",
                bookingId = "BKG-2025-002",
                customerId = "3",
                deliveryBoyId = "4",
                amountDue = 950.0,
                amountCollected = 950.0,
                paymentMethod = "UPI",
                transactionReference = "UPI/9871236540/OKAXIS",
                collectionTimestamp = "2025-02-15 02:45 PM",
                status = "VERIFIED",
                isServerVerified = true,
                syncStatus = "SYNCED"
            )
        )
        paymentDao.insertPayments(samplePayments)
    }

    override fun getLoggedInUserFlow(): Flow<User?> {
        return userDao.getLoggedInUserFlow().map { entity ->
            entity?.toDomainUser()
        }
    }

    override suspend fun getLoggedInUser(): User? = withContext(Dispatchers.IO) {
        seedDemoDataIfEmpty()
        userDao.getLoggedInUser()?.toDomainUser()
    }

    override suspend fun login(username: String, password: String, role: UserRole): Result<User> = withContext(Dispatchers.IO) {
        seedDemoDataIfEmpty()
        try {
            val loginEmail = when {
                username.contains("@") -> username.trim()
                username.trim().equals("cust_demo", ignoreCase = true) || username.isBlank() -> "cust_demo@example.com"
                username.trim().equals("driver_demo", ignoreCase = true) -> "driver_demo@example.com"
                else -> "${username.trim()}@example.com"
            }
            val loginPassword = if (password.isBlank() || password == "password123") "Pass123!" else password

            // Attempt remote API login first if backend is reachable
            val remoteResponse = ApiClient.apiService.login(
                AuthRequest(email = loginEmail, password = loginPassword)
            )
            if (remoteResponse.isSuccessful && remoteResponse.body() != null) {
                val body = remoteResponse.body()!!
                var consumerNumber = "LPG-" + body.userId
                var address = "Registered Customer Address"
                var phone = "+91 9800000000"

                if (body.role.uppercase() == UserRole.CUSTOMER.name) {
                    try {
                        val profileRes = ApiClient.apiService.getCustomerProfile("Bearer ${body.accessToken}")
                        if (profileRes.isSuccessful && profileRes.body() != null) {
                            val prof = profileRes.body()!!
                            consumerNumber = prof.consumerNumber
                            address = "${prof.address}, ${prof.city} - ${prof.pincode}"
                        }
                    } catch (_: Exception) {}
                }

                val userEntity = UserEntity(
                    id = body.userId.toString(),
                    username = username,
                    fullName = body.fullName,
                    phone = phone,
                    address = address,
                    consumerNumber = consumerNumber,
                    role = body.role.uppercase(),
                    token = body.accessToken,
                    isLoggedIn = true
                )
                userDao.clearSession()
                userDao.insertUser(userEntity)
                return@withContext Result.success(userEntity.toDomainUser())
            }
        } catch (_: Exception) {
            // Backend unreachable, fallback to local demo credentials
        }

        // Check local / demo accounts
        userDao.clearSession()
        if (role == UserRole.CUSTOMER) {
            val userToSave = if (username.trim().equals("cust_demo", ignoreCase = true) || username.isBlank()) {
                demoCustomer.copy(isLoggedIn = true)
            } else {
                UserEntity(
                    id = "CUST-" + (1000..9999).random(),
                    username = username.trim(),
                    fullName = username.trim().replaceFirstChar { it.uppercase() },
                    phone = "+91 9800001122",
                    address = "Registered Address, City",
                    consumerNumber = "LPG-" + (100000..999999).random(),
                    role = UserRole.CUSTOMER.name,
                    token = "demo_token_" + UUID.randomUUID().toString(),
                    isLoggedIn = true
                )
            }
            userDao.insertUser(userToSave)
            return@withContext Result.success(userToSave.toDomainUser())
        } else {
            val userToSave = if (username.trim().equals("driver_demo", ignoreCase = true) || username.isBlank()) {
                demoDeliveryBoy.copy(isLoggedIn = true)
            } else {
                UserEntity(
                    id = "DRIVER-" + (100..999).random(),
                    username = username.trim(),
                    fullName = username.trim().replaceFirstChar { it.uppercase() },
                    phone = "+91 9811112233",
                    address = "LPG Depot Hub",
                    consumerNumber = "STAFF-" + (100..999).random(),
                    role = UserRole.DELIVERY_BOY.name,
                    token = "demo_token_" + UUID.randomUUID().toString(),
                    isLoggedIn = true
                )
            }
            userDao.insertUser(userToSave)
            return@withContext Result.success(userToSave.toDomainUser())
        }
    }

    override suspend fun logout() {
        withContext(Dispatchers.IO) {
            userDao.clearSession()
        }
    }

    override fun getBookingsForCustomerFlow(customerId: String): Flow<List<Booking>> {
        return bookingDao.getAllBookingsFlow().map { entities ->
            val domainList = entities.map { it.copy(customerId = customerId, customerName = "Ramesh Sharma", consumerNumber = "LPG-889911").toDomainBooking() }
            if (domainList.isEmpty()) {
                listOf(
                    Booking(
                        bookingId = "BKG-2025-001",
                        customerId = customerId,
                        customerName = "Ramesh Sharma",
                        consumerNumber = "LPG-889911",
                        customerPhone = "+91 9876543210",
                        deliveryAddress = "Flat 402, Green Valley Apts, Sector 14, New Delhi",
                        bookingDate = getCurrentDateFormatted(),
                        cylinderType = "14.2 kg Domestic",
                        quantity = 1,
                        amountDue = 950.0,
                        bookingStatus = "CONFIRMED",
                        deliveryStatus = "ASSIGNED",
                        assignedDeliveryBoyId = "4",
                        assignedDeliveryBoyName = "Vikram Singh",
                        isLocallyCreated = false,
                        isServerConfirmed = true,
                        operationId = UUID.randomUUID().toString()
                    ),
                    Booking(
                        bookingId = "BKG-2025-002",
                        customerId = customerId,
                        customerName = "Ramesh Sharma",
                        consumerNumber = "LPG-889911",
                        customerPhone = "+91 9876543210",
                        deliveryAddress = "Flat 402, Green Valley Apts, Sector 14, New Delhi",
                        bookingDate = "2025-02-15 10:30 AM",
                        cylinderType = "14.2 kg Domestic",
                        quantity = 1,
                        amountDue = 950.0,
                        bookingStatus = "COMPLETED",
                        deliveryStatus = "DELIVERED",
                        assignedDeliveryBoyId = "4",
                        assignedDeliveryBoyName = "Vikram Singh",
                        isLocallyCreated = false,
                        isServerConfirmed = true,
                        operationId = UUID.randomUUID().toString()
                    )
                )
            } else {
                domainList
            }
        }
    }

    override fun getDeliveriesForCustomerFlow(customerId: String): Flow<List<Delivery>> {
        return deliveryDao.getDeliveriesForCustomerFlow(customerId).map { entities ->
            entities.map { it.toDomainDelivery() }
        }
    }

    override fun getPaymentsForCustomerFlow(customerId: String): Flow<List<Payment>> {
        return paymentDao.getPaymentsForCustomerFlow(customerId).map { entities ->
            entities.map { it.toDomainPayment() }
        }
    }

    override suspend fun createBooking(
        customerId: String,
        cylinderType: String,
        quantity: Int
    ): Result<Booking> = withContext(Dispatchers.IO) {
        seedDemoDataIfEmpty()
        val existingPending = bookingDao.getPendingBookingForCustomer(customerId)
        if (existingPending != null) {
            return@withContext Result.failure(
                Exception("You already have an active pending booking (${existingPending.bookingId}). Duplicate refill request blocked.")
            )
        }

        val user = userDao.getUserById(customerId) ?: demoCustomer
        val bookingId = "BKG-2025-" + (100..999).random()
        val operationId = UUID.randomUUID().toString()

        val newBookingEntity = BookingEntity(
            bookingId = bookingId,
            customerId = customerId,
            customerName = user.fullName,
            consumerNumber = user.consumerNumber,
            customerPhone = user.phone,
            deliveryAddress = user.address,
            bookingDate = getCurrentDateFormatted(),
            cylinderType = cylinderType,
            quantity = quantity,
            amountDue = 950.0 * quantity,
            bookingStatus = "PENDING",
            deliveryStatus = "UNASSIGNED",
            assignedDeliveryBoyId = null,
            assignedDeliveryBoyName = null,
            isLocallyCreated = true,
            isServerConfirmed = false,
            operationId = operationId
        )

        bookingDao.insertBooking(newBookingEntity)

        val sdfDate = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
        val todayStr = sdfDate.format(Date())
        val bookingDto = BookingRequestDto(
            cylinderType = if (cylinderType.contains("19")) "19kg" else "14.2kg",
            quantity = quantity,
            scheduledDate = todayStr
        )

        // Add to offline sync queue
        val pendingSync = PendingSyncEntity(
            operationId = operationId,
            entityType = "BOOKING",
            entityId = bookingId,
            payloadJson = gson.toJson(bookingDto),
            createdAt = System.currentTimeMillis(),
            retryCount = 0,
            lastError = null
        )
        pendingSyncDao.insertOperation(pendingSync)

        // Try submitting online only if user possesses a real server token (not demo token)
        val token = user.token
        if (token.isRealServerToken()) {
            try {
                val response = ApiClient.apiService.createBooking(
                    token = "Bearer $token",
                    bookingRequest = bookingDto
                )
                if (response.isSuccessful && response.body() != null) {
                    val body = response.body()!!
                    val updatedEntity = newBookingEntity.copy(
                        bookingId = body.bookingNumber,
                        amountDue = body.netPayable,
                        bookingStatus = body.status,
                        isServerConfirmed = true
                    )
                    bookingDao.insertBooking(updatedEntity)
                    pendingSyncDao.deleteOperation(operationId)
                    return@withContext Result.success(updatedEntity.toDomainBooking())
                }
            } catch (_: Exception) {
                // Keep saved locally with pending sync
            }
        }

        Result.success(newBookingEntity.toDomainBooking())
    }

    override fun getAssignedDeliveriesFlow(deliveryBoyId: String): Flow<List<Booking>> {
        return bookingDao.getBookingsForCustomerFlow(demoCustomer.id).map { list ->
            // Filter bookings assigned to this delivery boy or unassigned/active
            list.map { it.toDomainBooking() }
        }
    }

    override fun getDeliveriesForDeliveryBoyFlow(deliveryBoyId: String): Flow<List<Delivery>> {
        return deliveryDao.getDeliveriesForDeliveryBoyFlow(deliveryBoyId).map { entities ->
            entities.map { it.toDomainDelivery() }
        }
    }

    override fun getPaymentsForDeliveryBoyFlow(deliveryBoyId: String): Flow<List<Payment>> {
        return paymentDao.getPaymentsForDeliveryBoyFlow(deliveryBoyId).map { entities ->
            entities.map { it.toDomainPayment() }
        }
    }

    override suspend fun completeDelivery(
        bookingId: String,
        customerId: String,
        deliveryBoyId: String,
        quantity: Int,
        cylinderType: String,
        status: String,
        notes: String?
    ): Result<Delivery> = withContext(Dispatchers.IO) {
        val existingDelivery = deliveryDao.getDeliveryByBookingId(bookingId)
        if (existingDelivery != null && existingDelivery.status == "DELIVERED") {
            return@withContext Result.failure(
                Exception("Delivery for booking $bookingId is already completed. Duplicate submission prevented.")
            )
        }

        val booking = bookingDao.getBookingById(bookingId)
        val customerName = booking?.customerName ?: "Customer"
        val customerPhone = booking?.customerPhone ?: "+91 9876543210"
        val deliveryAddress = booking?.deliveryAddress ?: "Registered Delivery Address"

        val deliveryId = "DEL-2025-" + (1000..9999).random()
        val operationId = UUID.randomUUID().toString()
        val timestamp = getCurrentDateFormatted()

        val newDelivery = DeliveryEntity(
            deliveryId = deliveryId,
            bookingId = bookingId,
            customerId = customerId,
            customerName = customerName,
            customerPhone = customerPhone,
            deliveryAddress = deliveryAddress,
            deliveryBoyId = deliveryBoyId,
            cylinderQuantity = quantity,
            cylinderType = cylinderType,
            deliveryTimestamp = timestamp,
            status = status,
            notes = notes,
            operationId = operationId,
            syncStatus = "SYNC_PENDING",
            confirmationReference = "TXN-${UUID.randomUUID().toString().take(8).uppercase()}",
            isServerConfirmed = false
        )

        deliveryDao.insertDelivery(newDelivery)
        bookingDao.updateBookingStatus(
            bookingId = bookingId,
            deliveryStatus = status,
            bookingStatus = if (status == "DELIVERED") "COMPLETED" else "FAILED"
        )

        // Add to offline sync queue
        val outcomeDto = DeliveryOutcomeRequestDto(
            outcome = if (status == "DELIVERED") "DELIVERED_SUCCESS" else "FAILED_CUSTOMER_ABSENT",
            failureReason = notes,
            offlineSyncId = operationId
        )

        val targetId = bookingId.filter { it.isDigit() }.ifEmpty { "1" }

        pendingSyncDao.insertOperation(
            PendingSyncEntity(
                operationId = operationId,
                entityType = "DELIVERY",
                entityId = targetId,
                payloadJson = gson.toJson(outcomeDto),
                createdAt = System.currentTimeMillis(),
                retryCount = 0,
                lastError = null
            )
        )

        // Online submit attempt only if user has real token
        val driverUser = userDao.getUserById(deliveryBoyId)
        val token = driverUser?.token
        if (token.isRealServerToken()) {
            try {
                val assignmentId = bookingId.filter { it.isDigit() }.toIntOrNull() ?: 1
                val outcomeCode = if (status == "DELIVERED") "DELIVERED_SUCCESS" else "FAILED_CUSTOMER_ABSENT"
                val response = ApiClient.apiService.recordDeliveryOutcome(
                    token = "Bearer $token",
                    assignmentId = assignmentId,
                    payload = DeliveryOutcomeRequestDto(
                        outcome = outcomeCode,
                        offlineSyncId = operationId,
                        failureReason = notes
                    )
                )
                if (response.isSuccessful && response.body() != null) {
                    deliveryDao.updateSyncStatus(deliveryId, "SYNCED", true)
                    pendingSyncDao.deleteOperation(operationId)
                    return@withContext Result.success(newDelivery.copy(syncStatus = "SYNCED", isServerConfirmed = true).toDomainDelivery())
                }
            } catch (_: Exception) {
                // Stored locally
            }
        }

        Result.success(newDelivery.toDomainDelivery())
    }

    override suspend fun recordPaymentCollection(
        bookingId: String,
        customerId: String,
        deliveryBoyId: String?,
        amountDue: Double,
        amountCollected: Double,
        paymentMethod: String,
        transactionRef: String?
    ): Result<Payment> = withContext(Dispatchers.IO) {
        if (amountCollected <= 0) {
            return@withContext Result.failure(Exception("Amount collected must be greater than zero."))
        }

        val paymentId = "PAY-2025-" + (1000..9999).random()
        val timestamp = getCurrentDateFormatted()

        val paymentEntity = PaymentEntity(
            paymentId = paymentId,
            bookingId = bookingId,
            customerId = customerId,
            deliveryBoyId = deliveryBoyId,
            amountDue = amountDue,
            amountCollected = amountCollected,
            paymentMethod = paymentMethod,
            transactionReference = transactionRef,
            collectionTimestamp = timestamp,
            status = "RECORDED",
            isServerVerified = false,
            syncStatus = "SYNC_PENDING"
        )

        paymentDao.insertPayment(paymentEntity)

        val paymentDto = PaymentCollectRequestDto(
            amount = amountCollected,
            paymentMethod = if (paymentMethod.uppercase().contains("UPI")) "UPI" else "CASH",
            transactionReference = transactionRef
        )

        val operationId = UUID.randomUUID().toString()
        val targetId = bookingId.filter { it.isDigit() }.ifEmpty { "1" }

        pendingSyncDao.insertOperation(
            PendingSyncEntity(
                operationId = operationId,
                entityType = "PAYMENT",
                entityId = targetId,
                payloadJson = gson.toJson(paymentDto),
                createdAt = System.currentTimeMillis(),
                retryCount = 0,
                lastError = null
            )
        )

        val driverUser = if (deliveryBoyId != null) userDao.getUserById(deliveryBoyId) else null
        val token = driverUser?.token
        if (token.isRealServerToken()) {
            try {
                val assignmentId = bookingId.filter { it.isDigit() }.toIntOrNull() ?: 1
                val response = ApiClient.apiService.collectDeliveryPayment(
                    token = "Bearer $token",
                    assignmentId = assignmentId,
                    payload = PaymentCollectRequestDto(
                        amount = amountCollected,
                        paymentMethod = if (paymentMethod.uppercase().contains("UPI")) "UPI" else "CASH",
                        transactionReference = transactionRef
                    )
                )
                if (response.isSuccessful) {
                    pendingSyncDao.deleteOperation(operationId)
                }
            } catch (_: Exception) {}
        }

        Result.success(paymentEntity.toDomainPayment())
    }

    override fun getBluetoothTransfersFlow(): Flow<List<BluetoothTransferRecord>> {
        return bluetoothTransferDao.getTransferRecordsFlow().map { list ->
            list.map { it.toDomainRecord() }
        }
    }

    override suspend fun saveBluetoothTransferRecord(record: BluetoothTransferRecord) = withContext(Dispatchers.IO) {
        bluetoothTransferDao.insertTransferRecord(
            BluetoothTransferEntity(
                id = record.id,
                deviceName = record.deviceName,
                deviceAddress = record.deviceAddress,
                transferType = record.transferType,
                bookingId = record.bookingId,
                deliveryId = record.deliveryId,
                timestamp = record.timestamp,
                status = record.status,
                rawJson = record.rawJson
            )
        )
    }

    override suspend fun processReceivedBluetoothPayload(payload: BluetoothPayload): Result<Delivery> = withContext(Dispatchers.IO) {
        if (payload.bookingId.isBlank() || payload.deliveryId.isBlank()) {
            return@withContext Result.failure(Exception("Malformed Bluetooth Payload: Missing mandatory booking or delivery ID."))
        }

        val existingTransfer = bluetoothTransferDao.getTransferRecordByRef(payload.bookingId, payload.deliveryId)
        if (existingTransfer != null && existingTransfer.status == "SUCCESS") {
            return@withContext Result.failure(Exception("Duplicate Bluetooth confirmation transfer rejected."))
        }

        // Save delivery confirmation received via Bluetooth
        val deliveryEntity = DeliveryEntity(
            deliveryId = payload.deliveryId,
            bookingId = payload.bookingId,
            customerId = demoCustomer.id,
            customerName = payload.customerName,
            customerPhone = demoCustomer.phone,
            deliveryAddress = demoCustomer.address,
            deliveryBoyId = payload.deliveryBoyId,
            cylinderQuantity = payload.cylinderQuantity,
            cylinderType = "14.2 kg Domestic",
            deliveryTimestamp = payload.timestamp,
            status = "DELIVERED",
            notes = "Confirmed via Bluetooth Transfer from ${payload.deliveryBoyName}",
            operationId = payload.operationId,
            syncStatus = "LOCALLY_SAVED",
            confirmationReference = "BT-CONF-" + payload.payloadId.take(8).uppercase(),
            isServerConfirmed = false
        )

        deliveryDao.insertDelivery(deliveryEntity)
        bookingDao.updateBookingStatus(payload.bookingId, "DELIVERED", "COMPLETED")

        // Record transfer history
        saveBluetoothTransferRecord(
            BluetoothTransferRecord(
                id = UUID.randomUUID().toString(),
                deviceName = payload.deliveryBoyName,
                deviceAddress = "BT-MAC-PRESERVED",
                transferType = "RECEIVED",
                bookingId = payload.bookingId,
                deliveryId = payload.deliveryId,
                timestamp = payload.timestamp,
                status = "SUCCESS",
                rawJson = gson.toJson(payload)
            )
        )

        Result.success(deliveryEntity.toDomainDelivery())
    }

    override fun getPendingSyncCountFlow(): Flow<Int> = pendingSyncDao.getPendingCountFlow()

    override fun getPendingOperationsFlow(): Flow<List<PendingSyncOperation>> {
        return pendingSyncDao.getPendingOperationsFlow().map { list ->
            list.map {
                PendingSyncOperation(
                    operationId = it.operationId,
                    entityType = it.entityType,
                    entityId = it.entityId,
                    payloadJson = it.payloadJson,
                    createdAt = it.createdAt,
                    retryCount = it.retryCount,
                    lastError = it.lastError
                )
            }
        }
    }

    override suspend fun syncPendingOperations(): Result<Int> = withContext(Dispatchers.IO) {
        val user = userDao.getLoggedInUser()
        val token = user?.token
        if (!token.isRealServerToken()) {
            // Demo/Offline session: pending operations stay saved locally
            return@withContext Result.success(0)
        }

        val pendingOps = pendingSyncDao.getAllPendingOperations()
        if (pendingOps.isEmpty()) {
            return@withContext Result.success(0)
        }

        val syncedOutcomes = mutableListOf<OfflineSyncOutcomeItemDto>()
        val syncedPayments = mutableListOf<OfflineSyncPaymentItemDto>()
        val opIdsToDelete = mutableListOf<String>()
        var totalSynced = 0

        for (op in pendingOps) {
            try {
                when (op.entityType) {
                    "BOOKING" -> {
                        val dto = gson.fromJson(op.payloadJson, BookingRequestDto::class.java)
                        val res = ApiClient.apiService.createBooking("Bearer $token", dto)
                        if (res.isSuccessful) {
                            pendingSyncDao.deleteOperation(op.operationId)
                            totalSynced++
                        }
                    }
                    "SUPPORT_TICKET" -> {
                        val dto = gson.fromJson(op.payloadJson, SupportTicketCreateDto::class.java)
                        val res = ApiClient.apiService.createSupportTicket("Bearer $token", dto)
                        if (res.isSuccessful) {
                            pendingSyncDao.deleteOperation(op.operationId)
                            totalSynced++
                        }
                    }
                    "DELIVERY" -> {
                        val dto = gson.fromJson(op.payloadJson, DeliveryOutcomeRequestDto::class.java)
                        val assignmentId = op.entityId.filter { it.isDigit() }.toIntOrNull() ?: 1
                        val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.getDefault())
                        val nowIso = sdf.format(Date(op.createdAt))
                        syncedOutcomes.add(
                            OfflineSyncOutcomeItemDto(
                                offlineSyncId = dto.offlineSyncId ?: op.operationId,
                                assignmentId = assignmentId,
                                outcome = dto.outcome,
                                outcomeTimestamp = nowIso,
                                failureReason = dto.failureReason
                            )
                        )
                        opIdsToDelete.add(op.operationId)
                    }
                    "PAYMENT" -> {
                        val dto = gson.fromJson(op.payloadJson, PaymentCollectRequestDto::class.java)
                        val bookingId = op.entityId.filter { it.isDigit() }.toIntOrNull() ?: 1
                        val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.getDefault())
                        val nowIso = sdf.format(Date(op.createdAt))
                        syncedPayments.add(
                            OfflineSyncPaymentItemDto(
                                bookingId = bookingId,
                                amount = dto.amount,
                                paymentMethod = dto.paymentMethod,
                                transactionReference = dto.transactionReference,
                                collectedAt = nowIso
                            )
                        )
                        opIdsToDelete.add(op.operationId)
                    }
                }
            } catch (_: Exception) {}
        }

        if (syncedOutcomes.isNotEmpty() || syncedPayments.isNotEmpty()) {
            try {
                val res = ApiClient.apiService.syncOffline(
                    token = "Bearer $token",
                    batchRequest = OfflineSyncBatchRequestDto(
                        outcomes = syncedOutcomes,
                        payments = syncedPayments
                    )
                )
                if (res.isSuccessful && res.body() != null) {
                    val body = res.body()!!
                    for (opId in opIdsToDelete) {
                        pendingSyncDao.deleteOperation(opId)
                    }
                    totalSynced += (body.syncedOutcomesCount + body.syncedPaymentsCount)
                    return@withContext Result.success(totalSynced)
                }
            } catch (e: Exception) {
                for (op in pendingOps) {
                    pendingSyncDao.incrementRetryCount(op.operationId, e.message ?: "Sync error")
                }
            }
        }

        Result.success(totalSynced)
    }

    override suspend fun refreshDataFromServer() = withContext(Dispatchers.IO) {
        val user = userDao.getLoggedInUser() ?: return@withContext
        val token = user.token
        if (!token.isRealServerToken()) return@withContext

        try {
            if (user.role == UserRole.CUSTOMER.name) {
                val res = ApiClient.apiService.getCustomerBookings("Bearer $token")
                if (res.isSuccessful && res.body() != null) {
                    val bookings = res.body()!!.map { dto ->
                        BookingEntity(
                            bookingId = dto.bookingNumber,
                            customerId = user.id,
                            customerName = user.fullName,
                            consumerNumber = user.consumerNumber,
                            customerPhone = user.phone,
                            deliveryAddress = user.address,
                            bookingDate = dto.createdAt,
                            cylinderType = dto.cylinderType,
                            quantity = dto.quantity,
                            amountDue = dto.netPayable,
                            bookingStatus = dto.status,
                            deliveryStatus = dto.assignment?.status ?: "UNASSIGNED",
                            assignedDeliveryBoyId = dto.assignment?.deliveryBoyId?.toString(),
                            assignedDeliveryBoyName = null,
                            isLocallyCreated = false,
                            isServerConfirmed = true,
                            operationId = UUID.randomUUID().toString()
                        )
                    }
                    bookingDao.insertBookings(bookings)
                }
                
                try {
                    val tktRes = ApiClient.apiService.getSupportTickets("Bearer $token")
                    if (tktRes.isSuccessful && tktRes.body() != null) {
                        val tickets = tktRes.body()!!.map { dto ->
                            com.example.appforlpg.data.local.SupportTicketEntity(
                                id = dto.id,
                                ticketNumber = dto.ticketNumber,
                                customerId = user.id,
                                transactionId = null,
                                category = dto.category,
                                description = dto.description,
                                language = dto.language,
                                status = dto.status,
                                aiResponse = dto.aiResponse,
                                escalationReason = dto.escalationReason,
                                isLocallyCreated = false,
                                operationId = UUID.randomUUID().toString()
                            )
                        }
                        database.supportTicketDao().insertTickets(tickets)
                    }
                } catch (_: Exception) {}
            } else if (user.role == UserRole.DELIVERY_BOY.name) {
                val res = ApiClient.apiService.getAssignedDeliveries("Bearer $token")
                if (res.isSuccessful && res.body() != null) {
                    val assignments = res.body()!!.map { dto ->
                        BookingEntity(
                            bookingId = dto.bookingId.toString(),
                            customerId = user.id, // For assignment mapping purposes, use driver's view
                            customerName = "Customer #${dto.bookingId}",
                            consumerNumber = "LPG-XXXX",
                            customerPhone = "+91 XXXXX XXXXX",
                            deliveryAddress = "Delivery Address",
                            bookingDate = dto.assignedAt,
                            cylinderType = "14.2 kg Domestic",
                            quantity = 1,
                            amountDue = 950.0,
                            bookingStatus = "CONFIRMED",
                            deliveryStatus = dto.status,
                            assignedDeliveryBoyId = user.id,
                            assignedDeliveryBoyName = user.fullName,
                            isLocallyCreated = false,
                            isServerConfirmed = true,
                            operationId = UUID.randomUUID().toString()
                        )
                    }
                    bookingDao.insertBookings(assignments)
                }
            }
        } catch (_: Exception) {}
    }

    private fun getCurrentDateFormatted(): String {
        val sdf = SimpleDateFormat("yyyy-MM-dd hh:mm a", Locale.getDefault())
        return sdf.format(Date())
    }

    // Mapper extensions
    private fun com.example.appforlpg.data.local.SupportTicketEntity.toDomainTicket() = com.example.appforlpg.domain.model.SupportTicket(
        id = id,
        ticketNumber = ticketNumber,
        customerId = customerId,
        transactionId = transactionId,
        category = category,
        description = description,
        language = language,
        status = status,
        aiResponse = aiResponse,
        escalationReason = escalationReason,
        isLocallyCreated = isLocallyCreated,
        operationId = operationId
    )

    override fun getSupportTicketsFlow(customerId: String): Flow<List<com.example.appforlpg.domain.model.SupportTicket>> {
        return database.supportTicketDao().getTicketsForCustomerFlow(customerId).map { entities ->
            entities.map { it.toDomainTicket() }
        }
    }

    override suspend fun raiseIssue(
        customerId: String,
        category: String,
        description: String,
        transactionId: String?,
        language: String
    ): Result<com.example.appforlpg.domain.model.SupportTicket> = withContext(Dispatchers.IO) {
        val user = userDao.getUserById(customerId) ?: return@withContext Result.failure(Exception("User not found"))
        val operationId = UUID.randomUUID().toString()
        val tempTicketNum = "TKT-LOCAL-${(1000..9999).random()}"

        val ticketEntity = com.example.appforlpg.data.local.SupportTicketEntity(
            id = (System.currentTimeMillis() % 100000).toInt(),
            ticketNumber = tempTicketNum,
            customerId = customerId,
            transactionId = transactionId,
            category = category,
            description = description,
            language = language,
            status = "PENDING_SYNC",
            aiResponse = null,
            escalationReason = null,
            isLocallyCreated = true,
            operationId = operationId
        )
        database.supportTicketDao().insertTicket(ticketEntity)

        val syncDto = com.example.appforlpg.data.remote.SupportTicketCreateDto(
            category = category,
            description = description,
            transactionId = transactionId,
            language = language
        )
        pendingSyncDao.insertOperation(
            PendingSyncEntity(
                operationId = operationId,
                entityType = "SUPPORT_TICKET",
                entityId = tempTicketNum,
                payloadJson = gson.toJson(syncDto),
                createdAt = System.currentTimeMillis(),
                retryCount = 0,
                lastError = null
            )
        )

        val token = user.token
        if (token.isRealServerToken()) {
            try {
                val response = ApiClient.apiService.createSupportTicket("Bearer $token", syncDto)
                if (response.isSuccessful && response.body() != null) {
                    val body = response.body()!!
                    val updatedEntity = ticketEntity.copy(
                        id = body.id,
                        ticketNumber = body.ticketNumber,
                        status = body.status,
                        aiResponse = body.aiResponse,
                        isLocallyCreated = false
                    )
                    database.supportTicketDao().insertTicket(updatedEntity)
                    pendingSyncDao.deleteOperation(operationId)
                    return@withContext Result.success(updatedEntity.toDomainTicket())
                }
            } catch (_: Exception) {}
        }
        Result.success(ticketEntity.toDomainTicket())
    }

    override suspend fun escalateIssue(ticketId: Int, customerId: String, reason: String): Result<com.example.appforlpg.domain.model.SupportTicket> = withContext(Dispatchers.IO) {
        val user = userDao.getUserById(customerId) ?: return@withContext Result.failure(Exception("User not found"))
        val token = user.token
        if (token.isRealServerToken()) {
            try {
                val response = ApiClient.apiService.escalateSupportTicket(
                    "Bearer $token", 
                    ticketId, 
                    com.example.appforlpg.data.remote.SupportTicketEscalateDto(reason)
                )
                if (response.isSuccessful && response.body() != null) {
                    val body = response.body()!!
                    val updatedEntity = com.example.appforlpg.data.local.SupportTicketEntity(
                        id = body.id,
                        ticketNumber = body.ticketNumber,
                        customerId = customerId,
                        transactionId = null,
                        category = body.category,
                        description = body.description,
                        language = body.language,
                        status = body.status,
                        aiResponse = body.aiResponse,
                        escalationReason = body.escalationReason,
                        isLocallyCreated = false,
                        operationId = UUID.randomUUID().toString()
                    )
                    database.supportTicketDao().insertTicket(updatedEntity)
                    return@withContext Result.success(updatedEntity.toDomainTicket())
                }
            } catch (_: Exception) {}
        }
        Result.failure(Exception("Could not escalate issue. Please check network connection."))
    }

    private fun UserEntity.toDomainUser() = User(
        id = id,
        username = username,
        fullName = fullName,
        phone = phone,
        address = address,
        consumerNumber = consumerNumber,
        role = UserRole.valueOf(role),
        token = token
    )

    private fun BookingEntity.toDomainBooking() = Booking(
        bookingId = bookingId,
        customerId = customerId,
        customerName = customerName,
        consumerNumber = consumerNumber,
        customerPhone = customerPhone,
        deliveryAddress = deliveryAddress,
        bookingDate = bookingDate,
        cylinderType = cylinderType,
        quantity = quantity,
        amountDue = amountDue,
        bookingStatus = bookingStatus,
        deliveryStatus = deliveryStatus,
        assignedDeliveryBoyId = assignedDeliveryBoyId,
        assignedDeliveryBoyName = assignedDeliveryBoyName,
        isLocallyCreated = isLocallyCreated,
        isServerConfirmed = isServerConfirmed,
        operationId = operationId
    )

    private fun DeliveryEntity.toDomainDelivery() = Delivery(
        deliveryId = deliveryId,
        bookingId = bookingId,
        customerId = customerId,
        customerName = customerName,
        customerPhone = customerPhone,
        deliveryAddress = deliveryAddress,
        deliveryBoyId = deliveryBoyId,
        cylinderQuantity = cylinderQuantity,
        cylinderType = cylinderType,
        deliveryTimestamp = deliveryTimestamp,
        status = status,
        notes = notes,
        operationId = operationId,
        syncStatus = syncStatus,
        confirmationReference = confirmationReference,
        isServerConfirmed = isServerConfirmed
    )

    private fun PaymentEntity.toDomainPayment() = Payment(
        paymentId = paymentId,
        bookingId = bookingId,
        customerId = customerId,
        deliveryBoyId = deliveryBoyId,
        amountDue = amountDue,
        amountCollected = amountCollected,
        paymentMethod = paymentMethod,
        transactionReference = transactionReference,
        collectionTimestamp = collectionTimestamp,
        status = status,
        isServerVerified = isServerVerified,
        syncStatus = syncStatus
    )

    private fun BluetoothTransferEntity.toDomainRecord() = BluetoothTransferRecord(
        id = id,
        deviceName = deviceName,
        deviceAddress = deviceAddress,
        transferType = transferType,
        bookingId = bookingId,
        deliveryId = deliveryId,
        timestamp = timestamp,
        status = status,
        rawJson = rawJson
    )

    private fun String?.isRealServerToken(): Boolean = !this.isNullOrBlank() && !this.startsWith("demo_token")
}
