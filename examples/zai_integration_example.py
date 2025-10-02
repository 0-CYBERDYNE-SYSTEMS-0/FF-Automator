#!/usr/bin/env python3
"""
Z.AI Integration Example

This example demonstrates how to use the Z.AI provider for:
1. Text generation with GLM models
2. Vision analysis with MCP
3. Prompt caching for cost optimization
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the gradio_app src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "gradio_app" / "src"))

from models.llm_models import get_llm, get_available_models
from services.zai_prompt_caching import enable_zai_caching, track_zai_response_caching, get_zai_caching_stats
from tools.zai_vision_tools import capture_and_analyze


async def example_text_generation():
    """Example: Text generation with Z.AI GLM models"""
    print("🤖 Z.AI Text Generation Example")
    print("-" * 40)

    # Test different models
    models = ["GLM-4.5", "GLM-4.5-Air", "claude-3-5-sonnet-20241022"]
    prompt = "Explain quantum computing in simple terms."

    for model in models:
        try:
            print(f"\n📝 Testing model: {model}")

            # Initialize LLM
            llm = get_llm("Z.AI", model)

            # Generate response
            response = await llm.ainvoke(prompt)

            print(f"Response ({len(response.content)} chars):")
            print(response.content[:200] + "..." if len(response.content) > 200 else response.content)

        except Exception as e:
            print(f"❌ Error with {model}: {e}")


async def example_prompt_caching():
    """Example: Prompt caching for cost optimization"""
    print("\n💾 Z.AI Prompt Caching Example")
    print("-" * 40)

    # Create messages with caching
    messages = [
        {
            "role": "system",
            "content": "You are a helpful AI assistant with extensive knowledge about science, technology, and history. " * 50  # Long message for caching
        },
        {
            "role": "user",
            "content": "What is the difference between AI and machine learning?"
        }
    ]

    # Example tools
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Search the web for information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            }
        }
    ]

    try:
        # Enable caching
        cached_messages, cached_tools, cache_keys = enable_zai_caching(
            messages=messages,
            tools=tools,
            enable_caching=True
        )

        print(f"✅ Added cache control to {len(cache_keys)} items")
        print(f"📊 Cache stats: {get_zai_caching_stats()['cache_stats']}")

        # Use cached messages with LLM
        llm = get_llm("Z.AI", "GLM-4.5")
        response = await llm.ainvoke(cached_messages)

        # Track cache usage (would normally get from API response)
        mock_response = {
            "usage": {
                "cached_tokens": 1500,
                "cache_creation_tokens": 200,
                "cache_read_tokens": 1300
            }
        }

        cache_usage = track_zai_response_caching(mock_response, cache_keys)
        print(f"💰 Cache savings: {cache_usage['tokens_saved']} tokens, ${cache_usage['cost_saved']:.4f}")

    except Exception as e:
        print(f"❌ Caching example error: {e}")


async def example_vision_analysis():
    """Example: Vision analysis with Z.AI MCP"""
    print("\n👁️ Z.AI Vision Analysis Example")
    print("-" * 40)

    try:
        # Capture and analyze screen
        print("📸 Capturing screenshot...")
        result = await capture_and_analyze(
            analysis_type="ui_elements",
            custom_prompt="Identify all interactive elements and their coordinates"
        )

        if result:
            print("✅ Vision analysis completed!")
            print(f"📊 Analysis type: {result['analysis_type']}")
            print(f"📝 Analysis summary:")
            print(result['analysis'][:300] + "..." if len(result['analysis']) > 300 else result['analysis'])

            if result.get('processed_data'):
                processed = result['processed_data']
                if 'ui_elements' in processed:
                    print(f"🎯 Found {len(processed['ui_elements'])} UI elements")
        else:
            print("❌ Vision analysis failed")

    except Exception as e:
        print(f"❌ Vision example error: {e}")


async def example_model_compatibility():
    """Example: Model compatibility mappings"""
    print("\n🔄 Z.AI Model Compatibility Example")
    print("-" * 40)

    # Show available Z.AI models
    zai_models = get_available_models("Z.AI")
    print(f"📋 Available Z.AI models ({len(zai_models)}):")
    for model in zai_models[:10]:  # Show first 10
        print(f"  - {model}")
    if len(zai_models) > 10:
        print(f"  ... and {len(zai_models) - 10} more")

    # Test compatibility model names
    compatibility_examples = [
        ("claude-3-5-sonnet-20241022", "Maps to GLM-4.5"),
        ("claude-3-5-haiku-20241022", "Maps to GLM-4.5-Air"),
        ("gpt-4", "Maps to GLM-4.5"),
        ("gpt-3.5-turbo", "Maps to GLM-4.5-Air"),
    ]

    print("\n🔄 Compatibility mappings:")
    for model, description in compatibility_examples:
        try:
            llm = get_llm("Z.AI", model)
            actual_model = getattr(llm, 'model', 'Unknown')
            print(f"  {model} -> {actual_model} ({description})")
        except Exception as e:
            print(f"  {model} -> Error: {e}")


async def main():
    """Run all examples"""
    print("🚀 Z.AI Integration Examples")
    print("=" * 50)
    print("This demonstrates the Z.AI provider capabilities including:")
    print("- Text generation with GLM-4.5 and GLM-4.5-Air models")
    print("- Model compatibility mappings (Claude/OpenAI -> GLM)")
    print("- Prompt caching for cost optimization")
    print("- Vision analysis through MCP (if available)")
    print("=" * 50)

    # Check environment
    auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
    zai_api_key = os.getenv("Z_AI_API_KEY")

    if not auth_token:
        print("⚠️ ANTHROPIC_AUTH_TOKEN not set. Text generation may not work.")
    if not zai_api_key:
        print("⚠️ Z_AI_API_KEY not set. Vision analysis may not work.")

    print("\n🏃 Running examples...")

    try:
        await example_text_generation()
        await example_prompt_caching()
        await example_model_compatibility()
        await example_vision_analysis()  # This may fail if MCP server not available

        print("\n✅ Examples completed!")

    except KeyboardInterrupt:
        print("\n⏹️ Examples interrupted")
    except Exception as e:
        print(f"\n❌ Example error: {e}")


if __name__ == "__main__":
    # Load environment variables from .env file if it exists
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

    asyncio.run(main())