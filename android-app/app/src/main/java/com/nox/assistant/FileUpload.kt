package com.nox.assistant

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File

// Max upload size mirrors the 50MB limit enforced server-side in main.py.
const val MAX_UPLOAD_BYTES = 50L * 1024 * 1024

object FileUpload {
    fun uriToTempFile(context: Context, uri: Uri): File? {
        val resolver = context.contentResolver
        val name = getFileName(context, uri) ?: "upload_${System.currentTimeMillis()}"
        val tempFile = File(context.cacheDir, name)
        resolver.openInputStream(uri)?.use { input ->
            tempFile.outputStream().use { output -> input.copyTo(output) }
        } ?: return null
        return if (tempFile.length() in 1..MAX_UPLOAD_BYTES) tempFile else null
    }

    private fun getFileName(context: Context, uri: Uri): String? {
        var name: String? = null
        context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (idx >= 0 && cursor.moveToFirst()) name = cursor.getString(idx)
        }
        return name
    }

    fun buildPart(file: File, partName: String, mimeType: String): MultipartBody.Part {
        val body = file.asRequestBody(mimeType.toMediaType())
        return MultipartBody.Part.createFormData(partName, file.name, body)
    }

    fun buildNamePart(name: String?): okhttp3.RequestBody? =
        name?.toRequestBody("text/plain".toMediaType())
}
