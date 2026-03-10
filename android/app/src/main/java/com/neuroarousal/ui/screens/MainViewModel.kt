package com.neuroarousal.ui.screens

import androidx.compose.runtime.*
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.neuroarousal.api.*
import kotlinx.coroutines.launch

class MainViewModel : ViewModel() {

    var serverUrl by mutableStateOf("http://10.0.2.2:7860")
        private set

    var api: NeuroArousalApi = ApiClientFactory.create(serverUrl)
        private set

    var isLoading by mutableStateOf(false)
        private set

    var errorMessage by mutableStateOf<String?>(null)
        private set

    // Scenarios
    var scenarios by mutableStateOf<List<String>>(emptyList())
        private set

    var adapters by mutableStateOf<List<AdapterOut>>(emptyList())
        private set

    // Simulation result
    var result by mutableStateOf<SimulationOut?>(null)
        private set

    var scenarioInfo by mutableStateOf<ScenarioInfoOut?>(null)
        private set

    // State explorer
    var stateSnapshot by mutableStateOf<StateSnapshot?>(null)
        private set

    init {
        loadInitial()
    }

    fun setServerUrl(url: String) {
        serverUrl = url.trimEnd('/')
        api = ApiClientFactory.create(serverUrl)
        loadInitial()
    }

    fun testConnection(url: String, onResult: (String) -> Unit) {
        viewModelScope.launch {
            try {
                val testApi = ApiClientFactory.create(url)
                testApi.listScenarios()
                onResult("Connected OK")
            } catch (e: Exception) {
                onResult("Error: ${e.message}")
            }
        }
    }

    private fun loadInitial() {
        viewModelScope.launch {
            try {
                scenarios = api.listScenarios()
                adapters = api.listAdapters()
            } catch (e: Exception) {
                errorMessage = e.message
            }
        }
    }

    fun runScenario(name: String, adapter: String = "default") {
        viewModelScope.launch {
            isLoading = true
            errorMessage = null
            try {
                result = api.runScenario(name, adapter)
                scenarioInfo = try { api.getScenarioInfo(name) } catch (_: Exception) { null }
            } catch (e: Exception) {
                errorMessage = e.message
            }
            isLoading = false
        }
    }

    fun runCustom(request: CustomRunRequest) {
        viewModelScope.launch {
            isLoading = true
            errorMessage = null
            try {
                result = api.runCustom(request)
            } catch (e: Exception) {
                errorMessage = e.message
            }
            isLoading = false
        }
    }

    fun inspectState(step: Int) {
        viewModelScope.launch {
            errorMessage = null
            try {
                stateSnapshot = api.getState(step)
            } catch (e: Exception) {
                errorMessage = e.message
            }
        }
    }
}
