from typing import Optional, Dict, List
from pydantic import SecretStr
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

# Comprehensive LLM model mappings for 2025
LLM_MODELS = {
    "OpenAI": [
        # GPT-5 series (Latest 2025)
        "gpt-5",
        "gpt-5-mini",
        "gpt-5-nano",
        # Previous 2025 models
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
    ],
    "Z.AI": [
        # GLM-4.5 series (High-performance models)
        "GLM-4.5",
        "glm-4.5",
        # GLM-4.5-Air series (Faster, cost-effective models)
        "GLM-4.5-Air",
        "glm-4.5-air",
        # GLM-4.6 model (Latest model)
        "glm-4.6",
        "GLM-4.6",
        # Claude model compatibility (automatically mapped to GLM equivalents)
        "claude-3-5-sonnet-20241022",  # Maps to GLM-4.5
        "claude-3-5-haiku-20241022",   # Maps to GLM-4.5-Air
        "claude-3-opus",               # Maps to GLM-4.5
        "claude-3-sonnet",             # Maps to GLM-4.5
        "claude-3-haiku",              # Maps to GLM-4.5-Air
        # OpenAI model compatibility (automatically mapped)
        "gpt-4",                       # Maps to GLM-4.5
        "gpt-4-turbo",                 # Maps to GLM-4.5
        "gpt-3.5-turbo",               # Maps to GLM-4.5-Air
        "gpt-5-mini"                   # Maps to GLM-4.5-Air
    ]
}

# Provider-specific model categories for better organization
MODEL_CATEGORIES = {
    "OpenAI": {
        "gpt5": ["gpt-5", "gpt-5-mini", "gpt-5-nano"],
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
    },
    "Z.AI": {
        "glm_4_6": ["GLM-4.6", "glm-4.6"],
        "glm_4_5": ["GLM-4.5", "glm-4.5"],
        "glm_4_5_air": ["GLM-4.5-Air", "glm-4.5-air"],
        "claude_compatible": ["claude-3-5-sonnet-20241022", "claude-3-opus", "claude-3-sonnet"],
        "openai_compatible": ["gpt-4", "gpt-4-turbo"]
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
    },
    "Z.AI": {
        "base_url": "https://open.bigmodel.cn/api/anthropic/v1",
        "api_key_env": "ANTHROPIC_AUTH_TOKEN",
        "vision_api_key_env": "Z_AI_API_KEY",
        "requires_auth": True,
        "openai_compatible": False,
        "anthropic_compatible": True,
        "supports_vision": True,
        "supports_prompt_caching": True,
        "model_mapping": {
            "claude-3-5-sonnet-20241022": "GLM-4.6",
            "claude-3-5-haiku-20241022": "GLM-4.5-Air",
            "claude-3-opus": "GLM-4.6",
            "claude-3-sonnet": "GLM-4.6",
            "claude-3-haiku": "GLM-4.5-Air",
            "gpt-4": "GLM-4.6",
            "gpt-4-turbo": "GLM-4.6",
            "gpt-3.5-turbo": "GLM-4.5-Air",
            "gpt-5-mini": "GLM-4.5-Air",
            "glm-4.6": "GLM-4.6",
            "GLM-4.6": "GLM-4.6"
        }
    }
}

