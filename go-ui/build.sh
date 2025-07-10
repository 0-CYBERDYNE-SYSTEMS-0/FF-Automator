#!/bin/bash

# Build script for macOS-use Go UI

echo "🔧 Building macOS-use Native UI..."

# Check for Wails
if ! command -v wails &> /dev/null; then
    echo "❌ Wails not found. Installing..."
    go install github.com/wailsapp/wails/v2/cmd/wails@latest
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
    wails build -production -clean
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