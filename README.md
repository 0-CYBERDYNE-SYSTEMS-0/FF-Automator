# FF-Automator
<div align="center">
  <img src="./static/macos-use.png" alt="FF-Automator Logo" width="full">
  
  <h2>Advanced macOS Automation Framework with AI-Powered Natural Language Control</h2>
  
  [![GitHub stars](https://img.shields.io/github/stars/0-CYBERDYNE-SYSTEMS-0/FF-Automator?style=social)](https://github.com/0-CYBERDYNE-SYSTEMS-0/FF-Automator/stargazers)
  [![Release](https://img.shields.io/github/v/release/0-CYBERDYNE-SYSTEMS-0/FF-Automator)](https://github.com/0-CYBERDYNE-SYSTEMS-0/FF-Automator/releases)
  [![License](https://img.shields.io/github/license/0-CYBERDYNE-SYSTEMS-0/FF-Automator)](LICENSE)
</div>

---

##  Major Features
###  Native macOS Desktop Application
- **Go/Wails-based native app** for seamless macOS integration
- **No browser conflicts** - runs independently of web automation tasks
- **System integration** with menu bar and dock support
- **Complete feature parity** with web interface
- **Better performance** with direct system access

###  Advanced Web Interface
- **Conversational chat** with autonomous multi-step execution
- **Real-time streaming** with live progress updates
- **Task queue system** for handling multiple requests
- **Advanced controls**: interrupt, redirect, task refinement
- **Session management** with persistent conversation history

###  Comprehensive LLM Support
- **Cloud Providers**: 
  - OpenAI (GPT-4.1, o3, o4-mini, o3-pro, o4-mini-high, gpt-4o, gpt-4o-mini)
  - Anthropic (Claude 4 Opus/Sonnet, Claude 3.5 Sonnet/Haiku, Claude 3 series)
  - Google (Gemini 2.5 Pro/Flash, Gemini 2.0 Flash/Live, Gemini 1.5 series)
  - DeepSeek (deepseek-chat V3-0324, deepseek-reasoner R1-0528)
  - OpenRouter (400+ models including free options)
- **Local Providers**: 
  - Ollama (auto-detected, no API key needed)
  - LM Studio (auto-detected, no API key needed)
- **Smart fallback** and provider health checking

###  Automation System
- **Pre-built templates** for common macOS tasks
- **Cron-based scheduling** with enable/disable controls
- **Execution history** tracking success/failure rates
- **Category and tag organization**
- **Template duplication and customization**

###  Enhanced CLI
- **Session management** with persistent history
- **Command auto-completion** and history
- **Streaming output** with real-time progress
- **Natural language parsing**
- **Standalone demo mode** (no installation required)

---

##  Quick Start
### Option 1: Web Interface (Recommended)
```bash
git clone https://github.com/0-CYBERDYNE-SYSTEMS-0/FF-Automator.git
cd FF-Automator
cp .env.example .env  # Add your API keys
python web_interface_app.py

Open [http://127.0.0.1:8080](http://127.0.0.1:8080) in your browser.

### Option 2: Native macOS App (Best Performance)
```bash
cd go-ui
./install.sh  # First-time setup (installs Wails CLI)
make build    # Development build
make dev      # Development with hot reload
make build-prod  # Production .app bundle
make dmg      # Create DMG installer

### Option 3: Enhanced CLI
```bash
python mlx_use_cli.py              # Full-featured CLI
python standalone_cli.py           # Standalone demo (no installation)

---

##  Installation & Setup
### Requirements
- **macOS** (accessibility permissions required)
- **Python 3.11+**
- **Go 1.21+** (for native app)

### Environment Setup
```bash
# Using uv (recommended)
brew install uv && uv venv && source .venv/bin/activate
uv pip install --editable .

# Copy and configure environment
cp .env.example .env
open .env  # Add your API keys

### API Keys Configuration
Get your API keys from:
- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/account/keys  
- **Google**: https://console.cloud.google.com/apis/credentials
- **DeepSeek**: https://platform.deepseek.com/api_keys
- **OpenRouter**: https://openrouter.ai/keys

---

##  Usage Examples
### Conversational Automation
Try these complex multi-step commands:

```bash
"Open Calculator, compute 15 * 23, then open Notes and write the result"
"Go to GitHub, find trending repositories, and create a note with the top 3"  
"Check my system information and create an email draft with the details"
"Open Excel, create a budget spreadsheet, and add sample categories"

### Automation Templates
Access pre-built templates for:
- **Calculator Operations**: Complex mathematical computations
- **Note Taking**: Structured note creation and organization
- **System Information**: Hardware and software inventory
- **File Management**: Automated file organization
- **Web Research**: Automated information gathering

### Scheduling
Set up automated tasks with cron expressions:
```bash
"0 9 * * 1-5"  # Every weekday at 9 AM
"*/30 * * * *"  # Every 30 minutes
"0 0 1 * *"     # First day of every month

---

##  Technical Architecture
### Core Components
- **`mlx_use/agent/`**: AI agent logic and LLM conversation management
- **`mlx_use/controller/`**: Action orchestration and registry system
- **`mlx_use/mac/`**: macOS accessibility API integration layer
- **`mlx_use/cli/`**: Enhanced CLI interface with session management
- **`mlx_use/automation/`**: Task automation, scheduling, and templates
- **`web_interface/`**: Modern JavaScript-based web interface
- **`go-ui/`**: Native macOS desktop application (Wails + Go)

### Key Features
- **Async/await patterns** throughout codebase
- **Structured logging** with configurable levels
- **Error handling** with graceful degradation
- **Security-focused** with comprehensive .gitignore
- **Registry pattern** for action discovery and registration

---

##  Testing & Development
### Running Tests
```bash
pytest                    # All tests
pytest -m unit           # Unit tests only  
pytest -m integration    # Integration tests only
pytest -m slow           # Slow tests only
pytest -v --tb=short     # Verbose output
pytest -m "not slow"     # Skip slow tests

### Code Quality
```bash
ruff format .             # Format code (single quotes, tabs, 130 char limit)
ruff check .              # Lint code
ruff check --fix .        # Fix auto-fixable issues

### Development Commands
```bash
python examples/try.py              # Interactive agent demo
python examples/calculate.py        # Calculator automation
python examples/excel.py           # Excel automation demo
python test_providers.py           # Test all LLM providers

---

##  Security & Privacy
### Security Features
- **No credentials stored** in repository
- **Comprehensive .gitignore** protecting sensitive data
- **Environment variable** configuration for API keys
- **Local model support** for privacy-focused use cases
- **Provider health checking** with automatic failover

### Privacy Options
- Use **local models** (Ollama, LM Studio) for complete privacy
- **Disable telemetry** via environment variables
- **Session encryption** for conversation history
- **Selective data sharing** controls

---

##  Model Recommendations
### By Task Type
- **Reasoning Tasks**: o3, o3-pro, Claude 4 Opus, deepseek-reasoner, Gemini 2.5 Pro
- **Coding Tasks**: gpt-4.1, Claude 4 Sonnet, deepseek-chat, Gemini 2.5 Flash
- **General Chat**: gpt-4o, Claude 3.5 Sonnet, Gemini 2.0 Flash
- **Cost-Effective**: o4-mini, OpenRouter free models, Local models

### Provider Benefits
- **OpenAI**: Latest models, reliable performance
- **Anthropic**: Excellent reasoning, safety-focused
- **Google**: Fast inference, good free tier
- **DeepSeek**: Strong reasoning capabilities, cost-effective
- **OpenRouter**: Access to 400+ models, many free options
- **Local**: Complete privacy, no API costs, works offline

---

##  Roadmap
### Completed
- [x] Enhanced conversational chat interface with multi-step autonomous execution
- [x] Comprehensive LLM provider support (OpenAI, Anthropic, Google, DeepSeek, OpenRouter, Ollama, LM Studio)
- [x] Web interface with real-time streaming and interactive controls
- [x] Session management and conversation history persistence
- [x] Task queue system for handling multiple requests and follow-ups
- [x] Native macOS desktop application with complete feature parity
- [x] Automation templates and scheduling system
- [x] Enhanced CLI with session management and auto-completion

### In Progress
-  Refine agent prompting for improved reliability
-  Enhanced self-correction mechanisms
-  User input prompts for interactive workflows
-  Performance optimizations and cost reduction

### Future Plans
-  MLX and mlx-vlm integration for local inference
-  Fine-tuned small model for on-device operation
-  iPhone/iPad support expansion
-  Advanced automation workflow builder

---

##  Important Notes
### Accessibility Permissions
FF-Automator requires macOS accessibility permissions to interact with applications. Grant permissions when prompted for full functionality.

### User Discretion Advised
This is an advanced automation tool that can:
- Access system-wide applications and credentials
- Perform login operations and use stored passwords  
- Interact with every app and UI component on your Mac
- Execute complex multi-step workflows autonomously

**Always review tasks before execution and use appropriate caution.**

---

##  Contributing
We welcome contributions! Feel free to:
- Submit pull requests for new features or bug fixes
- Open issues for bug reports or feature requests
- Contribute to documentation and examples
- Share automation templates and workflows

---

##  Support & Community
- **Issues**: [GitHub Issues](https://github.com/0-CYBERDYNE-SYSTEMS-0/FF-Automator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/0-CYBERDYNE-SYSTEMS-0/FF-Automator/discussions)
- **Documentation**: See CLAUDE.md for detailed technical documentation

---

##  License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <h3> Advanced macOS automation framework with AI-powered natural language control</h3>
  <p>Tell your Mac what to do, and watch it happen across ANY app.</p>
</div>