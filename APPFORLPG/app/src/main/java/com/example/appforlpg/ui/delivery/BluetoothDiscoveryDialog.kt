package com.example.appforlpg.ui.delivery

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bluetooth
import androidx.compose.material.icons.filled.BluetoothConnected
import androidx.compose.material.icons.filled.BluetoothSearching
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.appforlpg.bluetooth.BluetoothDeviceDomain
import com.example.appforlpg.domain.model.Booking

sealed class DeliveryBleState {
    object Idle : DeliveryBleState()
    object Scanning : DeliveryBleState()
    data class DeviceFound(val device: BluetoothDeviceDomain) : DeliveryBleState()
    data class Connecting(val deviceName: String) : DeliveryBleState()
    data class VerifyingBooking(val deviceName: String) : DeliveryBleState()
    data class BookingVerified(val deviceName: String, val transactionRef: String) : DeliveryBleState()
    data class HandshakeCompleted(val confirmationRef: String) : DeliveryBleState()
    data class Error(val message: String) : DeliveryBleState()
}

@Composable
fun BluetoothDiscoveryDialog(
    booking: Booking,
    isKannada: Boolean,
    pairedDevices: List<BluetoothDeviceDomain>,
    scannedDevices: List<BluetoothDeviceDomain>,
    onStartScan: () -> Unit,
    onConnectDevice: (BluetoothDeviceDomain, (Boolean, String) -> Unit) -> Unit,
    onDismiss: () -> Unit
) {
    var bleState by remember { mutableStateOf<DeliveryBleState>(DeliveryBleState.Scanning) }
    var connectingAddress by remember { mutableStateOf<String?>(null) }

    val allDevices = (pairedDevices + scannedDevices).distinctBy { it.address }

    LaunchedEffect(Unit) {
        onStartScan()
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.BluetoothSearching,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(24.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (isKannada) "ಸಮೀಪದ ಗ್ರಾಹಕರ ಸಾಧನಗಳು" else "Nearby Customer Devices",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                }

                IconButton(onClick = onDismiss) {
                    Icon(Icons.Default.Close, contentDescription = "Close")
                }
            }
        },
        text = {
            Column(modifier = Modifier.fillMaxWidth()) {
                // Booking Info Header
                Surface(
                    color = MaterialTheme.colorScheme.primaryContainer,
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp)
                ) {
                    Column(modifier = Modifier.padding(10.dp)) {
                        Text(
                            text = "${booking.customerName} (${booking.bookingId})",
                            fontWeight = FontWeight.Bold,
                            style = MaterialTheme.typography.bodyMedium
                        )
                        Text(
                            text = "${booking.cylinderType} × ${booking.quantity} | Due: ₹${booking.amountDue.toInt()}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.8f)
                        )
                    }
                }

                // Live BLE Status Banner
                val statusText = when (val state = bleState) {
                    is DeliveryBleState.Scanning -> if (isKannada) "ಸಮೀಪದ ಸಾಧನಗಳನ್ನು ಹುಡುಕಲಾಗುತ್ತಿದೆ…" else "Searching for nearby devices…"
                    is DeliveryBleState.Connecting -> if (isKannada) "${state.deviceName} ಗೆ ಸಂಪರ್ಕಿಸಲಾಗುತ್ತಿದೆ…" else "Connecting to ${state.deviceName}…"
                    is DeliveryBleState.VerifyingBooking -> if (isKannada) "ಬುಕಿಂಗ್ ಸುರಕ್ಷಿತವಾಗಿ ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ…" else "Connected — verifying booking securely with server…"
                    is DeliveryBleState.BookingVerified -> if (isKannada) "ಬುಕಿಂಗ್ ದೃಢೀಕರಿಸಲಾಗಿದೆ! ಗ್ರಾಹಕರ ಅನುಮೋದನೆಗೆ ಕಾಯಲಾಗುತ್ತಿದೆ…" else "Booking verified — ready for customer handover confirmation"
                    is DeliveryBleState.HandshakeCompleted -> if (isKannada) "ವಿಲೇವಾರಿ ಪೂರ್ಣಗೊಂಡಿದೆ: ${state.confirmationRef}" else "Handshake Completed: ${state.confirmationRef}"
                    is DeliveryBleState.Error -> state.message
                    else -> if (isKannada) "ಸಾಧನ ಆಯ್ಕೆಮಾಡಿ" else "Select a customer device to connect"
                }

                Surface(
                    color = when (bleState) {
                        is DeliveryBleState.HandshakeCompleted -> MaterialTheme.colorScheme.primaryContainer
                        is DeliveryBleState.Error -> MaterialTheme.colorScheme.errorContainer
                        else -> MaterialTheme.colorScheme.secondaryContainer
                    },
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(10.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        if (bleState is DeliveryBleState.Connecting || bleState is DeliveryBleState.VerifyingBooking) {
                            CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                            Spacer(modifier = Modifier.width(8.dp))
                        } else if (bleState is DeliveryBleState.HandshakeCompleted) {
                            Icon(Icons.Default.CheckCircle, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                        } else if (bleState is DeliveryBleState.Error) {
                            Icon(Icons.Default.Warning, contentDescription = null, tint = MaterialTheme.colorScheme.error, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(8.dp))
                        }

                        Text(
                            text = statusText,
                            style = MaterialTheme.typography.bodySmall,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = if (isKannada) "ಕಂಡುಬಂದ ಸಾಧನಗಳು (${allDevices.size}):" else "Discovered Sessions (${allDevices.size}):",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.Bold
                    )

                    TextButton(onClick = {
                        bleState = DeliveryBleState.Scanning
                        onStartScan()
                    }) {
                        Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(if (isKannada) "ಮತ್ತೆ ಹುಡುಕಿ" else "Scan Again", fontSize = 12.sp)
                    }
                }

                Spacer(modifier = Modifier.height(6.dp))

                if (allDevices.isEmpty()) {
                    Surface(
                        color = MaterialTheme.colorScheme.surfaceVariant,
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.fillMaxWidth().padding(vertical = 12.dp)
                    ) {
                        Text(
                            text = if (isKannada) "ಯಾವುದೇ ಸಮೀಪದ ಸಾಧನಗಳು ಕಂಡುಬಂದಿಲ್ಲ. ಬ್ಲೂಟೂತ್ ಆನ್ ಆಗಿದೆಯೇ ಪರಿಶೀಲಿಸಿ." else "No nearby customer devices found. Ensure Bluetooth is ON.",
                            style = MaterialTheme.typography.bodySmall,
                            modifier = Modifier.padding(12.dp)
                        )
                    }
                } else {
                    LazyColumn(
                        modifier = Modifier.heightIn(max = 240.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items(allDevices) { dev ->
                            val isThisConnecting = connectingAddress == dev.address
                            val isConnectingAny = connectingAddress != null

                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(10.dp),
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                            ) {
                                Row(
                                    modifier = Modifier.fillMaxWidth().padding(12.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(
                                            text = "Customer Session ${dev.name.takeLast(6)}",
                                            fontWeight = FontWeight.Bold,
                                            style = MaterialTheme.typography.bodyMedium
                                        )
                                        Text(
                                            text = if (isThisConnecting) "Connecting..." else "Device found — not connected",
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }

                                    Button(
                                        enabled = !isConnectingAny,
                                        onClick = {
                                            connectingAddress = dev.address
                                            bleState = DeliveryBleState.Connecting(dev.name)

                                            onConnectDevice(dev) { success, resultMsg ->
                                                connectingAddress = null
                                                if (success) {
                                                    bleState = DeliveryBleState.HandshakeCompleted(resultMsg)
                                                } else {
                                                    bleState = DeliveryBleState.Error(resultMsg)
                                                }
                                            }
                                        },
                                        shape = RoundedCornerShape(8.dp),
                                        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                                    ) {
                                        if (isThisConnecting) {
                                            CircularProgressIndicator(
                                                modifier = Modifier.size(14.dp),
                                                strokeWidth = 2.dp,
                                                color = MaterialTheme.colorScheme.onPrimary
                                            )
                                            Spacer(modifier = Modifier.width(6.dp))
                                            Text(if (isKannada) "ಸಂಪರ್ಕಿಸಲಾಗುತ್ತಿದೆ…" else "Connecting…", fontSize = 12.sp)
                                        } else {
                                            Icon(Icons.Default.BluetoothConnected, contentDescription = null, modifier = Modifier.size(14.dp))
                                            Spacer(modifier = Modifier.width(4.dp))
                                            Text(if (isKannada) "ಸಂಪರ್ಕಿಸಿ" else "Connect", fontSize = 12.sp)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        confirmButton = {
            if (bleState is DeliveryBleState.Error) {
                Button(onClick = {
                    bleState = DeliveryBleState.Scanning
                    onStartScan()
                }) {
                    Text(if (isKannada) "ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ" else "Retry")
                }
            } else {
                TextButton(onClick = onDismiss) {
                    Text(if (isKannada) "ರದ್ದುಮಾಡಿ" else "Cancel")
                }
            }
        }
    )
}
