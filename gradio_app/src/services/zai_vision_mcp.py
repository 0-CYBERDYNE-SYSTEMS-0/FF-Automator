"""
Z.AI Vision MCP Client Integration

This module provides integration with Z.AI Vision capabilities through the
Model Context Protocol (MCP) for advanced vision analysis and automation.
"""

import asyncio
import json
import os
import subprocess
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ZAIVisionMCPClient:
    """Z.AI Vision MCP client for computer vision and UI analysis"""

    def __init__(self):
        self.process = None
        self.server_capabilities = {}
        self.available_tools = {}
        self.initialized = False
        self.server_name = "zai-vision"

    async def start(self) -> bool:
        """Start the Z.AI Vision MCP server process and initialize connection"""
        try:
            logger.info("Starting Z.AI Vision MCP server")

            # Get Z.AI API key from environment
            zai_api_key = os.getenv("Z_AI_API_KEY")
            if not zai_api_key:
                logger.error("Z_AI_API_KEY environment variable not set")
                return False

            # Z.AI Vision MCP server command
            command = ["npx", "-y", "@z_ai/mcp-server"]

            # Environment for MCP server
            env = {
                "Z_AI_API_KEY": zai_api_key,
                "Z_AI_MODE": "ZAI"
            }

            # Create environment for subprocess
            subprocess_env = dict(os.environ)
            subprocess_env.update(env)

            # Start the MCP server process
            self.process = await asyncio.create_subprocess_exec(
                *command,
                env=subprocess_env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Initialize the MCP connection
            await self._initialize_connection()

            logger.info("Z.AI Vision MCP server started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start Z.AI Vision MCP server: {e}")
            if self.process:
                self.process.terminate()
                self.process = None
            return False

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
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "macos-use",
                        "version": "1.0.0"
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
                raise Exception("Failed to initialize Z.AI Vision MCP connection")

        except Exception as e:
            logger.error(f"Z.AI Vision MCP initialization failed: {e}")
            raise

    async def _load_tools(self):
        """Load available tools from Z.AI Vision MCP server"""
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
                logger.info(f"Loaded {len(self.available_tools)} tools from Z.AI Vision MCP")

                for tool_name, tool_info in self.available_tools.items():
                    logger.debug(
                        f"Available Z.AI Vision tool: {tool_name} - "
                        f"{tool_info.get('description', 'No description')}"
                    )

        except Exception as e:
            logger.error(f"Failed to load tools from Z.AI Vision MCP server: {e}")

    async def _send_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a JSON-RPC request and wait for response"""
        if not self.process or not self.process.stdin:
            raise Exception("MCP process not available")

        try:
            # Send request
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()

            # Read response
            response_line = await self.process.stdout.readline()
            if not response_line:
                raise Exception("No response from MCP server")

            response = json.loads(response_line.decode().strip())
            return response

        except Exception as e:
            logger.error(f"Failed to send MCP request: {e}")
            return None

    async def _send_notification(self, notification: Dict[str, Any]):
        """Send a JSON-RPC notification (no response expected)"""
        if not self.process or not self.process.stdin:
            raise Exception("MCP process not available")

        try:
            notification_json = json.dumps(notification) + "\n"
            self.process.stdin.write(notification_json.encode())
            await self.process.stdin.drain()

        except Exception as e:
            logger.error(f"Failed to send MCP notification: {e}")

    async def analyze_image(self, image_path: str, prompt: str) -> Optional[Dict[str, Any]]:
        """Analyze an image using Z.AI Vision"""
        if not self.initialized:
            raise Exception("Z.AI Vision MCP client not initialized")

        if "analyze_image" not in self.available_tools:
            raise Exception("analyze_image tool not available on Z.AI Vision MCP server")

        try:
            # Build tool call request
            tool_call_request = {
                "jsonrpc": "2.0",
                "id": hash(f"analyze_image_{asyncio.get_event_loop().time()}"),
                "method": "tools/call",
                "params": {
                    "name": "analyze_image",
                    "arguments": {
                        "image_source": image_path,
                        "prompt": prompt
                    }
                }
            }

            logger.info(f"Analyzing image with Z.AI Vision: {image_path}")

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
                logger.error("No valid response from Z.AI Vision analyze_image tool")
                return None

        except Exception as e:
            logger.error(f"Failed to analyze image with Z.AI Vision: {e}")
            return None

    async def capture_and_analyze_screen(self,
                                       analysis_type: str = "general",
                                       custom_prompt: str = "",
                                       region: str = "full") -> Optional[Dict[str, Any]]:
        """Capture screen and analyze with Z.AI Vision"""
        try:
            # Import screenshot capture functionality
            import subprocess
            import tempfile
            import time

            # Create temporary file for screenshot
            temp_dir = Path(tempfile.gettempdir())
            timestamp = int(time.time())
            screenshot_path = temp_dir / f"zai_vision_screenshot_{timestamp}.png"

            # Capture screenshot based on region
            if region == "full":
                cmd = ["screencapture", "-x", str(screenshot_path)]
            elif region == "active":
                cmd = ["screencapture", "-x", "-w", str(screenshot_path)]
            else:
                # Parse coordinates
                coords = [int(x.strip()) for x in region.split(',')]
                x, y, w, h = coords
                cmd = ["screencapture", "-x", "-R", f"{x},{y},{w},{h}", str(screenshot_path)]

            # Execute screenshot capture
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Screenshot capture failed: {result.stderr}")
                return None

            # Determine analysis prompt
            if custom_prompt:
                prompt = custom_prompt
            else:
                prompt = self._get_analysis_prompt(analysis_type)

            # Analyze screenshot
            analysis_result = await self.analyze_image(str(screenshot_path), prompt)

            # Clean up temporary file
            try:
                screenshot_path.unlink()
            except:
                pass

            return analysis_result

        except Exception as e:
            logger.error(f"Failed to capture and analyze screen: {e}")
            return None

    def _get_analysis_prompt(self, analysis_type: str) -> str:
        """Get analysis prompt based on type"""
        prompts = {
            "general": "Analyze this screenshot and describe what you see in detail.",
            "ui_elements": "Identify all UI elements (buttons, menus, text fields, etc.) in this screenshot with their coordinates.",
            "accessibility": "Analyze this interface for accessibility issues and suggest improvements.",
            "automation": "Identify elements that can be automated and suggest actions for UI automation.",
            "error_detection": "Look for error messages, warnings, or UI issues in this screenshot."
        }
        return prompts.get(analysis_type, prompts["general"])

    async def close(self):
        """Close the MCP connection and cleanup"""
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except Exception as e:
                logger.error(f"Error closing MCP process: {e}")
            finally:
                self.process = None
                self.initialized = False


# Global MCP client instance
_zai_vision_client = None


async def get_zai_vision_client() -> ZAIVisionMCPClient:
    """Get or create Z.AI Vision MCP client"""
    global _zai_vision_client

    if _zai_vision_client is None:
        _zai_vision_client = ZAIVisionMCPClient()

    # Start the client if not already started
    if not _zai_vision_client.initialized:
        success = await _zai_vision_client.start()
        if not success:
            raise RuntimeError("Failed to start Z.AI Vision MCP server")

    return _zai_vision_client


async def analyze_screenshot_with_zai(image_path: str,
                                    analysis_type: str = "general",
                                    custom_prompt: str = "") -> Optional[str]:
    """Convenience function to analyze a screenshot with Z.AI Vision"""
    try:
        client = await get_zai_vision_client()

        if custom_prompt:
            prompt = custom_prompt
        else:
            # Create a prompt based on analysis type
            prompts = {
                "general": "Analyze this screenshot and describe what you see in detail.",
                "ui_elements": "Identify all interactive UI elements with their coordinates and descriptions.",
                "accessibility": "Analyze this interface for accessibility issues and suggest improvements.",
                "automation": "Identify elements suitable for automation and suggest specific actions."
            }
            prompt = prompts.get(analysis_type, "Analyze this screenshot and describe what you see.")

        result = await client.analyze_image(image_path, prompt)

        if result and "analysis" in result:
            return result["analysis"]
        else:
            return None

    except Exception as e:
        logger.error(f"Failed to analyze screenshot with Z.AI: {e}")
        return None


def is_zai_vision_available() -> bool:
    """Check if Z.AI Vision is available"""
    try:
        # Check if required environment variables are set
        zai_api_key = os.getenv("Z_AI_API_KEY")
        if not zai_api_key:
            return False

        # Check if npx is available
        result = subprocess.run(["npx", "--version"], capture_output=True, text=True)
        return result.returncode == 0

    except Exception:
        return False