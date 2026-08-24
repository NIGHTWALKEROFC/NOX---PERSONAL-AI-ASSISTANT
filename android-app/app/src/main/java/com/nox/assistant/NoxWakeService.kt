package com.nox.assistant

import android.app.*
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.os.IBinder
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*

class NoxWakeService : Service() {

    private var recognizer: SpeechRecognizer? = null
    private var active = false
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    companion object {
        const val CHANNEL_ID = "nox_wake_channel"
        const val NOTIF_ID = 42
        const val WAKE_PHRASE = "hey nox"
        const val SLEEP_PHRASE = "nox sleep"
    }

    override fun onCreate() {
        super.onCreate()
        NoxTts.init(applicationContext)
        createChannel()
        startForeground(NOTIF_ID, buildNotification("Listening for \"hey nox\""))
        startListening()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        recognizer?.destroy()
        scope.cancel()
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

    private fun startListening() {
        recognizer?.destroy()
        recognizer = SpeechRecognizer.createSpeechRecognizer(this)
        recognizer?.setRecognitionListener(object : RecognitionListener {
            override fun onResults(results: Bundle?) {
                val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                val text = matches?.firstOrNull()?.lowercase()?.trim().orEmpty()
                handleTranscript(text)
                startListening()
            }
            override fun onError(error: Int) { startListening() }
            override fun onReadyForSpeech(params: Bundle?) {}
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
        }
        recognizer?.startListening(intent)
    }

    private fun handleTranscript(text: String) {
        if (text.isEmpty()) return

        if (!active) {
            if (text.contains(WAKE_PHRASE)) {
                active = true
                updateNotification("Active — listening for command")
                NoxTts.speak("Yes?")
            }
            return
        }

        if (text.contains(SLEEP_PHRASE)) {
            active = false
            updateNotification("Listening for \"hey nox\"")
            NoxTts.speak("Going to sleep.")
            return
        }

        updateNotification("Thinking...")
        scope.launch {
            try {
                val api = ApiClient.get(applicationContext)
                val sessionId = Prefs.getSessionId(applicationContext)
                val result = withContext(Dispatchers.IO) {
                    api.chat(ChatRequest(sessionId, text, speak = false))
                }
                NoxTts.speak(result.reply)
            } catch (e: Exception) {
                NoxTts.speak("Sorry, I could not reach the brain server.")
            }
            updateNotification("Active — listening for command")
        }
    }
}
