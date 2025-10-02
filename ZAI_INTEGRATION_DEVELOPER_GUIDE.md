# Z.AI Integration Developer Guide

This guide provides a comprehensive overview of the Z.AI Vision and API integration in FF-Terminal, including authentication, structured outputs, prompt caching, and agent interaction patterns. Use this as a reference for implementing similar integrations in your own projects.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Authentication System](#authentication-system)
3. [Z.AI API Provider](#zai-api-provider)
4. [Z.AI Vision via MCP](#zai-vision-via-mcp)
5. [Structured Outputs](#structured-outputs)
6. [Prompt Caching](#prompt-caching)
7. [Agent Integration](#agent-integration)
8. [Implementation Examples](#implementation-examples)

---

## Architecture Overview

FF-Terminal integrates Z.AI through **two distinct pathways**:

### 1. Z.AI API Provider (Text Models)
- **Purpose**: Access to GLM-4.5 and GLM-4.5-Air models via Anthropic-compatible API
- **Location**: `ff_terminal/core/model_providers.py` (ZaiProvider class)
- **Protocol**: OpenAI-compatible API with Anthropic fallback via LiteLLM
- **Authentication**: Bearer token via `ANTHROPIC_AUTH_TOKEN` environment variable

### 2. Z.AI Vision via MCP (Vision Models)
- **Purpose**: Screen analysis, UI element detection, and computer vision automation
- **Location**: `ff_terminal/core/mcp_client.py` + `ff_terminal/simple_tools/vision_tools.py`
- **Protocol**: JSON-RPC 2.0 via MCP (Model Context Protocol)
- **Authentication**: API key via `Z_AI_API_KEY` environment variable

```
┌─────────────────────────────────────────────────────────────┐
│                      FF-Terminal Agent                       │
│                                                              │
│  ┌────────────────────────┐  ┌──────────────────────────┐  │
│  │   ZaiProvider          │  │  Z.AI Vision MCP Client  │  │
│  │   (Text Generation)    │  │  (Computer Vision)       │  │
│  └──────────┬─────────────┘  └────────────┬─────────────┘  │
│             │                              │                 │
└─────────────┼──────────────────────────────┼─────────────────┘
              │                              │
              ▼                              ▼
┌─────────────────────────┐    ┌────────────────────────────┐
│ Z.AI Anthropic Gateway  │    │  Z.AI Vision MCP Server    │
│ open.bigmodel.cn        │    │  @z_ai/mcp-server (npm)    │
│ (GLM-4.5 / GLM-4.5-Air) │    │  (Vision Analysis API)     │
└─────────────────────────┘    └────────────────────────────┘
```

---

## Authentication System

### Z.AI API Provider Authentication

**Environment Variables:**
```bash
# Required for Z.AI API access
export ANTHROPIC_AUTH_TOKEN="your_zai_api_key_here"

# Optional: Override default base URL
export ANTHROPIC_BASE_URL="https://open.bigmodel.cn/api/anthropic"
```

**Code Implementation** (`model_providers.py:2116-2125`):

```python
class ZaiProvider(ModelProvider):
    def __init__(self, model: str = "claude-3-5-sonnet-20241022", **kwargs):
        super().__init__(model, **kwargs)

        # Multi-source API key resolution (priority order)
        api_key = kwargs.get("api_key") or os.getenv("ANTHROPIC_AUTH_TOKEN")

        if not api_key:
            raise ValueError(
                f"Z.ai API key not found for model '{model}'. "
                f"This model requires Z.ai access. Please:\n"
                f"1. Set ANTHROPIC_AUTH_TOKEN environment variable\n"
                f"2. Or pass api_key parameter\n"
                f"Get your API key at: https://z.ai/manage-apikey/apikey-list"
            )

        # Get base URL with fallback chain
        base_url = kwargs.get("base_url") or \
                   os.getenv("ANTHROPIC_BASE_URL") or \
                   "https://open.bigmodel.cn/api/anthropic"

        # Initialize OpenAI-compatible client
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers={
                "HTTP-Referer": "https://github.com/anthropics/ff-terminal",
                "X-Title": "FF-Terminal"
            }
        )
```

**Key Points:**
- Uses OpenAI client library for compatibility
- Custom headers for tracking and attribution
- Explicit base URL to prevent environment variable interference
- Graceful fallback chain for configuration

### Z.AI Vision MCP Authentication

**Environment Variables:**
```bash
# Required for Z.AI Vision MCP
export Z_AI_API_KEY="your_zai_api_key"
export Z_AI_MODE="ZAI"
```

**Code Implementation** (`mcp_client.py:259-273`):

```python
async def get_zai_vision_client() -> MCPClient:
    """Get the Z.AI Vision MCP client"""
    import os

    # Get Z.AI API key from environment (or use known key for testing)
    zai_api_key = os.getenv("Z_AI_API_KEY", "fallback_key_if_needed")

    # Z.AI Vision MCP server command (spawns subprocess)
    command = ["npx", "-y", "@z_ai/mcp-server"]
    env = {
        "Z_AI_API_KEY": zai_api_key,
        "Z_AI_MODE": "ZAI"  # Critical: tells MCP server which provider to use
    }

    return await get_mcp_client("zai-vision", command, env)
```

**MCP Server Initialization** (`mcp_client.py:40-66`):

```python
class MCPClient:
    async def start(self) -> bool:
        """Start the MCP server process and initialize connection"""
        try:
            logger.info(f"Starting MCP server: {self.server_name}")

            # Create environment for subprocess
            env = dict(os.environ)
            env.update(self.env)  # Merge in Z_AI_API_KEY and Z_AI_MODE

            # Start the MCP server process via npx
            self.process = await asyncio.create_subprocess_exec(
                *self.command,  # ["npx", "-y", "@z_ai/mcp-server"]
                env=env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Initialize the MCP connection with handshake
            await self._initialize_connection()

            logger.info(f"MCP server '{self.server_name}' started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start MCP server '{self.server_name}': {e}")
            return False
```

---

## Z.AI API Provider

### Model Mapping Strategy

Z.AI provides GLM models via an Anthropic-compatible API. FF-Terminal automatically maps Claude model names to GLM equivalents:

**Mapping Table** (`model_providers.py:2141-2161`):

```python
self.model_mapping = {
    # Claude Sonnet models -> GLM-4.5 (most capable)
    "claude-3-5-sonnet-20241022": "GLM-4.5",
    "claude-3-sonnet": "GLM-4.5",
    "claude-3-5-sonnet": "GLM-4.5",
    "claude-3-opus": "GLM-4.5",

    # Claude Haiku models -> GLM-4.5-Air (faster, cheaper)
    "claude-3-5-haiku-20241022": "GLM-4.5-Air",
    "claude-3-haiku": "GLM-4.5-Air",
    "claude-3-5-haiku": "GLM-4.5-Air",

    # Direct GLM model names (exact Z.ai API names)
    "glm-4.5": "GLM-4.5",
    "glm-4.5-air": "GLM-4.5-Air",
    "GLM-4.5": "GLM-4.5",
    "GLM-4.5-Air": "GLM-4.5-Air",

    # Default OpenAI models -> GLM mapping
    "gpt-4": "GLM-4.5",
    "gpt-4-turbo": "GLM-4.5",
    "gpt-3.5-turbo": "GLM-4.5-Air",
    "gpt-5-mini": "GLM-4.5-Air"
}
```

### Chat Completion Implementation

**Dual-Path Strategy** (`model_providers.py:2168-2215`):

```python
async def chat_completion(self,
                        messages: List[Dict[str, Any]],
                        tools: Optional[List[Dict[str, Any]]] = None,
                        **kwargs) -> Dict[str, Any]:
    """Create a chat completion using Z.ai Anthropic-compatible API"""
    try:
        # PRIMARY PATH: OpenAI-compatible format
        api_kwargs = {
            "model": self.zai_model,  # e.g., "GLM-4.5"
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 12000),
        }
        if tools:
            api_kwargs["tools"] = tools

        logger.info(f"Making Z.ai API call with GLM model: {self.zai_model}")
        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            **api_kwargs
        )

        # Try OpenAI-format parsing
        try:
            return self._format_zai_response(response)
        except Exception as format_err:
            # FALLBACK PATH: Anthropic format via LiteLLM
            logger.debug(f"OpenAI-format parsing failed, using LiteLLM fallback")
            return await self._fallback_via_litellm(messages, tools, **kwargs)

    except Exception as e:
        logger.warning(f"Z.ai OpenAI-format call failed: {e}")
        # Final fallback with enhanced error messages
        try:
            return await self._fallback_via_litellm(messages, tools, **kwargs)
        except Exception as inner:
            # Translate common errors to user-friendly messages
            err_text = str(inner)
            if "401" in err_text or "Unauthorized" in err_text:
                raise Exception(
                    "Z.ai API key invalid (401 Unauthorized). "
                    "Check ANTHROPIC_AUTH_TOKEN or --zai-key."
                )
            if "403" in err_text or "Forbidden" in err_text:
                raise Exception(
                    "Z.ai access forbidden (403). "
                    "Verify subscription and API key permissions."
                )
            if "quota" in err_text.lower():
                raise Exception(
                    "Z.ai quota exceeded. "
                    "Check usage/billing on https://z.ai/manage-apikey/."
                )
            raise
```

### LiteLLM Fallback Implementation

**Anthropic Messages API via LiteLLM** (`model_providers.py:2217-2276`):

```python
async def _fallback_via_litellm(self,
                               messages: List[Dict[str, Any]],
                               tools: Optional[List[Dict[str, Any]]],
                               **kwargs) -> Dict[str, Any]:
    """Fallback to Anthropic Messages via LiteLLM against Z.ai base URL"""
    if not LITELLM_AVAILABLE:
        raise RuntimeError("LiteLLM not available. Install: pip install litellm")

    # Map to Anthropic model name for LiteLLM
    anthropic_model = self._map_to_anthropic_model(self.model)
    if not anthropic_model:
        anthropic_model = "claude-3-5-sonnet-20241022"

    # Get Z.AI credentials
    api_base = os.getenv("ANTHROPIC_BASE_URL") or \
               os.getenv("ANTHROPIC_API_BASE") or \
               "https://api.z.ai/api/anthropic"
    api_key = self.kwargs.get("api_key") or \
              os.getenv("ANTHROPIC_AUTH_TOKEN") or \
              os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        raise RuntimeError("Missing ANTHROPIC_AUTH_TOKEN for Z.ai fallback")

    # Build LiteLLM request
    request_kwargs = {
        "model": anthropic_model,
        "messages": messages,
        "api_base": api_base,
        "api_key": api_key,
        "temperature": kwargs.get("temperature", 0.7),
        "max_tokens": kwargs.get("max_tokens", 12000),
    }
    if tools:
        request_kwargs["tools"] = tools

    # CRITICAL: Add Anthropic prompt-caching beta header
    request_kwargs["extra_headers"] = {
        "anthropic-beta": "prompt-caching-2024-07-31"
    }

    logger.info(f"Z.ai fallback via LiteLLM with model: {anthropic_model}")

    from litellm import acompletion
    response = await acompletion(**request_kwargs)

    # Format response (reuse LiteLLM provider formatting)
    formatted = self._format_litellm_response(response)
    formatted["usage"]["cost_source"] = "zai_api"
    formatted["provider"] = "zai"
    formatted["zai_model_used"] = self.zai_model

    return formatted
```

**Key Benefits:**
- Seamless fallback if OpenAI format fails
- Automatic prompt caching support via Anthropic beta headers
- Cost tracking with Z.AI attribution

---

## Z.AI Vision via MCP

### MCP Protocol Implementation

**JSON-RPC 2.0 Communication** (`mcp_client.py:68-108`):

```python
async def _initialize_connection(self):
    """Initialize MCP connection with handshake"""
    try:
        # Send initialize request (JSON-RPC 2.0)
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}  # Request tool capabilities
                },
                "clientInfo": {
                    "name": "ff-terminal",
                    "version": "3.0.0"
                }
            }
        }

        response = await self._send_request(init_request)

        if response and "result" in response:
            self.server_capabilities = response["result"].get("capabilities", {})
            self.initialized = True

            # Send initialized notification
            await self._send_notification({
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            })

            # Discover available tools
            await self._load_tools()
        else:
            raise Exception("Failed to initialize MCP connection")

    except Exception as e:
        logger.error(f"MCP initialization failed: {e}")
        raise
```

**Tool Discovery** (`mcp_client.py:110-131`):

```python
async def _load_tools(self):
    """Load available tools from MCP server"""
    try:
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }

        response = await self._send_request(tools_request)

        if response and "result" in response:
            tools = response["result"].get("tools", [])
            self.available_tools = {tool["name"]: tool for tool in tools}
            logger.info(f"Loaded {len(self.available_tools)} tools from MCP")

            for tool_name, tool_info in self.available_tools.items():
                logger.debug(
                    f"Available MCP tool: {tool_name} - "
                    f"{tool_info.get('description', 'No description')}"
                )

    except Exception as e:
        logger.error(f"Failed to load tools from MCP server: {e}")
```

### Vision Tool Implementation

**Screenshot Capture Tool** (`vision_tools.py:29-128`):

```python
class ScreenshotCaptureTool(BaseTool):
    """Capture screenshots for vision analysis"""

    def __init__(self):
        super().__init__(
            name="capture_screenshot",
            description="Take a screenshot of the current screen for vision analysis",
            category=ToolCategory.SYSTEM
        )

    async def execute(self, region: str = "full", save_path: str = "", **kwargs):
        """Capture a screenshot"""
        # Determine save path
        if not save_path:
            temp_dir = Path(tempfile.gettempdir())
            timestamp = asyncio.get_event_loop().time()
            save_path = str(temp_dir / f"ff_terminal_screenshot_{timestamp}.png")

        # Build screencapture command based on region
        if region == "full":
            cmd = ["screencapture", "-x", save_path]
        elif region == "active":
            cmd = ["screencapture", "-x", "-w", save_path]  # Active window
        else:
            # Parse x,y,width,height coordinates
            coords = [int(x.strip()) for x in region.split(',')]
            x, y, w, h = coords
            cmd = ["screencapture", "-x", "-R", f"{x},{y},{w},{h}", save_path]

        # Execute screenshot capture
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return ToolResult(success=False, error=f"Capture failed: {result.stderr}")

        # Return path and metadata
        file_size = os.path.getsize(save_path)
        return ToolResult(
            success=True,
            data={
                "screenshot_path": save_path,
                "region": region,
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2)
            }
        )
```

**Z.AI Vision Analysis Tool** (`vision_tools.py:130-233`):

```python
class ZaiVisionAnalysisTool(BaseTool):
    """Analyze screenshots using Z.AI Vision MCP server"""

    def __init__(self):
        super().__init__(
            name="zai_vision_analysis",
            description="Analyze screenshots using Z.AI Vision AI",
            category=ToolCategory.VISUALIZATION
        )
        self._mcp_client = None

    async def _get_mcp_client(self):
        """Get or create MCP client"""
        if self._mcp_client is None:
            self._mcp_client = await get_zai_vision_client()
        return self._mcp_client

    async def execute(self,
                     image_path: str,
                     analysis_type: str = "general",
                     custom_prompt: str = "",
                     **kwargs):
        """Analyze image using Z.AI Vision"""
        # Validate image exists
        if not os.path.exists(image_path):
            return ToolResult(success=False, error=f"Image not found: {image_path}")

        # Get MCP client
        mcp_client = await self._get_mcp_client()

        # Determine analysis prompt
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = self._get_analysis_prompt(analysis_type)

        logger.info(f"Analyzing image with Z.AI Vision: {analysis_type}")

        # Call Z.AI vision analysis via MCP
        result = await mcp_client.call_tool("analyze_image", {
            "image_source": image_path,
            "prompt": prompt
        })

        if result and "analysis" in result:
            analysis_text = result["analysis"]
            processed_data = self._post_process_analysis(analysis_text, analysis_type)

            return ToolResult(
                success=True,
                data={
                    "analysis": analysis_text,
                    "analysis_type": analysis_type,
                    "processed_data": processed_data,
                    "image_path": image_path,
                    "model": "Z.AI Vision"
                }
            )
        else:
            return ToolResult(
                success=False,
                error="No analysis received from Z.AI Vision"
            )
```

**MCP Tool Call Implementation** (`mcp_client.py:172-220`):

```python
async def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
    """Call a tool on the MCP server"""
    if not self.initialized:
        raise Exception("MCP client not initialized")

    if tool_name not in self.available_tools:
        raise Exception(f"Tool '{tool_name}' not available on MCP server")

    try:
        # Build JSON-RPC tool call request
        tool_call_request = {
            "jsonrpc": "2.0",
            "id": hash(f"{tool_name}_{asyncio.get_event_loop().time()}"),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        logger.info(f"Calling MCP tool: {tool_name}")

        response = await self._send_request(tool_call_request)

        if response and "result" in response:
            result = response["result"]

            # Handle MCP content format
            if "content" in result:
                content = result["content"]
                if isinstance(content, list) and content:
                    # Extract text from content items
                    text_content = []
                    for item in content:
                        if item.get("type") == "text":
                            text_content.append(item.get("text", ""))
                    return {
                        "analysis": "\n".join(text_content),
                        "raw_content": content
                    }
                else:
                    return {"analysis": str(content), "raw_content": content}
            else:
                # Direct response
                return {"analysis": str(result), "raw_content": result}
        else:
            logger.error(f"No valid response from MCP tool '{tool_name}'")
            return None

    except Exception as e:
        logger.error(f"Failed to call MCP tool '{tool_name}': {e}")
        return None
```

---

## Structured Outputs

### Response Format Standardization

All providers return a standardized response format for consistency:

**Standard Response Schema:**

```python
{
    "content": str,              # The text response from the model
    "tool_calls": List[ToolCall] | None,  # Any tool calls requested
    "model": str,                # Actual model used (e.g., "GLM-4.5")
    "usage": {
        "prompt_tokens": int,
        "completion_tokens": int,
        "total_tokens": int,
        "cost_source": str       # "zai_api", "openai", "openrouter", etc.
    },
    "finish_reason": str,        # "stop", "tool_calls", "length", etc.
    "provider": str,             # "zai", "openai", "ollama", etc.
    "zai_model_used": str        # Z.AI only: actual GLM model used
}
```

**ZaiProvider Response Formatting** (`model_providers.py:2291-2309`):

```python
def _format_zai_response(self, response) -> Dict[str, Any]:
    """Format Z.ai response to standardized format"""
    message = response.choices[0].message

    return {
        "content": message.content,
        "tool_calls": message.tool_calls,
        "model": response.model,  # GLM-4.5 or GLM-4.5-Air
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
            "cost_source": "zai_api"  # Attribution for cost tracking
        },
        "finish_reason": response.choices[0].finish_reason,
        "provider": "zai",
        "original_model_requested": self.model,  # What user asked for
        "zai_model_used": self.zai_model         # What Z.AI actually used
    }
```

### Tool Call Format

**OpenAI-Compatible Tool Calls:**

```python
{
    "id": "call_abc123",
    "type": "function",
    "function": {
        "name": "read_file",
        "arguments": '{"file_path": "/path/to/file.txt"}'
    }
}
```

**Tool Response Format:**

```python
{
    "role": "tool",
    "tool_call_id": "call_abc123",
    "content": "File contents here..."
}
```

---

## Prompt Caching

### Anthropic Prompt Caching Implementation

FF-Terminal implements Anthropic's prompt caching API for up to **90% cost reduction** and **85% latency reduction**.

**Cache Control Headers** (`prompt_caching.py:139-211`):

```python
def add_cache_control_to_messages(
    self,
    messages: List[Dict[str, Any]],
    enable_caching: bool = True
) -> Tuple[List[Dict[str, Any]], Set[str]]:
    """Add cache_control headers to messages for Anthropic caching"""

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

        # Check if content is cacheable (minimum size requirements)
        if self._is_cacheable(content, content_type):
            cache_key = self._generate_cache_key(content, content_type)
            cache_keys.add(cache_key)

            # Add cache_control to message for Anthropic API
            modified_message = message.copy()
            modified_message["cache_control"] = {"type": "ephemeral"}

            # Track in local cache for statistics
            if cache_key not in self.cache:
                self.cache[cache_key] = CacheEntry(
                    cache_key=cache_key,
                    content=content,
                    timestamp=time.time(),
                    ttl_seconds=self.ttl_seconds  # 5 minutes default
                )
                self.stats.cache_writes += 1
            else:
                # Refresh existing entry (Anthropic refreshes TTL on use)
                self.cache[cache_key].refresh_ttl()
                self.stats.cache_hits += 1

            modified_messages.append(modified_message)
        else:
            # Content not cacheable, add as-is
            modified_messages.append(message)

    return modified_messages, cache_keys
```

**Cacheable Content Criteria** (`prompt_caching.py:84-91`):

```python
self.cacheable_types = {
    "system_prompt": 1000,           # Cache system prompts >1000 chars
    "tool_schema": 500,              # Cache tool schemas >500 chars
    "conversation_context": 2000,    # Cache long conversation context
    "mood_template": 800,            # Cache mood templates
}

def _is_cacheable(self, content: str, content_type: str = "general") -> bool:
    """Determine if content should be cached"""
    min_size = self.cacheable_types.get(content_type, 1000)
    return len(content) >= min_size
```

**Tool Schema Caching** (`prompt_caching.py:213-263`):

```python
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

        # For Anthropic API, add cache_control to the first tool
        modified_tools = tools.copy()
        if modified_tools:
            if "cache_control" not in modified_tools[0]:
                modified_tools[0]["cache_control"] = {"type": "ephemeral"}

        return modified_tools, cache_keys

    return tools, cache_keys
```

**Usage in Z.AI Provider** (`model_providers.py:2249`):

```python
# Add Anthropic prompt-caching beta header when using LiteLLM fallback
request_kwargs["extra_headers"] = {
    "anthropic-beta": "prompt-caching-2024-07-31"
}
```

### Cache Statistics Tracking

**Performance Metrics** (`prompt_caching.py:265-314`):

```python
def track_response_cache_usage(
    self,
    response: Dict[str, Any],
    cache_keys: Set[str]
) -> Dict[str, Any]:
    """Track cache usage from API response and calculate savings"""

    usage = response.get("usage", {})

    # Extract cache-related metrics from Anthropic response
    cached_tokens = usage.get("cached_tokens", 0)
    cache_creation_tokens = usage.get("cache_creation_tokens", 0)
    cache_read_tokens = usage.get("cache_read_tokens", 0)

    # Calculate savings (Anthropic: 90% savings on cached tokens)
    tokens_saved = cached_tokens * 0.9

    # Update statistics
    if cached_tokens > 0:
        self.stats.tokens_saved += int(tokens_saved)
        self.stats.total_tokens_cached += cached_tokens

        # Estimate cost savings (Claude Sonnet pricing)
        cost_per_token = 0.000003  # $3 per 1M tokens for input
        cache_savings = tokens_saved * cost_per_token
        self.stats.cost_saved += cache_savings

        # Estimate latency savings (Anthropic: up to 85% reduction)
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
```

---

## Agent Integration

### How Agents Use Providers

**Agent Model Provider Setup** (`chat_agent.py`):

```python
class ChatAgent(BaseAgent):
    def __init__(self, config: FFTerminalConfig, session: Session):
        super().__init__(config, session)

        # Model provider is injected by the factory
        self.model_provider = config.model_provider

        # Agent uses provider's chat_completion method
        self.supports_tools = self.model_provider.supports_tools()
```

**Agent Chat Completion Call Pattern**:

```python
# From chat_agent.py (multiple locations: 1099, 1289, 1488, etc.)

# Build messages array
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_input},
    # ... conversation history ...
]

# Prepare tools
tools = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to file"}
                },
                "required": ["file_path"]
            }
        }
    },
    # ... more tools ...
]

# Call provider (automatically uses Z.AI if configured)
response = await self.model_provider.chat_completion(
    messages=messages,
    tools=tools,
    temperature=0.7,
    max_tokens=12000
)

# Extract response
content = response["content"]
tool_calls = response.get("tool_calls")
```

### Provider Selection Logic

**Factory Pattern** (`model_providers.py:2362-2402`):

```python
@staticmethod
def create_from_args(args, model_key: str = "main_model") -> ModelProvider:
    """Create provider based on command line arguments"""
    model = getattr(args, model_key)

    # Priority order for provider selection
    if args.local:
        return OllamaProvider(model=model, ...)
    elif getattr(args, 'litellm', False):
        return LiteLLMProvider(model=model, ...)
    elif getattr(args, 'openrouter', False):
        return OpenRouterProvider(model=model, ...)
    elif getattr(args, 'zai', False):  # Z.AI provider
        return ZaiProvider(
            model=model,
            api_key=getattr(args, 'zai_key', None)
        )
    else:
        return OpenAIProvider(model=model)  # Default
```

**CLI Usage:**

```bash
# Use Z.AI provider
python main_refactored.py --zai --main-model claude-3-5-sonnet-20241022

# Pass API key directly
python main_refactored.py --zai --zai-key your_api_key --main-model GLM-4.5

# Use Z.AI for all models (master mode)
python main_refactored.py --zai --master-model claude-3-5-sonnet-20241022
```

---

## Implementation Examples

### Example 1: Basic Z.AI Text Generation

```python
from ff_terminal.core.model_providers import ZaiProvider

# Initialize provider
provider = ZaiProvider(
    model="claude-3-5-sonnet-20241022",
    api_key="your_zai_api_key"
)

# Simple chat completion
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"}
]

response = await provider.chat_completion(messages)
print(response["content"])  # "The capital of France is Paris."
```

### Example 2: Tool Calling with Z.AI

```python
# Define tools
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City and country"
                    },
                    "units": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"]
                    }
                },
                "required": ["location"]
            }
        }
    }
]

# Request with tools
messages = [
    {"role": "user", "content": "What's the weather in Tokyo?"}
]

response = await provider.chat_completion(messages, tools=tools)

# Check for tool calls
if response.get("tool_calls"):
    for tool_call in response["tool_calls"]:
        print(f"Tool: {tool_call.function.name}")
        print(f"Arguments: {tool_call.function.arguments}")
        # Execute tool and send result back...
```

### Example 3: Vision Analysis with Z.AI MCP

```python
from ff_terminal.simple_tools.vision_tools import (
    screenshot_capture_tool,
    zai_vision_analysis_tool
)

# Capture screenshot
screenshot_result = await screenshot_capture_tool.execute(region="full")
screenshot_path = screenshot_result.data["screenshot_path"]

# Analyze screenshot
analysis_result = await zai_vision_analysis_tool.execute(
    image_path=screenshot_path,
    analysis_type="ui_elements"
)

# Extract results
analysis = analysis_result.data["analysis"]
ui_elements = analysis_result.data["processed_data"]["ui_elements"]

for element in ui_elements:
    print(f"Element: {element['description']}")
    if element.get('coordinates'):
        print(f"  Coordinates: {element['coordinates']}")
```

### Example 4: Vision-Guided Automation

```python
from ff_terminal.simple_tools.vision_tools import vision_guided_automation_tool

# Execute complex task with vision guidance
result = await vision_guided_automation_tool.execute(
    task="Click the Save button in the top right corner",
    verification_prompt="Is the file saved successfully?",
    max_attempts=3
)

if result.success:
    print(f"Task completed in {result.data['attempts']} attempts")
    print(f"Actions executed: {result.data['actions_executed']}")
    for action in result.data['action_results']:
        print(f"  - {action['action']['description']}: {action['success']}")
else:
    print(f"Task failed: {result.error}")
```

### Example 5: Prompt Caching with Z.AI

```python
from ff_terminal.core.prompt_caching import enable_anthropic_caching

# Prepare messages with large system prompt
messages = [
    {
        "role": "system",
        "content": "Very long system prompt with tool descriptions..." * 100
    },
    {"role": "user", "content": "What can you help me with?"}
]

# Enable caching
cached_messages, cached_tools, cache_keys = enable_anthropic_caching(
    messages=messages,
    tools=tools
)

# First call: writes to cache
response1 = await provider.chat_completion(cached_messages, cached_tools)

# Second call: reads from cache (90% cost reduction!)
response2 = await provider.chat_completion(cached_messages, cached_tools)

# Check cache statistics
from ff_terminal.core.prompt_caching import get_caching_stats
stats = get_caching_stats()
print(f"Cache hit ratio: {stats['cache_stats']['hit_ratio']:.1%}")
print(f"Tokens saved: {stats['token_stats']['tokens_saved']}")
print(f"Cost saved: ${stats['token_stats']['cost_saved']:.4f}")
```

---

## Key Takeaways

### Authentication
- **Z.AI API**: Uses `ANTHROPIC_AUTH_TOKEN` environment variable
- **Z.AI Vision**: Uses `Z_AI_API_KEY` with MCP subprocess
- **Headers**: Custom referer/title headers for attribution

### Structured Outputs
- Standardized response format across all providers
- Tool calls use OpenAI-compatible format
- Cost tracking with provider attribution

### Prompt Caching
- Automatic cache control headers for Anthropic API
- 90% cost reduction on cached content
- TTL management and statistics tracking

### Agent Integration
- Provider abstraction allows seamless switching
- Factory pattern for CLI-based provider selection
- Dual-path fallback (OpenAI format → LiteLLM Anthropic format)

### Vision Integration
- MCP protocol for subprocess communication
- JSON-RPC 2.0 for tool calls
- Screenshot capture → Vision analysis → Automation pipeline

---

## Additional Resources

- **Z.AI Documentation**: https://docs.z.ai/devpack/tool/claude
- **Z.AI API Keys**: https://z.ai/manage-apikey/apikey-list
- **Anthropic Prompt Caching**: https://docs.anthropic.com/claude/docs/prompt-caching
- **MCP Protocol**: https://modelcontextprotocol.io/

---

**Last Updated**: 2025-10-01
**FF-Terminal Version**: v3.0
**Z.AI Integration Status**: ✅ Production Ready
