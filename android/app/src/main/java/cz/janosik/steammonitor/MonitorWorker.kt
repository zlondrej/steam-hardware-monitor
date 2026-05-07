package cz.janosik.steammonitor

import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import java.text.SimpleDateFormat
import java.util.*

class MonitorWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {
    private val api = SteamHardwareApi(context)
    private val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
    private val prefs = context.getSharedPreferences("steam_monitor", Context.MODE_PRIVATE)

    companion object {
        const val WORKER_NOTIFICATION_CHANNEL_ID = "steam_hardware_worker_status"
        const val AVAILABILITY_NOTIFICATION_CHANNEL_ID = "steam_hardware_availability"
        const val NOTIFICATION_ID_BASE = 1001
        const val WORKER_NOTIFICATION_ID = 999
        const val STEAM_CONTROLLER_ID = 1558609
        const val WORK_NAME = "steam_hardware_monitor"
        private const val PREF_LAST_CHECK = "last_check_time"
    }

    override suspend fun doWork(): Result =
        try {
            android.util.Log.d("cz.janosik.steammonitor.MonitorWorker", "Worker started")

            // Save the check time FIRST so notification shows current time
            prefs.edit().putLong(PREF_LAST_CHECK, System.currentTimeMillis()).apply()

            // Then show persistent status notification with updated time
            BootHelper.updateWorkerNotification(applicationContext, isSuspended = false)
            android.util.Log.d("cz.janosik.steammonitor.MonitorWorker", "Notification updated")

            val trackSteamController = prefs.getBoolean("track_steam_controller", true)
            val hardwareIds = mutableListOf<Int>()
            if (trackSteamController) {
                hardwareIds.add(STEAM_CONTROLLER_ID)
            }

            for (id in hardwareIds) {
                val item = api.fetchHardwareData(id)
                if (item != null && item.available) { // Only notify if available
                    sendNotification(item)
                    android.util.Log.d("cz.janosik.steammonitor.MonitorWorker", "Item $id is available, notification sent")
                }
            }

            android.util.Log.d("cz.janosik.steammonitor.MonitorWorker", "Worker completed successfully")
            Result.success()
        } catch (e: Exception) {
            android.util.Log.e("cz.janosik.steammonitor.MonitorWorker", "Worker failed", e)
            e.printStackTrace()
            Result.retry()
        }

    private fun sendNotification(item: HardwareItem) {
        val intent =
            Intent(applicationContext, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            }
        val pendingIntent =
            PendingIntent.getActivity(
                applicationContext,
                item.packageId,
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )

        val status = applicationContext.getString(R.string.in_stock)
        val deliveryInfo =
            item.estimatedDelivery?.let { (s, l) ->
                "\n" + applicationContext.getString(R.string.notification_delivery, s, l)
            } ?: ""
        val checkedTime = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        val checkedText = applicationContext.getString(R.string.notification_checked, checkedTime)

        val notification =
            NotificationCompat
                .Builder(applicationContext, AVAILABILITY_NOTIFICATION_CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_notification)
                .setContentTitle(item.name)
                .setContentText(status)
                .setStyle(
                    NotificationCompat
                        .BigTextStyle()
                        .bigText("$status$deliveryInfo\n$checkedText"),
                ).setContentIntent(pendingIntent)
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .build()

        notificationManager.notify(NOTIFICATION_ID_BASE + item.packageId, notification)
    }
}
