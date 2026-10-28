package com.example.appforlpg

import android.app.Application
import com.example.appforlpg.bluetooth.BluetoothController
import com.example.appforlpg.data.local.AppDatabase
import com.example.appforlpg.data.repository.LpgRepository
import com.example.appforlpg.data.repository.LpgRepositoryImpl
import com.example.appforlpg.sync.SyncWorker

class LpgApplication : Application() {

    lateinit var database: AppDatabase
        private set

    lateinit var repository: LpgRepository
        private set

    lateinit var bluetoothController: BluetoothController
        private set

    override fun onCreate() {
        super.onCreate()
        database = AppDatabase.getDatabase(this)
        repository = LpgRepositoryImpl(database)
        bluetoothController = BluetoothController(this)

        // Schedule periodic background synchronization with WorkManager
        SyncWorker.schedulePeriodicSync(this)
    }

    override fun onTerminate() {
        super.onTerminate()
        bluetoothController.unregister()
    }
}
