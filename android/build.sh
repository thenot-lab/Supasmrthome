#!/bin/bash
# ============================================================
# NeuroArousal Android — Build & Install Script
# ============================================================
#
# Prerequisites:
#   1. Android SDK installed (Android Studio or command-line tools)
#   2. ANDROID_HOME / ANDROID_SDK_ROOT set in environment
#   3. Java 17+ (e.g., brew install openjdk@17 / apt install openjdk-17-jdk)
#
# Usage:
#   cd android/
#   chmod +x build.sh
#   ./build.sh              # build debug APK
#   ./build.sh release      # build release APK
#   ./build.sh install      # build + install on connected device
#
# The resulting APK is a clickable-install file:
#   - Transfer to phone via USB, email, cloud storage, or QR code link
#   - Enable "Install from Unknown Sources" in Android Settings
#   - Tap the APK to install
#
# ============================================================

set -euo pipefail
cd "$(dirname "$0")"

MODE="${1:-debug}"
GRADLEW="./gradlew"

# Check for Gradle wrapper; if not present, use system gradle
if [ ! -f "$GRADLEW" ]; then
    echo "Gradle wrapper not found. Using system gradle..."
    GRADLEW="gradle"
    if ! command -v gradle &> /dev/null; then
        echo "ERROR: Neither ./gradlew nor system gradle found."
        echo "Run 'gradle wrapper' first, or install Gradle."
        exit 1
    fi
fi

echo "=== NeuroArousal Android Build ==="
echo "Mode: $MODE"
echo ""

if [ "$MODE" = "debug" ]; then
    echo "[1/2] Building debug APK..."
    $GRADLEW assembleDebug --no-daemon 2>&1 | tail -20

    APK_PATH="app/build/outputs/apk/debug/app-debug.apk"
    echo ""
    echo "=== Build Complete ==="
    echo "APK: $APK_PATH"
    echo ""
    echo "Install methods:"
    echo "  1. USB: adb install $APK_PATH"
    echo "  2. Transfer APK to phone -> tap to install"
    echo "  3. Share via cloud storage / QR code"

elif [ "$MODE" = "release" ]; then
    echo "[1/2] Building release APK..."
    $GRADLEW assembleRelease --no-daemon 2>&1 | tail -20

    APK_PATH="app/build/outputs/apk/release/app-release-unsigned.apk"
    echo ""
    echo "=== Build Complete ==="
    echo "APK: $APK_PATH"
    echo ""
    echo "NOTE: Release APK is unsigned. To sign:"
    echo "  apksigner sign --ks my-keystore.jks $APK_PATH"
    echo ""
    echo "Or create a signed release:"
    echo "  Add signing config to app/build.gradle.kts"

elif [ "$MODE" = "install" ]; then
    echo "[1/3] Building debug APK..."
    $GRADLEW assembleDebug --no-daemon 2>&1 | tail -20

    APK_PATH="app/build/outputs/apk/debug/app-debug.apk"

    echo "[2/3] Installing on connected device..."
    adb install -r "$APK_PATH"

    echo "[3/3] Launching app..."
    adb shell am start -n com.neuroarousal.exhibit/.app.MainActivity

    echo ""
    echo "=== Installed & Launched ==="

else
    echo "Usage: $0 [debug|release|install]"
    exit 1
fi
