# Android App - Steam Hardware Monitor

## Building

```bash
cd android
./gradlew build
./gradlew assembleDebug  # Build APK
```

## Running

```bash
./gradlew installDebug   # Install on connected device
./gradlew runDebug       # Run app
```

## Features

- ✅ Real-time hardware availability checking
- ✅ Periodic monitoring every 5 minutes
- ✅ Support for multiple hardware items
- ✅ Material Design 3 UI
- ✅ Protobuf API integration
- ✅ Dark theme (Steam-inspired)

## Package Structure

```
cz.janosik.steammonitor/
├── MainActivity.kt          # Main UI (Compose)
├── MonitorViewModel.kt      # State management
├── SteamHardwareApi.kt      # API communication
└── Models.kt                # Data classes
```

## Supported Hardware

- Steam Controller (1558609)

## Permissions

- `INTERNET` - API calls to Steam
- `ACCESS_NETWORK_STATE` - Check connectivity
