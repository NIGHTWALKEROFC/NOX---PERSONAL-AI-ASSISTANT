package com.nox.assistant

import okhttp3.ConnectionPool
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {
    private var retrofit: Retrofit? = null
    private var currentBaseUrl: String = ""

    fun get(context: android.content.Context): ApiService {
        val baseUrl = Prefs.getServerUrl(context)
        if (retrofit == null || currentBaseUrl != baseUrl) {
            currentBaseUrl = baseUrl
            val client = OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(60, TimeUnit.SECONDS)
                // Auto-reconnect support: retry once transparently on a dropped
                // connection (e.g. the Brain Server was just restarted), and keep
                // connections alive only briefly so a stale/dead socket from before
                // a restart isn't reused and mistaken for a real failure.
                .retryOnConnectionFailure(true)
                .connectionPool(ConnectionPool(5, 20, TimeUnit.SECONDS))
                .build()
            retrofit = Retrofit.Builder()
                .baseUrl(if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/")
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
        }
        return retrofit!!.create(ApiService::class.java)
    }

    /** Quick reachability check — used by the wake service and UI to distinguish
     * "server just isn't up yet" from a real error, without spamming retries. */
    suspend fun isServerReachable(context: android.content.Context): Boolean {
        return try {
            get(context).chat(ChatRequest("healthcheck", "__healthcheck__", speak = false))
            true
        } catch (e: Exception) {
            false
        }
    }
}
