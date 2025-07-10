"""Agent module for macOS automation."""

from .context_manager import (
    ContextBucketManager,
    AgentFactory,
    create_agent_with_context,
    add_context_to_session,
    get_context_from_session
)

__all__ = [
    'ContextBucketManager',
    'AgentFactory', 
    'create_agent_with_context',
    'add_context_to_session',
    'get_context_from_session'
]