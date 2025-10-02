"""
Z.AI Vision Tools

This module provides tools for capturing screenshots and analyzing them
with Z.AI Vision capabilities through MCP.
"""

import os
import subprocess
import tempfile
import asyncio
import time
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

from ..services.zai_vision_mcp import get_zai_vision_client, analyze_screenshot_with_zai, is_zai_vision_available

@dataclass
class ToolResult:
    """Standard result format for tool operations"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ScreenshotCaptureTool:
    """Capture screenshots for Z.AI Vision analysis"""

    def __init__(self):
        self.name = "capture_screenshot"
        self.description = "Take a screenshot of the current screen for vision analysis"

    async def execute(self,
                     region: str = "full",
                     save_path: str = "",
                     **kwargs) -> ToolResult:
        """Capture a screenshot"""
        try:
            # Determine save path
            if not save_path:
                temp_dir = Path(tempfile.gettempdir())
                timestamp = int(time.time())
                save_path = str(temp_dir / f"zai_screenshot_{timestamp}.png")

            # Build screencapture command based on region
            if region == "full":
                cmd = ["screencapture", "-x", save_path]
            elif region == "active":
                cmd = ["screencapture", "-x", "-w", save_path]  # Active window
            else:
                # Parse x,y,width,height coordinates
                try:
                    coords = [int(x.strip()) for x in region.split(',')]
                    x, y, w, h = coords
                    cmd = ["screencapture", "-x", "-R", f"{x},{y},{w},{h}", save_path]
                except ValueError:
                    return ToolResult(
                        success=False,
                        error=f"Invalid region format: {region}. Use 'x,y,width,height'"
                    )

            # Execute screenshot capture
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                return ToolResult(
                    success=False,
                    error=f"Screenshot capture failed: {result.stderr}"
                )

            # Return path and metadata
            if os.path.exists(save_path):
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
            else:
                return ToolResult(
                    success=False,
                    error="Screenshot file was not created"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Screenshot capture error: {str(e)}"
            )


class ZaiVisionAnalysisTool:
    """Analyze screenshots using Z.AI Vision AI"""

    def __init__(self):
        self.name = "zai_vision_analysis"
        self.description = "Analyze screenshots using Z.AI Vision AI"
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
                     **kwargs) -> ToolResult:
        """Analyze image using Z.AI Vision"""
        try:
            # Validate image exists
            if not os.path.exists(image_path):
                return ToolResult(
                    success=False,
                    error=f"Image not found: {image_path}"
                )

            # Get analysis prompt
            if custom_prompt:
                prompt = custom_prompt
            else:
                prompt = self._get_analysis_prompt(analysis_type)

            # Use convenience function for analysis
            analysis_result = await analyze_screenshot_with_zai(
                image_path=image_path,
                analysis_type=analysis_type,
                custom_prompt=custom_prompt
            )

            if analysis_result:
                processed_data = self._post_process_analysis(analysis_result, analysis_type)
                return ToolResult(
                    success=True,
                    data={
                        "analysis": analysis_result,
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

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Z.AI Vision analysis error: {str(e)}"
            )

    def _get_analysis_prompt(self, analysis_type: str) -> str:
        """Get analysis prompt based on type"""
        prompts = {
            "general": "Analyze this screenshot and provide a detailed description of what you see.",
            "ui_elements": "Identify all interactive UI elements (buttons, menus, text fields, links, etc.) and provide their coordinates and descriptions.",
            "accessibility": "Analyze this interface for accessibility issues and provide specific suggestions for improvement.",
            "automation": "Identify elements that can be automated and suggest specific actions that could be performed.",
            "error_detection": "Look for error messages, warnings, failed validations, or other UI issues in this screenshot.",
            "content_analysis": "Analyze the content on screen and summarize key information, data, or text present."
        }
        return prompts.get(analysis_type, prompts["general"])

    def _post_process_analysis(self, analysis_text: str, analysis_type: str) -> Dict[str, Any]:
        """Post-process analysis text to extract structured data"""
        processed = {
            "summary": analysis_text[:200] + "..." if len(analysis_text) > 200 else analysis_text,
            "analysis_type": analysis_type
        }

        # Extract specific information based on analysis type
        if analysis_type == "ui_elements":
            # Try to extract UI elements information
            processed["ui_elements"] = self._extract_ui_elements(analysis_text)
        elif analysis_type == "accessibility":
            processed["accessibility_issues"] = self._extract_accessibility_issues(analysis_text)
        elif analysis_type == "error_detection":
            processed["errors_found"] = self._extract_errors(analysis_text)

        return processed

    def _extract_ui_elements(self, text: str) -> list:
        """Extract UI elements from analysis text"""
        elements = []
        # Simple extraction - in practice, this would be more sophisticated
        lines = text.split('\n')
        current_element = {}

        for line in lines:
            line = line.strip()
            if line.lower() in ['button:', 'menu:', 'field:', 'link:']:
                if current_element:
                    elements.append(current_element)
                current_element = {"type": line[:-1], "description": ""}
            elif current_element and 'description' in current_element:
                if not current_element['description']:
                    current_element['description'] = line
                else:
                    current_element['description'] += ' ' + line

        if current_element:
            elements.append(current_element)

        return elements

    def _extract_accessibility_issues(self, text: str) -> list:
        """Extract accessibility issues from analysis text"""
        issues = []
        lines = text.split('\n')
        for line in lines:
            line = line.strip().lower()
            if any(keyword in line for keyword in ['issue', 'problem', 'missing', 'should', 'need']):
                issues.append(line)
        return issues

    def _extract_errors(self, text: str) -> list:
        """Extract errors from analysis text"""
        errors = []
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['error', 'failed', 'warning', 'invalid']):
                errors.append(line)
        return errors


class VisionGuidedAutomationTool:
    """Execute automation tasks guided by Z.AI Vision analysis"""

    def __init__(self):
        self.name = "vision_guided_automation"
        self.description = "Perform UI automation guided by Z.AI Vision analysis"

    async def execute(self,
                     task: str,
                     verification_prompt: str = "",
                     max_attempts: int = 3,
                     **kwargs) -> ToolResult:
        """Execute automation task with vision guidance"""
        try:
            # Get MCP client
            mcp_client = await get_zai_vision_client()

            actions_executed = []
            action_results = []

            for attempt in range(max_attempts):
                # Capture current screen
                screenshot_result = await ScreenshotCaptureTool().execute(region="full")
                if not screenshot_result.success:
                    return ToolResult(
                        success=False,
                        error=f"Failed to capture screen on attempt {attempt + 1}"
                    )

                # Analyze current screen state
                analysis_result = await ZaiVisionAnalysisTool().execute(
                    image_path=screenshot_result.data["screenshot_path"],
                    custom_prompt=f"Task: {task}\n\nCurrent state analysis: What actions are needed to complete this task?"
                )

                if not analysis_result.success:
                    return ToolResult(
                        success=False,
                        error=f"Vision analysis failed on attempt {attempt + 1}"
                    )

                # Extract actions from analysis (simplified - in practice would use more sophisticated parsing)
                analysis_text = analysis_result.data["analysis"]
                actions = self._parse_actions_from_analysis(analysis_text)

                if not actions:
                    # Task may be complete or unclear
                    if verification_prompt:
                        verification_result = await ZaiVisionAnalysisTool().execute(
                            image_path=screenshot_result.data["screenshot_path"],
                            custom_prompt=verification_prompt
                        )
                        if verification_result.success:
                            verification_analysis = verification_result.data["analysis"]
                            if "complete" in verification_analysis.lower() or "success" in verification_analysis.lower():
                                return ToolResult(
                                    success=True,
                                    data={
                                        "task": task,
                                        "attempts": attempt + 1,
                                        "actions_executed": actions_executed,
                                        "action_results": action_results,
                                        "status": "completed",
                                        "verification": verification_analysis
                                    }
                                )

                    return ToolResult(
                        success=False,
                        error=f"No clear actions identified on attempt {attempt + 1}"
                    )

                # Execute actions (placeholder - would integrate with actual automation system)
                for action in actions:
                    action_result = {
                        "action": action,
                        "success": True,  # Placeholder
                        "message": "Action executed successfully"  # Placeholder
                    }
                    actions_executed.append(action)
                    action_results.append(action_result)

                    # Short delay between actions
                    await asyncio.sleep(0.5)

            # Check final state
            final_screenshot = await ScreenshotCaptureTool().execute(region="full")
            if final_screenshot.success and verification_prompt:
                final_verification = await ZaiVisionAnalysisTool().execute(
                    image_path=final_screenshot.data["screenshot_path"],
                    custom_prompt=verification_prompt
                )

                if final_verification.success:
                    return ToolResult(
                        success=True,
                        data={
                            "task": task,
                            "attempts": max_attempts,
                            "actions_executed": actions_executed,
                            "action_results": action_results,
                            "status": "completed",
                            "final_verification": final_verification.data["analysis"]
                        }
                    )

            return ToolResult(
                success=False,
                data={
                    "task": task,
                    "attempts": max_attempts,
                    "actions_executed": actions_executed,
                    "action_results": action_results,
                    "status": "max_attempts_reached"
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Vision-guided automation error: {str(e)}"
            )

    def _parse_actions_from_analysis(self, analysis_text: str) -> list:
        """Parse suggested actions from vision analysis (simplified)"""
        actions = []
        lines = analysis_text.split('\n')

        for line in lines:
            line = line.strip()
            # Look for action indicators in the text
            if any(keyword in line.lower() for keyword in ['click', 'type', 'select', 'press']):
                actions.append({
                    "description": line,
                    "type": "action"
                })

        return actions


# Tool instances
screenshot_capture_tool = ScreenshotCaptureTool()
zai_vision_analysis_tool = ZaiVisionAnalysisTool()
vision_guided_automation_tool = VisionGuidedAutomationTool()


def is_zai_vision_enabled() -> bool:
    """Check if Z.AI Vision is available and enabled"""
    return is_zai_vision_available()


async def capture_and_analyze(analysis_type: str = "general",
                            region: str = "full",
                            custom_prompt: str = "") -> Optional[Dict[str, Any]]:
    """Convenience function to capture screenshot and analyze with Z.AI Vision"""
    try:
        # Capture screenshot
        screenshot_result = await screenshot_capture_tool.execute(region=region)
        if not screenshot_result.success:
            return None

        # Analyze screenshot
        analysis_result = await zai_vision_analysis_tool.execute(
            image_path=screenshot_result.data["screenshot_path"],
            analysis_type=analysis_type,
            custom_prompt=custom_prompt
        )

        if analysis_result.success:
            return analysis_result.data
        else:
            return None

    except Exception as e:
        print(f"Error in capture_and_analyze: {e}")
        return None