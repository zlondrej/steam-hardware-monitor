#!/bin/bash
# Android setup and build script

set -e

PROJECT_DIR="$(readlink -e "$(dirname "${BASH_SOURCE[0]}")")"

echo "📱 Steam Hardware Monitor - Android Setup"
echo "=========================================="
echo ""

# Check if Android SDK is installed
if [ ! -d "$HOME/AndroidSDK" ]; then
    echo "❌ Android SDK not found at $HOME/AndroidSDK"
    echo "Please install Android SDK first"
    exit 1
fi

# Build the app
echo "📦 Building Android app..."
cd "$PROJECT_DIR"

# Check if gradle wrapper exists
if [ ! -f "gradlew" ]; then
    echo "Creating gradle wrapper..."
    gradle wrapper --gradle-version 8.14.4
fi

# Make gradlew executable
chmod +x gradlew

# Build
./gradlew build

echo ""
echo "✅ Build complete!"
echo ""
echo "Next steps:"
echo "1. Connect Android device (or start emulator)"
echo "2. Run: ./gradlew installDebug"
echo "3. Or build APK: ./gradlew assembleDebug"
echo ""
echo "APK location: $PROJECT_DIR/app/build/outputs/apk/debug/"
