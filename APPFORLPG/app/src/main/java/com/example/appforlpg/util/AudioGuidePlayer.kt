package com.example.appforlpg.util

import android.content.Context
import android.content.SharedPreferences
import android.media.MediaPlayer
import android.util.Log

class AudioGuidePlayer(private val context: Context) {

    private var mediaPlayer: MediaPlayer? = null
    private val prefs: SharedPreferences = context.getSharedPreferences("audio_guide_prefs", Context.MODE_PRIVATE)

    var isMuted: Boolean
        get() = prefs.getBoolean("is_muted", false)
        set(value) = prefs.edit().putBoolean("is_muted", value).apply()

    fun play(audioId: String, isKannada: Boolean, onEnded: (() -> Unit)? = null) {
        stop()

        if (isMuted) {
            onEnded?.invoke()
            return
        }

        val langCode = if (isKannada) "kn" else "en"
        val assetPath = "audio/$langCode/$audioId.mp3"

        try {
            val afd = context.assets.openFd(assetPath)
            mediaPlayer = MediaPlayer().apply {
                setDataSource(afd.fileDescriptor, afd.startOffset, afd.length)
                afd.close()
                prepare()
                setOnCompletionListener {
                    stop()
                    onEnded?.invoke()
                }
                setOnErrorListener { _, what, extra ->
                    Log.w("AudioGuidePlayer", "Playback error for $assetPath: what=$what extra=$extra")
                    stop()
                    onEnded?.invoke()
                    true
                }
                start()
            }
        } catch (e: Exception) {
            Log.w("AudioGuidePlayer", "Audio file missing or failed to play ($assetPath): ${e.message}")
            onEnded?.invoke()
        }
    }

    fun stop() {
        try {
            mediaPlayer?.let {
                if (it.isPlaying) {
                    it.stop()
                }
                it.release()
            }
        } catch (e: Exception) {
            Log.w("AudioGuidePlayer", "Error stopping player: ${e.message}")
        } finally {
            mediaPlayer = null
        }
    }

    fun toggleMute(): Boolean {
        isMuted = !isMuted
        if (isMuted) {
            stop()
        }
        return isMuted
    }

    fun release() {
        stop()
    }
}
