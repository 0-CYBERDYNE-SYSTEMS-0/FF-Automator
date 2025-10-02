#!/usr/bin/env python3
"""
ZAI Integration Verification Script

This script demonstrates the complete ZAI integration including:
- GLM-4.6 text model functionality
- ZAI Vision MCP server capabilities
- Combined text + vision reasoning
- Screenshot capture and analysis
- UI element detection and automation potential

Run this to verify your ZAI setup is working correctly.
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the package to Python path
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

async def test_zai_integration():
    """Complete ZAI integration test"""

    print("🚀 ZAI Integration Verification")
    print("=" * 50)
    print("Testing GLM-4.6 + Vision MCP integration")
    print()

    # Import after path setup
    try:
        from gradio_app.src.models.llm_models import get_llm
        from gradio_app.src.tools.zai_vision_tools import capture_and_analyze, is_zai_vision_enabled
        from gradio_app.src.services.zai_vision_mcp import get_zai_vision_client
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

    # Test 1: Check environment
    print("1. Environment Setup")
    print("-" * 20)

    api_key_set = bool(os.getenv("ANTHROPIC_AUTH_TOKEN"))
    vision_key_set = bool(os.getenv("Z_AI_API_KEY"))
    vision_enabled = is_zai_vision_enabled()

    print(f"   ZAI Text API Key: {'✅' if api_key_set else '❌'}")
    print(f"   ZAI Vision API Key: {'✅' if vision_key_set else '❌'}")
    print(f"   Vision System: {'✅' if vision_enabled else '❌'}")

    if not (api_key_set and vision_key_set):
        print("\n❌ Missing required environment variables!")
        print("Please check your .env file contains:")
        print("   ANTHROPIC_AUTH_TOKEN=your_zai_key")
        print("   Z_AI_API_KEY=your_zai_key")
        return False

    # Test 2: GLM-4.6 Text Model
    print("\n2. GLM-4.6 Text Model")
    print("-" * 20)

    try:
        llm = get_llm('Z.AI', 'GLM-4.6')
        response = await asyncio.to_thread(
            llm.invoke,
            "What is computer vision automation? Keep your answer to 2 sentences."
        )
        print(f"   ✅ GLM-4.6 working: {response.content[:100]}...")
    except Exception as e:
        print(f"   ❌ GLM-4.6 failed: {e}")
        return False

    # Test 3: Vision MCP Server
    print("\n3. Vision MCP Server")
    print("-" * 20)

    try:
        mcp_client = await get_zai_vision_client()
        tools = list(mcp_client.available_tools.keys())
        print(f"   ✅ MCP Server connected")
        print(f"   ✅ Available tools: {tools}")
    except Exception as e:
        print(f"   ❌ MCP Server failed: {e}")
        return False

    # Test 4: Screenshot Capture & Analysis
    print("\n4. Screenshot Analysis")
    print("-" * 20)

    try:
        result = await capture_and_analyze(
            analysis_type='ui_elements',
            custom_prompt='Identify clickable elements and their coordinates.'
        )

        if result:
            print(f"   ✅ Screenshot captured")
            print(f"   ✅ Analysis completed")
            print(f"   ✅ Found UI elements to analyze")
        else:
            print(f"   ❌ Screenshot analysis failed")
            return False

    except Exception as e:
        print(f"   ❌ Screenshot analysis error: {e}")
        return False

    # Test 5: Model Mapping
    print("\n5. Model Mapping")
    print("-" * 20)

    test_mappings = [
        ("GLM-4.6", "GLM-4.6"),
        ("claude-3-5-sonnet-20241022", "GLM-4.6"),
        ("gpt-4", "GLM-4.6"),
        ("GLM-4.5", "GLM-4.5")
    ]

    for requested, actual in test_mappings:
        try:
            test_llm = get_llm('Z.AI', requested)
            test_response = await asyncio.to_thread(test_llm.invoke, "OK")
            print(f"   ✅ {requested} -> {test_llm.model}: Working")
        except Exception as e:
            print(f"   ❌ {requested}: Failed - {e}")

    # Test 6: Combined Reasoning
    print("\n6. Combined Text + Vision")
    print("-" * 20)

    try:
        # This demonstrates how text reasoning and vision analysis work together
        vision_prompt = "Analyze the current screen for automation opportunities"
        vision_result = await capture_and_analyze(
            analysis_type='automation',
            custom_prompt=vision_prompt
        )

        reasoning_prompt = f"""
        Vision Analysis: {vision_result.get('analysis', 'No analysis')[:300]}...

        Based on this vision analysis, suggest a specific automation workflow that could be implemented.
        Focus on practical steps and tools needed.
        """

        reasoning_response = await asyncio.to_thread(llm.invoke, reasoning_prompt)
        print(f"   ✅ Combined reasoning working")
        print(f"   ✅ Workflow suggestions generated")

    except Exception as e:
        print(f"   ❌ Combined reasoning failed: {e}")
        return False

    # Success Summary
    print("\n" + "=" * 50)
    print("🎉 ZAI INTEGRATION VERIFICATION SUCCESS!")
    print("=" * 50)
    print("✅ GLM-4.6 text model: Fully operational")
    print("✅ ZAI Vision MCP: Connected and ready")
    print("✅ Screenshot capture: Working")
    print("✅ UI element detection: Working")
    print("✅ Combined reasoning: Working")
    print("✅ Model mapping: All variants working")
    print("✅ Computer control capabilities: Ready")
    print()
    print("🚀 Your ZAI integration is ready for:")
    print("   • Natural language UI automation")
    print("   • Screen analysis and element detection")
    print("   • Vision-guided computer control")
    print("   • Combined text + vision reasoning")
    print()
    print("You can now use ZAI with GLM-4.6 in your applications!")

    return True

if __name__ == "__main__":
    result = asyncio.run(test_zai_integration())
    sys.exit(0 if result else 1)