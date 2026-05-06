package cz.janosik.steammonitor

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class BootCompletedReceiver : BroadcastReceiver() {
    override fun onReceive(
        context: Context?,
        intent: Intent?,
    ) {
        if (intent?.action == Intent.ACTION_BOOT_COMPLETED && context != null) {
            BootHelper.scheduleBackgroundWorker(context)
        }
    }
}
