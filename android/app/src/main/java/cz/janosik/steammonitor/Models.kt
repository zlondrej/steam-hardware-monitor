package cz.janosik.steammonitor

data class HardwareItem(
    val name: String,
    val packageId: Int,
    val available: Boolean,
    val estimatedDelivery: Pair<Int, Int>? = null,
    val highPendingOrders: Boolean = false,
    val requiresReservation: Boolean = false,
    val allowPurchase: Boolean = false,
)

data class MonitorState(
    val isLoading: Boolean = false,
    val items: List<HardwareItem> = emptyList(),
    val error: String? = null,
    val lastUpdated: String = "Never",
)
