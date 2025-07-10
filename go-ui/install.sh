#!/bin/bash

echo "🔧 Installing macOS-use Native UI..."

# Check if Go is installed
if ! command -v go &> /dev/null; then
    echo "❌ Go is not installed. Please install Go first:"
    echo "  brew install go"
    exit 1
fi

# Install Wails CLI
echo "📦 Installing Wails CLI..."
go install github.com/wailsapp/wails/v2/cmd/wails@latest

# Add Go bin to PATH if not already there
GO_BIN_PATH="$HOME/go/bin"
if [[ ":$PATH:" != *":$GO_BIN_PATH:"* ]]; then
    echo "🔧 Adding Go bin to PATH..."
    
    # Add to shell profile
    if [[ "$SHELL" == *"zsh"* ]]; then
        echo "export PATH=\"$GO_BIN_PATH:\$PATH\"" >> ~/.zshrc
        echo "✅ Added to ~/.zshrc"
    elif [[ "$SHELL" == *"bash"* ]]; then
        echo "export PATH=\"$GO_BIN_PATH:\$PATH\"" >> ~/.bash_profile
        echo "✅ Added to ~/.bash_profile"
    fi
    
    # Export for current session
    export PATH="$GO_BIN_PATH:$PATH"
    echo "✅ Added to current session PATH"
fi

# Download Go dependencies
echo "📦 Downloading Go dependencies..."
go mod download
go mod tidy

# Check if wails is now available
if command -v wails &> /dev/null; then
    echo "✅ Wails CLI installed successfully!"
    echo ""
    echo "🚀 You can now run:"
    echo "  ./build.sh dev   # Start development server"
    echo "  ./build.sh prod  # Build production app"
    echo "  make dev         # Alternative development command"
else
    echo "❌ Installation may have failed. Please restart your terminal and try again."
    echo "Or manually run: export PATH=\"$HOME/go/bin:\$PATH\""
fi

echo ""
echo "📚 See README.md for more information."