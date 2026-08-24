package com.nox.assistant

import android.content.Context

object Prefs {
    private const val FILE = "nox_prefs"
    private const val KEY_SERVER_URL = "server_url"
    private const val KEY_SESSION_ID = "session_id"
    private const val KEY_VOICE_ENABLED = "voice_enabled"
    private const val KEY_GREETED = "greeted_this_session"

    fun getServerUrl(context: Context): String =
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
            .getString(KEY_SERVER_URL, "http://192.168.1.100:8420") ?: "http://192.168.1.100:8420"

    fun setServerUrl(context: Context, url: String) {
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE).edit()
            .putString(KEY_SERVER_URL, url).apply()
    }

    fun getSessionId(context: Context): String =
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
            .getString(KEY_SESSION_ID, "android-main") ?: "android-main"

    fun isVoiceEnabled(context: Context): Boolean =
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
            .getBoolean(KEY_VOICE_ENABLED, false)

    fun setVoiceEnabled(context: Context, enabled: Boolean) {
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE).edit()
            .putBoolean(KEY_VOICE_ENABLED, enabled).apply()
    }

    fun wasGreetedThisSession(context: Context): Boolean =
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE)
            .getBoolean(KEY_GREETED, false)

    fun setGreetedThisSession(context: Context, value: Boolean) {
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE).edit()
            .putBoolean(KEY_GREETED, value).apply()
    }
}
