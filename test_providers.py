#!/usr/bin/env python3
"""
Test script to verify all LLM providers work correctly
Run this to test your provider configurations before using the UI
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

def test_provider_imports():
    """Test that all provider modules can be imported"""
    print("🔧 Testing provider imports...")
    
    try:
        from gradio_app.src.models.llm_models import (
            LLM_MODELS, PROVIDER_CONFIGS, get_llm, 
            check_provider_availability, get_available_models
        )
        print("✅ All provider modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_provider_availability():
    """Test which providers are available"""
    print("\n🌐 Testing provider availability...")
    
    try:
        from gradio_app.src.models.llm_models import PROVIDER_CONFIGS, check_provider_availability
        
        available_providers = []
        for provider, config in PROVIDER_CONFIGS.items():
            is_available = check_provider_availability(provider)
            status = "✅" if is_available else "❌"
            auth_info = "API Key Required" if config.get("requires_auth") else "No Auth Needed"
            local_info = " (Local)" if config.get("local_provider") else ""
            
            print(f"  {status} {provider}{local_info} - {auth_info}")
            
            if is_available:
                available_providers.append(provider)
        
        print(f"\n📊 {len(available_providers)} providers available: {', '.join(available_providers)}")
        return available_providers
        
    except Exception as e:
        print(f"❌ Error checking availability: {e}")
        return []

def test_model_initialization(providers):
    """Test initializing models for available providers"""
    print("\n🤖 Testing model initialization...")
    
    try:
        from gradio_app.src.models.llm_models import get_llm, LLM_MODELS, PROVIDER_CONFIGS
        
        successful_inits = []
        
        for provider in providers:
            try:
                config = PROVIDER_CONFIGS.get(provider, {})
                models = LLM_MODELS.get(provider, [])
                
                if not models:
                    print(f"  ⚠️ {provider}: No models configured")
                    continue
                
                # Use first available model
                model = models[0]
                
                # Get API key if needed
                api_key = None
                if config.get("requires_auth"):
                    api_key_env = config.get("api_key_env")
                    if api_key_env:
                        api_key = os.getenv(api_key_env)
                        if not api_key:
                            print(f"  ⚠️ {provider}: No API key found in environment")
                            continue
                
                # Try to initialize
                llm = get_llm(provider, model, api_key)
                if llm:
                    print(f"  ✅ {provider}: {model} initialized successfully")
                    successful_inits.append((provider, model))
                else:
                    print(f"  ❌ {provider}: Failed to initialize {model}")
                    
            except Exception as e:
                print(f"  ❌ {provider}: Error - {e}")
        
        print(f"\n📊 {len(successful_inits)} models initialized successfully")
        return successful_inits
        
    except Exception as e:
        print(f"❌ Error testing initialization: {e}")
        return []

async def test_llm_responses(successful_inits):
    """Test actual LLM responses"""
    print("\n💬 Testing LLM responses...")
    
    try:
        from gradio_app.src.models.llm_models import get_llm, PROVIDER_CONFIGS
        
        test_message = "Hello! Please respond with exactly: 'Test successful'"
        
        for provider, model in successful_inits[:3]:  # Test first 3 to avoid rate limits
            try:
                config = PROVIDER_CONFIGS.get(provider, {})
                
                # Get API key if needed
                api_key = None
                if config.get("requires_auth"):
                    api_key_env = config.get("api_key_env")
                    if api_key_env:
                        api_key = os.getenv(api_key_env)
                
                # Initialize LLM
                llm = get_llm(provider, model, api_key)
                
                # Test response
                print(f"  🔄 Testing {provider}:{model}...")
                response = await asyncio.to_thread(llm.invoke, test_message)
                
                if response and hasattr(response, 'content'):
                    response_text = response.content.strip().lower()
                    if "test successful" in response_text:
                        print(f"  ✅ {provider}: Perfect response!")
                    else:
                        print(f"  ✅ {provider}: Responded (content: {response_text[:50]}...)")
                else:
                    print(f"  ⚠️ {provider}: Unexpected response format")
                    
            except Exception as e:
                error_msg = str(e).lower()
                if "rate limit" in error_msg:
                    print(f"  ⚠️ {provider}: Rate limited (connection works)")
                elif "api key" in error_msg or "auth" in error_msg:
                    print(f"  ❌ {provider}: Authentication failed")
                else:
                    print(f"  ❌ {provider}: Error - {e}")
    
    except Exception as e:
        print(f"❌ Error testing responses: {e}")

def print_setup_instructions():
    """Print setup instructions for missing providers"""
    print("\n📋 Setup Instructions:")
    print("=" * 50)
    
    instructions = {
        "OpenAI": "Set OPENAI_API_KEY in .env - Get key: https://platform.openai.com/api-keys",
        "Anthropic": "Set ANTHROPIC_API_KEY in .env - Get key: https://console.anthropic.com/account/keys", 
        "Google": "Set GEMINI_API_KEY in .env - Get key: https://console.cloud.google.com/apis/credentials",
        "DeepSeek": "Set DEEPSEEK_API_KEY in .env - Get key: https://platform.deepseek.com/api_keys",
        "OpenRouter": "Set OPENROUTER_API_KEY in .env - Get key: https://openrouter.ai/keys",
        "Ollama": "Install and start Ollama: https://ollama.ai/ (no API key needed)",
        "LM Studio": "Download and start LM Studio: https://lmstudio.ai/ (no API key needed)"
    }
    
    for provider, instruction in instructions.items():
        print(f"• {provider}: {instruction}")

async def main():
    print("🚀 macOS-use Provider Test Suite")
    print("=" * 60)
    
    # Test imports
    if not test_provider_imports():
        print("\n❌ Critical error: Cannot import provider modules")
        return
    
    # Test availability
    available_providers = test_provider_availability()
    if not available_providers:
        print("\n❌ No providers available. Please check your setup.")
        print_setup_instructions()
        return
    
    # Test initialization
    successful_inits = test_model_initialization(available_providers)
    if not successful_inits:
        print("\n❌ No models could be initialized.")
        print_setup_instructions()
        return
    
    # Test responses (optional, can be slow)
    print(f"\n❓ Test actual LLM responses? This may take time and use API credits.")
    try:
        response = input("Test responses? (y/N): ").strip().lower()
        if response == 'y':
            await test_llm_responses(successful_inits)
    except (KeyboardInterrupt, EOFError):
        print("\nSkipping response tests...")
    
    print("\n🎉 Testing complete!")
    print(f"✅ {len(successful_inits)} providers ready for use")
    print("\nYou can now use the Gradio UI or CLI with confidence!")

if __name__ == "__main__":
    asyncio.run(main())