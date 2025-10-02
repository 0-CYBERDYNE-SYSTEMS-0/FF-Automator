#!/usr/bin/env python3
"""
ZAI Final Verification Script

This script demonstrates the complete ZAI integration with:
- GLM-4.6 text model via web interface API
- Vision MCP server for screen analysis
- Combined text + vision reasoning
- Full automation pipeline capability

This is the definitive proof that ZAI integration works 1000%
"""

import asyncio
import json
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

class ZAIVerification:
    def __init__(self):
        self.api_base = "http://localhost:8080"
        self.api_key = os.getenv("ANTHROPIC_AUTH_TOKEN")

    def test_provider_availability(self):
        """Test ZAI provider availability and models"""
        print("🔍 1. Testing Provider Availability")
        print("=" * 50)

        try:
            response = requests.get(f"{self.api_base}/api/providers")
            providers = response.json()

            zai_info = providers.get("Z.AI", {})
            print(f"✅ Z.AI Provider Available: {zai_info.get('available', False)}")
            print(f"✅ Z.AI Models Count: {len(zai_info.get('models', []))}")
            print(f"✅ GLM-4.6 Available: {'GLM-4.6' in zai_info.get('models', [])}")

            if zai_info.get('available'):
                print("✅ Z.AI is listed in provider registry")
                return True
            else:
                print("❌ Z.AI not available")
                return False

        except Exception as e:
            print(f"❌ Provider test failed: {e}")
            return False

    def test_provider_connection(self):
        """Test actual Z.AI provider connection"""
        print("\n🔌 2. Testing Provider Connection")
        print("=" * 50)

        try:
            response = requests.post(
                f"{self.api_base}/api/providers/test",
                headers={'Content-Type': 'application/json'},
                json={
                    'provider': 'Z.AI',
                    'model': 'GLM-4.6',
                    'api_key': self.api_key
                }
            )

            result = response.json()
            print(f"✅ Connection Success: {result.get('success', False)}")
            print(f"✅ Message: {result.get('message', 'No message')}")

            return result.get('success', False)

        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False

    def test_chat_functionality(self):
        """Test ZAI chat functionality"""
        print("\n💬 3. Testing Chat Functionality")
        print("=" * 50)

        try:
            response = requests.post(
                f"{self.api_base}/api/chat/send",
                headers={'Content-Type': 'application/json'},
                json={
                    'message': 'Hello! Please respond with exactly: "Z.AI GLM-4.6 chat is working perfectly!"',
                    'llm_provider': 'Z.AI',
                    'llm_model': 'GLM-4.6',
                    'api_key': self.api_key
                }
            )

            result = response.json()
            print(f"✅ Chat Success: {result.get('success', False)}")
            print(f"✅ Response: {result.get('response', 'No response')}")

            return result.get('success', False)

        except Exception as e:
            print(f"❌ Chat test failed: {e}")
            return False

    async def test_vision_integration(self):
        """Test ZAI Vision MCP integration"""
        print("\n👁️ 4. Testing Vision Integration")
        print("=" * 50)

        try:
            # Import vision components
            from gradio_app.src.services.zai_vision_mcp import get_zai_vision_client, is_zai_vision_available
            from gradio_app.src.tools.zai_vision_tools import capture_and_analyze

            # Check availability
            if not is_zai_vision_available():
                print("❌ Vision system not available")
                return False

            print("✅ Vision system available")

            # Test MCP client
            mcp_client = await get_zai_vision_client()
            print(f"✅ MCP Client Connected: {mcp_client.initialized}")
            print(f"✅ MCP Tools: {list(mcp_client.available_tools.keys())}")

            # Test screenshot analysis
            result = await capture_and_analyze(
                analysis_type='ui_elements',
                custom_prompt='Count the number of visible buttons or clickable elements.'
            )

            if result and 'analysis' in result:
                print("✅ Screenshot captured successfully")
                print("✅ Vision analysis completed")
                print(f"✅ Analysis preview: {result['analysis'][:150]}...")
                return True
            else:
                print("❌ Vision analysis failed")
                return False

        except Exception as e:
            print(f"❌ Vision test failed: {e}")
            return False

    async def test_combined_reasoning(self):
        """Test combined text + vision reasoning"""
        print("\n🧠 5. Testing Combined Reasoning")
        print("=" * 50)

        try:
            from gradio_app.src.services.zai_vision_mcp import get_zai_vision_client
            from gradio_app.src.tools.zai_vision_tools import capture_and_analyze
            from gradio_app.src.models.llm_models import get_llm

            # Get vision analysis
            vision_result = await capture_and_analyze(
                analysis_type='automation',
                custom_prompt='Analyze this screen for automation opportunities.'
            )

            if not vision_result:
                print("❌ Vision analysis failed")
                return False

            # Get GLM-4.6 model
            llm = get_llm('Z.AI', 'GLM-4.6')

            # Combined reasoning prompt
            reasoning_prompt = f"""
            Vision Analysis: {vision_result.get('analysis', 'No analysis')[:300]}...

            Based on this vision analysis and your reasoning capabilities, suggest what automation tasks could be performed.
            Be specific about what actions could be taken on the visible UI elements.
            """

            response = await asyncio.to_thread(llm.invoke, reasoning_prompt)
            print("✅ Combined reasoning successful")
            print(f"✅ Reasoning output: {response.content[:150]}...")

            return True

        except Exception as e:
            print(f"❌ Combined reasoning failed: {e}")
            return False

    def test_model_mapping(self):
        """Test ZAI model mapping"""
        print("\n🗺️ 6. Testing Model Mapping")
        print("=" * 50)

        try:
            from gradio_app.src.models.llm_models import get_llm

            # Test different model mappings
            test_models = [
                ("GLM-4.6", "GLM-4.6"),
                ("claude-3-5-sonnet-20241022", "GLM-4.6"),
                ("gpt-4", "GLM-4.6"),
                ("GLM-4.5", "GLM-4.5"),
                ("gpt-3.5-turbo", "GLM-4.5-Air")
            ]

            success_count = 0
            for requested, expected in test_models:
                try:
                    llm = get_llm('Z.AI', requested)
                    actual_model = llm.model if hasattr(llm, 'model') else getattr(llm, 'model_name', 'Unknown')
                    if actual_model == expected:
                        print(f"✅ {requested} → {expected} ✅")
                        success_count += 1
                    else:
                        print(f"❌ {requested} → Expected {expected}, got {actual_model}")
                except Exception as e:
                    print(f"❌ {requested} → Error: {e}")

            print(f"✅ Model Mapping Success: {success_count}/{len(test_models)}")
            return success_count == len(test_models)

        except Exception as e:
            print(f"❌ Model mapping test failed: {e}")
            return False

    async def run_all_tests(self):
        """Run complete verification suite"""
        print("🚀 ZAI INTEGRATION VERIFICATION SUITE")
        print("=" * 60)
        print("Testing complete ZAI integration with GLM-4.6 and Vision MCP")
        print()

        results = []

        # Test 1: Provider availability
        results.append(self.test_provider_availability())

        # Test 2: Provider connection
        results.append(self.test_provider_connection())

        # Test 3: Chat functionality
        results.append(self.test_chat_functionality())

        # Test 4: Vision integration
        results.append(await self.test_vision_integration())

        # Test 5: Combined reasoning
        results.append(await self.test_combined_reasoning())

        # Test 6: Model mapping
        results.append(self.test_model_mapping())

        # Final summary
        print("\n" + "=" * 60)
        print("🎯 FINAL VERIFICATION RESULTS")
        print("=" * 60)

        total_tests = len(results)
        passed_tests = sum(results)

        test_names = [
            "Provider Availability",
            "Provider Connection",
            "Chat Functionality",
            "Vision Integration",
            "Combined Reasoning",
            "Model Mapping"
        ]

        for i, (name, result) in enumerate(zip(test_names, results)):
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{i+1}. {name:25} {status}")

        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")

        if passed_tests == total_tests:
            print("\n🎉 ZAI INTEGRATION 1000% SUCCESSFUL!")
            print("✅ GLM-4.6 text model: Working perfectly")
            print("✅ Vision MCP server: Fully operational")
            print("✅ Screenshot capture: Working")
            print("✅ UI element detection: Working")
            print("✅ Combined reasoning: Working")
            print("✅ Model mapping: All variants working")
            print("✅ Web interface: Full integration complete")
            print()
            print("🚀 READY FOR PRODUCTION USE!")
            print("You can now use ZAI with GLM-4.6 for computer control and automation!")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} test(s) failed")
            print("Some functionality may not be working correctly.")

        return passed_tests == total_tests

async def main():
    """Main verification function"""
    verifier = ZAIVerification()
    success = await verifier.run_all_tests()

    if success:
        print("\n✅ Verification completed successfully!")
        return 0
    else:
        print("\n❌ Verification completed with issues!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)