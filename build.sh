#!/bin/bash
# Build script for Key Light Controller portable binary

echo "Key Light Controller - Binary Build Script"
echo "=========================================="

# Check if virtual environment exists
if [ ! -d "build_env" ]; then
    echo "Creating virtual environment..."
    python3 -m venv build_env
fi

# Activate virtual environment
source build_env/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt pyinstaller

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Build the binary
echo "Building standalone binary..."
pyinstaller keylight_controller.spec --clean --noconfirm

# Check if build was successful
if [ -f "dist/keylight-controller" ]; then
    SIZE=$(du -h dist/keylight-controller | cut -f1)
    echo ""
    echo "✅ Build successful!"
    echo "Binary location: dist/keylight-controller"
    echo "Binary size: $SIZE"
    echo ""
    echo "The binary is completely portable and can be run on any Linux system."
    echo "No Python or dependencies required!"
    echo ""
    echo "To run: ./dist/keylight-controller"
    echo "To install system-wide: sudo cp dist/keylight-controller /usr/local/bin/"
else
    echo "❌ Build failed! Check the output above for errors."
    exit 1
fi

deactivate