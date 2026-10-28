package com.example.appforlpg.ui.delivery

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.CloudDone
import androidx.compose.material.icons.filled.CloudSync
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.LocalShipping
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Payment
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.appforlpg.domain.model.Booking
import com.example.appforlpg.domain.model.User

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DeliveryBoyScreen(
    user: User,
    deliveryBoyViewModel: DeliveryBoyViewModel,
    isKannada: Boolean,
    onLanguageToggle: (Boolean) -> Unit,
    onLogout: () -> Unit
) {
    val uiState by deliveryBoyViewModel.uiState.collectAsState()
    val assignedBookings by deliveryBoyViewModel.assignedBookings.collectAsState()
    val pendingSyncCount by deliveryBoyViewModel.pendingSyncCount.collectAsState()

    var activeDeliveryForCompletion by remember { mutableStateOf<Booking?>(null) }
    var activeDeliveryForPayment by remember { mutableStateOf<Booking?>(null) }

    val filteredBookings = remember(assignedBookings, uiState.searchQuery, uiState.statusFilter) {
        assignedBookings.filter { booking ->
            val matchesQuery = uiState.searchQuery.isBlank() ||
                    booking.customerName.contains(uiState.searchQuery, ignoreCase = true) ||
                    booking.bookingId.contains(uiState.searchQuery, ignoreCase = true) ||
                    booking.customerPhone.contains(uiState.searchQuery)
            val matchesFilter = when (uiState.statusFilter) {
                "ASSIGNED" -> booking.deliveryStatus != "DELIVERED"
                "COMPLETED" -> booking.deliveryStatus == "DELIVERED"
                else -> true
            }
            matchesQuery && matchesFilter
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            text = if (isKannada) "ಎಲ್.ಪಿ.ಜಿ. ವಿಲೇವಾರಿ ಪಾಲುದಾರ" else "LPG Delivery Partner",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "${user.fullName} (${user.consumerNumber})",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.85f)
                        )
                    }
                },
                actions = {
                    IconButton(onClick = { onLanguageToggle(!isKannada) }) {
                        Icon(
                            imageVector = Icons.Default.Language,
                            contentDescription = "Language Switch",
                            tint = MaterialTheme.colorScheme.onPrimary
                        )
                    }
                    IconButton(onClick = onLogout) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.Logout,
                            contentDescription = "Log Out",
                            tint = MaterialTheme.colorScheme.onPrimary
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    actionIconContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            // Notifications / Messages Banner
            item {
                AnimatedVisibility(visible = uiState.successMessage != null) {
                    uiState.successMessage?.let { msg ->
                        Surface(
                            color = MaterialTheme.colorScheme.primaryContainer,
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(
                                modifier = Modifier.padding(14.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    imageVector = Icons.Default.CheckCircle,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.primary
                                )
                                Spacer(modifier = Modifier.width(10.dp))
                                Text(
                                    text = msg,
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onPrimaryContainer,
                                    modifier = Modifier.weight(1f)
                                )
                            }
                        }
                    }
                }

                AnimatedVisibility(visible = uiState.errorMessage != null) {
                    uiState.errorMessage?.let { msg ->
                        Surface(
                            color = MaterialTheme.colorScheme.errorContainer,
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(
                                modifier = Modifier.padding(14.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = msg,
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onErrorContainer,
                                    modifier = Modifier.weight(1f)
                                )
                            }
                        }
                    }
                }
            }

            // Sync Control Panel
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surfaceVariant
                    )
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = if (pendingSyncCount > 0) Icons.Default.CloudSync else Icons.Default.CloudDone,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(28.dp)
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Column {
                                Text(
                                    text = if (isKannada) "ಆಫ್‌ಲೈನ್ ಸಿಂಕ್ ನಿಯಂತ್ರಣ" else "Offline Sync Center",
                                    fontWeight = FontWeight.Bold,
                                    style = MaterialTheme.typography.titleSmall
                                )
                                Text(
                                    text = if (pendingSyncCount > 0) {
                                        if (isKannada) "$pendingSyncCount ಸ್ಥಳೀಯ ವಹಿವಾಟುಗಳು ಕಾಯುತ್ತಿವೆ" else "$pendingSyncCount Local Operations Pending"
                                    } else {
                                        if (isKannada) "ಎಲ್ಲಾ ಡೇಟಾ ಸಿಂಕ್ ಆಗಿದೆ" else "All Operations Synchronized"
                                    },
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }

                        Button(
                            onClick = { deliveryBoyViewModel.triggerSync() },
                            enabled = !uiState.isLoading,
                            shape = RoundedCornerShape(10.dp)
                        ) {
                            if (uiState.isLoading) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(18.dp),
                                    color = MaterialTheme.colorScheme.onPrimary,
                                    strokeWidth = 2.dp
                                )
                            } else {
                                Text(if (isKannada) "ಸಿಂಕ್ ಮಾಡಿ" else "Sync Now", fontSize = 13.sp)
                            }
                        }
                    }
                }
            }

            // Search Bar & Filter
            item {
                OutlinedTextField(
                    value = uiState.searchQuery,
                    onValueChange = { deliveryBoyViewModel.updateSearchQuery(it) },
                    placeholder = { Text(if (isKannada) "ಗ್ರಾಹಕರ ಹೆಸರು, ಫೋನ್ ಅಥವಾ ಐಡಿ ಹುಡುಕಿ..." else "Search customer, phone or booking ref...") },
                    leadingIcon = { Icon(imageVector = Icons.Default.Search, contentDescription = null) },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    singleLine = true
                )

                Spacer(modifier = Modifier.height(10.dp))

                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    FilterChip(
                        selected = uiState.statusFilter == "ALL",
                        onClick = { deliveryBoyViewModel.updateStatusFilter("ALL") },
                        label = { Text(if (isKannada) "ಎಲ್ಲಾ (${assignedBookings.size})" else "All (${assignedBookings.size})") }
                    )
                    FilterChip(
                        selected = uiState.statusFilter == "ASSIGNED",
                        onClick = { deliveryBoyViewModel.updateStatusFilter("ASSIGNED") },
                        label = { Text(if (isKannada) "ನಿಯೋಜಿಸಲಾಗಿದೆ" else "Pending") }
                    )
                    FilterChip(
                        selected = uiState.statusFilter == "COMPLETED",
                        onClick = { deliveryBoyViewModel.updateStatusFilter("COMPLETED") },
                        label = { Text(if (isKannada) "ಪೂರ್ಣಗೊಂಡಿದೆ" else "Completed") }
                    )
                }
            }

            // List of Assigned Deliveries
            if (filteredBookings.isEmpty()) {
                item {
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 20.dp),
                        shape = RoundedCornerShape(12.dp),
                        color = MaterialTheme.colorScheme.surface
                    ) {
                        Text(
                            text = if (isKannada) "ಯಾವುದೇ ವಿಲೇವಾರಿ ಕಾರ್ಯಗಳು ಕಂಡುಬಂದಿಲ್ಲ" else "No delivery assignments found.",
                            modifier = Modifier.padding(24.dp),
                            textAlign = TextAlign.Center,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            } else {
                items(filteredBookings) { booking ->
                    DeliveryAssignmentCard(
                        booking = booking,
                        isKannada = isKannada,
                        onCompleteClick = { activeDeliveryForCompletion = booking },
                        onPaymentClick = { activeDeliveryForPayment = booking }
                    )
                }
            }
        }
    }

    // Complete Delivery Dialog
    activeDeliveryForCompletion?.let { booking ->
        var deliveryNotes by remember { mutableStateOf("") }
        var status by remember { mutableStateOf("DELIVERED") }

        AlertDialog(
            onDismissRequest = { activeDeliveryForCompletion = null },
            title = { Text(if (isKannada) "ವಿಲೇವಾರಿ ಪೂರ್ಣಗೊಳಿಸಿ" else "Confirm Delivery") },
            text = {
                Column {
                    Text(text = "Booking Ref: ${booking.bookingId}", fontWeight = FontWeight.Bold)
                    Text(text = "Customer: ${booking.customerName}")
                    Spacer(modifier = Modifier.height(12.dp))

                    Row(verticalAlignment = Alignment.CenterVertically) {
                        RadioButton(selected = status == "DELIVERED", onClick = { status = "DELIVERED" })
                        Text(if (isKannada) "ಯಶಸ್ವಿಯಾಗಿ ತಲುಪಿಸಲಾಗಿದೆ (Delivered)" else "Delivered Successfully")
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        RadioButton(selected = status == "FAILED", onClick = { status = "FAILED" })
                        Text(if (isKannada) "ವಿಫಲವಾಗಿದೆ (Failed)" else "Delivery Failed")
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    OutlinedTextField(
                        value = deliveryNotes,
                        onValueChange = { deliveryNotes = it },
                        label = { Text(if (isKannada) "ಟಿಪ್ಪಣಿಗಳು / ವಿವರಗಳು" else "Notes / Observations") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        deliveryBoyViewModel.completeDelivery(
                            bookingId = booking.bookingId,
                            customerId = booking.customerId,
                            quantity = booking.quantity,
                            cylinderType = booking.cylinderType,
                            status = status,
                            notes = deliveryNotes.ifBlank { null }
                        )
                        activeDeliveryForCompletion = null
                    }
                ) {
                    Text(if (isKannada) "ಸಲ್ಲಿಸಿ" else "Submit")
                }
            },
            dismissButton = {
                TextButton(onClick = { activeDeliveryForCompletion = null }) {
                    Text(if (isKannada) "ರದ್ದುಮಾಡಿ" else "Cancel")
                }
            }
        )
    }

    // Record Payment Dialog
    activeDeliveryForPayment?.let { booking ->
        var paymentMethod by remember { mutableStateOf("CASH") }
        var amountCollected by remember { mutableStateOf(booking.amountDue.toInt().toString()) }
        var txnRef by remember { mutableStateOf("") }

        AlertDialog(
            onDismissRequest = { activeDeliveryForPayment = null },
            title = { Text(if (isKannada) "ಪಾವತಿ ಸಂಗ್ರಹಿಸಿ" else "Record Payment Collection") },
            text = {
                Column {
                    Text(text = "Booking Ref: ${booking.bookingId}", fontWeight = FontWeight.Bold)
                    Text(text = "Amount Due: ₹${booking.amountDue.toInt()}")
                    Spacer(modifier = Modifier.height(12.dp))

                    Text(text = if (isKannada) "ಪಾವತಿ ವಿಧಾನ" else "Payment Method:", fontWeight = FontWeight.Medium)
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        RadioButton(selected = paymentMethod == "CASH", onClick = { paymentMethod = "CASH" })
                        Text("Cash / ನಗದು")
                        Spacer(modifier = Modifier.width(16.dp))
                        RadioButton(selected = paymentMethod == "UPI", onClick = { paymentMethod = "UPI" })
                        Text("UPI")
                    }

                    Spacer(modifier = Modifier.height(10.dp))

                    OutlinedTextField(
                        value = amountCollected,
                        onValueChange = { amountCollected = it },
                        label = { Text(if (isKannada) "ಸಂಗ್ರಹಿಸಿದ ಮೊತ್ತ" else "Amount Collected (₹)") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    if (paymentMethod == "UPI") {
                        OutlinedTextField(
                            value = txnRef,
                            onValueChange = { txnRef = it },
                            label = { Text("UPI Ref / Txn ID") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true
                        )
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val amt = amountCollected.toDoubleOrNull() ?: booking.amountDue
                        deliveryBoyViewModel.recordPayment(
                            bookingId = booking.bookingId,
                            customerId = booking.customerId,
                            amountDue = booking.amountDue,
                            amountCollected = amt,
                            paymentMethod = paymentMethod,
                            transactionRef = txnRef.ifBlank { null }
                        )
                        activeDeliveryForPayment = null
                    }
                ) {
                    Text(if (isKannada) "ದಾಖಲಿಸಿ" else "Record Payment")
                }
            },
            dismissButton = {
                TextButton(onClick = { activeDeliveryForPayment = null }) {
                    Text(if (isKannada) "ರದ್ದುಮಾಡಿ" else "Cancel")
                }
            }
        )
    }
}

@Composable
fun DeliveryAssignmentCard(
    booking: Booking,
    isKannada: Boolean,
    onCompleteClick: () -> Unit,
    onPaymentClick: () -> Unit,
    onBluetoothConnectClick: () -> Unit = {}
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = booking.customerName,
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp,
                    color = MaterialTheme.colorScheme.onSurface
                )

                Surface(
                    color = if (booking.deliveryStatus == "DELIVERED") MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.secondaryContainer,
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text(
                        text = booking.deliveryStatus,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = if (booking.deliveryStatus == "DELIVERED") MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onSecondaryContainer
                    )
                }
            }

            Spacer(modifier = Modifier.height(6.dp))

            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(imageVector = Icons.Default.Phone, contentDescription = null, modifier = Modifier.size(16.dp), tint = MaterialTheme.colorScheme.primary)
                Spacer(modifier = Modifier.width(6.dp))
                Text(text = booking.customerPhone, style = MaterialTheme.typography.bodyMedium)
            }

            Spacer(modifier = Modifier.height(4.dp))

            Row(verticalAlignment = Alignment.Top) {
                Icon(imageVector = Icons.Default.LocationOn, contentDescription = null, modifier = Modifier.size(16.dp), tint = MaterialTheme.colorScheme.primary)
                Spacer(modifier = Modifier.width(6.dp))
                Text(text = booking.deliveryAddress, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }

            Spacer(modifier = Modifier.height(10.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "${booking.cylinderType} × ${booking.quantity}",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium
                )
                Text(
                    text = "Due: ₹${booking.amountDue.toInt()}",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
            }

            Spacer(modifier = Modifier.height(14.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedButton(
                    onClick = onBluetoothConnectClick,
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(10.dp)
                ) {
                    Icon(imageVector = Icons.Default.CloudSync, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(if (isKannada) "ಸಂಪರ್ಕಿಸಿ" else "Connect BT", fontSize = 12.sp)
                }

                OutlinedButton(
                    onClick = onPaymentClick,
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(10.dp)
                ) {
                    Icon(imageVector = Icons.Default.Payment, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(if (isKannada) "ಪಾವತಿ" else "Payment", fontSize = 12.sp)
                }

                Button(
                    onClick = onCompleteClick,
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                ) {
                    Icon(imageVector = Icons.Default.LocalShipping, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(if (isKannada) "ವಿಲೇವಾರಿ" else "Complete", fontSize = 12.sp)
                }
            }
        }
    }
}
