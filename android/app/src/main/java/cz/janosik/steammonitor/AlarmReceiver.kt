package cz.janosik.steammonitor

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class AlarmReceiver : BroadcastReceiver() {
    override fun onReceive(
        context: Context,
        intent: Intent,
    ) {
        android.util.Log.d("cz.janosik.steammonitor.AlarmReceiver", "Alarm fired")

        // Launch coroutine to handle the check
        CoroutineScope(Dispatchers.Default).launch {
            try {
                val api = SteamHardwareApi(context)
                val prefs = context.getSharedPreferences("steam_monitor", Context.MODE_PRIVATE)

                // Save check time
                prefs.edit().putLong("last_check_time", System.currentTimeMillis()).apply()

                // Send debug notification
                sendDebugNotification(context)

                // Update notification
                BootHelper.updateWorkerNotification(context, isSuspended = false)
                android.util.Log.d("cz.janosik.steammonitor.AlarmReceiver", "Notification updated")

                // Fetch and check hardware
                val trackSteamController = prefs.getBoolean("track_steam_controller", true)
                if (trackSteamController) {
                    val item = api.fetchHardwareData(MonitorWorker.STEAM_CONTROLLER_ID)

                    if (item != null) {
                        android.util.Log.d(
                            "cz.janosik.steammonitor.AlarmReceiver",
                            "Item fetched - packageId=${item.packageId}, name=${item.name}, available=${item.available}",
                        )
                        if (item.available) {
                            sendAvailabilityNotification(context, item)
                            android.util.Log.d("cz.janosik.steammonitor.AlarmReceiver", "Item is available, notification sent")
                        }
                    } else {
                        android.util.Log.d("cz.janosik.steammonitor.AlarmReceiver", "Item fetch returned null")
                    }
                }

                android.util.Log.d("cz.janosik.steammonitor.AlarmReceiver", "Alarm check completed")

                // Reschedule the alarm for the next interval
                BootHelper.scheduleBackgroundWorker(context)
            } catch (e: Exception) {
                android.util.Log.e("cz.janosik.steammonitor.AlarmReceiver", "Error in alarm check", e)
            }
        }
    }

    private fun sendAvailabilityNotification(
        context: Context,
        item: HardwareItem,
    ) {
        val notificationManager = context.getSystemService(android.app.NotificationManager::class.java)
        val intent =
            Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            }
        val pendingIntent =
            android.app.PendingIntent.getActivity(
                context,
                item.packageId,
                intent,
                android.app.PendingIntent.FLAG_UPDATE_CURRENT or android.app.PendingIntent.FLAG_IMMUTABLE,
            )

        val status = context.getString(R.string.in_stock)
        val deliveryInfo =
            item.estimatedDelivery?.let { (s, l) ->
                "\n" + context.getString(R.string.notification_delivery, s, l)
            } ?: ""
        val checkedTime = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault()).format(java.util.Date())
        val checkedText = context.getString(R.string.notification_checked, checkedTime)

        val notification =
            androidx.core.app.NotificationCompat
                .Builder(context, MonitorWorker.AVAILABILITY_NOTIFICATION_CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle(item.name)
                .setContentText(status)
                .setStyle(
                    androidx.core.app.NotificationCompat
                        .BigTextStyle()
                        .bigText("$status$deliveryInfo\n$checkedText"),
                ).setContentIntent(pendingIntent)
                .setAutoCancel(true)
                .setPriority(androidx.core.app.NotificationCompat.PRIORITY_HIGH)
                .build()

        notificationManager.notify(MonitorWorker.NOTIFICATION_ID_BASE + item.packageId, notification)
    }

    private fun sendDebugNotification(context: Context) {
        val prefs = context.getSharedPreferences("steam_monitor", Context.MODE_PRIVATE)
        val debugNotificationsEnabled = prefs.getBoolean("debug_notifications", false)

        if (!debugNotificationsEnabled) return

        val notificationManager = context.getSystemService(android.app.NotificationManager::class.java)
        val checkedTime = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault()).format(java.util.Date())
        val uniqueId = (System.currentTimeMillis() % 100000).toInt()

        val notification =
            androidx.core.app.NotificationCompat
                .Builder(context, MonitorWorker.AVAILABILITY_NOTIFICATION_CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle("Steam Hardware Monitor")
                .setContentText("Availability check started at $checkedTime")
                .setPriority(androidx.core.app.NotificationCompat.PRIORITY_LOW)
                .setAutoCancel(true)
                .build()

        notificationManager.notify(uniqueId, notification)
    }
}
