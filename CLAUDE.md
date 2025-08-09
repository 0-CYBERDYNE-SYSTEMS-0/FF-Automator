# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**macOS-use** is a Python AI agent framework that enables natural language control of macOS applications through accessibility APIs. The project bridges AI language models with native macOS applications for task automation.

## Essential Commands

### Development Setup
```bash
# Development installation
uv venv && source .venv/bin/activate
uv pip install --editable .

# Required environment setup
cp .env.example .env
# Edit .env to add API keys (OpenAI, Anthropic, Gemini, DeepSeek)
```

### Testing
```bash
# Run all tests
pytest

# Run specific test types
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m slow          # Slow tests only

# Run with verbose output
pytest -v --tb=short
```

### Code Quality
```bash
# Format code (follows project standards: single quotes, tabs, 130 char limit)
ruff format .

# Lint code
ruff check .

# Fix auto-fixable lint issues
ruff check --fix .
```

### Running Examples
```bash
python examples/try.py              # Interactive agent demo
python examples/calculate.py        # Calculator automation
python examples/login_to_auth0.py   # Authentication workflow
python examples/excel.py           # Excel automation demo
python examples/check_time_online.py # Web browsing demo
python gradio_app/app.py           # Legacy Gradio web interface
python mlx_use_cli.py              # Enhanced interactive CLI
python standalone_cli.py           # Standalone demo CLI (no installation)
python web_interface_app.py        # Modern web interface (recommended)
```

### New UI Interfaces

#### Enhanced CLI Interface
```bash
# Full-featured CLI (requires package installation)
python mlx_use_cli.py

# Standalone demo CLI (works without full installation)
python standalone_cli.py

# CLI Features:
# - Persistent session management
# - Command history and auto-completion  
# - Real-time streaming output
# - Natural language command parsing
# - Session save/load/list commands
```

#### Enhanced Web Interface

**Launch the modern web interface:**
```bash
python web_interface/api/main.py
# Then open http://localhost:8080 in your browser
```

**Features:**
- **Conversational Chat**: Natural language control with autonomous multi-step execution
- **Agent Mode**: Terminal-style execution with real-time progress
- **Session Management**: Save, load, and manage conversation history  
- **Provider Support**: Switch between OpenAI, Anthropic, Google, DeepSeek, OpenRouter, Ollama, and LM Studio
- **Automation Templates**: Quick-start templates for common tasks
- **Interactive Controls**: Interrupt, redirect, and queue multiple tasks
- **Real-time Streaming**: Live progress updates and step-by-step feedback
- **Task Queue System**: Handle multiple requests and follow-ups automatically
- **Conversation Memory**: Persistent context tracking across interactions

**Enhanced Chat Capabilities:**
The chat interface now operates with full autonomous multi-step execution - no more stopping after the first action! Complex requests like "Open Calculator, compute 15 * 23, then open Notes and write the result" are executed completely automatically while maintaining conversational interaction.

#### Native macOS Desktop Application (Go UI)

**Launch the native macOS app (recommended for production use):**
```bash
cd go-ui
./install.sh          # First-time setup (installs Wails CLI)
make build            # Development build
make dev              # Development with hot reload
make build-prod       # Production .app bundle
make dmg              # Create DMG installer
```

**Benefits of Native App:**
- **No Browser Conflicts**: Won't interfere with browser automation tasks
- **System Integration**: Native macOS menu bar and dock integration  
- **Better Performance**: Direct system access without browser overhead
- **Standalone**: Runs independently without browser dependencies
- **Complete Feature Parity**: All web interface features in native app

### Automation Templates and Scheduling

**Built-in automation features:**
```bash
# Available via web interface and native app
# - Pre-built automation templates (Calculator, Notes, System Info, etc.)
# - Cron-based task scheduling with enable/disable controls
# - Task execution history with success/failure tracking
# - Template duplication and customization
# - Category and tag organization system
```

### Comprehensive LLM Provider Support (2025)

#### Supported Providers & Models

**🌐 Cloud Providers:**
- **OpenAI**: GPT-4.1, o3, o4-mini, o3-pro, o4-mini-high, gpt-4o, gpt-4o-mini
- **Anthropic**: Claude 4 (Opus, Sonnet), Claude 3.5 (Sonnet, Haiku), Claude 3 series
- **Google**: Gemini 2.5 (Pro, Flash), Gemini 2.0 (Flash, Live), Gemini 1.5 series
- **DeepSeek**: deepseek-chat (V3-0324), deepseek-reasoner (R1-0528)
- **OpenRouter**: 400+ models including free options (Llama, Phi, Gemma)

