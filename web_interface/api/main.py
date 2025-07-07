#!/usr/bin/env python3
"""
FastAPI backend for the elegant JavaScript interface to macOS automation.
Provides REST endpoints and WebSocket streaming for real-time agent communication.
"""

import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv, set_key

# Import from existing project
from mlx_use.agent.service import Agent
from mlx_use.agent.prompts import SystemPrompt
from mlx_use.controller.service import Controller

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class ChatSystemPrompt(SystemPrompt):
	"""System prompt optimized for chat interactions with macOS automation"""
	
	def important_rules(self) -> str:
		"""Chat-optimized rules that emphasize conversational responses"""
		text = """
1. RESPONSE FORMAT:
   You must ALWAYS respond with a valid JSON object that has EXACTLY two keys:
     {
     "current_state": {
       "evaluation_previous_goal": "Success|Failed|Unknown - Analyze if the user's request was completed",
       "memory": "What you've done and learned from this interaction", 
       "next_goal": "How to help the user next"
     },
     "action": [
       {
         "action_name": {
           // action parameters
         }
       }
     ]
   }

2. CHAT BEHAVIOR:
   - Use the "reply" action for conversational responses that don't need automation
   - Use macOS actions (open_app, click_element, etc.) when the user asks for specific tasks
   - Always be helpful and explain what you're doing
   - If you can't complete a task, explain why and suggest alternatives

3. ACTION SELECTION:
   - For simple questions/chat: Use "reply" action with your response
   - For automation requests: Use appropriate macOS actions (open_app, click_element, etc.)
   - For task completion: Use "done" action with final results
   - You can chain multiple actions, but prioritize clear communication

4. EXAMPLES:
   - User: "How are you?" → Use "reply" action
   - User: "Open Notes app" → Use "open_app" action then "reply" to confirm
   - User: "What's the weather?" → Use "reply" to explain you can't check weather directly
   - User: "Find my system info note" → Use "open_app" for Notes, then search actions
"""
		return text

	def get_user_prompt(self, task: str, action_descriptions: str, state: str, include_attributes: List[str], 
						max_error_length: int, last_result: Optional[list] = None, 
						step_info: Optional[any] = None) -> str:
		"""Chat-optimized user prompt"""
		
		prompt = f"""You are a helpful AI assistant for macOS automation. You can both have conversations and perform automation tasks.

AVAILABLE ACTIONS:
{action_descriptions}

CURRENT TASK: {task}

IMPORTANT BEHAVIORAL RULES:
{self.important_rules()}

CURRENT STATE:
{state if state else "Starting conversation - no app is currently active."}
"""

		if last_result:
			prompt += f"\nPREVIOUS ACTION RESULTS:\n"
			for result in last_result:
				if result.extracted_content:
					prompt += f"✅ {result.extracted_content}\n"
				if result.error:
					error = result.error[:max_error_length] if max_error_length > 0 else result.error
					prompt += f"❌ Error: {error}\n"

		prompt += f"""
TASK ANALYSIS:
- If this is a simple conversation/question, use the "reply" action
- If this requires macOS automation, use the appropriate actions
- Always communicate clearly about what you're doing

Remember: You can both chat naturally AND perform automation tasks. Choose the right approach for each user message.

Current date and time: {self.current_date}
Maximum actions per step: {self.max_actions_per_step}

Respond with valid JSON following the exact format specified above."""

		return prompt

