package com.nox.assistant

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import com.k2fsa.sherpa.onnx.OfflineTts
import com.k2fsa.sherpa.onnx.OfflineTtsConfig
import com.k2fsa.sherpa.onnx.OfflineTtsModelConfig
import com.k2fsa.sherpa.onnx.OfflineTtsVitsModelConfig

// Place these into app/src/main/assets/nox-voice/ (not via GitHub, added locally):
//   en_US-amy-medium.onnx
//   tokens.txt
//   espeak-ng-data/   (whole folder)
// All three come from https://huggingface.co/csukuangfj/vits-piper-en_US-amy-medium
object NoxTts {
    private var tts: OfflineTts? = null

    fun init(context: Context) {
        if (tts != null) return
        val vitsConfig = OfflineTtsVitsModelConfig(
            model = "nox-voice/en_US-amy-medium.onnx",
            lexicon = "",
            tokens = "nox-voice/tokens.txt",
            dataDir = "nox-voice/espeak-ng-data",
        )
        val modelConfig = OfflineTtsModelConfig(
            vits = vitsConfig,
            numThreads = 2,
            debug = false,
            provider = "cpu",
        )
        val config = OfflineTtsConfig(model = modelConfig, maxNumSentences = 1)
        tts = OfflineTts(assetManager = context.assets, config = config)
    }

    fun speak(text: String) {
        val engine = tts ?: return
        val audio = engine.generate(text = text, sid = 0, speed = 1.0f)
        playPcm(audio.samples, audio.sampleRate)
    }

    private fun playPcm(samples: FloatArray, sampleRate: Int) {
        val bufferSize = AudioTrack.getMinBufferSize(
            sampleRate, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_FLOAT
        )
        val track = AudioTrack(
            AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ASSISTANT)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                .build(),
            AudioFormat.Builder()
                .setSampleRate(sampleRate)
                .setEncoding(AudioFormat.ENCODING_PCM_FLOAT)
                .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                .build(),
            maxOf(bufferSize, samples.size * 4),
            AudioTrack.MODE_STATIC,
            AudioTrack.SESSION_ID_GENERATE
        )
        track.write(samples, 0, samples.size, AudioTrack.WRITE_BLOCKING)
        track.play()
    }
}
