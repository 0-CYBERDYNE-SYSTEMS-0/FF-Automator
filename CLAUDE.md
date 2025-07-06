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
python gradio_app/app.py           # Web UI interface
python mlx_use_cli.py              # Enhanced interactive CLI
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

#### Web Chat Interface
- New "Chat" tab in Gradio app provides conversational interface
- Persistent conversation history across sessions
- Quick action buttons for common tasks
- Session management with save/load functionality
- Real-time agent feedback

## Architecture

### Core Components
- **`mlx_use/agent/`**: AI agent logic and LLM conversation management
- **`mlx_use/controller/`**: Action orchestration and registry system
- **`mlx_use/mac/`**: macOS accessibility API integration layer
- **`gradio_app/`**: Web-based user interface

### Key Service Classes
- **`Agent`** (`mlx_use/agent/service.py`): Main orchestration class for AI task execution
- **`Controller`** (`mlx_use/controller/service.py`): Coordinates actions and maintains state
- **`MessageManager`** (`mlx_use/agent/message_manager/`): Handles LLM conversation flow

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

### Code Style
- Single quotes for strings
- Tab indentation (not spaces)
- 130-character line limit
- Ruff for formatting and linting