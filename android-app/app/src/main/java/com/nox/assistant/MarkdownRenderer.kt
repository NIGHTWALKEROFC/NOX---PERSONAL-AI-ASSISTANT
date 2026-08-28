package com.nox.assistant

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp

sealed class MessageSegment
data class TextSegment(val text: String) : MessageSegment()
data class CodeSegment(val language: String, val code: String) : MessageSegment()

private val CODE_FENCE_REGEX = Regex("```([a-zA-Z0-9_+-]*)\\n([\\s\\S]*?)```")

fun parseMessageSegments(text: String): List<MessageSegment> {
    val segments = mutableListOf<MessageSegment>()
    var lastEnd = 0
    for (match in CODE_FENCE_REGEX.findAll(text)) {
        if (match.range.first > lastEnd) {
            segments.add(TextSegment(text.substring(lastEnd, match.range.first)))
        }
        val lang = match.groupValues[1].ifBlank { "text" }
        val code = match.groupValues[2].trimEnd('\n')
        segments.add(CodeSegment(lang, code))
        lastEnd = match.range.last + 1
    }
    if (lastEnd < text.length) {
        segments.add(TextSegment(text.substring(lastEnd)))
    }
    if (segments.isEmpty()) segments.add(TextSegment(text))
    return segments
}

@Composable
fun CodeBlockView(segment: CodeSegment) {
    val clipboard = LocalClipboardManager.current
    Column(
        Modifier
            .padding(vertical = 6.dp)
            .clip(RoundedCornerShape(10.dp))
            .background(NoxSurfaceVariant)
    ) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 6.dp),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(segment.language, color = NoxTextSecondary)
            TextButton(onClick = { clipboard.setText(AnnotatedString(segment.code)) }) {
                Text("Copy", color = NoxAccent)
            }
        }
        Text(
            segment.code,
            color = NoxTextPrimary,
            fontFamily = FontFamily.Monospace,
            modifier = Modifier
                .horizontalScroll(rememberScrollState())
                .padding(horizontal = 12.dp, vertical = 8.dp)
        )
    }
}

@Composable
fun RichMessageContent(text: String, textColor: Color) {
    val segments = parseMessageSegments(text)
    Column {
        segments.forEach { seg ->
            when (seg) {
                is TextSegment -> if (seg.text.isNotBlank()) Text(seg.text.trim(), color = textColor)
                is CodeSegment -> CodeBlockView(seg)
            }
        }
    }
}
