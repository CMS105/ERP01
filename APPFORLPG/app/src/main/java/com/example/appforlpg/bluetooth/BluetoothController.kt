package com.example.appforlpg.bluetooth

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothServerSocket
import android.bluetooth.BluetoothSocket
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import com.example.appforlpg.domain.model.BluetoothPayload
import com.example.appforlpg.domain.model.BluetoothTransferRecord
import com.google.gson.Gson
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.InputStream
import java.io.OutputStream
import java.util.UUID

sealed class BluetoothConnectionState {
    object Idle : BluetoothConnectionState()
    data class Discovering(val devices: List<BluetoothDeviceDomain>) : BluetoothConnectionState()
    data class Connecting(val deviceName: String) : BluetoothConnectionState()
    data class Transferring(val progressText: String) : BluetoothConnectionState()
    data class Success(val message: String, val payload: BluetoothPayload? = null) : BluetoothConnectionState()
    data class Error(val errorMessage: String) : BluetoothConnectionState()
}

data class BluetoothDeviceDomain(
    val name: String,
    val address: String
)

class BluetoothController(private val context: Context) {

    private val bluetoothManager: BluetoothManager? =
        context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
    private val bluetoothAdapter: BluetoothAdapter? = bluetoothManager?.adapter

    private val APP_UUID: UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB") // Standard SPP UUID
    private val APP_NAME = "LPG_ERP_BLUETOOTH"

    private val _connectionState = MutableStateFlow<BluetoothConnectionState>(BluetoothConnectionState.Idle)
    val connectionState: StateFlow<BluetoothConnectionState> = _connectionState.asStateFlow()

    private val _scannedDevices = MutableStateFlow<List<BluetoothDeviceDomain>>(emptyList())
    val scannedDevices: StateFlow<List<BluetoothDeviceDomain>> = _scannedDevices.asStateFlow()

    private val _pairedDevices = MutableStateFlow<List<BluetoothDeviceDomain>>(emptyList())
    val pairedDevices: StateFlow<List<BluetoothDeviceDomain>> = _pairedDevices.asStateFlow()

    private var serverSocket: BluetoothServerSocket? = null
    private var clientSocket: BluetoothSocket? = null
    private val gson = Gson()
    private val scope = CoroutineScope(Dispatchers.IO)

