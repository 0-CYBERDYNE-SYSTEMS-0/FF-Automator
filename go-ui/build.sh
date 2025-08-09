#!/bin/bash

# Build script for macOS-use Go UI

echo "🔧 Building macOS-use Native UI..."

# Check for Wails
if ! command -v wails &> /dev/null; then
    echo "❌ Wails not found. Installing..."
    go install github.com/wailsapp/wails/v2/cmd/wails@latest
    
    # Add Go bin to PATH if not already there
    if [[ ":$PATH:" != *":$HOME/go/bin:"* ]]; then
        export PATH="$HOME/go/bin:$PATH"
        echo "✅ Added Go bin to PATH for this session"
    fi
    
    # Check again after installation
    if ! command -v wails &> /dev/null; then
        echo "❌ Wails installation failed. Please ensure Go is properly installed and try:"
        echo "  export PATH=\"\$HOME/go/bin:\$PATH\""
        echo "  go install github.com/wailsapp/wails/v2/cmd/wails@latest"
        exit 1
    fi
fi

# Check Python backend
if [ ! -d "../.venv" ]; then
    echo "❌ Python virtual environment not found!"
    echo "Please run in parent directory:"
    echo "  uv venv && source .venv/bin/activate && uv pip install --editable ."
    exit 1
fi

if [ ! -f "../.env" ]; then
    echo "❌ Environment file not found!"
    echo "Please copy .env.example to .env and add your API keys"
    exit 1
fi

# Download dependencies
echo "📦 Downloading Go dependencies..."
go mod download
go mod tidy

# Build based on argument
if [ "$1" = "dev" ]; then
    echo "🚀 Starting development server..."
    wails dev
elif [ "$1" = "prod" ]; then
    echo "📦 Building production app..."
    wails build -clean
    echo "✅ Build complete! App is in build/bin/"
else
    echo "🔨 Building development app..."
    wails build
    echo "✅ Build complete! App is in build/bin/"
    echo ""
    echo "Usage:"
    echo "  ./build.sh       - Build development version"
    echo "  ./build.sh dev   - Start development server"
    echo "  ./build.sh prod  - Build production version"
fi