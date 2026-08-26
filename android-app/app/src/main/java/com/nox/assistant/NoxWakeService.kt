package com.nox.assistant

import android.Manifest
import android.app.*
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import kotlinx.coroutines.*

class NoxWakeService : Service() {

    private var recognizer: SpeechRecognizer? = null
    private var active = false
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private val mainHandler = Handler(Looper.getMainLooper())
    private var consecutiveErrors = 0

    companion object {
        const val CHANNEL_ID = "nox_wake_channel"
        const val NOTIF_ID = 42
        const val WAKE_PHRASE = "hey nox"
        const val SLEEP_PHRASE = "nox sleep"
        const val BASE_RESTART_DELAY_MS = 800L
        const val MAX_RESTART_DELAY_MS = 6000L
    }

    override fun onCreate() {
        super.onCreate()

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            createChannel()
            startForeground(NOTIF_ID, buildNotification("Microphone permission not granted — open the app and allow it"))
            stopSelf()
            return
        }

        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            createChannel()
            startForeground(NOTIF_ID, buildNotification("No speech recognizer available on this device"))
            stopSelf()
            return
        }

        NoxTts.init(applicationContext)
        createChannel()
        startForeground(NOTIF_ID, buildNotification("Starting up..."))
        startListening()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        recognizer?.destroy()
        scope.cancel()
        mainHandler.removeCallbacksAndMessages(null)
        super.onDestroy()
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(CHANNEL_ID, "NOX Voice", NotificationManager.IMPORTANCE_LOW)
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    private fun buildNotification(text: String): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("NOX")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setOngoing(true)
            .build()
    }

    private fun updateNotification(text: String) {
        val nm = getSystemService(NotificationManager::class.java)
        nm.notify(NOTIF_ID, buildNotification(text))
    }

    private fun errorName(code: Int): String = when (code) {
        SpeechRecognizer.ERROR_AUDIO -> "audio error"
        SpeechRecognizer.ERROR_CLIENT -> "client error"
        SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "missing permission"
        SpeechRecognizer.ERROR_NETWORK -> "network error (needs internet)"
        SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "network timeout"
        SpeechRecognizer.ERROR_NO_MATCH -> "no match"
        SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "recognizer busy"
        SpeechRecognizer.ERROR_SERVER -> "server error"
        SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "no speech detected"
        11 -> "server disconnected (recovering)"
        else -> "error $code"
    }

    private fun scheduleRestart(baseDelay: Long = BASE_RESTART_DELAY_MS) {
        // Exponential backoff on repeated errors — prevents the restart-loop
        // that causes ERROR_SERVER_DISCONNECTED (error 11) in the first place.
        val delay = (baseDelay * (1 shl consecutiveErrors.coerceAtMost(3))).coerceAtMost(MAX_RESTART_DELAY_MS)
        mainHandler.postDelayed({ startListening() }, delay)
    }

    private fun startListening() {
        recognizer?.destroy()
        recognizer = SpeechRecognizer.createSpeechRecognizer(this)
        recognizer?.setRecognitionListener(object : RecognitionListener {
            override fun onResults(results: Bundle?) {
                consecutiveErrors = 0
                val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                val text = matches?.firstOrNull()?.lowercase()?.trim().orEmpty()
                handleTranscript(text)
                scheduleRestart(300)
            }
            override fun onError(error: Int) {
                consecutiveErrors++
                val label = errorName(error)
                if (!active) {
                    updateNotification("Listening for \"hey nox\" ($label)")
                } else {
                    updateNotification("Active — listening for command ($label)")
                }
                scheduleRestart()
            }
            override fun onReadyForSpeech(params: Bundle?) {
                updateNotification(if (active) "Active — listening for command" else "Listening for \"hey nox\"")
            }
            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(rmsdB: Float) {}
            override fun onBufferReceived(buffer: ByteArray?) {}
            override fun onEndOfSpeech() {}
            override fun onPartialResults(partialResults: Bundle?) {}
            override fun onEvent(eventType: Int, params: Bundle?) {}
        })

        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false)
            putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, packageName)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1200)
            // Not forcing a single language — lets Malayalam and English both work,
            // matching the auto-detect approach used on the Windows side.
        }
        try {
            recognizer?.startListening(intent)
        } catch (e: Exception) {
            consecutiveErrors++
            updateNotification("Failed to start listening: ${e.message}")
            scheduleRestart(1500)
        }
    }

    private fun handleTranscript(text: String) {
        if (text.isEmpty()) return

        if (!active) {
            if (text.contains(WAKE_PHRASE) || text.contains("nox") || text.contains("knox") || text.contains("notes")) {
                active = true
                updateNotification("Active — listening for command")
                NoxTts.speak("Yes?")
            }
            return
        }

        if (text.contains(SLEEP_PHRASE) || (text.contains("sleep") && (text.contains("nox") || text.contains("knox")))) {
            active = false
            updateNotification("Listening for \"hey nox\"")
            NoxTts.speak("Going to sleep.")
            return
        }

        updateNotification("Thinking...")
        scope.launch {
            var fullReply = ""
            try {
                StreamClient.chatStream(applicationContext, text) { event ->
                    when (event.type) {
                        "status" -> updateNotification(event.text ?: "...")
                        "done" -> fullReply = event.reply ?: fullReply
                        else -> {}
                    }
                }
                if (fullReply.isNotBlank()) NoxTts.speak(fullReply)
            } catch (e: Exception) {
                NoxTts.speak("Sorry, I could not reach the brain server.")
            }
            updateNotification("Active — listening for command")
        }
    }
}
