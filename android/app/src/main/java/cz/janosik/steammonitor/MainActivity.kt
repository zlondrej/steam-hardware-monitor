package cz.janosik.steammonitor

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectVerticalDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.ProcessLifecycleOwner
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import cz.janosik.steammonitor.ui.SteamMonitorTheme
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        android.util.Log.d("cz.janosik.steammonitor.MainActivity", "onCreate")

        // Pause background alarm when app is in foreground
        ProcessLifecycleOwner.get().lifecycleScope.launch {
            ProcessLifecycleOwner.get().lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
                // App is in foreground - cancel the periodic alarm and show suspended status
                android.util.Log.d("cz.janosik.steammonitor.MainActivity", "Lifecycle STARTED - canceling alarm")
                BootHelper.cancelBackgroundWorker(applicationContext)
                BootHelper.updateWorkerNotification(applicationContext, isSuspended = true)
            }
        }

        setContent {
            SteamMonitorApp(this)
        }
    }

    override fun onPause() {
        super.onPause()
        android.util.Log.d("cz.janosik.steammonitor.MainActivity", "onPause - app going to background")
        // App going to background - reschedule the periodic worker and update notification
        BootHelper.scheduleBackgroundWorker(applicationContext)
        BootHelper.updateWorkerNotification(applicationContext, isSuspended = false)
    }
}

private fun getHardwareIds(activity: Activity): List<Int> {
    val prefs = activity.applicationContext.getSharedPreferences("steam_monitor", android.content.Context.MODE_PRIVATE)
    val trackSteamController = prefs.getBoolean("track_steam_controller", true)
    val hardwareIds = mutableListOf<Int>()
    if (trackSteamController) {
        hardwareIds.add(MonitorWorker.STEAM_CONTROLLER_ID)
    }
    return hardwareIds
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SteamMonitorApp(activity: Activity) {
    val viewModelFactory =
        object : ViewModelProvider.Factory {
            override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
                @Suppress("UNCHECKED_CAST")
                return MonitorViewModel(activity.applicationContext) as T
            }
        }
    val viewModel: MonitorViewModel = viewModel(factory = viewModelFactory)
    val state by viewModel.state.collectAsState()

    var pullOffset by remember { mutableStateOf(0f) }
    var showPullHint by remember { mutableStateOf(true) }

    LaunchedEffect(Unit) {
        // Initial check
        val hardwareIds = getHardwareIds(activity)
        if (hardwareIds.isNotEmpty()) {
            viewModel.checkStatus(hardwareIds)
        }

        // Periodic checks every 5 minutes while app is active
        while (true) {
            delay(5 * 60 * 1000)
            val updatedIds = getHardwareIds(activity)
            if (updatedIds.isNotEmpty()) {
                viewModel.checkStatus(updatedIds)
            }
        }
    }

    SteamMonitorTheme {
        Scaffold(
            topBar = {
                TopAppBar(
                    title = { Text(stringResource(R.string.app_name)) },
                    actions = {
                        IconButton(onClick = {
                            val intent = Intent(activity, SettingsActivity::class.java)
                            activity.startActivity(intent)
                        }) {
                            Icon(Icons.Filled.Settings, contentDescription = stringResource(R.string.settings))
                        }
                    },
                )
            },
        ) { padding ->
            BoxWithConstraints(
                modifier =
                    Modifier
                        .fillMaxSize()
                        .padding(padding),
            ) {
                val screenHeightDp = maxHeight
                val pullThreshold = screenHeightDp * 0.30f // 30% of screen height
                val boxMaxHeightDp = screenHeightDp * 0.06f // 6% of screen height

                Box(
                    modifier =
                        Modifier
                            .fillMaxSize()
                            .pointerInput(Unit) {
                                detectVerticalDragGestures(
                                    onVerticalDrag = { change, dragAmount ->
                                        if (pullOffset > -(pullThreshold.value * 1.5)) {
                                            pullOffset += dragAmount
                                        }
                                    },
                                    onDragEnd = {
                                        if (pullOffset > pullThreshold.value) {
                                            val hardwareIds = getHardwareIds(activity)
                                            if (hardwareIds.isNotEmpty()) {
                                                viewModel.checkStatus(hardwareIds)
                                            }
                                            showPullHint = false
                                        }
                                        pullOffset = 0f
                                    },
                                )
                            },
                ) {
                    Column(
                        modifier =
                            Modifier
                                .fillMaxSize()
                                .padding(16.dp),
                    ) {
                        // Pull-to-refresh indicator
                        if (pullOffset > 0) {
                            val progress = (pullOffset / pullThreshold.value).coerceIn(0f, 1f)
                            val boxHeightFraction = (pullOffset / (pullThreshold.value / 2)).coerceAtMost(1f)
                            val boxHeight = (boxMaxHeightDp.value * boxHeightFraction).dp
                            Box(
                                modifier =
                                    Modifier
                                        .align(Alignment.CenterHorizontally)
                                        .height(boxHeight)
                                        .padding(bottom = 12.dp),
                            ) {
                                CircularProgressIndicator(
                                    progress = progress,
                                    modifier =
                                        Modifier
                                            .size(48.dp)
                                            .align(Alignment.Center),
                                    strokeWidth = 3.dp,
                                )
                            }
                        }

                        // Pull-to-refresh hint
                        if (showPullHint && pullOffset == 0f) {
                            Text(
                                stringResource(R.string.pull_to_refresh_hint),
                                fontSize = 12.sp,
                                modifier =
                                    Modifier
                                        .align(Alignment.CenterHorizontally)
                                        .padding(bottom = 12.dp),
                            )
                        }

                        // Last updated timestamp
                        Text(
                            stringResource(R.string.last_updated, state.lastUpdated),
                            fontSize = 12.sp,
                            modifier = Modifier.padding(bottom = 16.dp),
                        )

                        // Loading indicator
                        if (state.isLoading) {
                            CircularProgressIndicator(
                                modifier = Modifier.align(Alignment.CenterHorizontally),
                            )
                        }

                        // Error message
                        state.error?.let {
                            Text(
                                stringResource(R.string.error, it),
                                modifier = Modifier.padding(16.dp),
                            )
                        }

                        // Hardware items list
                        LazyColumn(
                            verticalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            items(state.items) { item ->
                                HardwareItemCard(item)
                            }
                        }

                        // Refresh button
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            modifier =
                                Modifier
                                    .align(Alignment.CenterHorizontally)
                                    .padding(top = 24.dp),
                        ) {
                            Button(
                                onClick = {
                                    val hardwareIds = getHardwareIds(activity)
                                    if (hardwareIds.isNotEmpty()) {
                                        viewModel.checkStatus(hardwareIds)
                                    }
                                    showPullHint = false
                                },
                                enabled = !state.isLoading,
                            ) {
                                Text(stringResource(R.string.refresh))
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun HardwareItemCard(item: HardwareItem) {
    Card(
        modifier =
            Modifier
                .fillMaxWidth()
                .padding(4.dp),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    item.name,
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp,
                    color = MaterialTheme.colorScheme.onSurface,
                )

                Text(
                    stringResource(if (item.available) R.string.in_stock else R.string.out_of_stock),
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = if (item.available) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Delivery estimate
            item.estimatedDelivery?.let { (soonest, latest) ->
                Text(
                    stringResource(R.string.estimated_delivery, soonest, latest),
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            // Pending orders
            if (item.highPendingOrders) {
                Text(
                    stringResource(R.string.high_pending_orders),
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.error,
                )
            }
        }
    }
}
