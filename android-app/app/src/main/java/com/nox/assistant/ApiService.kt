package com.nox.assistant

import okhttp3.MultipartBody
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.*

interface ApiService {
    @POST("chat")
    suspend fun chat(@Body req: ChatRequest): ChatResponse

    @GET("audio/{filename}")
    suspend fun getAudio(@Path("filename") filename: String): ResponseBody

    @POST("knowledge/text")
    suspend fun addTextKnowledge(@Body req: TextKnowledgeRequest): IdResponse

    @Multipart
    @POST("knowledge/pdf")
    suspend fun addPdfKnowledge(@Part file: MultipartBody.Part): IdResponse

    @POST("knowledge/url")
    suspend fun addUrlKnowledge(@Body req: UrlKnowledgeRequest): IdResponse

    @FormUrlEncoded
    @POST("knowledge/voice")
    suspend fun addVoiceKnowledge(@Field("transcript") transcript: String, @Field("name") name: String): IdResponse

    @GET("knowledge/list")
    suspend fun listKnowledge(): List<KnowledgeItem>

    @DELETE("knowledge/{docId}")
    suspend fun deleteKnowledge(@Path("docId") docId: String): Response<Unit>

    @POST("memory")
    suspend fun addMemory(@Body req: MemoryRequest): MemoryIdResponse

    @GET("memory")
    suspend fun listMemory(): List<MemoryItem>

    @DELETE("memory/{memoryId}")
    suspend fun deleteMemory(@Path("memoryId") memoryId: Int): Response<Unit>
}
