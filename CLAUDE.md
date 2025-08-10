# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**macOS-use** (FF-Automator) is a Python AI agent framework that enables natural language control of macOS applications through accessibility APIs. The project bridges AI language models with native macOS applications for task automation.

## Essential Commands

### Development Setup
```bash
# Development installation
uv venv && source .venv/bin/activate
uv pip install --editable .

# Required environment setup
cp .env.example .env
# Edit .env to add API keys (OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter)

# Install pre-commit hooks (optional but recommended)
pre-commit install
```

### Testing
```bash
# Run all tests
pytest

# Run specific test types
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m slow          # Slow tests only
pytest -m "not slow"    # Skip slow tests

# Run with verbose output
pytest -v --tb=short

# Run specific test file
pytest tests/test_agent.py

# Run specific test function
pytest tests/test_agent.py::test_agent_init
```

### Code Quality
```bash
# Format code (follows project standards: single quotes, tabs, 130 char limit)
ruff format .

# Lint code
ruff check .

# Fix auto-fixable lint issues
ruff check --fix .

# Run pre-commit hooks manually
pre-commit run --all-files
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

### Interface Launch Commands

#### Modern Web Interface (Recommended)
```bash
# Primary launch command
python web_interface_app.py

# Alternative (direct API server)
python web_interface/api/main.py
# Then open http://localhost:8080
```

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

#### Native macOS Desktop Application (Go UI)
```bash
cd go-ui
./install.sh          # First-time setup (installs Wails CLI)
make build            # Development build
make dev              # Development with hot reload
make build-prod       # Production .app bundle
make dmg              # Create DMG installer
make clean            # Clean build artifacts
```

**Benefits of Native App:**
- **No Browser Conflicts**: Won't interfere with browser automation tasks
- **System Integration**: Native macOS menu bar and dock integration  
- **Better Performance**: Direct system access without browser overhead
- **Standalone**: Runs independently without browser dependencies

### Provider Testing and Configuration

```bash
# Test all LLM providers
python test_providers.py

# Test specific provider
python -c "from mlx_use.agent.llm_models import test_provider; test_provider('OpenAI')"

# Environment configuration
cp .env.example .env
# Add your API keys to .env:
# OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, DEEPSEEK_API_KEY, OPENROUTER_API_KEY
# Set DEFAULT_LLM_PROVIDER and DEFAULT_LLM_MODEL for preferences
```

## Architecture

### Core Components
- **`mlx_use/agent/`**: AI agent logic and LLM conversation management
- **`mlx_use/controller/`**: Action orchestration and registry system
- **`mlx_use/mac/`**: macOS accessibility API integration layer
- **`mlx_use/cli/`**: Enhanced CLI interface with session management
- **`mlx_use/automation/`**: Task automation, scheduling, and templates
- **`gradio_app/`**: Legacy Gradio web interface
- **`web_interface/`**: Modern JavaScript-based web interface (FastAPI backend + vanilla JS frontend)
- **`go-ui/`**: Native macOS desktop application (Wails + Go + Vue.js)

### Key Service Classes
- **`Agent`** (`mlx_use/agent/service.py`): Main orchestration class for AI task execution
- **`Controller`** (`mlx_use/controller/service.py`): Coordinates actions and maintains state
- **`MessageManager`** (`mlx_use/agent/message_manager/`): Handles LLM conversation flow
- **`Registry`** (`mlx_use/controller/registry/service.py`): Action registration and discovery system
- **`MacUITreeBuilder`** (`mlx_use/mac/tree.py`): macOS UI element tree generation and analysis
- **`LLMModels`** (`mlx_use/agent/llm_models.py`): Multi-provider LLM management with fallback

### Action System
Actions are registered via the registry pattern in `mlx_use/controller/registry/`. New actions should:
- Inherit from appropriate base classes
- Be registered in the controller registry
- Follow async/await patterns
- Include proper error handling
- Implement `_invoke()` method for action logic

## Development Patterns

### Async/Await
All operations use async/await patterns. UI interactions are non-blocking and support concurrent execution.

### Error Handling
- Use structured logging via `mlx_use/logging_config.py`
- Implement graceful degradation for UI state changes
- Provide detailed error context for debugging
- Use try/except blocks with specific exception types

### Configuration
- Environment variables defined in `.env` (copy from `.env.example`)
- Pydantic models for configuration validation in `mlx_use/config/`
- Centralized logging configuration in `mlx_use/logging_config.py`
- Provider preferences in `.env` (DEFAULT_LLM_PROVIDER, DEFAULT_LLM_MODEL)

### WebSocket Communication
- Web interface uses WebSocket for real-time streaming
- Reconnection logic with exponential backoff
- Message queue for handling multiple requests
- Binary message support for images/screenshots

## Dependencies

### Core Stack
- **Python 3.11+** required
- **LangChain** (0.3.x): LLM integration and prompt management
- **pyobjc/pycocoa**: macOS native API bindings for accessibility
- **Pydantic** (2.10.4+): Data validation and modeling
- **FastAPI/Uvicorn**: Modern web interface backend
- **Playwright**: Web automation capabilities
- **Gradio** (5.16.1+): Legacy web interface

### Build Tools
- **uv**: Fast Python package manager (recommended)
- **Hatchling**: Python build backend
- **Wails**: Go framework for native macOS app
- **Ruff**: Fast Python linter and formatter

### Supported LLM Providers
Configure via environment variables:
- **OpenAI**: GPT-4.1, o3, o4-mini series
- **Anthropic**: Claude 4, Claude 3.5 series
- **Google**: Gemini 2.5, 2.0, 1.5 series
- **DeepSeek**: deepseek-chat, deepseek-reasoner
- **OpenRouter**: 400+ models with free options
- **Ollama**: Local models (auto-detected)
- **LM Studio**: Local models (auto-detected)

## Important Notes

### Platform Requirements
- **macOS only** - requires accessibility permissions
- **Python 3.11+** required
- **Go 1.21+** for native app development
- **Security Warning**: Can access system-wide applications and credentials

### Testing Strategy
- Use pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- Mock external services in unit tests
- Integration tests require macOS accessibility permissions
- Test files follow patterns: `test_*.py` or `*_test.py` in tests directory
- Async tests are automatically handled via `asyncio_mode = auto` configuration
- Use `pytest.ini` for test configuration

### Code Style
- Single quotes for strings
- Tab indentation (not spaces)
- 130-character line limit
- Ruff for formatting and linting
- Pre-commit hooks for code quality

### Development Workflow
1. Always run tests before committing: `pytest -m "not slow"`
2. Format code with: `ruff format .`
3. Check linting: `ruff check --fix .`
4. Test provider connectivity: `python test_providers.py`
5. For web interface changes, test both backend (FastAPI) and frontend (JavaScript)
6. For native app changes, test with `make dev` in go-ui directory

### Common Issues and Solutions
- **Accessibility permissions**: Grant Terminal.app or your IDE accessibility access in System Settings
- **Provider failures**: Check API keys in .env and run `python test_providers.py`
- **WebSocket disconnects**: Check port 8080 availability and firewall settings
- **Go UI build failures**: Ensure Wails CLI is installed with `./install.sh` in go-ui directory