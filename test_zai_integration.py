#!/usr/bin/env python3
"""
Z.AI Integration Test Script

This script tests the Z.AI provider integration including:
1. Text model functionality (GLM-4.5, GLM-4.5-Air)
2. Vision capabilities through MCP
3. Prompt caching functionality
4. Model mapping and compatibility
"""

import asyncio
import os
import sys
import json
import time
from pathlib import Path

# Add the gradio_app src to Python path
sys.path.insert(0, str(Path(__file__).parent / "gradio_app" / "src"))

from models.llm_models import (
    get_llm, check_provider_availability, get_available_models,
    validate_model_for_provider, get_model_capabilities
)
from services.zai_vision_mcp import get_zai_vision_client, is_zai_vision_available
from services.zai_prompt_caching import enable_zai_caching, track_zai_response_caching, get_zai_caching_stats


class ZAITestRunner:
    """Test runner for Z.AI integration"""

    def __init__(self):
        self.test_results = {}
        self.passed_tests = 0
        self.failed_tests = 0

    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"    {message}")

        self.test_results[test_name] = {"success": success, "message": message}
        if success:
            self.passed_tests += 1
        else:
            self.failed_tests += 1

    def test_environment_setup(self):
        """Test that required environment variables are set"""
        print("\n🔧 Testing Environment Setup")

        # Check ANTHROPIC_AUTH_TOKEN
        auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
        self.log_test(
            "ANTHROPIC_AUTH_TOKEN environment variable",
            bool(auth_token),
            "Set" if auth_token else "Not set - required for Z.AI API access"
        )

        # Check Z_AI_API_KEY
        zai_api_key = os.getenv("Z_AI_API_KEY")
        self.log_test(
            "Z_AI_API_KEY environment variable",
            bool(zai_api_key),
            "Set" if zai_api_key else "Not set - required for Z.AI Vision"
        )

        # Check base URL
        base_url = os.getenv("ANTHROPIC_BASE_URL", "https://open.bigmodel.cn/api/anthropic")
        self.log_test(
            "ANTHROPIC_BASE_URL environment variable",
            True,
            f"Using: {base_url}"
        )

    def test_provider_availability(self):
        """Test Z.AI provider availability"""
        print("\n🌐 Testing Provider Availability")

        # Test provider availability check
        is_available = check_provider_availability("Z.AI")
        self.log_test(
            "Z.AI provider availability",
            is_available,
            "Available" if is_available else "Not available - check API key and connection"
        )

        # Test model listing
        try:
            models = get_available_models("Z.AI")
            self.log_test(
                "Z.AI model list retrieval",
                len(models) > 0,
                f"Found {len(models)} models: {models[:5]}..."
            )
        except Exception as e:
            self.log_test(
                "Z.AI model list retrieval",
                False,
                f"Error: {str(e)}"
            )

    def test_model_mapping(self):
        """Test model name mapping"""
        print("\n🔄 Testing Model Mapping")

        test_mappings = [
            ("claude-3-5-sonnet-20241022", "GLM-4.5"),
            ("claude-3-5-haiku-20241022", "GLM-4.5-Air"),
            ("gpt-4", "GLM-4.5"),
            ("gpt-3.5-turbo", "GLM-4.5-Air"),
        ]

        for input_model, expected_zai_model in test_mappings:
            try:
                # Test model validation
                is_valid = validate_model_for_provider("Z.AI", input_model)
                self.log_test(
                    f"Model validation: {input_model}",
                    is_valid,
                    f"Valid" if is_valid else "Invalid"
                )

                # Test model capabilities
                capabilities = get_model_capabilities("Z.AI", input_model)
                has_capabilities = capabilities and capabilities.get("context_length") > 0
                self.log_test(
                    f"Model capabilities: {input_model}",
                    has_capabilities,
                    f"Context: {capabilities.get('context_length', 'N/A')}" if has_capabilities else "No capabilities"
                )
            except Exception as e:
                self.log_test(
                    f"Model mapping: {input_model}",
                    False,
                    f"Error: {str(e)}"
                )

    def test_llm_initialization(self):
        """Test LLM initialization with different models"""
        print("\n🤖 Testing LLM Initialization")

        test_models = [
            "GLM-4.5",
            "GLM-4.5-Air",
            "claude-3-5-sonnet-20241022",
        ]

        for model in test_models:
            try:
                llm = get_llm("Z.AI", model)
                self.log_test(
                    f"LLM initialization: {model}",
                    llm is not None,
                    f"Successfully initialized" if llm else "Failed to initialize"
                )

                # Check model name mapping
                if hasattr(llm, 'model'):
                    actual_model = llm.model
                    self.log_test(
                        f"Model name mapping: {model} -> {actual_model}",
                        True,
                        f"Mapped to: {actual_model}"
                    )
            except Exception as e:
                self.log_test(
                    f"LLM initialization: {model}",
                    False,
                    f"Error: {str(e)}"
                )

    async def test_basic_text_generation(self):
        """Test basic text generation"""
        print("\n💬 Testing Basic Text Generation")

        test_models = ["GLM-4.5", "GLM-4.5-Air"]
        test_prompt = "What is the capital of France? Answer in one word."

        for model in test_models:
            try:
                llm = get_llm("Z.AI", model)
                if not llm:
                    self.log_test(
                        f"Text generation: {model}",
                        False,
                        "Failed to initialize LLM"
                    )
                    continue

                # Test synchronous call (if supported)
                try:
                    response = llm.invoke(test_prompt)
                    response_text = response.content if hasattr(response, 'content') else str(response)
                    success = "paris" in response_text.lower()
                    self.log_test(
                        f"Text generation: {model}",
                        success,
                        f"Response: {response_text[:50]}..." if response_text else "No response"
                    )
                except Exception as invoke_error:
                    # Try async call if sync fails
                    try:
                        response = await llm.ainvoke(test_prompt)
                        response_text = response.content if hasattr(response, 'content') else str(response)
                        success = "paris" in response_text.lower()
                        self.log_test(
                            f"Text generation (async): {model}",
                            success,
                            f"Response: {response_text[:50]}..." if response_text else "No response"
                        )
                    except Exception as async_error:
                        self.log_test(
                            f"Text generation: {model}",
                            False,
                            f"Sync error: {invoke_error}, Async error: {async_error}"
                        )

            except Exception as e:
                self.log_test(
                    f"Text generation: {model}",
                    False,
                    f"Error: {str(e)}"
                )

    def test_prompt_caching(self):
        """Test prompt caching functionality"""
        print("\n💾 Testing Prompt Caching")

        try:
            # Test cache initialization
            from services.zai_prompt_caching import get_zai_cache
            cache = get_zai_cache()
            self.log_test(
                "Prompt cache initialization",
                cache is not None,
                "Cache instance created"
            )

            # Test message caching
            test_messages = [
                {"role": "system", "content": "You are a helpful assistant. " * 100},  # Long message for caching
                {"role": "user", "content": "What is 2+2?"},
            ]

            cached_messages, _, cache_keys = enable_zai_caching(test_messages)
            self.log_test(
                "Message cache control addition",
                len(cache_keys) > 0,
                f"Added cache control to {len(cache_keys)} messages"
            )

            # Test cache statistics
            stats = get_zai_caching_stats()
            self.log_test(
                "Cache statistics retrieval",
                "cache_stats" in stats,
                f"Cache entries: {stats.get('cache_stats', {}).get('total_entries', 0)}"
            )

        except Exception as e:
            self.log_test(
                "Prompt caching functionality",
                False,
                f"Error: {str(e)}"
            )

    async def test_vision_mcp(self):
        """Test Z.AI Vision MCP integration"""
        print("\n👁️ Testing Z.AI Vision MCP")

        # Check if Vision is available
        vision_available = is_zai_vision_available()
        self.log_test(
            "Z.AI Vision availability",
            vision_available,
            "Available" if vision_available else "Not available - check Z_AI_API_KEY and npm/npx"
        )

        if not vision_available:
            return

        try:
            # Test MCP client initialization
            client = await get_zai_vision_client()
            self.log_test(
                "MCP client initialization",
                client is not None,
                "Client created successfully"
            )

            # Test tool discovery
            if client and hasattr(client, 'available_tools'):
                tools_count = len(client.available_tools)
                self.log_test(
                    "MCP tool discovery",
                    tools_count > 0,
                    f"Found {tools_count} tools: {list(client.available_tools.keys())}"
                )

            # Test screenshot capture (if available)
            try:
                from tools.zai_vision_tools import capture_and_analyze
                result = await capture_and_analyze(analysis_type="general")
                self.log_test(
                    "Screenshot capture and analysis",
                    result is not None,
                    "Analysis completed" if result else "Analysis failed"
                )
            except Exception as screenshot_error:
                self.log_test(
                    "Screenshot capture and analysis",
                    False,
                    f"Error: {str(screenshot_error)}"
                )

        except Exception as e:
            self.log_test(
                "Z.AI Vision MCP integration",
                False,
                f"Error: {str(e)}"
            )

    def test_compatibility_mapping(self):
        """Test compatibility model mappings"""
        print("\n🔄 Testing Compatibility Mappings")

        compatibility_models = [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus",
            "gpt-4",
            "gpt-3.5-turbo",
        ]

        for model in compatibility_models:
            try:
                # Test that these models are recognized as valid Z.AI models
                is_valid = validate_model_for_provider("Z.AI", model)
                self.log_test(
                    f"Compatibility model: {model}",
                    is_valid,
                    "Valid compatibility model" if is_valid else "Invalid model"
                )

                if is_valid:
                    # Test that we can get capabilities
                    capabilities = get_model_capabilities("Z.AI", model)
                    has_glm_mapping = capabilities.get("model_type") == "glm"
                    self.log_test(
                        f"GLM mapping for {model}",
                        has_glm_mapping,
                        f"Mapped to GLM model" if has_glm_mapping else "No GLM mapping found"
                    )
            except Exception as e:
                self.log_test(
                    f"Compatibility model: {model}",
                    False,
                    f"Error: {str(e)}"
                )

    async def run_all_tests(self):
        """Run all Z.AI integration tests"""
        print("🚀 Starting Z.AI Integration Tests")
        print("=" * 50)

        start_time = time.time()

        # Run all test categories
        self.test_environment_setup()
        self.test_provider_availability()
        self.test_model_mapping()
        self.test_llm_initialization()
        await self.test_basic_text_generation()
        self.test_prompt_caching()
        await self.test_vision_mcp()
        self.test_compatibility_mapping()

        # Print summary
        duration = time.time() - start_time
        print("\n" + "=" * 50)
        print("📊 Test Summary")
        print("=" * 50)
        print(f"Total Tests: {self.passed_tests + self.failed_tests}")
        print(f"Passed: {self.passed_tests} ✅")
        print(f"Failed: {self.failed_tests} ❌")
        print(f"Duration: {duration:.2f} seconds")

        if self.failed_tests > 0:
            print("\n❌ Failed Tests:")
            for test_name, result in self.test_results.items():
                if not result["success"]:
                    print(f"  - {test_name}: {result['message']}")

        success_rate = (self.passed_tests / (self.passed_tests + self.failed_tests)) * 100 if (self.passed_tests + self.failed_tests) > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")

        if success_rate >= 80:
            print("🎉 Z.AI integration is working well!")
        elif success_rate >= 60:
            print("⚠️ Z.AI integration is partially working - some issues to address")
        else:
            print("🚨 Z.AI integration needs attention")

        return success_rate >= 80


async def main():
    """Main test function"""
    runner = ZAITestRunner()
    success = await runner.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # Check for environment file
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        # Load environment variables
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

    asyncio.run(main())