**💻 Local Providers:**
- **Ollama**: Auto-detected models (no API key needed)
- **LM Studio**: Auto-detected models (no API key needed)

#### Quick Setup

```bash
# Test all providers
python test_providers.py

# Copy environment template
cp .env.example .env

# Add your API keys to .env:
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GEMINI_API_KEY=your_google_key
DEEPSEEK_API_KEY=your_deepseek_key
OPENROUTER_API_KEY=your_openrouter_key

# Set preferred provider (optional)
DEFAULT_LLM_PROVIDER=OpenAI
DEFAULT_LLM_MODEL=gpt-4.1
```

#### Provider Features

**Model Selection by Task:**
- **Reasoning**: o3, o3-pro, Claude 4 Opus, deepseek-reasoner, Gemini 2.5 Pro
- **Coding**: gpt-4.1, Claude 4 Sonnet, deepseek-chat, Gemini 2.5 Flash
- **General Chat**: gpt-4o, Claude 3.5 Sonnet, Gemini 2.0 Flash
- **Cost-Effective**: o4-mini, OpenRouter free models, Local models

**Advanced Features:**
- Automatic provider health checking
- Smart fallback to available providers
- Cost optimization with spending limits
- Task-specific provider preferences
- Real-time provider status indicators

## Architecture

### Core Components
- **`mlx_use/agent/`**: AI agent logic and LLM conversation management
- **`mlx_use/controller/`**: Action orchestration and registry system
- **`mlx_use/mac/`**: macOS accessibility API integration layer
- **`mlx_use/cli/`**: Enhanced CLI interface with session management
- **`mlx_use/automation/`**: Task automation, scheduling, and templates
- **`gradio_app/`**: Legacy Gradio web interface
- **`web_interface/`**: Modern JavaScript-based web interface
- **`go-ui/`**: Native macOS desktop application (Wails + Go)

### Key Service Classes
- **`Agent`** (`mlx_use/agent/service.py`): Main orchestration class for AI task execution
- **`Controller`** (`mlx_use/controller/service.py`): Coordinates actions and maintains state
- **`MessageManager`** (`mlx_use/agent/message_manager/`): Handles LLM conversation flow
- **`Registry`** (`mlx_use/controller/registry/service.py`): Action registration and discovery system
- **`MacUITreeBuilder`** (`mlx_use/mac/tree.py`): macOS UI element tree generation and analysis

### Action System
Actions are registered via the registry pattern in `mlx_use/controller/registry/`. New actions should:
- Inherit from appropriate base classes
- Be registered in the controller registry
- Follow async/await patterns
- Include proper error handling

## Development Patterns

### Async/Await
All operations use async/await patterns. UI interactions are non-blocking and support concurrent execution.

### Error Handling
- Use structured logging via `mlx_use/logging_config.py`
- Implement graceful degradation for UI state changes
- Provide detailed error context for debugging

### Configuration
- Environment variables defined in `.env` (copy from `.env.example`)
- Pydantic models for configuration validation
- Centralized logging configuration

## Dependencies

### Core Stack
- **LangChain**: LLM integration and prompt management
- **pyobjc/pycocoa**: macOS native API bindings for accessibility
- **Pydantic**: Data validation and modeling
- **Playwright**: Web automation capabilities

### Supported LLM Providers
Configure via environment variables: OpenAI (GPT-4/4o), Anthropic (Claude), Google Gemini, DeepSeek

## Important Notes

### Platform Requirements
- **macOS only** - requires accessibility permissions
- **Python 3.11+** required
- **Security Warning**: Can access system-wide applications and credentials

### Testing Strategy
- Use pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- Mock external services in unit tests
- Integration tests require macOS accessibility permissions
- Run specific test suites: `pytest -m "not slow"` to skip slow tests
- Test files follow patterns: `test_*.py` or `*_test.py` in tests directory
- Async tests are automatically handled via `asyncio_mode = auto` configuration

### Code Style
- Single quotes for strings
- Tab indentation (not spaces)
- 130-character line limit
- Ruff for formatting and linting