package com.nox.assistant

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.Voice
import java.util.Locale

object NoxTts {
    private var tts: TextToSpeech? = null
    private var ready = false
    private val pending = mutableListOf<String>()

    fun init(context: Context) {
        if (tts != null) return
        tts = TextToSpeech(context.applicationContext) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.language = Locale.US
                selectFemaleVoice()
                ready = true
                pending.forEach { speakNow(it) }
                pending.clear()
            }
        }
    }

    private fun selectFemaleVoice() {
        val engine = tts ?: return
        val femaleVoice: Voice? = engine.voices?.firstOrNull { voice ->
            voice.locale == Locale.US &&
                !voice.isNetworkConnectionRequired &&
                voice.name.contains("female", ignoreCase = true)
        }
        if (femaleVoice != null) {
            engine.voice = femaleVoice
        }
    }

    fun speak(text: String) {
        if (!ready) {
            pending.add(text)
            return
        }
        speakNow(text)
    }

    private fun speakNow(text: String) {
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "nox_utterance")
    }
}
