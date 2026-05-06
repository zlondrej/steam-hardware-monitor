package cz.janosik.steammonitor

import android.content.Context
import android.content.SharedPreferences
import android.util.Base64
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import steam.store.SteamHardware

class SteamHardwareApi(
    private val context: Context,
) {
    private val client = OkHttpClient()
    private val apiUrl = "https://api.steampowered.com/IStoreBrowseService/GetHardwareItems/v1"
    private val detailsUrl = "https://store.steampowered.com/api/appdetails"
    private val sharedPrefs: SharedPreferences = context.getSharedPreferences("hardware_names", Context.MODE_PRIVATE)

    suspend fun fetchHardwareData(
        hardwareId: Int,
        countryCode: String = "CZ",
    ): HardwareItem? {
        return try {
            // Build protobuf request
            val requestProto = buildProtobufRequest(hardwareId, countryCode)
            val encoded = Base64.encodeToString(requestProto, Base64.NO_WRAP)

            // Make API call
            val request =
                Request
                    .Builder()
                    .url("$apiUrl?origin=https%3A%2F%2Fstore.steampowered.com&input_protobuf_encoded=$encoded")
                    .header("User-Agent", "Mozilla/5.0")
                    .build()

            val response = client.newCall(request).execute()
            if (!response.isSuccessful) return null

            // Parse response using generated protobuf classes
            val bytes = response.body?.bytes() ?: return null
            val item = parseHardwareResponse(bytes, hardwareId)

            // Fetch and cache the hardware name
            if (item != null) {
                val name = getHardwareName(hardwareId)
                item.copy(name = name)
            } else {
                item
            }
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    private suspend fun getHardwareName(hardwareId: Int): String {
        // Check cache first
        val cached = sharedPrefs.getString("name_$hardwareId", null)
        if (cached != null) {
            return cached
        }

        return try {
            // Fetch from Steam API
            val request =
                Request
                    .Builder()
                    .url("$detailsUrl?appids=$hardwareId")
                    .header("User-Agent", "Mozilla/5.0")
                    .build()

            val response = client.newCall(request).execute()
            if (!response.isSuccessful) return "Hardware #$hardwareId"

            val jsonBody = response.body?.string() ?: return "Hardware #$hardwareId"
            val jsonObject = JSONObject(jsonBody)

            // Navigate: { "appid": { "success": true, "data": { "name": "..." } } }
            val appData = jsonObject.optJSONObject(hardwareId.toString()) ?: return "Hardware #$hardwareId"
            if (!appData.optBoolean("success", false)) return "Hardware #$hardwareId"

            val data = appData.optJSONObject("data") ?: return "Hardware #$hardwareId"
            val name = data.optString("name", null) ?: return "Hardware #$hardwareId"

            // Cache the name
            sharedPrefs.edit().putString("name_$hardwareId", name).apply()

            name
        } catch (e: Exception) {
            e.printStackTrace()
            "Hardware #$hardwareId"
        }
    }

    private fun buildProtobufRequest(
        hardwareId: Int,
        countryCode: String,
    ): ByteArray {
        // Build protobuf using generated classes from steam_hardware.proto
        val options =
            SteamHardware.HardwareRequestOptions
                .newBuilder()
                .setLanguage("english")
                .setCountryCode(countryCode)
                .build()

        val request =
            SteamHardware.GetHardwareItemsRequest
                .newBuilder()
                .setHardwareId(hardwareId)
                .setOptions(options)
                .build()

        return request.toByteArray()
    }

    private fun parseHardwareResponse(
        bytes: ByteArray,
        hardwareId: Int,
    ): HardwareItem? =
        try {
            // Parse using generated protobuf class
            val response = SteamHardware.CHardwarePackageDetails.parseFrom(bytes)

            HardwareItem(
                name = "Hardware #$hardwareId", // Name will be fetched and replaced in fetchHardwareData
                packageId = hardwareId,
                available = response.inventoryAvailable,
                estimatedDelivery =
                    if (response.estimatedDeliverySoonestBusinessDays > 0 &&
                        response.estimatedDeliveryLatestBusinessDays > 0
                    ) {
                        Pair(response.estimatedDeliverySoonestBusinessDays, response.estimatedDeliveryLatestBusinessDays)
                    } else {
                        null
                    },
                highPendingOrders = response.highPendingOrders,
                requiresReservation = response.requiresReservation,
                allowPurchase = response.allowPurchaseInCountry,
            )
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
}
