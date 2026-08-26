package com.nox.assistant

import android.content.Context
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

data class StreamEvent(
    val type: String,
    val text: String? = null,
    val reply: String? = null,
    val audio_url: String? = null
)

object StreamClient {
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.SECONDS) // no timeout — streaming can take a while
        .build()
    private val gson = Gson()

    suspend fun chatStream(context: Context, message: String, onEvent: (StreamEvent) -> Unit) {
        withContext(Dispatchers.IO) {
            val baseUrl = Prefs.getServerUrl(context).trimEnd('/')
            val sessionId = Prefs.getSessionId(context)
            val bodyJson = gson.toJson(mapOf("session_id" to sessionId, "message" to message, "speak" to false))
            val request = Request.Builder()
                .url("$baseUrl/chat/stream")
                .post(bodyJson.toRequestBody("application/json".toMediaType()))
                .build()

            client.newCall(request).execute().use { response ->
                val body = response.body ?: return@use
                val source = body.source()
                while (!source.exhausted()) {
                    val line = source.readUtf8Line() ?: break
                    if (line.startsWith("data: ")) {
                        val payload = line.removePrefix("data: ")
                        try {
                            val event = gson.fromJson(payload, StreamEvent::class.java)
                            onEvent(event)
                        } catch (_: Exception) {
                            // skip malformed line
                        }
                    }
                }
            }
        }
    }
}
