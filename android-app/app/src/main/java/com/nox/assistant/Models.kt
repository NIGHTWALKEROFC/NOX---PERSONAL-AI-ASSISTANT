package com.nox.assistant

data class ChatRequest(val session_id: String, val message: String, val speak: Boolean = false)
data class ChatResponse(val reply: String, val audio_url: String?)
data class TextKnowledgeRequest(val text: String, val name: String = "manual text")
data class UrlKnowledgeRequest(val url: String)
data class MemoryRequest(val fact: String)
data class KnowledgeItem(val id: String, val source_type: String, val source_name: String, val added_at: String)
data class MemoryItem(val id: Int, val fact: String, val created_at: String)
data class IdResponse(val doc_id: String?)
data class MemoryIdResponse(val id: Int)
