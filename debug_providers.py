#!/usr/bin/env python3
"""
Debug script to check what providers are actually loaded in the gradio app
"""

import sys
from pathlib import Path

# Add the gradio_app src to Python path
sys.path.insert(0, str(Path(__file__).parent / "gradio_app" / "src"))

try:
    from models.llm_models import LLM_MODELS, check_provider_availability, PROVIDER_CONFIGS

    print("🔍 Debugging Gradio App Provider Loading")
    print("=" * 50)

    print("📋 Available providers in LLM_MODELS:")
    for provider, models in LLM_MODELS.items():
        print(f"  - {provider}: {len(models)} models")
        if provider == "Z.AI":
            print(f"    Models: {models[:3]}...")  # Show first 3 models

    print("\n🔍 Checking PROVIDER_CONFIGS:")
    for provider in LLM_MODELS.keys():
        config = PROVIDER_CONFIGS.get(provider, {})
        has_config = bool(config)
        print(f"  - {provider}: {'✅ Config' if has_config else '❌ No config'}")
        if provider == "Z.AI" and has_config:
            print(f"    Base URL: {config.get('base_url', 'N/A')}")
            print(f"    API Key Env: {config.get('api_key_env', 'N/A')}")

    print("\n🌐 Checking provider availability:")
    for provider in LLM_MODELS.keys():
        try:
            is_available = check_provider_availability(provider)
            status = "✅ Available" if is_available else "❌ Not available"
            print(f"  - {provider}: {status}")
        except Exception as e:
            print(f"  - {provider}: ❌ Error - {e}")

    print("\n🎯 Testing app initialization:")
    try:
        from models.app import MacOSUseGradioApp
        app = MacOSUseGradioApp()
        print("✅ App initialized successfully")

        print(f"📊 app.llm_models keys: {list(app.llm_models.keys())}")

        if "Z.AI" in app.llm_models:
            print("✅ Z.AI found in app.llm_models")
            zai_models = app.llm_models["Z.AI"]
            print(f"   Z.AI models: {len(zai_models)} models")
            print(f"   First 3 models: {zai_models[:3]}")
        else:
            print("❌ Z.AI NOT found in app.llm_models")

    except Exception as e:
        print(f"❌ App initialization failed: {e}")
        import traceback
        traceback.print_exc()

except ImportError as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()