# Import the exact same models from the Gradio app
LLM_MODELS = {
    "OpenAI": [
        # Latest 2025 models
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
        "o3",
        "o4-mini", 
        "o3-pro",
        "o4-mini-high",
        # Existing models
        "gpt-4o",
        "gpt-4o-mini",
        "o3-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo"
    ],
    "Anthropic": [
        # Claude 4 models (2025)
        "claude-4-opus",
        "claude-4-sonnet", 
        # Claude 3.5 models
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620",
        "claude-3-5-haiku-20241022",
        # Claude 3 models
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
        # Legacy naming
        "claude-3-7-sonnet-20250219"
    ],
    "Google": [
        # Gemini 2.5 models (2025)
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-preview",
        # Gemini 2.0 models
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash-live",
        # Gemini 1.5 models
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.5-flash-002"
    ],
    "DeepSeek": [
        # Latest DeepSeek models (2025)
        "deepseek-chat",        # Points to V3-0324
        "deepseek-reasoner",    # Points to R1-0528
        "deepseek-v3",
        "deepseek-r1"
    ],
    "OpenRouter": [
        # Tool-capable models (prioritized for agent use)
        "openai/gpt-4o",
        "openai/gpt-4o-mini", 
        "openai/gpt-4-turbo",
        "anthropic/claude-3.5-sonnet",
        "anthropic/claude-3-opus",
        "anthropic/claude-3-sonnet",
        "google/gemini-1.5-pro",
        "google/gemini-1.5-flash",
        "google/gemini-2.0-flash-exp",
        # Free models with tool support
        "openai/gpt-3.5-turbo:free",
        "meta-llama/llama-3.1-8b-instruct:free",
        "google/gemma-2-9b-it:free",
        # Other popular models
        "deepseek/deepseek-chat",
        "meta-llama/llama-3.3-70b-instruct",
        "microsoft/phi-3-mini-128k-instruct:free"
    ],
    "Ollama": [
        # Will be populated dynamically from local Ollama instance
        # Tool-calling capable models prioritized
        "llama3.1:latest",
        "granite3.3:8b",
        "granite3.2-vision:latest", 
        "qwen3:8b",
        "qwen2.5-coder:7b",
        "mistral-nemo",
        "command-r-plus",
        # Fallback models
        "llama3.2",
        "deepseek-r1"
    ],
    "LM Studio": [
        # Will be populated dynamically from local LM Studio instance
        "Available models will be detected from local LM Studio server"
    ]
}

# Automation Templates (replacing quick actions)
AUTOMATION_TEMPLATES = {
    "Quick Tasks": [
        {"name": "Play 'Tiny Dancer'", "prompt": "Play 'Tiny Dancer' by Elton John"},
        {"name": "Making Siri Speak", "prompt": "say Shame on YOU! i'm not Siri! but if you want to make me speak, just prompt the agent with 'say' followed by what you want."},
        {"name": "Show My Location", "prompt": "Open Maps and show my current location"},
        {"name": "Mail", "prompt": "Open Mail and quit"},
        {"name": "Calculator 5 x 4", "prompt": "Open Calculator, click the '5' button, then the multiply button, then the '4' button, then the equals button, and return the result"},
        {"name": "Create Meeting Note", "prompt": "Open Notes, click the 'New Note' button, type 'Meeting Notes' at the top as a title field, then type the text: 'Discuss project timeline'"}
    ],
    "Multi-Step Workflows": [
        {"name": "Organize Files and Message", "prompt": "Open Finder, go to the Documents folder, create a new folder called 'Projects', move all .txt files from Documents into 'Projects'. Then, open Messages, start a new conversation with 'team@example.com', type 'Projects are organized in Documents/Projects', and send it."},
        {"name": "Plan Meeting with Map", "prompt": "Open Maps, search for 'cafes near Union Square, San Francisco', select the first result, copy its address. Then, open Calendar, create an event titled 'Team Sync' for tomorrow at 9 AM, paste the address into the location field, and invite 'team@example.com'."},
        {"name": "Create Simple Presentation", "prompt": "Open Keynote, create a new presentation with the 'White' theme, add a title slide with 'Team Update', add a second slide with a bullet list: 'Goal 1: Finish report', 'Goal 2: Plan Q4'. Save it as 'update.key' on the Desktop."},
        {"name": "Screenshot and Share", "prompt": "Take a screenshot of the current screen, save it to Desktop as 'screenshot.png', then open Mail, create a new email to 'support@example.com' with subject 'Screen Capture', attach the screenshot, and send it."},
        {"name": "System Info Report", "prompt": "Open Terminal, run 'system_profiler SPHardwareDataType', copy the output, then open TextEdit, create a new document, paste the system information, and save it as 'system_info.txt' on Desktop."}
    ],
    "Productivity Automations": [
        {"name": "Daily Standup Prep", "prompt": "Open Calendar and check today's events, then open Notes, create a new note titled 'Daily Standup - [Today's Date]', list today's meetings as bullet points, then open Slack and set status to 'In meetings today'."},
        {"name": "Clean Downloads Folder", "prompt": "Open Finder, navigate to Downloads folder, select all files older than 7 days, move them to a new folder called 'Old Downloads', then empty the Trash."},
        {"name": "Weekly Report Setup", "prompt": "Open Numbers, create a new spreadsheet with columns: 'Task', 'Status', 'Notes', 'Due Date'. Add 5 sample rows with placeholder data, then save as 'Weekly Report - [This Week]' on Desktop."},
        {"name": "Focus Mode Setup", "prompt": "Turn on Do Not Disturb, close all applications except the current one, open Music and play a focus playlist, then open a timer for 25 minutes."},
        {"name": "End of Day Cleanup", "prompt": "Save all open documents, close all applications except Finder, empty Trash, run a system cleanup, then set computer to sleep mode."}
    ]
}

