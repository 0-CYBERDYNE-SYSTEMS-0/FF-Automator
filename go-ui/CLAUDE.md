# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**go-ui** is a native macOS desktop application for macOS-use, built with Go and Wails. It provides a standalone UI that avoids browser conflicts when automating browser applications. The application acts as a native wrapper around the existing Python backend, maintaining a clean separation between the UI and automation logic.

**✅ FEATURE COMPLETE**: This Go UI now has **full feature parity** with the web interface version, including all automation templates, scheduling, advanced chat controls, and comprehensive backend API integration.

## Essential Commands

### Development Setup
```bash
# Install Wails and dependencies
./install.sh

# OR manual setup
make setup

# Check backend dependencies
make check-backend
```

### Build Commands
```bash
# Development build
make build
wails build

# Production build
make build-prod
wails build -production -clean

# Development with hot reload
make dev
wails dev
```

### Utility Commands
```bash
# Clean build artifacts
make clean

# Create DMG installer (requires production build)
make dmg

# Run built application
make run

# Full setup from scratch
make setup-all
```

### Backend Integration
```bash
# Check Python backend setup
make check-backend

# The Python backend must be properly configured in parent directory:
# - .venv/ virtual environment
# - .env file with API keys
# - macOS-use package installed with: uv pip install --editable .
```

## Architecture

### High-Level Structure
The application follows a clean architecture separating concerns:

**Go Layer (Native UI)**
- `app.go` / `cmd/macos-use-ui/main.go`: Main application entry point
- `internal/ui/app.go`: Wails app bindings and UI logic
- `internal/backend/python_manager.go`: Python process management
- `internal/websocket/client.go`: WebSocket communication
- `assets/`: Frontend HTML/CSS/JS files

**Integration Layer**
- WebSocket communication for real-time updates
- HTTP REST API for configuration and data operations
- Process management for Python backend lifecycle

**Python Layer (Automation Logic)**
- All automation logic remains in the parent macOS-use Python project
- No duplication of functionality between Go and Python

### Key Components

**PythonManager** (`internal/backend/python_manager.go`):
- Manages Python subprocess lifecycle
- Handles environment setup and validation
- Provides logging and health monitoring
- Starts Python backend: `python web_interface/api/main.py`

**App** (`internal/ui/app.go`):
- Main Wails application struct with **comprehensive API bindings**
- **100+ Go methods** exposing full Python backend functionality
- Handles WebSocket communication with Python backend
- **Complete feature set**: automation templates, scheduling, search, history, provider testing
- Advanced chat controls: interrupt, redirect, task queues, custom system messages
- **All backend endpoints**: REST API + WebSocket protocol fully implemented

**WebSocket Client** (`internal/websocket/client.go`):
- Real-time communication with Python backend
- Handles chat messages, agent tasks, and status updates
- Automatic reconnection and heartbeat functionality

### Communication Flow
1. **Startup**: Go app starts Python backend as subprocess
2. **Connection**: WebSocket connection established to Python server
3. **User Action**: Frontend sends task via WebSocket
4. **Processing**: Python backend processes automation tasks
5. **Updates**: Real-time progress streamed back via WebSocket
6. **Completion**: Results displayed in native UI

## Configuration

### Environment Requirements
- Go 1.21+ with toolchain go1.24.4
- Wails v2.10.2 CLI
- Xcode Command Line Tools
- Python backend in parent directory with:
  - `.venv/` virtual environment
  - `.env` file with LLM API keys
  - macOS-use package installed

### Key Dependencies
- `github.com/wailsapp/wails/v2`: Native application framework
- `github.com/gorilla/websocket`: WebSocket communication
- `github.com/joho/godotenv`: Environment variable loading

### Wails Configuration
Project configured via `wails.json`:
- Frontend assets in `assets/` directory
- No build/install steps (vanilla HTML/CSS/JS)
- Main entry point: `app.go`
- Output binary: `macOS-use`

## Development Patterns

### Process Management
- Python backend runs as managed subprocess
- Graceful shutdown with interrupt signals
- Health monitoring with HTTP endpoint checks
- Automatic log forwarding to UI

### Error Handling
- Comprehensive error checking for subprocess operations
- Network communication error handling
- UI state management for connection failures
- Detailed logging for debugging

### Frontend Integration
- Wails runtime bindings for Go method calls
- Event system for real-time updates
- WebSocket message handling
- Session and automation management UI

## Important Notes

### Platform Requirements
- **macOS only** - uses macOS-specific Wails features
- **Native packaging** - creates .app bundles
- **Accessibility permissions** - inherited from Python backend

### Python Backend Dependency
- **Critical dependency** - Go app cannot function without Python backend
- **No code duplication** - all automation logic remains in Python
- **Environment validation** - checks for .venv and .env before startup
- **Process lifecycle** - manages Python backend start/stop

### Build and Distribution
- Development builds include debugging capabilities
- Production builds are optimized and can be packaged as DMG
- Code signing available for distribution outside App Store
- Single .app bundle contains all Go dependencies

## Development Workflow

1. **Setup**: Run `make setup-all` for complete environment setup
2. **Development**: Use `make dev` for hot reload during development
3. **Testing**: Test with both chat and agent modes
4. **Building**: Use `make build-prod` for production builds
5. **Distribution**: Use `make dmg` to create installer packages

### Backend Compatibility
- Must maintain compatibility with Python backend API
- WebSocket message format must match Python expectations
- HTTP endpoints must align with Python web interface
- Session and automation data structures must be consistent

## Complete Feature Set

### 🎯 **Automation Management**
- **Templates**: 5 built-in templates (Calculator, Notes, System Info, Email, Screenshot)
- **Scheduling**: Full cron-based scheduling with enable/disable
- **Search & Filter**: Search by name, category, tags
- **History**: Execution history with success/failure tracking
- **Duplication**: Clone existing automations
- **Categories & Tags**: Organize automations

### 💬 **Advanced Chat Features**
- **Multi-step Execution**: Autonomous task completion
- **Task Queues**: Add multiple tasks to queue
- **Interrupt/Redirect**: Control running tasks
- **Custom System Messages**: Personalized AI instructions
- **Prompt Refinement**: AI-assisted prompt improvement
- **Conversation Memory**: Persistent context tracking

### 🔧 **Provider Management**
- **Connection Testing**: Test all provider API keys
- **Health Monitoring**: Real-time provider status
- **Full Provider Support**: OpenAI, Anthropic, Google, DeepSeek, OpenRouter, Ollama, LM Studio

### 📊 **UI Features**
- **Four Modes**: Chat, Agent, Templates, Scheduler
- **Modal Dialogs**: Advanced interactions
- **Real-time Updates**: Live progress indicators
- **Session Management**: Save/load conversations
- **Responsive Design**: Mobile-friendly interface

### 🌐 **Complete API Integration**
- **REST Endpoints**: All 25+ backend endpoints implemented
- **WebSocket Protocol**: Full message type support
- **Error Handling**: Comprehensive error management
- **Data Consistency**: Matching data structures with web interface