def get_llm(provider: str, model: str, api_key: str = None, reasoning_effort: str = "medium", verbosity: str = "medium") -> Optional[object]:
    """Initialize LLM based on provider with support for all 2025 providers including GPT-5 parameters
    
    Args:
        provider: The LLM provider name
        model: The specific model to use
        api_key: API key for authentication
        reasoning_effort: For reasoning models - "minimal", "medium" (default), "high"
        verbosity: For GPT-5 models - "low", "medium" (default), "high"
    """
    try:
        if provider == "OpenAI":
            # Handle GPT-5 models with special parameters
            if model.startswith("gpt-5"):
                # GPT-5 uses the new Responses API with different parameter structure
                model_kwargs = {}
                
                # Add reasoning effort for GPT-5
                if reasoning_effort != "medium":
                    model_kwargs["reasoning"] = {"effort": reasoning_effort}
                
                # Add verbosity for GPT-5
                if verbosity != "medium":
                    model_kwargs["text"] = {"verbosity": verbosity}
                
                return ChatOpenAI(
                    model=model,
                    api_key=SecretStr(api_key),
                    model_kwargs=model_kwargs
                )
            else:
                # Standard OpenAI models
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

        elif provider == "Z.AI":
            # Z.AI uses Anthropic-compatible API with GLM models
            import os

            # Get API key with fallback chain
            zai_api_key = api_key or os.getenv("ANTHROPIC_AUTH_TOKEN")
            if not zai_api_key:
                raise ValueError("Z.AI requires ANTHROPIC_AUTH_TOKEN environment variable or api_key parameter")

            # Get base URL with fallback
            base_url = os.getenv("ANTHROPIC_BASE_URL", "https://open.bigmodel.cn/api/anthropic/v1")

            # Map model names to GLM equivalents
            config = PROVIDER_CONFIGS["Z.AI"]
            model_mapping = config.get("model_mapping", {})
            zai_model = model_mapping.get(model, model)

            # Ensure we're using a valid GLM model name
            if not zai_model.startswith("GLM-"):
                # Default to GLM-4.6 for unmapped models
                zai_model = "GLM-4.6"

            return ChatAnthropic(
                model=zai_model,
                api_key=SecretStr(zai_api_key),
                base_url=base_url,
                default_headers={
                    "HTTP-Referer": "https://github.com/macOS-use/macOS-use",
                    "X-Title": "macOS-use Agent"
                }
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
    
    # Check Z.AI provider specifically
    if provider == "Z.AI":
        try:
            api_key = os.getenv("ANTHROPIC_AUTH_TOKEN")
            if not api_key:
                return False

            # Test Z.AI API connectivity
            base_url = os.getenv("ANTHROPIC_BASE_URL", "https://open.bigmodel.cn/api/anthropic/v1")
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            # Test with a simple messages endpoint call
            response = requests.get(f"{base_url}/models", headers=headers, timeout=10)
            # Z.AI may not have a models endpoint, so we'll consider any non-401 response as available
            return response.status_code != 401
        except Exception as e:
            print(f"Z.AI availability check failed: {e}")
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
            "OpenAI": ["gpt-5", "o3", "o3-pro", "o4-mini"],
            "Anthropic": ["claude-4-opus", "claude-4-sonnet"],
            "DeepSeek": ["deepseek-reasoner", "deepseek-r1"],
            "Google": ["gemini-2.5-pro"]
        },
        "coding": {
            "OpenAI": ["gpt-5", "o3", "gpt-4.1-mini", "gpt-4.1"],
            "Anthropic": ["claude-4-sonnet", "claude-3-5-sonnet-20241022"],
            "DeepSeek": ["deepseek-chat", "deepseek-v3"],
            "Google": ["gemini-2.5-flash"]
        },
        "chat": {
            "OpenAI": ["gpt-5", "gpt-5-mini", "gpt-4.1-mini", "gpt-4.1", "gpt-4o"],
            "Anthropic": ["claude-4-sonnet", "claude-3-5-sonnet-20241022"],
            "Google": ["gemini-2.5-flash", "gemini-2.0-flash-exp"],
            "DeepSeek": ["deepseek-chat"]
        },
        "cost_effective": {
            "OpenAI": ["gpt-5-nano", "gpt-5-mini", "o4-mini", "gpt-4o-mini"],
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


def get_gpt5_parameters() -> Dict[str, List[str]]:
    """Get available GPT-5 specific parameters"""
    return {
        "reasoning_effort": ["minimal", "medium", "high"],
        "verbosity": ["low", "medium", "high"]
    }


def is_gpt5_model(model: str) -> bool:
    """Check if a model is a GPT-5 variant that supports new parameters"""
    return model.startswith("gpt-5")


def get_model_capabilities(provider: str, model: str) -> Dict[str, any]:
    """Get capabilities and supported parameters for a specific model"""
    capabilities = {
        "supports_reasoning_effort": False,
        "supports_verbosity": False,
        "supports_tool_calling": True,  # Assume most models support this
        "context_length": None,
        "model_type": "chat"
    }
    
    if provider == "OpenAI":
        if is_gpt5_model(model):
            capabilities["supports_reasoning_effort"] = True
            capabilities["supports_verbosity"] = True
            capabilities["model_type"] = "advanced_reasoning"
            capabilities["context_length"] = 200000  # Estimated for GPT-5
        elif model.startswith(("o3", "o4")):
            capabilities["supports_reasoning_effort"] = True
            capabilities["model_type"] = "reasoning"
            capabilities["context_length"] = 128000
        elif model.startswith("gpt-4"):
            capabilities["context_length"] = 128000
        elif model.startswith("gpt-3.5"):
            capabilities["context_length"] = 16000

    elif provider == "Z.AI":
        if model.startswith("GLM-4.6"):
            capabilities["context_length"] = 128000
            capabilities["model_type"] = "glm"
            capabilities["model_class"] = "advanced"
        elif model.startswith("GLM-4.5"):
            capabilities["context_length"] = 128000
            capabilities["model_type"] = "glm"
            if model.endswith("-Air"):
                capabilities["model_class"] = "fast"
            else:
                capabilities["model_class"] = "standard"
        # Mapped models inherit GLM capabilities
        elif model in ["claude-3-5-sonnet-20241022", "claude-3-opus", "claude-3-sonnet"]:
            capabilities["context_length"] = 128000
            capabilities["model_type"] = "glm"
            capabilities["model_class"] = "advanced"
        elif model in ["claude-3-5-haiku-20241022", "claude-3-haiku", "gpt-3.5-turbo", "gpt-5-mini"]:
            capabilities["context_length"] = 128000
            capabilities["model_type"] = "glm"
            capabilities["model_class"] = "fast"

    return capabilities 