    private val receiver = object : BroadcastReceiver() {
        @SuppressLint("MissingPermission")
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.action) {
                BluetoothDevice.ACTION_FOUND -> {
                    val device: BluetoothDevice? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                        intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE, BluetoothDevice::class.java)
                    } else {
                        @Suppress("DEPRECATION")
                        intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE)
                    }
                    device?.let { dev ->
                        val name = dev.name ?: "Unknown Device"
                        val address = dev.address ?: "00:00:00:00:00:00"
                        val newDevice = BluetoothDeviceDomain(name, address)
                        val current = _scannedDevices.value.toMutableList()
                        if (current.none { it.address == address }) {
                            current.add(newDevice)
                            _scannedDevices.value = current
                            if (_connectionState.value is BluetoothConnectionState.Discovering) {
                                _connectionState.value = BluetoothConnectionState.Discovering(current)
                            }
                        }
                    }
                }
            }
        }
    }

    init {
        val filter = IntentFilter(BluetoothDevice.ACTION_FOUND)
        try {
            context.registerReceiver(receiver, filter)
        } catch (_: Exception) {}
        fetchPairedDevices()
    }

    fun isBluetoothSupported(): Boolean = bluetoothAdapter != null
    fun isBluetoothEnabled(): Boolean = bluetoothAdapter?.isEnabled == true

    @SuppressLint("MissingPermission")
    fun fetchPairedDevices() {
        if (!isBluetoothEnabled()) return
        try {
            val bonded = bluetoothAdapter?.bondedDevices?.map {
                BluetoothDeviceDomain(it.name ?: "Paired Device", it.address)
            } ?: emptyList()
            _pairedDevices.value = bonded
        } catch (e: SecurityException) {
            _connectionState.value = BluetoothConnectionState.Error("Bluetooth permission missing")
        }
    }

    @SuppressLint("MissingPermission")
    fun startDiscovery() {
        if (!isBluetoothEnabled()) {
            _connectionState.value = BluetoothConnectionState.Error("Bluetooth is disabled. Please turn on Bluetooth.")
            return
        }
        try {
            _scannedDevices.value = emptyList()
            _connectionState.value = BluetoothConnectionState.Discovering(emptyList())
            fetchPairedDevices()
            if (bluetoothAdapter?.isDiscovering == true) {
                bluetoothAdapter.cancelDiscovery()
            }
            bluetoothAdapter?.startDiscovery()
        } catch (e: SecurityException) {
            _connectionState.value = BluetoothConnectionState.Error("Bluetooth SCAN permission required.")
        }
    }

    @SuppressLint("MissingPermission")
    fun startListeningForIncomingPayload(
        onRequestReceived: (BluetoothPayload, onRespond: (Boolean, String) -> Unit) -> Unit
    ) {
        if (!isBluetoothEnabled()) return
        scope.launch {
            try {
                _connectionState.value = BluetoothConnectionState.Connecting("Listening for Delivery Partner Bluetooth Request...")
                serverSocket = bluetoothAdapter?.listenUsingRfcommWithServiceRecord(APP_NAME, APP_UUID)
                val socket = serverSocket?.accept()
                serverSocket?.close()
                serverSocket = null

                if (socket != null) {
                    clientSocket = socket
                    _connectionState.value = BluetoothConnectionState.Transferring("Receiving delivery manifest...")
                    val inputStream: InputStream = socket.inputStream
                    val buffer = ByteArray(2048)
                    val bytes = inputStream.read(buffer)
                    if (bytes > 0) {
                        val json = String(buffer, 0, bytes)
                        val manifestPayload = gson.fromJson(json, BluetoothPayload::class.java)
                        _connectionState.value = BluetoothConnectionState.Connecting("Awaiting Customer Approval Decision...")
                        
                        onRequestReceived(manifestPayload) { approved, confirmationRef ->
                            scope.launch {
                                try {
                                    val responsePayload = manifestPayload.copy(
                                        transferType = if (approved) "CUSTOMER_CONFIRMATION" else "CUSTOMER_REJECTED",
                                        signature = confirmationRef
                                    )
                                    val outputStream: OutputStream = socket.outputStream
                                    outputStream.write(gson.toJson(responsePayload).toByteArray())
                                    outputStream.flush()
                                    _connectionState.value = BluetoothConnectionState.Success(
                                        message = if (approved) "Handshake Approved: $confirmationRef" else "Handshake Rejected",
                                        payload = responsePayload
                                    )
                                } catch (e: Exception) {
                                    _connectionState.value = BluetoothConnectionState.Error("Failed to send approval: ${e.message}")
                                } finally {
                                    closeSockets()
                                }
                            }
                        }
                    } else {
                        _connectionState.value = BluetoothConnectionState.Error("Empty manifest received.")
                        closeSockets()
                    }
                }
            } catch (e: Exception) {
                _connectionState.value = BluetoothConnectionState.Error("Bluetooth Server Error: ${e.message}")
                closeSockets()
            }
        }
    }

    @SuppressLint("MissingPermission")
    fun sendHandshakeAndAwaitConfirmation(
        deviceAddress: String,
        payload: BluetoothPayload,
        onComplete: (Boolean, String, BluetoothPayload?) -> Unit
    ) {
        if (!isBluetoothEnabled()) {
            _connectionState.value = BluetoothConnectionState.Error("Bluetooth is disabled")
            onComplete(false, "Bluetooth is disabled", null)
            return
        }

        scope.launch {
            try {
                if (bluetoothAdapter?.isDiscovering == true) {
                    bluetoothAdapter.cancelDiscovery()
                }
                val device = bluetoothAdapter?.getRemoteDevice(deviceAddress)
                if (device == null) {
                    _connectionState.value = BluetoothConnectionState.Error("Target Bluetooth device not found.")
                    onComplete(false, "Target device not found", null)
                    return@launch
                }

                _connectionState.value = BluetoothConnectionState.Connecting("Connecting to ${device.name ?: deviceAddress}...")
                val socket = device.createRfcommSocketToServiceRecord(APP_UUID)
                clientSocket = socket
                socket.connect()

                _connectionState.value = BluetoothConnectionState.Transferring("Sending delivery manifest over Bluetooth...")
                val outputStream: OutputStream = socket.outputStream
                val json = gson.toJson(payload)
                outputStream.write(json.toByteArray())
                outputStream.flush()

                _connectionState.value = BluetoothConnectionState.Connecting("Waiting for Customer Approval...")
                val inputStream: InputStream = socket.inputStream
                val buffer = ByteArray(2048)
                val bytes = inputStream.read(buffer)

                if (bytes > 0) {
                    val respJson = String(buffer, 0, bytes)
                    val confirmationPayload = gson.fromJson(respJson, BluetoothPayload::class.java)
                    _connectionState.value = BluetoothConnectionState.Success(
                        message = "Customer approved transaction: ${confirmationPayload.signature}",
                        payload = confirmationPayload
                    )
                    onComplete(true, "Customer Approved: ${confirmationPayload.signature}", confirmationPayload)
                } else {
                    _connectionState.value = BluetoothConnectionState.Error("Transfer interrupted: Customer disconnected.")
                    onComplete(false, "Transfer interrupted", null)
                }
            } catch (e: Exception) {
                _connectionState.value = BluetoothConnectionState.Error("Bluetooth Handshake Failed: ${e.message}")
                onComplete(false, e.message ?: "Handshake failed", null)
            } finally {
                closeSockets()
            }
        }
    }

    fun resetState() {
        _connectionState.value = BluetoothConnectionState.Idle
    }

    private fun closeSockets() {
        try {
            clientSocket?.close()
            clientSocket = null
            serverSocket?.close()
            serverSocket = null
        } catch (_: Exception) {}
    }

    fun unregister() {
        try {
            context.unregisterReceiver(receiver)
        } catch (_: Exception) {}
        closeSockets()
    }
}
