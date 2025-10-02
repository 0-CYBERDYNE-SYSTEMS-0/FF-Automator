"""
Z.AI Prompt Caching Integration

This module implements prompt caching functionality for Z.AI to achieve
up to 90% cost reduction and 85% latency reduction through Anthropic's
prompt caching API.
"""

import json
import time
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached prompt entry"""
    cache_key: str
    content: str
    timestamp: float
    ttl_seconds: int = 300  # 5 minutes default

    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return time.time() - self.timestamp > self.ttl_seconds

    def refresh_ttl(self):
        """Refresh the time-to-live"""
        self.timestamp = time.time()


@dataclass
class CacheStats:
    """Cache statistics tracking"""
    cache_hits: int = 0
    cache_writes: int = 0
    cache_misses: int = 0
    tokens_saved: int = 0
    cost_saved: float = 0.0
    latency_saved_ms: float = 0.0
    total_tokens_cached: int = 0

    @property
    def hit_ratio(self) -> float:
        """Calculate cache hit ratio"""
        total_requests = self.cache_hits + self.cache_misses
        return self.cache_hits / total_requests if total_requests > 0 else 0.0


class ZAIPromptCaching:
    """Z.AI prompt caching implementation"""

    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, CacheEntry] = {}
        self.stats = CacheStats()

        # Cacheable content types and minimum sizes
        self.cacheable_types = {
            "system_prompt": 1000,           # Cache system prompts >1000 chars
            "tool_schema": 500,              # Cache tool schemas >500 chars
            "conversation_context": 2000,    # Cache long conversation context
            "mood_template": 800,            # Cache mood templates
        }

    def _is_cacheable(self, content: str, content_type: str = "general") -> bool:
        """Determine if content should be cached"""
        if not content or not content.strip():
            return False

        min_size = self.cacheable_types.get(content_type, 1000)
        return len(content) >= min_size

    def _generate_cache_key(self, content: str, content_type: str) -> str:
        """Generate a cache key for content"""
        # Include content type in hash to avoid collisions
        content_with_type = f"{content_type}:{content}"
        return hashlib.md5(content_with_type.encode()).hexdigest()

    def add_cache_control_to_messages(
        self,
        messages: List[Dict[str, Any]],
        enable_caching: bool = True
    ) -> Tuple[List[Dict[str, Any]], Set[str]]:
        """Add cache_control headers to messages for Z.AI caching"""

        if not enable_caching:
            return messages, set()

        modified_messages = []
        cache_keys = set()

        for i, message in enumerate(messages):
            content = message.get("content", "")
            role = message.get("role", "")

            # Determine content type for caching decisions
            if role == "system":
                content_type = "system_prompt"
            elif role == "user" and i == 0:
                content_type = "conversation_context"
            else:
                content_type = "general"

            # Check if content is cacheable
            if self._is_cacheable(content, content_type):
                cache_key = self._generate_cache_key(content, content_type)
                cache_keys.add(cache_key)

                # Add cache_control to message for Z.AI API
                modified_message = message.copy()
                modified_message["cache_control"] = {"type": "ephemeral"}

                # Track in local cache for statistics
                if cache_key not in self.cache:
                    self.cache[cache_key] = CacheEntry(
                        cache_key=cache_key,
                        content=content,
                        timestamp=time.time(),
                        ttl_seconds=self.ttl_seconds
                    )
                    self.stats.cache_writes += 1
                else:
                    # Refresh existing entry
                    self.cache[cache_key].refresh_ttl()
                    self.stats.cache_hits += 1

                modified_messages.append(modified_message)
            else:
                # Content not cacheable, add as-is
                modified_messages.append(message)

        return modified_messages, cache_keys

    def add_cache_control_to_tools(
        self,
        tools: Optional[List[Dict[str, Any]]],
        enable_caching: bool = True
    ) -> Tuple[Optional[List[Dict[str, Any]]], Set[str]]:
        """Add cache control to tool schemas"""

        if not tools or not enable_caching:
            return tools, set()

        # Serialize tools for caching
        tools_content = json.dumps(tools, sort_keys=True)
        content_type = "tool_schema"
        cache_keys = set()

        if self._is_cacheable(tools_content, content_type):
            cache_key = self._generate_cache_key(tools_content, content_type)
            cache_keys.add(cache_key)

            # Check if already cached
            if cache_key not in self.cache:
                self.cache[cache_key] = CacheEntry(
                    cache_key=cache_key,
                    content=tools_content,
                    timestamp=time.time(),
                    ttl_seconds=self.ttl_seconds
                )
                self.stats.cache_writes += 1
            else:
                self.cache[cache_key].refresh_ttl()
                self.stats.cache_hits += 1

            # For Z.AI API, add cache_control to the first tool
            modified_tools = tools.copy()
            if modified_tools:
                if "cache_control" not in modified_tools[0]:
                    modified_tools[0]["cache_control"] = {"type": "ephemeral"}

            return modified_tools, cache_keys

        return tools, cache_keys

    def track_response_cache_usage(
        self,
        response: Dict[str, Any],
        cache_keys: Set[str]
    ) -> Dict[str, Any]:
        """Track cache usage from API response and calculate savings"""

        usage = response.get("usage", {})

        # Extract cache-related metrics from Z.AI response
        cached_tokens = usage.get("cached_tokens", 0)
        cache_creation_tokens = usage.get("cache_creation_tokens", 0)
        cache_read_tokens = usage.get("cache_read_tokens", 0)

        # Calculate savings (Z.AI: 90% savings on cached tokens)
        tokens_saved = cached_tokens * 0.9

        # Update statistics
        if cached_tokens > 0:
            self.stats.tokens_saved += int(tokens_saved)
            self.stats.total_tokens_cached += cached_tokens

            # Estimate cost savings (Z.AI GLM-4.5 pricing ~$3 per 1M tokens)
            cost_per_token = 0.000003
            cache_savings = tokens_saved * cost_per_token
            self.stats.cost_saved += cache_savings

            # Estimate latency savings (up to 85% reduction)
            estimated_latency_saved = cached_tokens * 0.1  # ms
            self.stats.latency_saved_ms += estimated_latency_saved

        return {
            "cache_keys_used": list(cache_keys),
            "cached_tokens": cached_tokens,
            "cache_creation_tokens": cache_creation_tokens,
            "cache_read_tokens": cache_read_tokens,
            "tokens_saved": int(tokens_saved),
            "cost_saved": tokens_saved * 0.000003,
            "latency_saved_ms": cached_tokens * 0.1
        }

    def cleanup_expired_entries(self):
        """Remove expired cache entries"""
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired()
        ]

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        return {
            "cache_stats": {
                "total_entries": len(self.cache),
                "cache_hits": self.stats.cache_hits,
                "cache_writes": self.stats.cache_writes,
                "cache_misses": self.stats.cache_misses,
                "hit_ratio": self.stats.hit_ratio,
            },
            "token_stats": {
                "tokens_saved": self.stats.tokens_saved,
                "total_tokens_cached": self.stats.total_tokens_cached,
                "cost_saved": self.stats.cost_saved,
                "latency_saved_ms": self.stats.latency_saved_ms,
            },
            "cacheable_types": self.cacheable_types
        }

    def clear_cache(self):
        """Clear all cache entries"""
        self.cache.clear()
        logger.info("Cache cleared")


# Global caching instance
_zai_cache_instance = None


def get_zai_cache(ttl_seconds: int = 300) -> ZAIPromptCaching:
    """Get or create Z.AI prompt caching instance"""
    global _zai_cache_instance

    if _zai_cache_instance is None:
        _zai_cache_instance = ZAIPromptCaching(ttl_seconds=ttl_seconds)

    return _zai_cache_instance


async def enable_zai_caching(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    enable_caching: bool = True
) -> Tuple[List[Dict[str, Any]], Optional[List[Dict[str, Any]]], Set[str]]:
    """
    Enable Z.AI prompt caching for messages and tools

    Args:
        messages: List of conversation messages
        tools: Optional list of tool definitions
        enable_caching: Whether to enable caching

    Returns:
        Tuple of (modified_messages, modified_tools, cache_keys)
    """
    cache = get_zai_cache()

    # Add cache control to messages
    modified_messages, message_cache_keys = cache.add_cache_control_to_messages(
        messages, enable_caching
    )

    # Add cache control to tools
    modified_tools, tool_cache_keys = cache.add_cache_control_to_tools(
        tools, enable_caching
    )

    # Combine cache keys
    all_cache_keys = message_cache_keys.union(tool_cache_keys)

    return modified_messages, modified_tools, all_cache_keys


def track_zai_response_caching(
    response: Dict[str, Any],
    cache_keys: Set[str]
) -> Dict[str, Any]:
    """Track cache usage from Z.AI API response"""
    cache = get_zai_cache()
    return cache.track_response_cache_usage(response, cache_keys)


def get_zai_caching_stats() -> Dict[str, Any]:
    """Get Z.AI caching statistics"""
    cache = get_zai_cache()
    return cache.get_cache_stats()


def clear_zai_cache():
    """Clear Z.AI cache"""
    cache = get_zai_cache()
    cache.clear_cache()