# Web Interface Documentation

## Overview

The macOS-use web interface provides a modern, elegant way to interact with AI agents through a browser-based interface. It features both conversational chat and terminal-style agent execution modes.

## Quick Start

### Launch the Web Interface

```bash
python web_interface/api/main.py
```

Then open [http://localhost:8080](http://localhost:8080) in your browser.

## Features

### 🤖 Conversational Chat Interface

The chat interface provides natural language control with autonomous multi-step execution capabilities.

**Key Features:**
- **Autonomous Multi-Step Execution**: Complex tasks are executed completely automatically
- **Real-time Progress Streaming**: Live updates showing step-by-step execution
- **Conversation Memory**: Persistent context tracking across interactions
- **Task Queue System**: Handle multiple requests and follow-ups automatically
- **Interactive Controls**: Interrupt, redirect, and queue tasks during execution

**Example Usage:**
```
"Open Calculator, compute 15 * 23, then open Notes and write the result"
"Go to GitHub, find trending repositories, and create a note with the top 3"
"Check my system information and create an email draft with the details"
```

**Interactive Controls:**
- **Send**: Execute the message/task
- **Stop**: Completely stop execution
- **Interrupt**: Pause execution for interaction
- **Redirect**: Change to a new task mid-execution

### 🖥️ Agent Mode

Terminal-style execution interface for detailed task automation.

**Features:**
- Real-time execution progress
- Step-by-step terminal output
- Configurable parameters (max steps, max actions)
- Task refinement with AI assistance

### 📂 Session Management

Save and manage conversation history and agent sessions.

**Features:**
- Save conversations with custom names
- Load previous sessions
- Session statistics (message count, success/failure rates)
- Delete unwanted sessions

### 🔌 Provider Support

Comprehensive support for multiple LLM providers:

**Cloud Providers:**
- **OpenAI**: GPT-4.1, o3, o4-mini, gpt-4o, etc.
- **Anthropic**: Claude 4 (Opus, Sonnet), Claude 3.5 series
- **Google**: Gemini 2.5 (Pro, Flash), Gemini 2.0 series
- **DeepSeek**: deepseek-chat, deepseek-reasoner
- **OpenRouter**: 400+ models including free options

**Local Providers:**
- **Ollama**: Auto-detected local models
- **LM Studio**: Auto-detected local models

### 🚀 Automation Templates

Quick-start templates for common automation tasks:

**Quick Tasks:**
- Play music
- Calculator operations
- Open applications
- Create notes

**Multi-Step Workflows:**
- File organization and messaging
- Meeting planning with maps
- Presentation creation
- Screenshot and sharing

**Productivity Automations:**
- Daily standup preparation
- Downloads folder cleanup
- Weekly report setup
- Focus mode activation

## Technical Architecture

### Backend (FastAPI)

**Main Components:**
- `web_interface/api/main.py`: FastAPI server with REST endpoints and WebSocket support
- Enhanced agent classes with conversational capabilities
- Task queue and conversation memory management
- Real-time streaming and progress updates

**Key Classes:**
- `ChatAgent`: Extended Agent with conversational capabilities
- `ConversationMemory`: Persistent context tracking
- `ChatTaskQueue`: Task queue management with dependencies
- `ConnectionManager`: WebSocket connection management

### Frontend (Vanilla JavaScript)

**Architecture:**
- Modern vanilla JavaScript with component-based design
- WebSocket integration for real-time communication
- Responsive design with elegant UI/UX
- State management for sessions and conversations

**Key Components:**
- Chat interface with streaming updates
- Agent execution with progress tracking
- Session management interface
- Provider configuration and testing

### WebSocket API

**Message Types:**
- `chat_message`: Send chat messages for processing
- `chat_stream_update`: Real-time progress updates
- `chat_complete`: Final completion status
- `agent_task`: Execute agent tasks
- `interrupt_chat`: Interrupt ongoing execution
- `redirect_chat`: Redirect to new task
- `add_task`: Add task to queue

## Configuration

### Environment Variables

Create `.env` file with your API keys:

```bash
# Required for cloud providers
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GEMINI_API_KEY=your_google_key
DEEPSEEK_API_KEY=your_deepseek_key
OPENROUTER_API_KEY=your_openrouter_key

# Optional: Set default provider
DEFAULT_LLM_PROVIDER=OpenAI
DEFAULT_LLM_MODEL=gpt-4.1
```

### Provider Testing

Test provider connectivity:

```bash
# Test all providers
python test_providers.py
```

Or use the web interface provider testing feature.

## Development

### Running in Development Mode

```bash
# Start the FastAPI server with auto-reload
uvicorn web_interface.api.main:app --host 0.0.0.0 --port 8080 --reload
```

### File Structure

```
web_interface/
├── api/
│   └── main.py              # FastAPI backend
├── static/
│   ├── index.html           # Main HTML interface
│   ├── js/
│   │   └── app.js          # JavaScript application
│   └── styles.css          # CSS styles
└── README.md
```

## Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   - Check if the server is running on port 8080
   - Verify firewall settings
   - Ensure browser supports WebSockets

2. **Provider API Errors**
   - Verify API keys in `.env` file
   - Check provider rate limits
   - Test provider connectivity in the interface

3. **Execution Errors**
   - Ensure macOS accessibility permissions are granted
   - Check system compatibility
   - Review console logs for detailed error messages

### Debug Mode

Enable debug logging by setting environment variable:

```bash
export LOG_LEVEL=DEBUG
python web_interface/api/main.py
```

## Security Considerations

- The web interface runs locally by default (localhost:8080)
- API keys are stored locally in `.env` file
- No data is transmitted to external services except chosen LLM providers
- Local models (Ollama/LM Studio) provide complete privacy

## Performance

- WebSocket connections provide real-time updates
- Conversation memory is stored in-memory per session
- Sessions are automatically cleaned up on disconnect
- Supports concurrent users with separate session isolation