package com.neuroarousal.api

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*
import java.util.concurrent.TimeUnit

interface NeuroArousalApi {

    @GET("scenarios")
    suspend fun listScenarios(): List<String>

    @GET("scenarios/{name}")
    suspend fun getScenarioInfo(@Path("name") name: String): ScenarioInfoOut

    @POST("run/scenario/{name}")
    suspend fun runScenario(
        @Path("name") name: String,
        @Query("adapter") adapter: String = "default"
    ): SimulationOut

    @POST("run/custom")
    suspend fun runCustom(@Body request: CustomRunRequest): SimulationOut

    @GET("state/{step}")
    suspend fun getState(@Path("step") step: Int): StateSnapshot

    @GET("state")
    suspend fun getCurrentState(): StateSnapshot

    @GET("alignment")
    suspend fun getAlignment(): AlignmentOut

    @GET("arc")
    suspend fun getArc(): NarrativeArcOut

    @GET("adapters")
    suspend fun listAdapters(): List<AdapterOut>

    @POST("adapters/{name}")
    suspend fun setAdapter(@Path("name") name: String): Map<String, String>

    @GET("nullclines")
    suspend fun getNullclines(
        @Query("soma_a") somaA: Double = 0.25,
        @Query("soma_b") somaB: Double = 0.5,
        @Query("psyche_a") psycheA: Double = 0.20,
        @Query("psyche_b") psycheB: Double = 0.45
    ): NullclineOut

    @GET("character/appearance")
    suspend fun getCharacterAppearance(@Query("step") step: Int? = null): CharacterAppearanceOut

    @GET("character/image")
    suspend fun getCharacterImage(@Query("step") step: Int? = null): okhttp3.ResponseBody
}

object ApiClientFactory {
    private var currentBaseUrl = "http://10.0.2.2:7860/" // Android emulator -> host

    fun create(baseUrl: String? = null): NeuroArousalApi {
        val url = baseUrl ?: currentBaseUrl
        currentBaseUrl = if (url.endsWith("/")) url else "$url/"

        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }

        val client = OkHttpClient.Builder()
            .addInterceptor(logging)
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()

        return Retrofit.Builder()
            .baseUrl(currentBaseUrl)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(NeuroArousalApi::class.java)
    }

    fun getBaseUrl(): String = currentBaseUrl
}
