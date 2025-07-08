from typing import Optional, Dict, List
from pydantic import SecretStr
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

# Comprehensive LLM model mappings for 2025
LLM_MODELS = {
    "OpenAI": [
        # Latest 2025 models
        "gpt-4.1-mini",
        "gpt-4.1",
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
        # Popular free models
        "meta-llama/llama-3.2-3b-instruct:free",
        "meta-llama/llama-3.1-8b-instruct:free", 
        "microsoft/phi-3-mini-128k-instruct:free",
        "google/gemma-2-9b-it:free",
        # Popular paid models
        "anthropic/claude-3.5-sonnet",
        "openai/gpt-4o",
        "google/gemini-2.0-flash-exp",
        "deepseek/deepseek-chat",
        "meta-llama/llama-3.3-70b-instruct",
        # Specialized variants
        "anthropic/claude-3.5-sonnet:beta",
        "openai/gpt-4o:extended",
        "google/gemini-2.0-flash-exp:online"
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

# Provider-specific model categories for better organization
MODEL_CATEGORIES = {
    "OpenAI": {
        "reasoning": ["o3", "o3-pro", "o4-mini", "o4-mini-high", "o3-mini"],
        "chat": ["gpt-4.1-mini", "gpt-4.1", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        "legacy": ["gpt-3.5-turbo"]
    },
    "Anthropic": {
        "claude_4": ["claude-4-opus", "claude-4-sonnet"],
        "claude_3_5": ["claude-3-5-sonnet-20241022", "claude-3-5-sonnet-20240620", "claude-3-5-haiku-20241022"],
        "claude_3": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
    },
    "Google": {
        "gemini_2_5": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-preview"],
        "gemini_2_0": ["gemini-2.0-flash-exp", "gemini-2.0-flash-live"],
        "gemini_1_5": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-flash-002"]
    },
    "DeepSeek": {
        "latest": ["deepseek-chat", "deepseek-reasoner"],
        "specific": ["deepseek-v3", "deepseek-r1"]
    }
}

# Provider endpoints and configurations
PROVIDER_CONFIGS = {
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "requires_auth": True,
        "openai_compatible": True
    },
    "Anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "api_key_env": "ANTHROPIC_API_KEY", 
        "requires_auth": True,
        "openai_compatible": False
    },
    "Google": {
        "base_url": "https://generativelanguage.googleapis.com/v1",
        "api_key_env": "GEMINI_API_KEY",
        "requires_auth": True,
        "openai_compatible": False
    },
    "DeepSeek": {
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "requires_auth": True,
        "openai_compatible": True
    },
    "OpenRouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "requires_auth": True,
        "openai_compatible": True,
        "free_models_available": True
    },
    "Ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key_env": None,
        "requires_auth": False,
        "openai_compatible": True,
        "local_provider": True,
        "default_port": 11434
    },
    "LM Studio": {
        "base_url": "http://localhost:1234/v1", 
        "api_key_env": None,
        "requires_auth": False,
        "openai_compatible": True,
        "local_provider": True,
        "default_port": 1234
    }
}

def get_llm(provider: str, model: str, api_key: str = None) -> Optional[object]:
    """Initialize LLM based on provider with support for all 2025 providers"""
    try:
        if provider == "OpenAI":
            return ChatOpenAI(model=model, api_key=SecretStr(api_key))
        
        elif provider == "Anthropic":
            return ChatAnthropic(model=model, api_key=SecretStr(api_key))
        
        elif provider == "Google":
            return ChatGoogleGenerativeAI(model=model, api_key=SecretStr(api_key))
        
        elif provider == "DeepSeek":
            # DeepSeek uses OpenAI-compatible API
            return ChatOpenAI(
                model=model,
                api_key=SecretStr(api_key),
                base_url="https://api.deepseek.com/v1"
            )
        
        elif provider == "OpenRouter":
            # OpenRouter uses OpenAI-compatible API with special headers
            if not api_key:
                raise ValueError("OpenRouter requires an API key")
            
            return ChatOpenAI(
                model=model,
                api_key=SecretStr(api_key),
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://FF-Terminal-app.local",
                    "X-Title": "FF-Terminal:Desktop_ver Agent",
                    "Content-Type": "application/json"
                },
                model_kwargs={
                    "stream": False
                }
            )
        
        elif provider == "Ollama":
            # Use native ChatOllama for better tool calling support
            try:
                from langchain_ollama import ChatOllama
                return ChatOllama(
                    model=model,
                    base_url="http://localhost:11434",
                    temperature=0.1
                )
            except ImportError:
                # Fallback to OpenAI-compatible endpoint if langchain_ollama not available
                print("⚠️ langchain_ollama not available, using OpenAI-compatible endpoint")
                return ChatOpenAI(
                    model=model,
                    api_key=SecretStr("ollama"),  # Dummy key for compatibility
                    base_url="http://localhost:11434/v1"
                )
        
        elif provider == "LM Studio":
            # LM Studio uses OpenAI-compatible API locally
            return ChatOpenAI(
                model=model,
                api_key=SecretStr("lm-studio"),  # Dummy key for compatibility
                base_url="http://localhost:1234/v1"
            )
        
        else:
            raise ValueError(f"Unsupported provider: {provider}")
            
    except Exception as e:
        raise ValueError(f"Failed to initialize {provider} LLM: {str(e)}")


