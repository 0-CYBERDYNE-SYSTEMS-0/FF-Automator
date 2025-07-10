# macOS-use Native UI

A native macOS desktop application for macOS-use, built with Go and Wails. This provides a standalone UI that doesn't require a web browser, avoiding conflicts when automating browser applications.

## Features

- 🖥️ **Native macOS Application** - No browser required
- 🔄 **Seamless Python Integration** - Uses existing Python backend
- 💬 **Chat Mode** - Conversational interface with multi-step execution
- 🤖 **Agent Mode** - Terminal-style task execution
- 🔌 **WebSocket Communication** - Real-time updates and progress
- 📦 **Easy Installation** - Single .app bundle
- 🎨 **Native UI** - Follows macOS design guidelines

## Prerequisites

1. Go 1.21 or later
2. Wails CLI v2
3. Xcode Command Line Tools
4. Existing macOS-use Python environment

## Installation

### Install Wails

```bash
go install github.com/wailsapp/wails/v2/cmd/wails@latest
```

### Build the Application

From the `go-ui` directory:

```bash
# Install dependencies
go mod download

# Build for development
wails build

# Build for production (creates .app bundle)
wails build -production
```

## Development

### Run in Development Mode

```bash
wails dev
```

This will:
1. Start the Python backend automatically
2. Launch the UI with hot reload
3. Enable developer tools

### Project Structure

```
go-ui/
├── cmd/macos-use-ui/     # Main application entry point
├── internal/
│   ├── backend/          # Python backend management
│   ├── ui/               # Wails app bindings
│   └── websocket/        # WebSocket client
├── assets/               # Frontend HTML/CSS/JS
└── build/                # Build output (generated)
```

## Usage

1. **First Time Setup**: 
   - Ensure Python environment is set up in parent directory
   - Copy `.env.example` to `.env` with your API keys

2. **Launch Application**:
   - Double-click the macOS-use app
   - Python backend starts automatically
   - UI connects via WebSocket

3. **Select Provider**:
   - Choose your LLM provider from dropdown
   - Select model

4. **Use Chat or Agent Mode**:
   - Chat Mode: Natural conversation with automation
   - Agent Mode: Direct task execution

## Architecture

The Go application acts as a native wrapper around the existing Python backend:

1. **Python Process Management**: Starts/stops Python backend as subprocess
2. **WebSocket Bridge**: Maintains connection to Python WebSocket server
3. **Native UI**: Provides macOS-native interface using Wails
4. **No Code Duplication**: All automation logic remains in Python

## Building for Distribution

### Create DMG Installer

```bash
# Build production app
wails build -production

# Create DMG (requires create-dmg)
brew install create-dmg
create-dmg \
  --volname "macOS-use" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "macOS-use.app" 175 120 \
  --hide-extension "macOS-use.app" \
  --app-drop-link 425 120 \
  "macOS-use.dmg" \
  "build/bin/"
```

### Code Signing (Optional)

For distribution outside the App Store:

```bash
codesign --deep --force --verify --verbose --sign "Developer ID Application: Your Name" build/bin/macOS-use.app
```

## Troubleshooting

### Python Backend Won't Start

- Check Python virtual environment exists: `.venv/bin/python`
- Verify `.env` file is present with API keys
- Check console logs in the UI

### WebSocket Connection Issues

- Ensure Python backend is running on port 8080
- Check firewall settings
- View connection status in bottom left of UI

### Accessibility Permissions

The app will request accessibility permissions on first run. Grant these in:
System Preferences → Security & Privacy → Privacy → Accessibility

## Development Tips

- Use `wails dev` for hot reload during development
- Python logs appear in the collapsible log panel
- WebSocket reconnects automatically on connection loss
- All Python changes take effect on backend restart

## License

Same as parent macOS-use project