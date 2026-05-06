package cz.janosik.steammonitor

import android.content.Context
import android.content.SharedPreferences
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

class MonitorViewModel(
    private val context: Context,
) : ViewModel() {
    private val _state = MutableStateFlow(MonitorState())
    val state: StateFlow<MonitorState> = _state

    private val prefs: SharedPreferences = context.getSharedPreferences("steam_monitor", Context.MODE_PRIVATE)
    private val api = SteamHardwareApi(context)

    init {
        loadSavedItems()
    }

    fun checkStatus(hardwareIds: List<Int>) {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null)
            try {
                val items = mutableListOf<HardwareItem>()
                for (id in hardwareIds) {
                    val data = api.fetchHardwareData(id)
                    if (data != null) {
                        items.add(data)
                    }
                }

                _state.value =
                    _state.value.copy(
                        isLoading = false,
                        items = items,
                        lastUpdated = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date()),
                    )

                savePreviousState(items)
            } catch (e: Exception) {
                _state.value =
                    _state.value.copy(
                        isLoading = false,
                        error = e.message ?: "Unknown error",
                    )
            }
        }
    }

    private fun savePreviousState(items: List<HardwareItem>) {
        prefs.edit().putString("last_items", items.toString()).apply()
    }

    private fun loadSavedItems() {
        // Load last known state from SharedPreferences
        val saved = prefs.getString("last_items", null)
        // Parse and display saved state
    }
}