def check_provider_availability(provider: str) -> bool:
    """Check if a provider is available and properly configured"""
    import os
    import requests
    
    config = PROVIDER_CONFIGS.get(provider)
    if not config:
        return False
    
    # Check API key for providers that require it
    if config.get("requires_auth") and config.get("api_key_env"):
        api_key = os.getenv(config["api_key_env"])
        if not api_key:
            return False
        
        # Special check for OpenRouter - test actual API connectivity
        if provider == "OpenRouter":
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://FF-Terminal-app.local",
                    "X-Title": "FF-Terminal:Desktop_ver Agent",
                    "Content-Type": "application/json"
                }
                response = requests.get("https://openrouter.ai/api/v1/models", 
                                      headers=headers, timeout=10)
                return response.status_code == 200
            except Exception as e:
                print(f"OpenRouter availability check failed: {e}")
                return False
    
    # Check local providers (Ollama, LM Studio)
    if config.get("local_provider"):
        try:
            if provider == "Ollama":
                # Use Ollama's native API endpoint
                response = requests.get("http://localhost:11434/api/tags", timeout=5)
                return response.status_code == 200
            elif provider == "LM Studio":
                # Use LM Studio's OpenAI-compatible endpoint
                response = requests.get("http://localhost:1234/v1/models", timeout=5)
                return response.status_code == 200
        except:
            return False
    
    return True


def get_available_models(provider: str) -> List[str]:
    """Get available models for a provider, including dynamic detection for local providers and OpenRouter"""
    import os
    import requests
    
    # Dynamic model detection for OpenRouter
    if provider == "OpenRouter":
        try:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if api_key:
                print("🔄 Fetching live OpenRouter models...")
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://FF-Terminal-app.local",
                    "X-Title": "FF-Terminal:Desktop_ver Agent",
                    "Content-Type": "application/json"
                }
                response = requests.get("https://openrouter.ai/api/v1/models", 
                                      headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    models = []
                    for model in data.get("data", []):
                        model_id = model.get("id", "")
                        if model_id:
                            models.append(model_id)
                    
                    if models:
                        # Sort models and prioritize free models
                        free_models = [m for m in models if ":free" in m.lower()]
                        paid_models = [m for m in models if ":free" not in m.lower()]
                        
                        print(f"✅ Fetched {len(models)} OpenRouter models ({len(free_models)} free, {len(paid_models)} paid)")
                        return free_models + paid_models
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


def get_recommended_models_by_task(task_type: str = "general") -> Dict[str, List[str]]:
    """Get recommended models by task type"""
    recommendations = {
        "reasoning": {
            "OpenAI": ["o3", "o3-pro", "o4-mini"],
            "Anthropic": ["claude-4-opus", "claude-4-sonnet"],
            "DeepSeek": ["deepseek-reasoner", "deepseek-r1"],
            "Google": ["gemini-2.5-pro"]
        },
        "coding": {
            "OpenAI": ["o3", "gpt-4.1-mini", "gpt-4.1"],
            "Anthropic": ["claude-4-sonnet", "claude-3-5-sonnet-20241022"],
            "DeepSeek": ["deepseek-chat", "deepseek-v3"],
            "Google": ["gemini-2.5-flash"]
        },
        "chat": {
            "OpenAI": ["gpt-4.1-mini", "gpt-4.1", "gpt-4o"],
            "Anthropic": ["claude-4-sonnet", "claude-3-5-sonnet-20241022"],
            "Google": ["gemini-2.5-flash", "gemini-2.0-flash-exp"],
            "DeepSeek": ["deepseek-chat"]
        },
        "cost_effective": {
            "OpenAI": ["o4-mini", "gpt-4o-mini"],
            "OpenRouter": ["meta-llama/llama-3.2-3b-instruct:free", "google/gemma-2-9b-it:free"],
            "Ollama": ["llama3.2", "phi3"],
            "LM Studio": ["Local models"]
        }
    }
    
    return recommendations.get(task_type, recommendations["chat"])


def validate_model_for_provider(provider: str, model: str) -> bool:
    """Validate if a model is available for a specific provider"""
    available_models = get_available_models(provider)
    return model in available_models 