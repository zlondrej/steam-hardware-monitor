package cz.janosik.steammonitor

import android.app.AlarmManager
import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class SteamMonitorApp : Application() {
    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
        // Don't schedule here - will be handled by MainActivity lifecycle
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val notificationManager = getSystemService(NotificationManager::class.java)

            // Foreground status notification channel (LOW importance)
            val foregroundChannel =
                NotificationChannel(
                    MonitorWorker.WORKER_NOTIFICATION_CHANNEL_ID,
                    "Monitoring Status",
                    NotificationManager.IMPORTANCE_LOW,
                ).apply {
                    description = "Shows the monitoring status and next check time"
                }
            notificationManager.createNotificationChannel(foregroundChannel)

            // Availability alert notification channel (HIGH importance)
            val availabilityChannel =
                NotificationChannel(
                    MonitorWorker.AVAILABILITY_NOTIFICATION_CHANNEL_ID,
                    "Hardware Availability",
                    NotificationManager.IMPORTANCE_HIGH,
                ).apply {
                    description = "Alerts when monitored hardware is available"
                }
            notificationManager.createNotificationChannel(availabilityChannel)
        }
    }
}

object BootHelper {
    const val ALARM_ACTION = "cz.janosik.steammonitor.ALARM_CHECK"

    fun pendingWorkerIntent(context: Context): PendingIntent {
        val intent =
            Intent(context, AlarmReceiver::class.java).apply {
                action = ALARM_ACTION
            }
        return PendingIntent.getBroadcast(
            context,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }

    fun cancelBackgroundWorker(context: Context) {
        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val pendingIntent = pendingWorkerIntent(context)

        alarmManager.cancel(pendingIntent)
        android.util.Log.d("cz.janosik.steammonitor.BootHelper", "Alarm canceled")
    }

    fun scheduleBackgroundWorker(context: Context) {
        val prefs = context.getSharedPreferences("steam_monitor", Context.MODE_PRIVATE)

        val trackSteamController = prefs.getBoolean("track_steam_controller", true)
        if (!trackSteamController) {
            return // Don't schedule if tracking is disabled
        }

        val intervalMinutes = prefs.getInt("check_interval", 5).toLong()
        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager

        val pendingIntent = pendingWorkerIntent(context)

        // Cancel any existing alarm first
        alarmManager.cancel(pendingIntent)

        // Schedule new alarm - use setAndAllowWhileIdle for reliability
        val intervalMillis = intervalMinutes * 60 * 1000
        val triggerAtMillis = System.currentTimeMillis() + intervalMillis

        try {
            // Try setExactAndAllowWhileIdle first (more reliable)
            alarmManager.setExactAndAllowWhileIdle(
                AlarmManager.RTC_WAKEUP,
                triggerAtMillis,
                pendingIntent,
            )
            android.util.Log.d("cz.janosik.steammonitor.BootHelper", "Alarm scheduled (exact): interval=$intervalMinutes minutes")
        } catch (e: SecurityException) {
            // Fall back to setAndAllowWhileIdle if permission denied
            alarmManager.setAndAllowWhileIdle(
                AlarmManager.RTC_WAKEUP,
                triggerAtMillis,
                pendingIntent,
            )
            android.util.Log.d("cz.janosik.steammonitor.BootHelper", "Alarm scheduled (inexact): interval=$intervalMinutes minutes")
        }
    }

    fun updateWorkerNotification(
        context: Context,
        isSuspended: Boolean,
    ) {
        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val prefs = context.getSharedPreferences("steam_monitor", Context.MODE_PRIVATE)
        val lastCheck = prefs.getLong("last_check_time", 0L)

        val lastCheckTimeStr =
            if (lastCheck > System.currentTimeMillis() - 3600000) {
                val timeFormat = SimpleDateFormat("HH:mm", Locale.getDefault())
                timeFormat.format(Date(lastCheck))
            } else {
                "--:--"
            }

        val contentText =
            if (isSuspended) {
                context.getString(R.string.worker_notification_suspended, lastCheckTimeStr)
            } else {
                val intervalMinutes = prefs.getInt("check_interval", 5)
                val nextCheckTime = System.currentTimeMillis() + (intervalMinutes * 60 * 1000)
                val nextCheckTimeFormat = SimpleDateFormat("HH:mm", Locale.getDefault())
                val nextCheckTimeStr = nextCheckTimeFormat.format(Date(nextCheckTime))

                context.getString(R.string.worker_notification_active, intervalMinutes, nextCheckTimeStr, lastCheckTimeStr)
            }

        val notification =
            NotificationCompat
                .Builder(context, MonitorWorker.WORKER_NOTIFICATION_CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_notification)
                .setContentTitle(context.getString(R.string.worker_notification_title))
                .setStyle(NotificationCompat.BigTextStyle().bigText(contentText))
                .setOngoing(true)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .build()

        notificationManager.notify(MonitorWorker.WORKER_NOTIFICATION_ID, notification)
        android.util.Log.d(
            "cz.janosik.steammonitor.BootHelper",
            "Notification updated: suspended=$isSuspended, lastCheck=$lastCheckTimeStr, content=$contentText",
        )
    }
}
