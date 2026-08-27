package com.nox.assistant

import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody
import retrofit2.http.*

data class ImageUploadResult(val doc_id: String?, val warning: String?, val extracted_preview: String?)

interface ApiService {
    @POST("chat")
    suspend fun chat(@Body req: ChatRequest): ChatResponse

    @GET("audio/{filename}")
    suspend fun getAudio(@Path("filename") filename: String): ResponseBody

    @POST("knowledge/text")
    suspend fun addTextKnowledge(@Body req: TextKnowledgeRequest): IdResponse

    @Multipart
    @POST("knowledge/pdf")
    suspend fun addPdfKnowledge(@Part file: MultipartBody.Part, @Part("name") name: RequestBody?): IdResponse

    @Multipart
    @POST("knowledge/image")
    suspend fun addImageKnowledge(@Part file: MultipartBody.Part, @Part("name") name: RequestBody?): ImageUploadResult

    @POST("knowledge/url")
    suspend fun addUrlKnowledge(@Body req: UrlKnowledgeRequest): IdResponse

    @FormUrlEncoded
    @POST("knowledge/voice")
    suspend fun addVoiceKnowledge(@Field("transcript") transcript: String, @Field("name") name: String): IdResponse

    @GET("knowledge/list")
    suspend fun listKnowledge(): List<KnowledgeItem>

    @DELETE("knowledge/{docId}")
    suspend fun deleteKnowledge(@Path("docId") docId: String): DeleteResult

    @POST("memory")
    suspend fun addMemory(@Body req: MemoryRequest): MemoryIdResponse

    @GET("memory")
    suspend fun listMemory(): List<MemoryItem>

    @DELETE("memory/{memoryId}")
    suspend fun deleteMemory(@Path("memoryId") memoryId: Int): retrofit2.Response<Unit>

    @GET("settings/personality")
    suspend fun getPersonality(): PersonalityText

    @POST("settings/personality")
    suspend fun setPersonality(@Body req: PersonalityText): retrofit2.Response<Unit>

    @GET("settings/code-execution")
    suspend fun getCodeExecution(): CodeExecutionState

    @POST("settings/code-execution")
    suspend fun setCodeExecution(@Body req: CodeExecutionState): CodeExecutionState

    @POST("chats")
    suspend fun createChat(@Body req: CreateChatRequest): CreateChatResponse

    @GET("chats")
    suspend fun listChats(): List<ChatSummary>

    @DELETE("chats/{chatId}")
    suspend fun deleteChat(@Path("chatId") chatId: String): retrofit2.Response<Unit>

    @POST("chats/{chatId}/save-to-memory")
    suspend fun saveChatToMemory(@Path("chatId") chatId: String): SaveToMemoryResponse
}