def get_llm(provider: str, model: str, api_key: Optional[str] = None):
	"""Get LLM instance for the specified provider and model"""
	try:
		if provider == "OpenAI":
			from langchain_openai import ChatOpenAI
			return ChatOpenAI(model=model, api_key=api_key or os.getenv("OPENAI_API_KEY"))
		elif provider == "Anthropic":
			from langchain_anthropic import ChatAnthropic
			return ChatAnthropic(model=model, api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
		elif provider == "Google":
			from langchain_google_genai import ChatGoogleGenerativeAI
			return ChatGoogleGenerativeAI(model=model, google_api_key=api_key or os.getenv("GOOGLE_API_KEY"))
		elif provider == "DeepSeek":
			from langchain_openai import ChatOpenAI
			return ChatOpenAI(
				model=model,
				api_key=api_key or os.getenv("DEEPSEEK_API_KEY"),
				base_url="https://api.deepseek.com"
			)
		elif provider == "OpenRouter":
			from langchain_openai import ChatOpenAI
			# OpenRouter uses OpenAI-compatible API with special headers
			if not (api_key or os.getenv("OPENROUTER_API_KEY")):
				raise ValueError("OpenRouter requires an API key")
			
			# For OpenRouter, ensure we use models that support tool use
			# Add provider routing for tool-capable models
			model_with_routing = model
			if not any(provider_prefix in model for provider_prefix in ["openai/", "anthropic/", "google/"]):
				# If no provider prefix, add routing to ensure tool use support
				if "gpt" in model.lower():
					model_with_routing = f"openai/{model}"
				elif "claude" in model.lower():
					model_with_routing = f"anthropic/{model}"
				elif "gemini" in model.lower():
					model_with_routing = f"google/{model}"
			
			return ChatOpenAI(
				model=model_with_routing,
				api_key=api_key or os.getenv("OPENROUTER_API_KEY"),
				base_url="https://openrouter.ai/api/v1",
				default_headers={
					"HTTP-Referer": "https://macOS-use-app.local",
					"X-Title": "macOS-use Agent"
				}
			)
		elif provider == "Ollama":
			try:
				from langchain_ollama import ChatOllama
				return ChatOllama(
					model=model,
					base_url="http://localhost:11434",
					temperature=0.1
				)
			except ImportError:
				# Fallback to OpenAI-compatible endpoint if langchain_ollama not available
				from langchain_openai import ChatOpenAI
				return ChatOpenAI(
					model=model,
					api_key="ollama",  # Dummy key for compatibility
					base_url="http://localhost:11434/v1"
				)
		elif provider == "LM Studio":
			from langchain_openai import ChatOpenAI
			return ChatOpenAI(
				model=model,
				api_key="lm-studio",  # Dummy key for compatibility
				base_url="http://localhost:1234/v1"
			)
		else:
			raise ValueError(f"Unsupported provider: {provider}")
	except ImportError as e:
		raise ValueError(f"Required package not installed for {provider}: {e}")

def get_available_models(provider: str) -> List[str]:
	"""Get available models for a provider, including dynamic detection for local providers and OpenRouter"""
	import requests
	
	# Dynamic model detection for OpenRouter
	if provider == "OpenRouter":
		try:
			api_key = os.getenv("OPENROUTER_API_KEY")
			if api_key:
				print("🔄 Fetching live OpenRouter models...")
				headers = {
					"Authorization": f"Bearer {api_key}",
					"HTTP-Referer": "https://macOS-use-app.local",
					"X-Title": "macOS-use Agent",
					"Content-Type": "application/json"
				}
				response = requests.get("https://openrouter.ai/api/v1/models", 
									  headers=headers, timeout=10)
				if response.status_code == 200:
					data = response.json()
					models = []
					tool_capable_models = []
					
					for model in data.get("data", []):
						model_id = model.get("id", "")
						supports_tools = model.get("architecture", {}).get("supports_tools", False)
						
						if model_id:
							models.append(model_id)
							# Prioritize models that explicitly support tools or are from known tool-capable providers
							if (supports_tools or 
								any(provider in model_id for provider in ["openai/", "anthropic/", "google/"]) or
								any(model_name in model_id.lower() for model_name in ["gpt", "claude", "gemini"])):
								tool_capable_models.append(model_id)
					
					if models:
						# Prioritize tool-capable models, then separate free/paid
						other_models = [m for m in models if m not in tool_capable_models]
						
						# Within each group, prioritize free models
						tool_free = [m for m in tool_capable_models if ":free" in m.lower()]
						tool_paid = [m for m in tool_capable_models if ":free" not in m.lower()]
						other_free = [m for m in other_models if ":free" in m.lower()]
						other_paid = [m for m in other_models if ":free" not in m.lower()]
						
						final_models = tool_free + tool_paid + other_free + other_paid
						
						print(f"✅ Fetched {len(models)} OpenRouter models ({len(tool_capable_models)} tool-capable, {len([m for m in models if ':free' in m.lower()])} free)")
						return final_models
					else:
						print("⚠️ No models returned from OpenRouter API, using static list")
						return LLM_MODELS.get("OpenRouter", [])
				else:
					print(f"❌ OpenRouter API error (status {response.status_code}), using static list")
					return LLM_MODELS.get("OpenRouter", [])
			else:
				print("ℹ️ No OpenRouter API key found, using static model list")
				return LLM_MODELS.get("OpenRouter", [])
		except Exception as e:
			print(f"❌ Error fetching OpenRouter models: {e}, using static list")
			return LLM_MODELS.get("OpenRouter", [])
	
	# Return static models for other cloud providers (except for dynamic providers)
	if provider in LLM_MODELS and provider not in ["Ollama", "LM Studio"]:
		return LLM_MODELS[provider]
	
	# Dynamic model detection for Ollama
	if provider == "Ollama":
		try:
			response = requests.get("http://localhost:11434/api/tags", timeout=5)
			if response.status_code == 200:
				data = response.json()
				models = [model["name"] for model in data.get("models", [])]
				if models:
					return models
				else:
					return ["No models installed - Run 'ollama pull <model>' to install models"]
		except Exception as e:
			return ["Ollama not running - Start Ollama service first"]
	
	# Dynamic model detection for LM Studio
	elif provider == "LM Studio":
		try:
			response = requests.get("http://localhost:1234/v1/models", timeout=5)
			if response.status_code == 200:
				data = response.json()
				models = [model["id"] for model in data.get("data", [])]
				if models:
					return models
				else:
					return ["No models loaded - Load a model in LM Studio first"]
		except Exception as e:
			return ["LM Studio not running - Start LM Studio server first"]
	
	return LLM_MODELS.get(provider, [])

def check_provider_availability(provider: str) -> bool:
	"""Check if a provider is available and properly configured"""
	import requests
	
	# Check API key for providers that require it
	key_map = {
		"OpenAI": "OPENAI_API_KEY",
		"Anthropic": "ANTHROPIC_API_KEY", 
		"Google": "GOOGLE_API_KEY",
		"DeepSeek": "DEEPSEEK_API_KEY",
		"OpenRouter": "OPENROUTER_API_KEY"
	}
	
	if provider in key_map:
		api_key = os.getenv(key_map[provider])
		if not api_key:
			return False
		
		# Special check for OpenRouter - test actual API connectivity
		if provider == "OpenRouter":
			try:
				headers = {
					"Authorization": f"Bearer {api_key}",
					"HTTP-Referer": "https://macOS-use-app.local",
					"X-Title": "macOS-use Agent",
					"Content-Type": "application/json"
				}
				response = requests.get("https://openrouter.ai/api/v1/models", 
									  headers=headers, timeout=10)
				return response.status_code == 200
			except Exception as e:
				print(f"OpenRouter availability check failed: {e}")
				return False
	
	# Check local providers (Ollama, LM Studio)
	elif provider == "Ollama":
		try:
			# Use Ollama's native API endpoint
			response = requests.get("http://localhost:11434/api/tags", timeout=5)
			return response.status_code == 200
		except:
			return False
	elif provider == "LM Studio":
		try:
			# Use LM Studio's OpenAI-compatible endpoint
			response = requests.get("http://localhost:1234/v1/models", timeout=5)
			return response.status_code == 200
		except:
			return False
	
	return True

# Standalone App class
class WebInterfaceApp:
	def __init__(self):
		self.sessions_dir = Path.home() / ".macOS-use-web-sessions"
		self.sessions_dir.mkdir(exist_ok=True)
	
	def get_current_timestamp(self):
		return datetime.now().isoformat()
	
	def save_api_key_to_env(self, provider: str, api_key: str):
		"""Save API key to environment"""
		if not api_key:
			return
			
		key_map = {
			"OpenAI": "OPENAI_API_KEY",
			"Anthropic": "ANTHROPIC_API_KEY",
			"Google": "GOOGLE_API_KEY", 
			"DeepSeek": "DEEPSEEK_API_KEY",
			"OpenRouter": "OPENROUTER_API_KEY"
		}
		
		env_var = key_map.get(provider)
		if env_var:
			os.environ[env_var] = api_key
			# Also save to .env file
			env_file = Path.cwd() / ".env"
			if env_file.exists():
				set_key(str(env_file), env_var, api_key)

	async def get_llm_response(self, system_message: str, user_message: str, 
							   llm_provider: str, llm_model: str) -> str:
		"""Get response from LLM"""
		try:
			llm = get_llm(llm_provider, llm_model)
			
			from langchain_core.messages import SystemMessage, HumanMessage
			messages = [
				SystemMessage(content=system_message),
				HumanMessage(content=user_message)
			]
			
			response = await llm.ainvoke(messages)
			return response.content
		except Exception as e:
			raise Exception(f"LLM Error: {str(e)}")

# Global app instance
web_app = None

@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Lifecycle manager for FastAPI app"""
	global web_app
	web_app = WebInterfaceApp()
	yield
	# Cleanup if needed

app = FastAPI(
	title="macOS-use Web Interface API",
	description="Elegant JavaScript interface backend for macOS automation",
	version="1.0.0",
	lifespan=lifespan
)

# CORS middleware
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # In production, specify exact origins
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Pydantic models for API
class AgentTaskRequest(BaseModel):
	task: str
	max_steps: int = 100
	max_actions: int = 10
	llm_provider: str = "OpenAI"
	llm_model: str = "gpt-4"
	api_key: Optional[str] = None

class ChatMessage(BaseModel):
	message: str
	llm_provider: str = "OpenAI"
	llm_model: str = "gpt-4"
	api_key: Optional[str] = None

class SessionSaveRequest(BaseModel):
	session_name: str
	conversation_history: List[Dict]

class ProviderTestRequest(BaseModel):
	provider: str
	model: str
	api_key: Optional[str] = None

# Connection manager for WebSocket
class ConnectionManager:
	def __init__(self):
		self.active_connections: Dict[str, WebSocket] = {}
		self.agent_sessions: Dict[str, Agent] = {}
		self.chat_agents: Dict[str, Agent] = {}  # Track chat agents separately

	async def connect(self, websocket: WebSocket, client_id: str):
		await websocket.accept()
		self.active_connections[client_id] = websocket

	def disconnect(self, client_id: str):
		if client_id in self.active_connections:
			del self.active_connections[client_id]
		if client_id in self.agent_sessions:
			del self.agent_sessions[client_id]
		if client_id in self.chat_agents:
			del self.chat_agents[client_id]

	async def send_message(self, message: dict, client_id: str):
		if client_id in self.active_connections:
			await self.active_connections[client_id].send_text(json.dumps(message))

	async def send_stream_update(self, data: dict, client_id: str):
		"""Send streaming update to client"""
		await self.send_message({
			"type": "stream_update",
			"data": data
		}, client_id)

manager = ConnectionManager()

# REST API Endpoints

@app.get("/api/automation-templates")
async def get_automation_templates():
	"""Get available automation templates"""
	try:
		return JSONResponse(content=AUTOMATION_TEMPLATES)
	except Exception as e:
		logger.error(f"Error getting automation templates: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/providers")
async def get_providers():
	"""Get available LLM providers and their models"""
	try:
		providers = {}
		provider_list = ["OpenAI", "Anthropic", "Google", "DeepSeek", "OpenRouter", "Ollama", "LM Studio"]
		
		for provider in provider_list:
			models = get_available_models(provider)
			is_available = check_provider_availability(provider)
			providers[provider] = {
				"models": models,
				"available": is_available,
				"api_key_required": provider not in ["Ollama", "LM Studio"]
			}
		
		return JSONResponse(content=providers)
	except Exception as e:
		logger.error(f"Error getting providers: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/providers/test")
async def test_provider(request: ProviderTestRequest):
	"""Test connection to a specific provider"""
	try:
		# Check if provider is available
		if not check_provider_availability(request.provider):
			return JSONResponse(content={
				"success": False,
				"message": "Provider not available. Check API key or local service."
			})
		
		# Try to initialize the LLM
		if not request.api_key and request.provider in ["OpenAI", "Anthropic", "Google", "DeepSeek", "OpenRouter"]:
			return JSONResponse(content={
				"success": False,
				"message": "API key required for this provider"
			})
		
		llm = get_llm(request.provider, request.model, request.api_key)
		
		# Test with a simple message
		test_response = llm.invoke("Hello, this is a connection test. Please respond with 'Test successful'.")
		
		if "test successful" in test_response.content.lower():
			message = "Connection successful! Provider is working correctly."
		else:
			message = "Connection established. Provider responded."
			
		return JSONResponse(content={
			"success": True,
			"message": message
		})
		
	except Exception as e:
		error_msg = str(e)
		if "rate limit" in error_msg.lower():
			message = "Rate limit reached. Connection works but try again later."
		elif "api key" in error_msg.lower():
			message = "Invalid API key. Please check your key."
		elif "auth" in error_msg.lower():
			message = "Authentication failed. Check API key."
		else:
			message = f"Connection failed: {error_msg}"
			
		return JSONResponse(content={
			"success": False,
			"message": message
		})

@app.get("/api/sessions")
async def get_sessions():
	"""Get list of saved sessions"""
	try:
		session_dir = web_app.sessions_dir
		if not session_dir.exists():
			return JSONResponse(content=[])
		
		sessions = []
		for session_file in session_dir.glob("*.json"):
			try:
				with open(session_file, 'r') as f:
					session_data = json.load(f)
					sessions.append({
						"name": session_file.stem,
						"timestamp": session_data.get("timestamp", ""),
						"message_count": len(session_data.get("messages", [])),
						"success_count": session_data.get("metadata", {}).get("success_count", 0),
						"failure_count": session_data.get("metadata", {}).get("failure_count", 0)
					})
			except Exception as e:
				logger.error(f"Error reading session {session_file}: {e}")
		
		return JSONResponse(content=sessions)
	except Exception as e:
		logger.error(f"Error getting sessions: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_name}")
async def get_session(session_name: str):
	"""Get specific session data"""
	try:
		session_file = web_app.sessions_dir / f"{session_name}.json"
		
		if not session_file.exists():
			raise HTTPException(status_code=404, detail="Session not found")
		
		with open(session_file, 'r') as f:
			session_data = json.load(f)
		
		return JSONResponse(content=session_data)
	except Exception as e:
		logger.error(f"Error getting session {session_name}: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions")
async def save_session(request: SessionSaveRequest):
	"""Save a conversation session"""
	try:
		session_file = web_app.sessions_dir / f"{request.session_name}.json"
		
		# Calculate metadata
		success_count = len([msg for msg in request.conversation_history if msg.get("success", False)])
		failure_count = len([msg for msg in request.conversation_history if msg.get("success") == False])
		
		session_data = {
			"timestamp": web_app.get_current_timestamp(),
			"messages": request.conversation_history,
			"metadata": {
				"success_count": success_count,
				"failure_count": failure_count,
				"total_messages": len(request.conversation_history)
			}
		}
		
		with open(session_file, 'w') as f:
			json.dump(session_data, f, indent=2)
		
		return JSONResponse(content={"success": True, "message": "Session saved successfully"})
	except Exception as e:
		logger.error(f"Error saving session: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{session_name}")
async def delete_session(session_name: str):
	"""Delete a session"""
	try:
		session_file = web_app.sessions_dir / f"{session_name}.json"
		
		if session_file.exists():
			session_file.unlink()
			return JSONResponse(content={"success": True, "message": "Session deleted successfully"})
		else:
			raise HTTPException(status_code=404, detail="Session not found")
	except Exception as e:
		logger.error(f"Error deleting session: {e}")
		raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/send")
async def send_chat_message(request: ChatMessage):
	"""Send a chat message using the full agent system"""
	try:
		# Save API key if provided
		if request.api_key:
			web_app.save_api_key_to_env(request.llm_provider, request.api_key)
		
		# Get LLM instance
		llm = get_llm(request.llm_provider, request.llm_model, request.api_key)
		
		# Create agent with chat-optimized system prompt
		agent = Agent(
			task=f"User message: {request.message}",
			llm=llm,
			controller=Controller(),
			max_actions_per_step=3,  # Allow multiple actions for complex requests
			system_prompt_class=ChatSystemPrompt  # We'll create this
		)
		
		# Run just one step to get the response
		await agent.step()
		
		# Extract the response from the agent's last result
		if agent._last_result and len(agent._last_result) > 0:
			last_result = agent._last_result[-1]
			response = last_result.extracted_content or "I completed your request."
			success = not bool(last_result.error)
		else:
			response = "I wasn't able to process your request properly."
			success = False
		
		return JSONResponse(content={
			"response": response,
			"success": success
		})
	except Exception as e:
		logger.error(f"Error in chat: {e}")
		return JSONResponse(content={
			"response": f"Sorry, I encountered an error: {str(e)}",
			"success": False
		})

# WebSocket endpoint for real-time agent execution
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
	await manager.connect(websocket, client_id)
	try:
		while True:
			data = await websocket.receive_text()
			message = json.loads(data)
			
			if message["type"] == "agent_task":
				await handle_agent_task(message["data"], client_id)
			elif message["type"] == "chat_message":
				await handle_chat_message(message["data"], client_id)
			elif message["type"] == "stop_agent":
				await handle_stop_agent(client_id)
			elif message["type"] == "stop_chat":
				await handle_stop_chat(client_id)
			elif message["type"] == "ping":
				await manager.send_message({"type": "pong"}, client_id)
				
	except WebSocketDisconnect:
		manager.disconnect(client_id)

async def handle_agent_task(task_data: dict, client_id: str):
	"""Handle agent task execution via WebSocket"""
	try:
		# Extract task parameters
		task = task_data["task"]
		max_steps = task_data.get("max_steps", 100)
		max_actions = task_data.get("max_actions", 10)
		llm_provider = task_data.get("llm_provider", "OpenAI")
		llm_model = task_data.get("llm_model", "gpt-4")
		api_key = task_data.get("api_key")
		
		# Save API key if provided
		if api_key:
			web_app.save_api_key_to_env(llm_provider, api_key)
		
		# Send start message
		await manager.send_stream_update({
			"status": "starting",
			"message": f"Starting task: {task}",
			"step": 0,
			"max_steps": max_steps
		}, client_id)
		
		# Get LLM instance
		llm = get_llm(llm_provider, llm_model, api_key)
		
		# Create agent
		agent = Agent(
			task=task,
			llm=llm,
			controller=Controller(),
			max_actions_per_step=max_actions
		)
		
		# Store agent for potential stopping
		manager.agent_sessions[client_id] = agent
		
		# Define step callback for streaming updates
		def step_callback(state: str, output, step: int):
			asyncio.create_task(manager.send_stream_update({
				"status": "running",
				"step": step,
				"max_steps": max_steps,
				"state": state,
				"agent_output": output.model_dump() if output else None,
				"message": f"Step {step}: {output.current_state.next_goal if output else 'Processing...'}"
			}, client_id))
		
		def done_callback(history):
			asyncio.create_task(manager.send_stream_update({
				"status": "completed",
				"message": "Task completed successfully!",
				"final_result": history.history[-1].result[-1].extracted_content if history.history and history.history[-1].result else "Task completed",
				"step_count": len(history.history)
			}, client_id))
		
		# Set callbacks
		agent.register_new_step_callback = step_callback
		agent.register_done_callback = done_callback
		
		# Run agent
		history = await agent.run(max_steps=max_steps)
		
		# Send completion message
		if history.is_done():
			await manager.send_stream_update({
				"status": "completed",
				"message": "Task completed successfully!",
				"final_result": history.history[-1].result[-1].extracted_content if history.history and history.history[-1].result else "Task completed",
				"step_count": len(history.history)
			}, client_id)
		else:
			await manager.send_stream_update({
				"status": "failed",
				"message": "Task failed to complete within maximum steps",
				"step_count": len(history.history)
			}, client_id)
		
	except Exception as e:
		logger.error(f"Error in agent task: {e}")
		await manager.send_stream_update({
			"status": "error",
			"message": f"Error: {str(e)}"
		}, client_id)
	finally:
		# Clean up agent session
		if client_id in manager.agent_sessions:
			del manager.agent_sessions[client_id]

async def handle_chat_message(message_data: dict, client_id: str):
	"""Handle chat message via WebSocket with streaming"""
	try:
		message = message_data["message"]
		llm_provider = message_data.get("llm_provider", "OpenAI")
		llm_model = message_data.get("llm_model", "gpt-4")
		api_key = message_data.get("api_key")
		
		# Save API key if provided
		if api_key:
			web_app.save_api_key_to_env(llm_provider, api_key)
		
		# Send start message
		await manager.send_message({
			"type": "chat_response",
			"data": {
				"status": "thinking",
				"message": "Processing your message..."
			}
		}, client_id)
		
		# Get LLM instance
		llm = get_llm(llm_provider, llm_model, api_key)
		
		# Create chat agent
		agent = Agent(
			task=f"User message: {message}",
			llm=llm,
			controller=Controller(),
			max_actions_per_step=3,
			system_prompt_class=ChatSystemPrompt
		)
		
		# Store agent for potential stopping
		manager.chat_agents[client_id] = agent
		
		# Run one step to get response
		await agent.step()
		
		# Extract response
		if agent._last_result and len(agent._last_result) > 0:
			last_result = agent._last_result[-1]
			response = last_result.extracted_content or "I completed your request."
			success = not bool(last_result.error)
		else:
			response = "I wasn't able to process your request properly."
			success = False
		
		# Send final response
		await manager.send_message({
			"type": "chat_response", 
			"data": {
				"status": "completed",
				"message": response,
				"success": success
			}
		}, client_id)
		
	except Exception as e:
		logger.error(f"Error in chat message: {e}")
		await manager.send_message({
			"type": "chat_response",
			"data": {
				"status": "error",
				"message": f"Error: {str(e)}",
				"success": False
			}
		}, client_id)
	finally:
		# Clean up chat agent session
		if client_id in manager.chat_agents:
			del manager.chat_agents[client_id]

async def handle_stop_agent(client_id: str):
	"""Stop running agent for client"""
	if client_id in manager.agent_sessions:
		agent = manager.agent_sessions[client_id]
		agent._stopped = True
		await manager.send_stream_update({
			"status": "stopped",
			"message": "Agent execution stopped by user"
		}, client_id)

async def handle_stop_chat(client_id: str):
	"""Stop running chat agent for client"""
	if client_id in manager.chat_agents:
		agent = manager.chat_agents[client_id]
		agent._stopped = True
		await manager.send_message({
			"type": "chat_response",
			"data": {
				"status": "stopped",
				"message": "Chat stopped by user",
				"success": False
			}
		}, client_id)

if __name__ == "__main__":
	import uvicorn
	uvicorn.run(app, host="0.0.0.0", port=8080)