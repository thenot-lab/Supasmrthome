#!/bin/bash
# ============================================================
# NeuroArousal iOS — Non-App Store Build & Deployment Script
# ============================================================
#
# Prerequisites:
#   1. macOS with Xcode 15+ installed
#   2. xcodegen installed:  brew install xcodegen
#   3. An Apple Developer account (free or paid)
#   4. A provisioning profile for ad-hoc distribution (or use
#      Automatic signing for development builds)
#
# Usage:
#   cd ios/
#   chmod +x build.sh
#   ./build.sh              # build .app for simulator
#   ./build.sh device       # build .ipa for physical device
#   ./build.sh install      # build + install via ios-deploy
#
# ============================================================

set -euo pipefail
cd "$(dirname "$0")"

MODE="${1:-simulator}"
BUILD_DIR="build"
SCHEME="NeuroArousal"

echo "=== NeuroArousal iOS Build ==="
echo "Mode: $MODE"
echo ""

# Step 1: Generate Xcode project from project.yml
if ! command -v xcodegen &> /dev/null; then
    echo "ERROR: xcodegen not found. Install with: brew install xcodegen"
    exit 1
fi

echo "[1/4] Generating Xcode project..."
xcodegen generate
echo "  -> NeuroArousal.xcodeproj created"

# Step 2: Build
mkdir -p "$BUILD_DIR"

if [ "$MODE" = "simulator" ]; then
    echo "[2/4] Building for iOS Simulator..."
    xcodebuild \
        -project NeuroArousal.xcodeproj \
        -scheme "$SCHEME" \
        -sdk iphonesimulator \
        -configuration Debug \
        -derivedDataPath "$BUILD_DIR/derived" \
        -destination 'platform=iOS Simulator,name=iPhone 15' \
        build 2>&1 | tail -20

    APP_PATH=$(find "$BUILD_DIR/derived" -name "*.app" -type d | head -1)
    echo ""
    echo "=== Build Complete ==="
    echo "App: $APP_PATH"
    echo ""
    echo "To install in simulator:"
    echo "  xcrun simctl boot 'iPhone 15'  # if not already booted"
    echo "  xcrun simctl install booted '$APP_PATH'"
    echo "  xcrun simctl launch booted com.neuroarousal.exhibit"

elif [ "$MODE" = "device" ]; then
    echo "[2/4] Building for physical device..."
    xcodebuild \
        -project NeuroArousal.xcodeproj \
        -scheme "$SCHEME" \
        -sdk iphoneos \
        -configuration Release \
        -derivedDataPath "$BUILD_DIR/derived" \
        -archivePath "$BUILD_DIR/$SCHEME.xcarchive" \
        archive 2>&1 | tail -20

    echo "[3/4] Exporting IPA..."
    xcodebuild \
        -exportArchive \
        -archivePath "$BUILD_DIR/$SCHEME.xcarchive" \
        -exportOptionsPlist ExportOptions.plist \
        -exportPath "$BUILD_DIR/ipa" 2>&1 | tail -10

    IPA_PATH="$BUILD_DIR/ipa/$SCHEME.ipa"
    echo ""
    echo "=== Build Complete ==="
    echo "IPA: $IPA_PATH"
    echo ""
    echo "Install methods (non-App Store):"
    echo "  1. Apple Configurator: Drag IPA onto connected device"
    echo "  2. ios-deploy: ios-deploy --bundle '$IPA_PATH'"
    echo "  3. Diawi/InstallOnAir: Upload IPA for OTA install link"
    echo "  4. Xcode: Window -> Devices -> drag IPA"

elif [ "$MODE" = "install" ]; then
    echo "[2/4] Building for device..."
    xcodebuild \
        -project NeuroArousal.xcodeproj \
        -scheme "$SCHEME" \
        -sdk iphoneos \
        -configuration Debug \
        -derivedDataPath "$BUILD_DIR/derived" \
        build 2>&1 | tail -20

    APP_PATH=$(find "$BUILD_DIR/derived" -name "*.app" -type d | head -1)

    if ! command -v ios-deploy &> /dev/null; then
        echo "ERROR: ios-deploy not found. Install with: brew install ios-deploy"
        echo "App built at: $APP_PATH"
        exit 1
    fi

    echo "[3/4] Installing on connected device..."
    ios-deploy --bundle "$APP_PATH" --debug

else
    echo "Usage: $0 [simulator|device|install]"
    exit 1
fi
