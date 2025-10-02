#!/usr/bin/env python3
"""
Debug script to simulate exactly what the UI does to create the provider dropdown
"""

import sys
from pathlib import Path

# Add the gradio_app src to Python path
sys.path.insert(0, str(Path(__file__).parent / "gradio_app" / "src"))

print("🎨 Debugging UI Provider Dropdown Creation")
print("=" * 50)

try:
    # Simulate what the UI does
    from models.llm_models import LLM_MODELS, PROVIDER_CONFIGS, check_provider_availability

    # This simulates app_instance.llm_models.keys()
    print("📋 Providers in LLM_MODELS keys:")
    providers = list(LLM_MODELS.keys())
    for i, provider in enumerate(providers):
        print(f"  {i+1}. {provider}")

    print("\n🔄 Testing provider dropdown creation logic:")
    print("(This is exactly what the UI does in lines 234-253 of interface.py)")

    provider_choices = []
    errors = []

    for provider in LLM_MODELS.keys():
        try:
            print(f"\n🔍 Processing provider: {provider}")

            # Test availability check
            is_available = check_provider_availability(provider)
            print(f"   ✅ Availability check: {is_available}")

            # Test config retrieval
            config = PROVIDER_CONFIGS.get(provider, {})
            print(f"   ✅ Config retrieved: {bool(config)}")

            # Test status logic
            if config.get('local_provider'):
                status = '💻 ' if is_available else '⚫ '
                provider_display = f'{status}{provider} (Local)'
            elif config.get('free_models_available'):
                status = '✅ ' if is_available else '❌ '
                provider_display = f'{status}{provider} (Free Options)'
            else:
                status = '✅ ' if is_available else '❌ '
                provider_display = f'{status}{provider}'

            print(f"   ✅ Status display: '{provider_display}'")

            provider_choices.append((provider_display, provider))
            print(f"   ✅ Added to choices")

        except Exception as e:
            error_msg = f"Error processing {provider}: {e}"
            errors.append(error_msg)
            print(f"   ❌ ERROR: {e}")

    print(f"\n📊 Final Results:")
    print(f"   Total providers processed: {len(LLM_MODELS.keys())}")
    print(f"   Successful choices: {len(provider_choices)}")
    print(f"   Errors: {len(errors)}")

    print(f"\n🎯 Provider choices that would appear in dropdown:")
    for display_name, provider_name in provider_choices:
        print(f"   '{display_name}' -> '{provider_name}'")

    if errors:
        print(f"\n❌ Errors that occurred:")
        for error in errors:
            print(f"   - {error}")

    # Check specifically for Z.AI
    zai_found = any(provider_name == "Z.AI" for _, provider_name in provider_choices)
    if zai_found:
        print(f"\n✅ Z.AI WOULD appear in dropdown")
    else:
        print(f"\n❌ Z.AI would NOT appear in dropdown")

        # Debug why Z.AI failed specifically
        print(f"\n🔍 Debugging Z.AI specifically:")
        try:
            is_available = check_provider_availability("Z.AI")
            print(f"   Z.AI availability: {is_available}")

            config = PROVIDER_CONFIGS.get("Z.AI", {})
            print(f"   Z.AI config: {bool(config)}")
            print(f"   Z.AI config keys: {list(config.keys())}")

            # Test the display logic specifically for Z.AI
            if config.get('local_provider'):
                status = '💻 ' if is_available else '⚫ '
                provider_display = f'{status}Z.AI (Local)'
            elif config.get('free_models_available'):
                status = '✅ ' if is_available else '❌ '
                provider_display = f'{status}Z.AI (Free Options)'
            else:
                status = '✅ ' if is_available else '❌ '
                provider_display = f'{status}Z.AI'

            print(f"   Z.AI display name: '{provider_display}'")

        except Exception as e:
            print(f"   ❌ Z.AI specific error: {e}")

except ImportError as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()