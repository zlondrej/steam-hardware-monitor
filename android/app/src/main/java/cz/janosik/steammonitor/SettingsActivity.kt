package cz.janosik.steammonitor

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import cz.janosik.steammonitor.ui.SteamMonitorTheme

class SettingsActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            SettingsScreen(this)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(activity: SettingsActivity) {
    val prefs = activity.getSharedPreferences("steam_monitor", android.content.Context.MODE_PRIVATE)
    var intervalText by remember { mutableStateOf(prefs.getInt("check_interval", 5).toString()) }
    var trackSteamController by remember { mutableStateOf(prefs.getBoolean("track_steam_controller", true)) }
    var debugNotifications by remember { mutableStateOf(prefs.getBoolean("debug_notifications", false)) }

    SteamMonitorTheme {
        Column(modifier = Modifier.fillMaxSize()) {
            TopAppBar(
                title = { Text(stringResource(R.string.settings)) },
                navigationIcon = {
                    IconButton(onClick = { activity.finish() }) {
                        Icon(Icons.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )

            Column(
                modifier =
                    Modifier
                        .fillMaxSize()
                        .padding(24.dp),
                verticalArrangement = Arrangement.Top,
            ) {
                Text(
                    stringResource(R.string.check_interval),
                    fontWeight = FontWeight.Bold,
                    fontSize = 18.sp,
                    color = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.padding(bottom = 16.dp),
                )

                OutlinedTextField(
                    value = intervalText,
                    onValueChange = { newValue ->
                        // Only allow numeric input
                        if (newValue.isEmpty() || newValue.all { it.isDigit() }) {
                            intervalText = newValue
                        }
                    },
                    label = { Text("Minutes") },
                    textStyle = androidx.compose.ui.text.TextStyle(color = MaterialTheme.colorScheme.onSurface),
                    modifier =
                        Modifier
                            .fillMaxWidth()
                            .padding(bottom = 24.dp),
                    colors =
                        OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = MaterialTheme.colorScheme.primary,
                            unfocusedBorderColor = MaterialTheme.colorScheme.outline,
                        ),
                )

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier =
                        Modifier
                            .fillMaxWidth()
                            .padding(bottom = 24.dp),
                ) {
                    Switch(
                        checked = trackSteamController,
                        onCheckedChange = { trackSteamController = it },
                        modifier = Modifier.padding(end = 12.dp),
                    )
                    Text(
                        stringResource(R.string.track_steam_controller),
                        color = MaterialTheme.colorScheme.onSurface,
                        modifier = Modifier.weight(1f),
                    )
                }

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier =
                        Modifier
                            .fillMaxWidth()
                            .padding(bottom = 24.dp),
                ) {
                    Switch(
                        checked = debugNotifications,
                        onCheckedChange = { debugNotifications = it },
                        modifier = Modifier.padding(end = 12.dp),
                    )
                    Text(
                        "Show Debug Notifications",
                        color = MaterialTheme.colorScheme.onSurface,
                        modifier = Modifier.weight(1f),
                    )
                }

                Button(
                    onClick = {
                        val intervalValue = intervalText.toIntOrNull() ?: prefs.getInt("check_interval", 5)
                        val clampedInterval = intervalValue.coerceIn(1, 1440) // 1 to 1440 minutes
                        prefs
                            .edit()
                            .apply {
                                putInt("check_interval", clampedInterval)
                                putBoolean("track_steam_controller", trackSteamController)
                                putBoolean("debug_notifications", debugNotifications)
                            }.apply()
                        activity.finish()
                    },
                    modifier =
                        Modifier
                            .align(Alignment.CenterHorizontally)
                            .padding(top = 24.dp),
                ) {
                    Text("Save")
                }
            }
        }
    }
}
