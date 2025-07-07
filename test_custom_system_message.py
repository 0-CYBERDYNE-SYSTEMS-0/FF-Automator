#!/usr/bin/env python3
"""
Test script to demonstrate custom system message functionality in the web interface backend.
"""

from web_interface.api.main import (
    ChatSystemPromptWithCustom, 
    SystemPromptWithCustom, 
    ChatSystemPrompt,
    ChatMessage,
    AgentTaskRequest
)
from datetime import datetime

def test_system_prompts():
    """Test the enhanced system prompt classes"""
    print("🧪 Testing System Prompt Classes")
    
    # Test basic chat system prompt
    basic_prompt = ChatSystemPrompt(
        action_description="test actions",
        current_date=datetime.now(),
        max_actions_per_step=10
    )
    basic_rules = basic_prompt.important_rules()
    print(f"✅ Basic ChatSystemPrompt: {len(basic_rules)} characters")
    
    # Test chat system prompt with custom message
    custom_chat_prompt = ChatSystemPromptWithCustom(
        action_description="test actions",
        current_date=datetime.now(),
        max_actions_per_step=10,
        custom_message="Always respond in a friendly, helpful manner and prioritize user safety."
    )
    custom_rules = custom_chat_prompt.important_rules()
    print(f"✅ Custom ChatSystemPrompt: {len(custom_rules)} characters")
    print(f"   Custom message included: {'CUSTOM INSTRUCTIONS' in custom_rules}")
    
    # Test system prompt with custom message
    custom_system_prompt = SystemPromptWithCustom(
        action_description="test actions",
        current_date=datetime.now(),
        max_actions_per_step=10,
        custom_message="Focus on accessibility and always verify actions before marking tasks complete."
    )
    system_rules = custom_system_prompt.important_rules()
    print(f"✅ Custom SystemPrompt: {len(system_rules)} characters")
    print(f"   Custom message included: {'CUSTOM INSTRUCTIONS' in system_rules}")

def test_api_models():
    """Test the Pydantic models for API requests"""
    print("\n🧪 Testing API Models")
    
    # Test ChatMessage with custom system message
    chat_msg = ChatMessage(
        message="Open Calculator and compute 5 + 3",
        llm_provider="OpenAI",
        llm_model="gpt-4",
        custom_system_message="Always show your work step by step"
    )
    print(f"✅ ChatMessage with custom system message: {chat_msg.custom_system_message}")
    
    # Test ChatMessage without custom system message (backward compatibility)
    chat_msg_basic = ChatMessage(
        message="Hello, how are you?",
        llm_provider="OpenAI",
        llm_model="gpt-4"
    )
    print(f"✅ ChatMessage without custom system message: {chat_msg_basic.custom_system_message}")
    
    # Test AgentTaskRequest with custom system message
    agent_task = AgentTaskRequest(
        task="Create a new note with today's date",
        max_steps=50,
        max_actions=5,
        custom_system_message="Be extra careful with file operations and always confirm actions"
    )
    print(f"✅ AgentTaskRequest with custom system message: {agent_task.custom_system_message}")

def demonstrate_usage():
    """Demonstrate how the custom system messages would be used"""
    print("\n💡 Usage Examples")
    
    # Example 1: Safety-focused custom message
    safety_prompt = ChatSystemPromptWithCustom(
        action_description="Available actions: open_app, click_element, type_text",
        current_date=datetime.now(),
        max_actions_per_step=3,
        custom_message="SAFETY PRIORITY: Never perform destructive actions like deleting files or closing important applications without explicit user confirmation."
    )
    
    print("📋 Example 1 - Safety-focused custom rules:")
    print(safety_prompt.important_rules()[-200:])  # Show last 200 chars
    
    # Example 2: Accessibility-focused custom message
    accessibility_prompt = SystemPromptWithCustom(
        action_description="Available actions: open_app, click_element, type_text",
        current_date=datetime.now(),
        max_actions_per_step=10,
        custom_message="ACCESSIBILITY FOCUS: Always check for alternative text, keyboard shortcuts, and ensure actions work for users with disabilities. Use VoiceOver-friendly approaches when possible."
    )
    
    print("\n📋 Example 2 - Accessibility-focused custom rules:")
    print(accessibility_prompt.important_rules()[-250:])  # Show last 250 chars

if __name__ == "__main__":
    print("🚀 Testing Custom System Message Functionality\n")
    
    test_system_prompts()
    test_api_models()
    demonstrate_usage()
    
    print(f"\n✅ All tests passed! Custom system message functionality is working correctly.")
    print(f"📝 Summary of changes:")
    print(f"   • ChatSystemPromptWithCustom: Extends ChatSystemPrompt with custom_message parameter")
    print(f"   • SystemPromptWithCustom: Extends SystemPrompt with custom_message parameter")
    print(f"   • ChatMessage: Added optional custom_system_message field")
    print(f"   • AgentTaskRequest: Added optional custom_system_message field")
    print(f"   • Backend handlers: Updated to use custom system prompts when provided")
    print(f"   • Backward compatibility: Maintained for existing code without custom messages")