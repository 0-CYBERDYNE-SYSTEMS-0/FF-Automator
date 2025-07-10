#!/usr/bin/env python3
"""
FastAPI backend for the elegant JavaScript interface to macOS automation.
Provides REST endpoints and WebSocket streaming for real-time agent communication.
"""

import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv, set_key
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.websockets import WebSocketState
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from mlx_use.agent.prompts import SystemPrompt

# Import from existing project
from mlx_use.agent.service import Agent
from mlx_use.agent.views import ActionResult
from mlx_use.automation import (
	AutomationExecutor,
	AutomationRecorder,
	AutomationScheduler,
	AutomationService,
	SavedAutomation,
	get_all_templates,
)
from mlx_use.automation.models import AutomationMetadata
from mlx_use.controller.service import Controller

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ChatSystemPromptWithCustom(SystemPrompt):
	"""System prompt optimized for chat interactions with macOS automation that supports custom messages"""

	def __init__(
		self, action_description: str, current_date: datetime, max_actions_per_step: int = 10, custom_message: str = None
	):
		"""Initialize with optional custom message"""
		super().__init__(action_description, current_date, max_actions_per_step)
		self.custom_message = custom_message

	def important_rules(self) -> str:
		"""Enhanced chat rules for multi-step autonomous execution with conversational capabilities"""
		text = """
1. RESPONSE FORMAT:
   You must ALWAYS respond with a valid JSON object that has EXACTLY two keys:
     {
     "current_state": {
       "evaluation_previous_goal": "Success|Failed|Unknown - Analyze if the user's request was completed",
       "memory": "What you've done and learned from this interaction. TRACK REPETITIVE PATTERNS: Note if you're repeating actions or responses.", 
       "next_goal": "How to help the user next, or 'COMPLETE' if task is finished (then use 'done' action)"
     },
     "action": [
       {
         "action_name": {
           // action parameters
         }
       }
     ]
   }

2. MULTI-STEP EXECUTION:
   - You are operating in AUTONOMOUS mode - continue working until the task is complete
   - Break complex requests into multiple steps and execute them sequentially
   - Use "reply" action to communicate progress and explain what you're doing
   - For complex tasks like "open Safari, go to website, get info, make note" - execute ALL steps
   - Don't stop after the first action - keep going until the entire request is fulfilled

3. CONVERSATIONAL BEHAVIOR:
   - Provide progress updates using "reply" actions between automation steps
   - Explain what you're doing and what you've accomplished
   - Ask for clarification only when absolutely necessary
   - Remember previous actions and reference them in conversation
   - Be proactive in suggesting follow-up actions

4. ACTION SELECTION STRATEGY:
   - For simple questions/chat: Use "reply" action with your response
   - For automation requests: Use appropriate macOS actions AND provide "reply" updates
   - For multi-step tasks: Chain actions with progress "reply" messages
   - **For task completion: Use "done" action with comprehensive results - NOT reply actions**
   - **CRITICAL**: The ONLY way to end execution is with "done" - saying "task finished" with reply is NOT enough
   - Always prioritize task completion over stopping early
   - **NEVER continue execution after stating the task is complete - immediately use "done"**

5. TASK QUEUE AWARENESS:
   - You can handle multiple tasks and follow-up requests
   - If user mentions additional tasks while working, note them for later
   - Complete current task before moving to next unless redirected
   - Reference completed tasks in conversation context

6. EXAMPLES:
   - User: "Open Safari and go to apple.com" → open_app + navigate + reply with confirmation
   - User: "Create a note with today's weather" → open_app + create note + reply about limitation + suggest alternatives
   - User: "Find my system info and email it to myself" → open app + find info + open mail + compose + send + reply with confirmation
   - Complex: "Open Calculator, do 5*4, then open Notes and write the result" → Execute ALL steps autonomously

7. CONTEXT RETENTION:
   - Remember what apps are open and what you've done
   - Reference previous actions in current responses
   - Build on previous work rather than starting fresh
   - Maintain conversation flow while executing tasks

8. REPETITIVE LOOP DETECTION:
   - **CRITICAL**: Check your conversation history before each action to avoid repetitive loops
   - If you've performed the same action or said the same thing 2+ times with no progress, STOP and use "done"
   - Common loop patterns to detect:
     * Repeatedly saying "task finished" or "task complete" without using "done" action
     * Clicking the same element multiple times with identical results
     * Repeating the same error message or failed action
     * Making identical progress updates with no actual advancement
     * Continuously using "reply" actions with the same message
   - **Self-awareness check**: Ask yourself "Have I done this exact same thing before in this conversation?"
   - If stuck in a loop: Use "done" action immediately with explanation: "Detected repetitive behavior, ending execution"
   - **Prevention**: Always vary your approach if the first attempt doesn't work - try alternatives, not repetition
   - Monitor your "memory" field for repetitive patterns and break the cycle with decisive action
"""
		# Add custom message if provided
		if self.custom_message:
			text += f'\n\n9. CUSTOM INSTRUCTIONS:\n   {self.custom_message}\n'

		return text

	def get_user_prompt(
		self,
		task: str,
		action_descriptions: str,
		state: str,
		include_attributes: List[str],
		max_error_length: int,
		last_result: Optional[list] = None,
		step_info: Optional[any] = None,
	) -> str:
		"""Enhanced chat prompt with multi-step awareness and conversation context"""

		prompt = f"""You are an AI assistant for macOS automation with AUTONOMOUS MULTI-STEP capabilities. You execute complex tasks until completion while maintaining conversational interaction.

CRITICAL LOOP PREVENTION:
- Before each response, review your conversation history to detect repetitive patterns
- If you've said "task finished", "task complete", or similar 2+ times, immediately use "done" action
- If you're repeating the same action with identical results, stop and use "done" with explanation
- The ONLY way to end execution is the "done" action - not repeated statements or "reply" actions
- Monitor your memory field for repetitive patterns and break cycles immediately

BROWSER WINDOW PROTECTION:
- **CRITICAL**: NEVER navigate URLs in current browser tabs - always open NEW WINDOWS/TABS
- Use AppleScript to create new browser windows: "tell application \"Safari\" to make new document"
- Never refresh or navigate away from localhost interfaces - protect the current UI session

AVAILABLE ACTIONS:
{action_descriptions}

CURRENT TASK: {task}

IMPORTANT BEHAVIORAL RULES:
{self.important_rules()}

CURRENT STATE:
{state if state else 'Starting conversation - no app is currently active.'}

CONVERSATION CONTEXT:
- You are in AUTONOMOUS MODE - execute ALL steps needed to complete the user's request
- Don't stop after one action - continue until the entire task is finished
- Use "reply" actions to provide progress updates and maintain conversation
- Remember what you've accomplished and build on previous actions
"""

		if last_result:
			prompt += '\nPREVIOUS ACTION RESULTS:\n'
			for result in last_result:
				if result.extracted_content:
					prompt += f'✅ {result.extracted_content}\n'
				if result.error:
					error = result.error[:max_error_length] if max_error_length > 0 else result.error
					prompt += f'❌ Error: {error}\n'

		prompt += f"""
TASK ANALYSIS:
- If this is a simple conversation/question, use the "reply" action
- If this requires macOS automation, use the appropriate actions
- Always communicate clearly about what you're doing

Remember: You can both chat naturally AND perform automation tasks. Choose the right approach for each user message.

Current date and time: {self.current_date}
Maximum actions per step: {self.max_actions_per_step}

Respond with valid JSON following the exact format specified above."""

		return prompt


class ChatSystemPrompt(ChatSystemPromptWithCustom):
	"""System prompt optimized for chat interactions with macOS automation (backward compatibility)"""

	def important_rules(self) -> str:
		"""Chat-optimized rules that emphasize conversational responses"""
		text = """
1. RESPONSE FORMAT:
   You must ALWAYS respond with a valid JSON object that has EXACTLY two keys:
     {
     "current_state": {
       "evaluation_previous_goal": "Success|Failed|Unknown - Analyze if the user's request was completed",
       "memory": "What you've done and learned from this interaction. TRACK REPETITIVE PATTERNS: Note if you're repeating actions or responses.", 
       "next_goal": "How to help the user next, or 'COMPLETE' if task is finished (then use 'done' action)"
     },
     "action": [
       {
         "action_name": {
           // action parameters
         }
       }
     ]
   }

2. CHAT BEHAVIOR:
   - Use the "reply" action for conversational responses that don't need automation
   - Use macOS actions (open_app, click_element, etc.) when the user asks for specific tasks
   - Always be helpful and explain what you're doing
   - If you can't complete a task, explain why and suggest alternatives

3. ACTION SELECTION:
   - For simple questions/chat: Use "reply" action with your response
   - For automation requests: Use appropriate macOS actions (open_app, click_element, etc.)
   - For task completion: Use "done" action with final results
   - You can chain multiple actions, but prioritize clear communication

4. EXAMPLES:
   - User: "How are you?" → Use "reply" action
   - User: "Open Notes app" → Use "open_app" action then "reply" to confirm
   - User: "What's the weather?" → Use "reply" to explain you can't check weather directly
   - User: "Find my system info note" → Use "open_app" for Notes, then search actions
"""
		return text

	def get_user_prompt(
		self,
		task: str,
		action_descriptions: str,
		state: str,
		include_attributes: List[str],
		max_error_length: int,
		last_result: Optional[list] = None,
		step_info: Optional[any] = None,
	) -> str:
		"""Chat-optimized user prompt"""

		prompt = f"""You are a helpful AI assistant for macOS automation. You can both have conversations and perform automation tasks.

AVAILABLE ACTIONS:
{action_descriptions}

CURRENT TASK: {task}

IMPORTANT BEHAVIORAL RULES:
{self.important_rules()}

CURRENT STATE:
{state if state else 'Starting conversation - no app is currently active.'}
"""

		if last_result:
			prompt += '\nPREVIOUS ACTION RESULTS:\n'
			for result in last_result:
				if result.extracted_content:
					prompt += f'✅ {result.extracted_content}\n'
				if result.error:
					error = result.error[:max_error_length] if max_error_length > 0 else result.error
					prompt += f'❌ Error: {error}\n'

		prompt += f"""
TASK ANALYSIS:
- If this is a simple conversation/question, use the "reply" action
- If this requires macOS automation, use the appropriate actions
- Always communicate clearly about what you're doing

Remember: You can both chat naturally AND perform automation tasks. Choose the right approach for each user message.

Current date and time: {self.current_date}
Maximum actions per step: {self.max_actions_per_step}

Respond with valid JSON following the exact format specified above."""

		return prompt


class SystemPromptWithCustom(SystemPrompt):
	"""SystemPrompt class that supports custom messages"""

	def __init__(
		self, action_description: str, current_date: datetime, max_actions_per_step: int = 10, custom_message: str = None
	):
		"""Initialize with optional custom message"""
		super().__init__(action_description, current_date, max_actions_per_step)
		self.custom_message = custom_message

	def important_rules(self) -> str:
		"""Returns a string containing important rules for the system, with custom message if provided"""
		text = """
1. RESPONSE FORMAT:
   You must ALWAYS respond with a valid JSON object that has EXACTLY two keys:
     {
     "current_state": {
       "evaluation_previous_goal": "Success|Failed|Unknown - Use UI context elements to verify outcomes (e.g., results in context). Use action results to confirm execution when UI changes are delayed or unclear.",
       "memory": "What you've done and need to remember. TRACK REPETITIVE PATTERNS: Note if you're repeating actions or responses. Include action count for similar attempts.",
       "next_goal": "Next step to achieve, or 'COMPLETE' if task is finished (then use 'done' action)"
     },
     "action": [
       {
         "one_action_name": {
           // action-specific parameter
         }
       },
       // ... more actions in sequence
     ]
   }'

2. ACTIONS: You can specify multiple actions in the list to be executed in sequence. But always specify only one action name per item.
    - Always start with open_app to ensure the correct app is active.
    - For stable UIs (e.g., Calculator), batch actions up to max_actions_per_step.
    - For dynamic UIs (e.g., Mail), perform one action at a time due to potential refreshes.


3. APP HANDLING:
   - App names are case-sensitive (e.g. 'Microsoft Excel', 'Calendar').
   - Always use the correct app for the task. (e.g. calculator for calculations, mail for sending emails, browser for browsing, etc.)
   - Never assume apps are already open.
   - When opening a browser, always open a new window with AppleScript.
   - Common app mappings:
       * Calendar app may appear as 'iCal' or 'com.apple.iCal'.
       * Excel may appear as 'Microsoft Excel' or 'com.microsoft.Excel'.
       * Messages may appear as 'Messages' or 'com.apple.MobileSMS'.

4. ELEMENT INTERACTION:
   - Interactive elements: "[index][:]<type> [interactive]" (e.g., "1[:]<AXButton>").
   - Context elements: "_[:]<type> [context]" (e.g., "_[:]<AXStaticText value='20'>").
   - Use context elements to verify outcomes (e.g., check results after actions).
   - Use attributes (description, title, value) to identify elements accurately.
   - When providing an element index to click, use the actions list attribute to choose which action to use.

5. TASK COMPLETION:
   - Use the "done" action when the task is complete.
   - Don't hallucinate actions.
   - After performing actions, verify the outcome using context elements in the UI tree.
   - For tasks like calculations, always verify the result using context elements before marking as complete.
   - For tasks like playing media, check the current track or playback status via AppleScript.
   - If verification fails, attempt retries or alternative approaches before using "done".
   - Include all task results in the "done" action text.
   - If stuck after 3 attempts, use "done" with error details.
   - If task is failed, provide the best explanation of what went wrong with the "done" action.
   - Stable UIs (e.g., Calculator): Element indices remain consistent across actions, Batch up to max_actions_per_step actions (e.g., click "5", "+", "3", "=").
   - Dynamic UIs (e.g., Mail): Elements may refresh or reorder after actions, perform one action at a time.

6. NAVIGATION & ERROR HANDLING:
   - **CRITICAL**: Never repeat the same failed action more than twice - try alternatives immediately
   - If click_element fails repeatedly on same index, STOP and try:
     * Different element indices with similar functionality
     * AppleScript approach for the same task
     * Keyboard shortcuts or menu navigation
     * Alternative UI paths (toolbars, context menus, etc.)
   - If an element isn't found, search for alternatives using descriptions or attributes.
   - If text input fails, ensure the element is a text field or try AppleScript.
   - If submit fails, try click_element on the submit button instead.
   - If the UI tree fails with "Window not found" or error `-25212`, use open_app to open the app again.
   - Before interacting, verify the element is enabled (check `enabled="True"` in attributes). If not, find an alternative or use AppleScript.
   - **Failure Recovery Strategy**:
     * 1st attempt: Try the direct UI approach
     * 2nd attempt: Try a different element or parameter variation  
     * 3rd attempt: Switch to AppleScript or keyboard shortcuts
     * 4th attempt: Try completely different approach (menus, drag-drop, etc.)
     * After 4 attempts: Use "done" with explanation of what was attempted

7. APPLESCRIPT SUPPORT:
   - Use AppleScript for precise control (e.g., creating a note directly) or when UI interactions fail after retries.
   - Use this for complex operations not possible through UI interactions.
   - **File Operations**: Always use proper path formats and check existence first
   - **Path Handling**: Use POSIX file paths for cross-compatibility: `POSIX file "/Users/username/folder"`
   - Always use AppleScript with the correct command syntax.
   - Examples: 
        - Create folder: {"run_apple_script": {"script": "tell application \"Finder\" to make new folder at desktop with properties {name:\"Screenshots\"}"}}
        - Move files: {"run_apple_script": {"script": "tell application \"Finder\" to move (files of desktop whose name starts with \"Screenshot\") to folder \"Screenshots\" of desktop"}}
        - Rename file: {"run_apple_script": {"script": "tell application \"Finder\" to set name of file \"oldname.png\" of desktop to \"newname.png\""}}
        - Text-to-speech: {"run_apple_script": {"script": "say \"Task complete\""}}
        - Check file existence: {"run_apple_script": {"script": "tell application \"Finder\" to exists file \"filename\" of desktop"}}
"""
		# Add custom message if provided
		if self.custom_message:
			text += f'\n\n8. CUSTOM INSTRUCTIONS:\n   {self.custom_message}\n'

		text += f'   - max_actions_per_step: {self.max_actions_per_step}'
		return text


class ConversationMemory:
	"""Manages conversation context and memory across multiple interactions"""

	def __init__(self):
		self.conversation_history = []
		self.completed_actions = []
		self.current_context = {}
		self.task_queue = []
		self.learned_info = {}

	def add_user_message(self, message: str):
		"""Add user message to conversation history"""
		self.conversation_history.append({'type': 'user', 'content': message, 'timestamp': datetime.now().isoformat()})

	def add_agent_response(self, response: str, actions_taken: List[str] = None):
		"""Add agent response and actions taken"""
		self.conversation_history.append(
			{'type': 'agent', 'content': response, 'actions_taken': actions_taken or [], 'timestamp': datetime.now().isoformat()}
		)
		if actions_taken:
			self.completed_actions.extend(actions_taken)

	def add_learned_info(self, key: str, value: str):
		"""Add learned information for future reference"""
		self.learned_info[key] = value

	def get_context_summary(self) -> str:
		"""Get a summary of the conversation context"""
		if not self.conversation_history:
			return 'No previous conversation.'

		recent_messages = self.conversation_history[-5:]  # Last 5 messages
		context = 'Recent conversation:\n'
		for msg in recent_messages:
			context += f'- {msg["type"]}: {msg["content"][:100]}...\n'

		if self.completed_actions:
			context += f'\nCompleted actions: {", ".join(self.completed_actions[-5:])}'

		if self.learned_info:
			context += f'\nLearned information: {self.learned_info}'

		return context


class ChatTaskQueue:
	"""Manages task queue for chat agent with follow-ups and dependencies"""

	def __init__(self):
		self.tasks = []
		self.current_task = None
		self.completed_tasks = []
		self.task_id_counter = 0

	def add_task(self, task: str, priority: str = 'normal', depends_on: str = None):
		"""Add a new task to the queue"""
		self.task_id_counter += 1
		task_item = {
			'id': str(self.task_id_counter),
			'task': task,
			'priority': priority,
			'depends_on': depends_on,
			'status': 'pending',
			'created_at': datetime.now().isoformat(),
		}

		if priority == 'high':
			self.tasks.insert(0, task_item)
		else:
			self.tasks.append(task_item)

		return task_item['id']

	def get_next_task(self):
		"""Get the next task to execute"""
		if not self.tasks:
			return None

		# Find first task with no dependencies or completed dependencies
		for task in self.tasks:
			if task['depends_on'] is None or task['depends_on'] in [t['id'] for t in self.completed_tasks]:
				return task

		return None

	def start_task(self, task_id: str):
		"""Mark a task as started"""
		for task in self.tasks:
			if task['id'] == task_id:
				task['status'] = 'in_progress'
				self.current_task = task
				break

	def complete_task(self, task_id: str, result: str = None):
		"""Mark a task as completed"""
		for i, task in enumerate(self.tasks):
			if task['id'] == task_id:
				task['status'] = 'completed'
				task['result'] = result
				task['completed_at'] = datetime.now().isoformat()
				self.completed_tasks.append(task)
				self.tasks.pop(i)
				if self.current_task and self.current_task['id'] == task_id:
					self.current_task = None
				break

	def has_tasks(self) -> bool:
		"""Check if there are pending tasks"""
		return len(self.tasks) > 0

	def get_queue_status(self) -> dict:
		"""Get current queue status"""
		return {
			'pending_tasks': len(self.tasks),
			'current_task': self.current_task,
			'completed_tasks': len(self.completed_tasks),
			'next_task': self.get_next_task(),
		}


class ChatAgent(Agent):
	"""Enhanced Agent with conversational capabilities and task queue management"""

	def __init__(self, *args, **kwargs):
		# Extract chat-specific parameters
		self.conversation_memory = kwargs.pop('conversation_memory', ConversationMemory())
		self.task_queue = kwargs.pop('task_queue', ChatTaskQueue())
		self.streaming_callback = kwargs.pop('streaming_callback', None)
		self.needs_input_callback = kwargs.pop('needs_input_callback', None)
		self.client_id = kwargs.pop('client_id', None)
		self.connection_manager = kwargs.pop('connection_manager', None)
		self.interrupt_flag = False
		self.redirect_message = None

		super().__init__(*args, **kwargs)

	async def run_conversational(self, max_steps: int = 50) -> dict:
		"""Run the agent with conversational capabilities and task queue management"""
		results = []

		try:
			# Check if stopped before starting
			if self._stopped:
				logger.info('Agent stopped before execution')
				return {'results': [], 'success': False, 'message': 'Agent stopped'}

			# Process current task or get next from queue
			if not self.task_queue.current_task:
				next_task = self.task_queue.get_next_task()
				if next_task:
					self.task_queue.start_task(next_task['id'])
					self.task = next_task['task']
				else:
					# No tasks in queue, create one from current task
					task_id = self.task_queue.add_task(self.task)
					self.task_queue.start_task(task_id)

			# Send initial status
			if self.streaming_callback:
				await self.streaming_callback(
					{
						'type': 'chat_stream_update',
						'data': {
							'status': 'starting',
							'message': f'Starting task: {self.task}',
							'current_task': self.task_queue.current_task,
							'queue_status': self.task_queue.get_queue_status(),
						},
					}
				)

			# Execute the task with streaming updates
			history = await self.run_with_streaming(max_steps)

			# Process results
			if history.is_done():
				final_result = (
					history.history[-1].result[-1].extracted_content
					if history.history and history.history[-1].result
					else 'Task completed successfully'
				)

				# Mark current task as completed
				if self.task_queue.current_task:
					self.task_queue.complete_task(self.task_queue.current_task['id'], final_result)

				# Add to conversation memory
				actions_taken = self._extract_actions_from_history(history)
				self.conversation_memory.add_agent_response(final_result, actions_taken)

				results.append({'task': self.task, 'result': final_result, 'success': True, 'actions_taken': actions_taken})

				# Send completion status
				if self.streaming_callback:
					await self.streaming_callback(
						{
							'type': 'chat_stream_update',
							'data': {
								'status': 'completed',
								'message': final_result,
								'task_completed': self.task_queue.current_task,
								'queue_status': self.task_queue.get_queue_status(),
							},
						}
					)

			else:
				# Task failed or hit max steps
				error_msg = 'Task failed to complete within maximum steps'
				if self.task_queue.current_task:
					self.task_queue.complete_task(self.task_queue.current_task['id'], error_msg)

				results.append({'task': self.task, 'result': error_msg, 'success': False, 'actions_taken': []})

			# Check for more tasks in queue only if still connected and not stopped
			if self.task_queue.has_tasks() and self._is_still_connected() and not self._stopped:
				next_task = self.task_queue.get_next_task()
				if next_task and self.streaming_callback:
					await self.streaming_callback(
						{
							'type': 'chat_stream_update',
							'data': {
								'status': 'next_task',
								'message': f'Moving to next task: {next_task["task"]}',
								'queue_status': self.task_queue.get_queue_status(),
							},
						}
					)

					# Continue with next task only if still connected and not stopped
					if self._is_still_connected() and not self._stopped:
						self.task = next_task['task']
						next_results = await self.run_conversational(max_steps)
						results.extend(next_results['results'])
					else:
						logger.info(f'Client {self.client_id} disconnected, stopping task queue processing')

		except Exception as e:
			logger.error(f'Error in conversational run: {e}')
			results.append({'task': self.task, 'result': f'Error: {str(e)}', 'success': False, 'actions_taken': []})

		return {
			'results': results,
			'conversation_memory': self.conversation_memory,
			'queue_status': self.task_queue.get_queue_status(),
		}

	async def run_with_streaming(self, max_steps: int):
		"""Run the agent with streaming callbacks"""
		# Execute initial actions if provided
		if self.initial_actions:
			result = await self.controller.multi_act(self.initial_actions, self.mac_tree_builder)
			self._last_result = result

		# Multi-step execution loop with streaming
		for step in range(max_steps):
			# Check if client is still connected
			if not self._is_still_connected():
				logger.info(f'Client {self.client_id} disconnected, stopping execution')
				break

			# Check if agent was stopped
			if self._stopped:
				logger.info('Agent stopped by user, ending execution')
				break

			# Check for interruption or redirection
			if self.interrupt_flag:
				if self.redirect_message:
					self.task = self.redirect_message
					self.redirect_message = None
				self.interrupt_flag = False

			if self._too_many_failures():
				break

			# Check control flags (pause/stop)
			if not await self._handle_control_flags():
				break

			# Send step update
			if self.streaming_callback:
				await self.streaming_callback(
					{
						'type': 'chat_stream_update',
						'data': {
							'status': 'running',
							'message': f'Step {step + 1}: Processing...',
							'step': step + 1,
							'max_steps': max_steps,
							'current_task': self.task_queue.current_task,
						},
					}
				)

			# Execute one step
			await self.step()

			# Send step completion update with actions taken
			if self.streaming_callback and self._last_result:
				actions_summary = self._summarize_actions(self._last_result)
				# Extract action names for tracking
				actions_taken = []
				for result in self._last_result:
					if hasattr(result, 'action_name'):
						actions_taken.append(result.action_name)

				await self.streaming_callback(
					{
						'type': 'chat_stream_update',
						'data': {
							'status': 'step_completed',
							'message': f'Step {step + 1} completed: {actions_summary}',
							'step': step + 1,
							'max_steps': max_steps,
							'actions_taken': actions_taken[0] if len(actions_taken) == 1 else actions_taken,
						},
					}
				)

			# Check if task is complete
			if self.history.is_done():
				logger.info('✅ Task completed successfully')
				break

			# Additional safety check: If last action was "done", force break
			if self._last_result and len(self._last_result) > 0 and self._last_result[-1].is_done:
				logger.info('✅ Done action detected - forcing task completion')
				break
		else:
			logger.info('❌ Failed to complete task in maximum steps')

		return self.history

	def interrupt_execution(self, redirect_message: str = None):
		"""Interrupt current execution and optionally redirect to new task"""
		self.interrupt_flag = True
		if redirect_message:
			self.redirect_message = redirect_message

	def add_task_to_queue(self, task: str, priority: str = 'normal'):
		"""Add a new task to the queue"""
		return self.task_queue.add_task(task, priority)

	def _extract_actions_from_history(self, history) -> List[str]:
		"""Extract action names from agent history"""
		actions = []
		for step in history.history:
			if step.result:
				for result in step.result:
					if hasattr(result, 'action_name'):
						actions.append(result.action_name)
		return actions

	def _summarize_actions(self, results: List[ActionResult]) -> str:
		"""Summarize actions taken in this step"""
		if not results:
			return 'No actions taken'

		summaries = []
		for result in results:
			if hasattr(result, 'action_name'):
				summaries.append(result.action_name)
			elif result.extracted_content:
				summaries.append(result.extracted_content[:50] + '...')

		return ', '.join(summaries) if summaries else 'Actions completed'

	def _is_still_connected(self) -> bool:
		"""Check if the client is still connected"""
		if not self.client_id or not self.connection_manager:
			return True  # Default to True if no connection info
		return self.connection_manager.is_connection_active(self.client_id)


# Import the exact same models from the Gradio app
LLM_MODELS = {
	'OpenAI': [
		# Latest 2025 models
		'gpt-4.1-mini',
		'gpt-4.1',
		'gpt-4.1-nano',
		'o3',
		'o4-mini',
		'o3-pro',
		'o4-mini-high',
		# Existing models
		'gpt-4o',
		'gpt-4o-mini',
		'o3-mini',
		'gpt-4-turbo',
		'gpt-3.5-turbo',
	],
	'Anthropic': [
		# Claude 4 models (2025)
		'claude-4-opus',
		'claude-4-sonnet',
		# Claude 3.5 models
		'claude-3-5-sonnet-20241022',
		'claude-3-5-sonnet-20240620',
		'claude-3-5-haiku-20241022',
		# Claude 3 models
		'claude-3-opus-20240229',
		'claude-3-sonnet-20240229',
		'claude-3-haiku-20240307',
		# Legacy naming
		'claude-3-7-sonnet-20250219',
	],
	'Google': [
		# Gemini 2.5 models (2025)
		'gemini-2.5-pro',
		'gemini-2.5-flash',
		'gemini-2.5-flash-preview',
		# Gemini 2.0 models
		'gemini-2.0-flash-exp',
		'gemini-2.0-flash-live',
		# Gemini 1.5 models
		'gemini-1.5-pro',
		'gemini-1.5-flash',
		'gemini-1.5-flash-002',
	],
	'DeepSeek': [
		# Latest DeepSeek models (2025)
		'deepseek-chat',  # Points to V3-0324
		'deepseek-reasoner',  # Points to R1-0528
		'deepseek-v3',
		'deepseek-r1',
	],
	'OpenRouter': [
		# Tool-capable models (prioritized for agent use)
		'openai/gpt-4o',
		'openai/gpt-4o-mini',
		'openai/gpt-4-turbo',
		'anthropic/claude-3.5-sonnet',
		'anthropic/claude-3-opus',
		'anthropic/claude-3-sonnet',
		'google/gemini-1.5-pro',
		'google/gemini-1.5-flash',
		'google/gemini-2.0-flash-exp',
		# Free models with tool support
		'openai/gpt-3.5-turbo:free',
		'meta-llama/llama-3.1-8b-instruct:free',
		'google/gemma-2-9b-it:free',
		# Other popular models
		'deepseek/deepseek-chat',
		'meta-llama/llama-3.3-70b-instruct',
		'microsoft/phi-3-mini-128k-instruct:free',
	],
	'Ollama': [
		# Will be populated dynamically from local Ollama instance
		# Tool-calling capable models prioritized
		'llama3.1:latest',
		'granite3.3:8b',
		'granite3.2-vision:latest',
		'qwen3:8b',
		'qwen2.5-coder:7b',
		'mistral-nemo',
		'command-r-plus',
		# Fallback models
		'llama3.2',
		'deepseek-r1',
	],
	'LM Studio': [
		# Will be populated dynamically from local LM Studio instance
		'Available models will be detected from local LM Studio server'
	],
}

# Automation Templates (replacing quick actions)
AUTOMATION_TEMPLATES = {
	'Quick Tasks': [
		{'name': "Play 'Tiny Dancer'", 'prompt': "Play 'Tiny Dancer' by Elton John"},
		{
			'name': 'Making Siri Speak',
			'prompt': "say Shame on YOU! i'm not Siri! but if you want to make me speak, just prompt the agent with 'say' followed by what you want.",
		},
		{'name': 'Show My Location', 'prompt': 'Open Maps and show my current location'},
		{'name': 'Mail', 'prompt': 'Open Mail and quit'},
		{
			'name': 'Calculator 5 x 4',
			'prompt': "Open Calculator, click the '5' button, then the multiply button, then the '4' button, then the equals button, and return the result",
		},
		{
			'name': 'Create Meeting Note',
			'prompt': "Open Notes, click the 'New Note' button, type 'Meeting Notes' at the top as a title field, then type the text: 'Discuss project timeline'",
		},
	],
	'Multi-Step Workflows': [
		{
			'name': 'Organize Files and Message',
			'prompt': "Open Finder, go to the Documents folder, create a new folder called 'Projects', move all .txt files from Documents into 'Projects'. Then, open Messages, start a new conversation with 'team@example.com', type 'Projects are organized in Documents/Projects', and send it.",
		},
		{
			'name': 'Plan Meeting with Map',
			'prompt': "Open Maps, search for 'cafes near Union Square, San Francisco', select the first result, copy its address. Then, open Calendar, create an event titled 'Team Sync' for tomorrow at 9 AM, paste the address into the location field, and invite 'team@example.com'.",
		},
		{
			'name': 'Create Simple Presentation',
			'prompt': "Open Keynote, create a new presentation with the 'White' theme, add a title slide with 'Team Update', add a second slide with a bullet list: 'Goal 1: Finish report', 'Goal 2: Plan Q4'. Save it as 'update.key' on the Desktop.",
		},
		{
			'name': 'Screenshot and Share',
			'prompt': "Take a screenshot of the current screen, save it to Desktop as 'screenshot.png', then open Mail, create a new email to 'support@example.com' with subject 'Screen Capture', attach the screenshot, and send it.",
		},
		{
			'name': 'System Info Report',
			'prompt': "Open Terminal, run 'system_profiler SPHardwareDataType', copy the output, then open TextEdit, create a new document, paste the system information, and save it as 'system_info.txt' on Desktop.",
		},
	],
	'Productivity Automations': [
		{
			'name': 'Daily Standup Prep',
			'prompt': "Open Calendar and check today's events, then open Notes, create a new note titled 'Daily Standup - [Today's Date]', list today's meetings as bullet points, then open Slack and set status to 'In meetings today'.",
		},
		{
			'name': 'Clean Downloads Folder',
			'prompt': "Open Finder, navigate to Downloads folder, select all files older than 7 days, move them to a new folder called 'Old Downloads', then empty the Trash.",
		},
		{
			'name': 'Weekly Report Setup',
			'prompt': "Open Numbers, create a new spreadsheet with columns: 'Task', 'Status', 'Notes', 'Due Date'. Add 5 sample rows with placeholder data, then save as 'Weekly Report - [This Week]' on Desktop.",
		},
		{
			'name': 'Focus Mode Setup',
			'prompt': 'Turn on Do Not Disturb, close all applications except the current one, open Music and play a focus playlist, then open a timer for 25 minutes.',
		},
		{
			'name': 'End of Day Cleanup',
			'prompt': 'Save all open documents, close all applications except Finder, empty Trash, run a system cleanup, then set computer to sleep mode.',
		},
	],
}


def get_llm(provider: str, model: str, api_key: Optional[str] = None):
	"""Get LLM instance for the specified provider and model"""
	try:
		if provider == 'OpenAI':
			from langchain_openai import ChatOpenAI

			return ChatOpenAI(model=model, api_key=api_key or os.getenv('OPENAI_API_KEY'))
		elif provider == 'Anthropic':
			from langchain_anthropic import ChatAnthropic

			return ChatAnthropic(model=model, api_key=api_key or os.getenv('ANTHROPIC_API_KEY'))
		elif provider == 'Google':
			from langchain_google_genai import ChatGoogleGenerativeAI

			return ChatGoogleGenerativeAI(model=model, google_api_key=api_key or os.getenv('GOOGLE_API_KEY'))
		elif provider == 'DeepSeek':
			from langchain_openai import ChatOpenAI

			return ChatOpenAI(model=model, api_key=api_key or os.getenv('DEEPSEEK_API_KEY'), base_url='https://api.deepseek.com')
		elif provider == 'OpenRouter':
			from langchain_openai import ChatOpenAI

			# OpenRouter uses OpenAI-compatible API with special headers
			if not (api_key or os.getenv('OPENROUTER_API_KEY')):
				raise ValueError('OpenRouter requires an API key')

			# For OpenRouter, ensure we use models that support tool use
			# Add provider routing for tool-capable models
			model_with_routing = model
			if not any(provider_prefix in model for provider_prefix in ['openai/', 'anthropic/', 'google/']):
				# If no provider prefix, add routing to ensure tool use support
				if 'gpt' in model.lower():
					model_with_routing = f'openai/{model}'
				elif 'claude' in model.lower():
					model_with_routing = f'anthropic/{model}'
				elif 'gemini' in model.lower():
					model_with_routing = f'google/{model}'

			return ChatOpenAI(
				model=model_with_routing,
				api_key=api_key or os.getenv('OPENROUTER_API_KEY'),
				base_url='https://openrouter.ai/api/v1',
				default_headers={'HTTP-Referer': 'https://macOS-use-app.local', 'X-Title': 'macOS-use Agent'},
			)
		elif provider == 'Ollama':
			try:
				from langchain_ollama import ChatOllama

				return ChatOllama(model=model, base_url='http://localhost:11434', temperature=0.1)
			except ImportError:
				# Fallback to OpenAI-compatible endpoint if langchain_ollama not available
				from langchain_openai import ChatOpenAI

				return ChatOpenAI(
					model=model,
					api_key='ollama',  # Dummy key for compatibility
					base_url='http://localhost:11434/v1',
				)
		elif provider == 'LM Studio':
			from langchain_openai import ChatOpenAI

			return ChatOpenAI(
				model=model,
				api_key='lm-studio',  # Dummy key for compatibility
				base_url='http://localhost:1234/v1',
			)
		else:
			raise ValueError(f'Unsupported provider: {provider}')
	except ImportError as e:
		raise ValueError(f'Required package not installed for {provider}: {e}')


def get_available_models(provider: str) -> List[str]:
	"""Get available models for a provider, including dynamic detection for local providers and OpenRouter"""
	import requests

	# Dynamic model detection for OpenRouter
	if provider == 'OpenRouter':
		try:
			api_key = os.getenv('OPENROUTER_API_KEY')
			if api_key:
				print('🔄 Fetching live OpenRouter models...')
				headers = {
					'Authorization': f'Bearer {api_key}',
					'HTTP-Referer': 'https://macOS-use-app.local',
					'X-Title': 'macOS-use Agent',
					'Content-Type': 'application/json',
				}
				response = requests.get('https://openrouter.ai/api/v1/models', headers=headers, timeout=10)
				if response.status_code == 200:
					data = response.json()
					models = []
					tool_capable_models = []

					for model in data.get('data', []):
						model_id = model.get('id', '')
						supports_tools = model.get('architecture', {}).get('supports_tools', False)

						if model_id:
							models.append(model_id)
							# Prioritize models that explicitly support tools or are from known tool-capable providers
							if (
								supports_tools
								or any(provider in model_id for provider in ['openai/', 'anthropic/', 'google/'])
								or any(model_name in model_id.lower() for model_name in ['gpt', 'claude', 'gemini'])
							):
								tool_capable_models.append(model_id)

					if models:
						# Prioritize tool-capable models, then separate free/paid
						other_models = [m for m in models if m not in tool_capable_models]

						# Within each group, prioritize free models
						tool_free = [m for m in tool_capable_models if ':free' in m.lower()]
						tool_paid = [m for m in tool_capable_models if ':free' not in m.lower()]
						other_free = [m for m in other_models if ':free' in m.lower()]
						other_paid = [m for m in other_models if ':free' not in m.lower()]

						final_models = tool_free + tool_paid + other_free + other_paid

						print(
							f'✅ Fetched {len(models)} OpenRouter models ({len(tool_capable_models)} tool-capable, {len([m for m in models if ":free" in m.lower()])} free)'
						)
						return final_models
					else:
						print('⚠️ No models returned from OpenRouter API, using static list')
						return LLM_MODELS.get('OpenRouter', [])
				else:
					print(f'❌ OpenRouter API error (status {response.status_code}), using static list')
					return LLM_MODELS.get('OpenRouter', [])
			else:
				print('ℹ️ No OpenRouter API key found, using static model list')
				return LLM_MODELS.get('OpenRouter', [])
		except Exception as e:
			print(f'❌ Error fetching OpenRouter models: {e}, using static list')
			return LLM_MODELS.get('OpenRouter', [])

	# Return static models for other cloud providers (except for dynamic providers)
	if provider in LLM_MODELS and provider not in ['Ollama', 'LM Studio']:
		return LLM_MODELS[provider]

	# Dynamic model detection for Ollama
	if provider == 'Ollama':
		try:
			response = requests.get('http://localhost:11434/api/tags', timeout=5)
			if response.status_code == 200:
				data = response.json()
				models = [model['name'] for model in data.get('models', [])]
				if models:
					return models
				else:
					return ["No models installed - Run 'ollama pull <model>' to install models"]
		except Exception:
			return ['Ollama not running - Start Ollama service first']

	# Dynamic model detection for LM Studio
	elif provider == 'LM Studio':
		try:
			response = requests.get('http://localhost:1234/v1/models', timeout=5)
			if response.status_code == 200:
				data = response.json()
				models = [model['id'] for model in data.get('data', [])]
				if models:
					return models
				else:
					return ['No models loaded - Load a model in LM Studio first']
		except Exception:
			return ['LM Studio not running - Start LM Studio server first']

	return LLM_MODELS.get(provider, [])


def check_provider_availability(provider: str) -> bool:
	"""Check if a provider is available and properly configured"""
	import requests

	# Check API key for providers that require it
	key_map = {
		'OpenAI': 'OPENAI_API_KEY',
		'Anthropic': 'ANTHROPIC_API_KEY',
		'Google': 'GOOGLE_API_KEY',
		'DeepSeek': 'DEEPSEEK_API_KEY',
		'OpenRouter': 'OPENROUTER_API_KEY',
	}

	if provider in key_map:
		api_key = os.getenv(key_map[provider])
		if not api_key:
			return False

		# Special check for OpenRouter - test actual API connectivity
		if provider == 'OpenRouter':
			try:
				headers = {
					'Authorization': f'Bearer {api_key}',
					'HTTP-Referer': 'https://macOS-use-app.local',
					'X-Title': 'macOS-use Agent',
					'Content-Type': 'application/json',
				}
				response = requests.get('https://openrouter.ai/api/v1/models', headers=headers, timeout=10)
				return response.status_code == 200
			except Exception as e:
				print(f'OpenRouter availability check failed: {e}')
				return False

	# Check local providers (Ollama, LM Studio)
	elif provider == 'Ollama':
		try:
			# Use Ollama's native API endpoint
			response = requests.get('http://localhost:11434/api/tags', timeout=5)
			return response.status_code == 200
		except:
			return False
	elif provider == 'LM Studio':
		try:
			# Use LM Studio's OpenAI-compatible endpoint
			response = requests.get('http://localhost:1234/v1/models', timeout=5)
			return response.status_code == 200
		except:
			return False

	return True


# Standalone App class
class WebInterfaceApp:
	def __init__(self):
		self.sessions_dir = Path.home() / '.macOS-use-web-sessions'
		self.sessions_dir.mkdir(exist_ok=True)

	def get_current_timestamp(self):
		return datetime.now().isoformat()

	def save_api_key_to_env(self, provider: str, api_key: str):
		"""Save API key to environment"""
		if not api_key:
			return

		key_map = {
			'OpenAI': 'OPENAI_API_KEY',
			'Anthropic': 'ANTHROPIC_API_KEY',
			'Google': 'GOOGLE_API_KEY',
			'DeepSeek': 'DEEPSEEK_API_KEY',
			'OpenRouter': 'OPENROUTER_API_KEY',
		}

		env_var = key_map.get(provider)
		if env_var:
			os.environ[env_var] = api_key
			# Also save to .env file
			env_file = Path.cwd() / '.env'
			if env_file.exists():
				set_key(str(env_file), env_var, api_key)

	async def get_llm_response(self, system_message: str, user_message: str, llm_provider: str, llm_model: str) -> str:
		"""Get response from LLM"""
		try:
			llm = get_llm(llm_provider, llm_model)

			from langchain_core.messages import HumanMessage, SystemMessage

			messages = [SystemMessage(content=system_message), HumanMessage(content=user_message)]

			response = await llm.ainvoke(messages)
			return response.content
		except Exception as e:
			raise Exception(f'LLM Error: {str(e)}')


# Global app instance
web_app = None
automation_service = None
automation_scheduler = None
automation_recorder = None
automation_executor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Lifecycle manager for FastAPI app"""
	global web_app, automation_service, automation_scheduler, automation_recorder, automation_executor
	web_app = WebInterfaceApp()

	# Initialize automation services
	automation_service = AutomationService()
	automation_executor = AutomationExecutor()
	automation_scheduler = AutomationScheduler(automation_service, automation_executor)
	automation_recorder = AutomationRecorder()

	# Start scheduler
	automation_scheduler.start()

	yield

	# Cleanup
	if automation_scheduler:
		automation_scheduler.stop()


app = FastAPI(
	title='macOS-use Web Interface API',
	description='Elegant JavaScript interface backend for macOS automation',
	version='1.0.0',
	lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
	CORSMiddleware,
	allow_origins=['*'],  # In production, specify exact origins
	allow_credentials=True,
	allow_methods=['*'],
	allow_headers=['*'],
)


# Pydantic models for API
class AgentTaskRequest(BaseModel):
	task: str
	max_steps: int = 100
	max_actions: int = 10
	llm_provider: str = 'OpenAI'
	llm_model: str = 'gpt-4'
	api_key: Optional[str] = None
	custom_system_message: Optional[str] = None


class ChatMessage(BaseModel):
	message: str
	llm_provider: str = 'OpenAI'
	llm_model: str = 'gpt-4'
	api_key: Optional[str] = None
	custom_system_message: Optional[str] = None


class SessionSaveRequest(BaseModel):
	session_name: str
	conversation_history: List[Dict]


class ProviderTestRequest(BaseModel):
	provider: str
	model: str
	api_key: Optional[str] = None


class AutomationSaveRequest(BaseModel):
	name: str
	description: Optional[str] = None
	task: str
	conversation_history: Optional[List[Dict]] = None
	custom_system_message: Optional[str] = None
	category: Optional[str] = None
	tags: Optional[List[str]] = None
	llm_provider: str = 'OpenAI'
	llm_model: str = 'gpt-4'


class AutomationExecuteRequest(BaseModel):
	automation_id: str
	runtime_parameters: Optional[Dict[str, Any]] = None


class AutomationScheduleRequest(BaseModel):
	automation_id: str
	cron_expression: str
	parameters: Optional[Dict[str, Any]] = None


# Connection manager for WebSocket
class ConnectionManager:
	def __init__(self):
		self.active_connections: Dict[str, WebSocket] = {}
		self.agent_sessions: Dict[str, Agent] = {}
		self.chat_agents: Dict[str, Agent] = {}  # Track chat agents separately

	async def connect(self, websocket: WebSocket, client_id: str):
		await websocket.accept()
		self.active_connections[client_id] = websocket

	def disconnect(self, client_id: str):
		# Stop running agents first to prevent them from trying to send messages
		if client_id in self.agent_sessions:
			self.agent_sessions[client_id]._stopped = True
			del self.agent_sessions[client_id]
		if client_id in self.chat_agents:
			self.chat_agents[client_id]._stopped = True
			del self.chat_agents[client_id]

		# Then clean up connections
		if client_id in self.active_connections:
			del self.active_connections[client_id]

		# Clean up conversation memory and task queues
		if hasattr(self, 'conversation_memories') and client_id in self.conversation_memories:
			del self.conversation_memories[client_id]
		if hasattr(self, 'task_queues') and client_id in self.task_queues:
			del self.task_queues[client_id]

	def is_connection_active(self, client_id: str) -> bool:
		"""Check if a WebSocket connection is still active"""
		if client_id not in self.active_connections:
			return False
		try:
			ws = self.active_connections[client_id]
			# Check if WebSocket is in CONNECTED state and application state is valid
			return (
				hasattr(ws, 'client_state')
				and ws.client_state == WebSocketState.CONNECTED
				and hasattr(ws, 'application_state')
				and ws.application_state == WebSocketState.CONNECTED
			)
		except Exception:
			# If any error occurs checking connection state, assume it's disconnected
			return False

	async def send_message(self, message: dict, client_id: str):
		if client_id in self.active_connections:
			# Double-check connection is still active before sending
			if not self.is_connection_active(client_id):
				logger.info(f'Connection {client_id} is no longer active, cleaning up')
				self.disconnect(client_id)
				return

			try:
				await self.active_connections[client_id].send_text(json.dumps(message))
			except (WebSocketDisconnect, RuntimeError, ConnectionError, ConnectionClosedError, ConnectionClosedOK) as e:
				logger.warning(f'Failed to send message to {client_id}: {e}')
				self.disconnect(client_id)
			except Exception as e:
				logger.error(f'Unexpected error sending message to {client_id}: {e}')
				self.disconnect(client_id)

	async def send_stream_update(self, data: dict, client_id: str):
		"""Send streaming update to client"""
		await self.send_message({'type': 'stream_update', 'data': data}, client_id)


manager = ConnectionManager()

# REST API Endpoints


@app.get('/api/automation-templates')
async def get_automation_templates():
	"""Get available automation templates"""
	try:
		return JSONResponse(content=AUTOMATION_TEMPLATES)
	except Exception as e:
		logger.error(f'Error getting automation templates: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/providers')
async def get_providers():
	"""Get available LLM providers and their models"""
	try:
		providers = {}
		provider_list = ['OpenAI', 'Anthropic', 'Google', 'DeepSeek', 'OpenRouter', 'Ollama', 'LM Studio']

		for provider in provider_list:
			models = get_available_models(provider)
			is_available = check_provider_availability(provider)
			providers[provider] = {
				'models': models,
				'available': is_available,
				'api_key_required': provider not in ['Ollama', 'LM Studio'],
			}

		return JSONResponse(content=providers)
	except Exception as e:
		logger.error(f'Error getting providers: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/providers/test')
async def test_provider(request: ProviderTestRequest):
	"""Test connection to a specific provider"""
	try:
		# Check if provider is available
		if not check_provider_availability(request.provider):
			return JSONResponse(content={'success': False, 'message': 'Provider not available. Check API key or local service.'})

		# Try to initialize the LLM
		if not request.api_key and request.provider in ['OpenAI', 'Anthropic', 'Google', 'DeepSeek', 'OpenRouter']:
			return JSONResponse(content={'success': False, 'message': 'API key required for this provider'})

		llm = get_llm(request.provider, request.model, request.api_key)

		# Test with a simple message
		test_response = llm.invoke("Hello, this is a connection test. Please respond with 'Test successful'.")

		if 'test successful' in test_response.content.lower():
			message = 'Connection successful! Provider is working correctly.'
		else:
			message = 'Connection established. Provider responded.'

		return JSONResponse(content={'success': True, 'message': message})

	except Exception as e:
		error_msg = str(e)
		if 'rate limit' in error_msg.lower():
			message = 'Rate limit reached. Connection works but try again later.'
		elif 'api key' in error_msg.lower():
			message = 'Invalid API key. Please check your key.'
		elif 'auth' in error_msg.lower():
			message = 'Authentication failed. Check API key.'
		else:
			message = f'Connection failed: {error_msg}'

		return JSONResponse(content={'success': False, 'message': message})


@app.get('/api/sessions')
async def get_sessions():
	"""Get list of saved sessions"""
	try:
		session_dir = web_app.sessions_dir
		if not session_dir.exists():
			return JSONResponse(content=[])

		sessions = []
		for session_file in session_dir.glob('*.json'):
			try:
				with open(session_file, 'r') as f:
					session_data = json.load(f)
					sessions.append(
						{
							'name': session_file.stem,
							'timestamp': session_data.get('timestamp', ''),
							'message_count': len(session_data.get('messages', [])),
							'success_count': session_data.get('metadata', {}).get('success_count', 0),
							'failure_count': session_data.get('metadata', {}).get('failure_count', 0),
						}
					)
			except Exception as e:
				logger.error(f'Error reading session {session_file}: {e}')

		return JSONResponse(content=sessions)
	except Exception as e:
		logger.error(f'Error getting sessions: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/sessions/{session_name}')
async def get_session(session_name: str):
	"""Get specific session data"""
	try:
		session_file = web_app.sessions_dir / f'{session_name}.json'

		if not session_file.exists():
			raise HTTPException(status_code=404, detail='Session not found')

		with open(session_file, 'r') as f:
			session_data = json.load(f)

		return JSONResponse(content=session_data)
	except Exception as e:
		logger.error(f'Error getting session {session_name}: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/sessions')
async def save_session(request: SessionSaveRequest):
	"""Save a conversation session"""
	try:
		session_file = web_app.sessions_dir / f'{request.session_name}.json'

		# Calculate metadata
		success_count = len([msg for msg in request.conversation_history if msg.get('success', False)])
		failure_count = len([msg for msg in request.conversation_history if msg.get('success') == False])

		session_data = {
			'timestamp': web_app.get_current_timestamp(),
			'messages': request.conversation_history,
			'metadata': {
				'success_count': success_count,
				'failure_count': failure_count,
				'total_messages': len(request.conversation_history),
			},
		}

		with open(session_file, 'w') as f:
			json.dump(session_data, f, indent=2)

		return JSONResponse(content={'success': True, 'message': 'Session saved successfully'})
	except Exception as e:
		logger.error(f'Error saving session: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.delete('/api/sessions/{session_name}')
async def delete_session(session_name: str):
	"""Delete a session"""
	try:
		session_file = web_app.sessions_dir / f'{session_name}.json'

		if session_file.exists():
			session_file.unlink()
			return JSONResponse(content={'success': True, 'message': 'Session deleted successfully'})
		else:
			raise HTTPException(status_code=404, detail='Session not found')
	except Exception as e:
		logger.error(f'Error deleting session: {e}')
		raise HTTPException(status_code=500, detail=str(e))


# Automation API Endpoints


@app.get('/api/automations')
async def get_automations():
	"""Get list of all saved automations"""
	try:
		automations = automation_service.list_automations()
		return JSONResponse(content=automations)
	except Exception as e:
		logger.error(f'Error getting automations: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/automations/{automation_id}')
async def get_automation(automation_id: str):
	"""Get specific automation by ID"""
	try:
		automation = automation_service.load_automation(automation_id)
		if not automation:
			raise HTTPException(status_code=404, detail='Automation not found')
		return JSONResponse(content=automation.model_dump())
	except Exception as e:
		logger.error(f'Error getting automation {automation_id}: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/automations')
async def save_automation(request: AutomationSaveRequest):
	"""Save a successful interaction as an automation"""
	try:
		# Create automation from successful run
		automation = automation_service.save_automation_from_successful_run(
			name=request.name,
			task=request.task,
			history=None,  # Will need to be passed from actual agent run
			agent_params={
				'llm_provider': request.llm_provider,
				'llm_model': request.llm_model,
				'max_steps': 100,
				'max_actions_per_step': 10,
			},
			custom_system_message=request.custom_system_message,
			description=request.description,
			category=request.category,
			tags=request.tags,
		)

		return JSONResponse(
			content={
				'success': True,
				'automation_id': automation.id,
				'message': f"Automation '{request.name}' saved successfully",
			}
		)
	except Exception as e:
		logger.error(f'Error saving automation: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/automations/{automation_id}/execute')
async def execute_automation(automation_id: str, request: AutomationExecuteRequest):
	"""Execute a saved automation"""
	try:
		automation = automation_service.load_automation(automation_id)
		if not automation:
			raise HTTPException(status_code=404, detail='Automation not found')

		# Execute automation
		result = await automation_executor.execute_automation(automation, request.runtime_parameters)

		# Update automation stats
		automation.update_execution_stats(result.success)
		automation_service.save_automation(automation)

		# Save execution result
		automation_service.save_execution_result(result)

		return JSONResponse(content=result.model_dump())
	except Exception as e:
		logger.error(f'Error executing automation {automation_id}: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.delete('/api/automations/{automation_id}')
async def delete_automation(automation_id: str):
	"""Delete an automation"""
	try:
		success = automation_service.delete_automation(automation_id)
		if not success:
			raise HTTPException(status_code=404, detail='Automation not found')

		# Also unschedule if it was scheduled
		automation_scheduler.unschedule_automation(automation_id)

		return JSONResponse(content={'success': True, 'message': 'Automation deleted successfully'})
	except Exception as e:
		logger.error(f'Error deleting automation {automation_id}: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/automations/{automation_id}/duplicate')
async def duplicate_automation(automation_id: str, new_name: str):
	"""Duplicate an automation"""
	try:
		duplicate = automation_service.duplicate_automation(automation_id, new_name)
		if not duplicate:
			raise HTTPException(status_code=404, detail='Automation not found')

		return JSONResponse(
			content={'success': True, 'automation_id': duplicate.id, 'message': f"Automation duplicated as '{new_name}'"}
		)
	except Exception as e:
		logger.error(f'Error duplicating automation {automation_id}: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/automations/{automation_id}/history')
async def get_automation_history(automation_id: str, limit: int = 50):
	"""Get execution history for an automation"""
	try:
		history = automation_service.get_execution_history(automation_id, limit)
		return JSONResponse(content=[result.model_dump() for result in history])
	except Exception as e:
		logger.error(f'Error getting automation history {automation_id}: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/automations/{automation_id}/schedule')
async def schedule_automation(automation_id: str, request: AutomationScheduleRequest):
	"""Add a schedule to an automation"""
	try:
		success = automation_scheduler.add_schedule_to_automation(automation_id, request.cron_expression, request.parameters)

		if not success:
			raise HTTPException(status_code=404, detail='Automation not found')

		return JSONResponse(content={'success': True, 'message': 'Schedule added to automation'})
	except Exception as e:
		logger.error(f'Error scheduling automation {automation_id}: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.delete('/api/automations/{automation_id}/schedule/{schedule_index}')
async def unschedule_automation(automation_id: str, schedule_index: int):
	"""Remove a schedule from an automation"""
	try:
		success = automation_scheduler.remove_schedule_from_automation(automation_id, schedule_index)
		if not success:
			raise HTTPException(status_code=404, detail='Automation or schedule not found')

		return JSONResponse(content={'success': True, 'message': 'Schedule removed from automation'})
	except Exception as e:
		logger.error(f'Error unscheduling automation {automation_id}: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/scheduled-automations')
async def get_scheduled_automations():
	"""Get list of scheduled automations"""
	try:
		scheduled = automation_scheduler.get_scheduled_automations()
		return JSONResponse(content=scheduled)
	except Exception as e:
		logger.error(f'Error getting scheduled automations: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/automation-categories')
async def get_automation_categories():
	"""Get all automation categories"""
	try:
		categories = automation_service.get_categories()
		return JSONResponse(content=categories)
	except Exception as e:
		logger.error(f'Error getting automation categories: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/automation-tags')
async def get_automation_tags():
	"""Get all automation tags"""
	try:
		tags = automation_service.get_tags()
		return JSONResponse(content=tags)
	except Exception as e:
		logger.error(f'Error getting automation tags: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/automations/search')
async def search_automations(query: str = '', category: Optional[str] = None, tags: Optional[str] = None):
	"""Search automations"""
	try:
		tag_list = tags.split(',') if tags else None
		results = automation_service.search_automations(query, category, tag_list)
		return JSONResponse(content=results)
	except Exception as e:
		logger.error(f'Error searching automations: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/automation-templates')
async def get_automation_templates():
	"""Get available automation templates"""
	try:
		templates = get_all_templates()
		template_data = []

		for template in templates:
			template_data.append(
				{
					'name': template.name,
					'description': template.description,
					'category': template.category,
					'parameters': template.parameters,
					'preview_image': template.preview_image,
				}
			)

		return JSONResponse(content=template_data)
	except Exception as e:
		logger.error(f'Error getting automation templates: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/automation-templates/{template_name}')
async def create_automation_from_template(template_name: str, parameters: Dict[str, Any]):
	"""Create automation from template"""
	try:
		automation = automation_service.create_automation_from_template(
			template_name, f'{template_name} - {datetime.now().strftime("%Y%m%d_%H%M%S")}', parameters
		)

		if automation:
			return JSONResponse(
				content={
					'success': True,
					'automation_id': automation.id,
					'message': f'Automation created from {template_name} template',
				}
			)
		else:
			raise HTTPException(status_code=404, detail='Template not found')

	except Exception as e:
		logger.error(f'Error creating automation from template: {e}')
		raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/refine-prompt')
async def refine_prompt(request: dict):
	"""Refine a prompt using direct LLM call without agent system"""
	try:
		# Extract request data
		message = request.get('message', '')
		system_message = request.get('system_message', '')
		llm_provider = request.get('llm_provider', 'OpenAI')
		llm_model = request.get('llm_model', 'gpt-4')
		api_key = request.get('api_key')

		# Save API key if provided
		if api_key:
			web_app.save_api_key_to_env(llm_provider, api_key)

		# Get refined response directly from LLM
		response = await web_app.get_llm_response(
			system_message=system_message, user_message=message, llm_provider=llm_provider, llm_model=llm_model
		)

		return JSONResponse(content={'response': response, 'success': True})
	except Exception as e:
		logger.error(f'Error in prompt refinement: {e}')
		return JSONResponse(
			content={
				'response': message,  # Return original on error
				'success': False,
				'error': str(e),
			}
		)


@app.post('/api/chat/send')
async def send_chat_message(request: ChatMessage):
	"""Send a chat message using the full agent system"""
	try:
		# Save API key if provided
		if request.api_key:
			web_app.save_api_key_to_env(request.llm_provider, request.api_key)

		# Get LLM instance
		llm = get_llm(request.llm_provider, request.llm_model, request.api_key)

		# Choose system prompt class based on whether custom message is provided
		if request.custom_system_message:
			system_prompt_class = ChatSystemPromptWithCustom
			system_prompt_kwargs = {'custom_message': request.custom_system_message}
		else:
			system_prompt_class = ChatSystemPrompt
			system_prompt_kwargs = {}

		# Create agent with appropriate system prompt
		agent = Agent(
			task=f'User message: {request.message}',
			llm=llm,
			controller=Controller(),
			max_actions_per_step=3,  # Allow multiple actions for complex requests
			system_prompt_class=system_prompt_class,
			system_prompt_kwargs=system_prompt_kwargs,
		)

		# Run just one step to get the response
		await agent.step()

		# Extract the response from the agent's last result
		if agent._last_result and len(agent._last_result) > 0:
			last_result = agent._last_result[-1]
			response = last_result.extracted_content or 'I completed your request.'
			success = not bool(last_result.error)
		else:
			response = "I wasn't able to process your request properly."
			success = False

		return JSONResponse(content={'response': response, 'success': success})
	except Exception as e:
		logger.error(f'Error in chat: {e}')
		return JSONResponse(content={'response': f'Sorry, I encountered an error: {str(e)}', 'success': False})


# WebSocket endpoint for real-time agent execution
@app.websocket('/ws/{client_id}')
async def websocket_endpoint(websocket: WebSocket, client_id: str):
	await manager.connect(websocket, client_id)
	try:
		while True:
			# Check if connection is still active before trying to receive
			if not manager.is_connection_active(client_id):
				break

			data = await websocket.receive_text()
			message = json.loads(data)

			if message['type'] == 'agent_task':
				await handle_agent_task(message['data'], client_id)
			elif message['type'] == 'chat_message':
				await handle_chat_message(message['data'], client_id)
			elif message['type'] == 'stop_agent':
				await handle_stop_agent(client_id)
			elif message['type'] == 'stop_chat':
				await handle_stop_chat(client_id)
			elif message['type'] == 'interrupt_chat':
				await handle_interrupt_chat(message['data'], client_id)
			elif message['type'] == 'redirect_chat':
				await handle_redirect_chat(message['data'], client_id)
			elif message['type'] == 'add_task':
				await handle_add_task(message['data'], client_id)
			elif message['type'] == 'save_automation':
				await handle_save_automation(message['data'], client_id)
			elif message['type'] == 'execute_automation':
				await handle_execute_automation(message['data'], client_id)
			elif message['type'] == 'ping':
				await manager.send_message({'type': 'pong'}, client_id)

	except (WebSocketDisconnect, RuntimeError, ConnectionError, ConnectionClosedError, ConnectionClosedOK) as e:
		logger.info(f'WebSocket disconnected for client {client_id}: {e}')
		manager.disconnect(client_id)
	except Exception as e:
		logger.error(f'Unexpected error in WebSocket endpoint for client {client_id}: {e}')
		manager.disconnect(client_id)


async def handle_agent_task(task_data: dict, client_id: str):
	"""Handle agent task execution via WebSocket"""
	try:
		# Extract task parameters
		task = task_data['task']
		max_steps = task_data.get('max_steps', 100)
		max_actions = task_data.get('max_actions', 10)
		llm_provider = task_data.get('llm_provider', 'OpenAI')
		llm_model = task_data.get('llm_model', 'gpt-4')
		api_key = task_data.get('api_key')
		custom_system_message = task_data.get('custom_system_message')

		# Save API key if provided
		if api_key:
			web_app.save_api_key_to_env(llm_provider, api_key)

		# Send start message
		await manager.send_stream_update(
			{'status': 'starting', 'message': f'Starting task: {task}', 'step': 0, 'max_steps': max_steps}, client_id
		)

		# Get LLM instance
		llm = get_llm(llm_provider, llm_model, api_key)

		# Choose system prompt class based on whether custom message is provided
		if custom_system_message:
			system_prompt_class = SystemPromptWithCustom
			system_prompt_kwargs = {'custom_message': custom_system_message}
		else:
			system_prompt_class = SystemPrompt
			system_prompt_kwargs = {}

		# Create agent
		agent = Agent(
			task=task,
			llm=llm,
			controller=Controller(),
			max_actions_per_step=max_actions,
			system_prompt_class=system_prompt_class,
			system_prompt_kwargs=system_prompt_kwargs,
		)

		# Store agent for potential stopping
		manager.agent_sessions[client_id] = agent

		# Define step callback for streaming updates with connection check
		def step_callback(state: str, output, step: int):
			if manager.is_connection_active(client_id):
				asyncio.create_task(
					manager.send_stream_update(
						{
							'status': 'running',
							'step': step,
							'max_steps': max_steps,
							'state': state,
							'agent_output': output.model_dump() if output else None,
							'message': f'Step {step}: {output.current_state.next_goal if output else "Processing..."}',
						},
						client_id,
					)
				)

		def done_callback(history):
			if manager.is_connection_active(client_id):
				asyncio.create_task(
					manager.send_stream_update(
						{
							'status': 'completed',
							'message': 'Task completed successfully!',
							'final_result': history.history[-1].result[-1].extracted_content
							if history.history and history.history[-1].result
							else 'Task completed',
							'step_count': len(history.history),
						},
						client_id,
					)
				)

		# Set callbacks
		agent.register_new_step_callback = step_callback
		agent.register_done_callback = done_callback

		# Run agent
		history = await agent.run(max_steps=max_steps)

		# Send completion message
		if history.is_done():
			await manager.send_stream_update(
				{
					'status': 'completed',
					'message': 'Task completed successfully!',
					'final_result': history.history[-1].result[-1].extracted_content
					if history.history and history.history[-1].result
					else 'Task completed',
					'step_count': len(history.history),
				},
				client_id,
			)
		else:
			await manager.send_stream_update(
				{
					'status': 'failed',
					'message': 'Task failed to complete within maximum steps',
					'step_count': len(history.history),
				},
				client_id,
			)

	except Exception as e:
		logger.error(f'Error in agent task: {e}')
		await manager.send_stream_update({'status': 'error', 'message': f'Error: {str(e)}'}, client_id)
	finally:
		# Clean up agent session
		if client_id in manager.agent_sessions:
			del manager.agent_sessions[client_id]


async def handle_chat_message(message_data: dict, client_id: str):
	"""Handle chat message via WebSocket with enhanced multi-step execution and streaming"""
	conversation_memory = getattr(manager, 'conversation_memories', {}).get(client_id, ConversationMemory())
	task_queue = getattr(manager, 'task_queues', {}).get(client_id, ChatTaskQueue())

	try:
		message = message_data['message']
		llm_provider = message_data.get('llm_provider', 'OpenAI')
		llm_model = message_data.get('llm_model', 'gpt-4')
		api_key = message_data.get('api_key')
		custom_system_message = message_data.get('custom_system_message')

		# Save API key if provided
		if api_key:
			web_app.save_api_key_to_env(llm_provider, api_key)

		# Add user message to conversation memory
		conversation_memory.add_user_message(message)

		# Send start message
		await manager.send_message(
			{
				'type': 'chat_stream_update',
				'data': {
					'status': 'starting',
					'message': 'Processing your message...',
					'queue_status': task_queue.get_queue_status(),
				},
			},
			client_id,
		)

		# Get LLM instance
		llm = get_llm(llm_provider, llm_model, api_key)

		# Choose system prompt class based on whether custom message is provided
		if custom_system_message:
			system_prompt_class = ChatSystemPromptWithCustom
			system_prompt_kwargs = {'custom_message': custom_system_message}
		else:
			system_prompt_class = ChatSystemPromptWithCustom
			system_prompt_kwargs = {}

		# Create streaming callback with connection check
		async def streaming_callback(data):
			if manager.is_connection_active(client_id):
				await manager.send_message(data, client_id)
			else:
				logger.warning(f'Skipping message to disconnected client {client_id}')

		# Create enhanced chat agent with conversation capabilities
		agent = ChatAgent(
			task=f'User message: {message}',
			llm=llm,
			controller=Controller(),
			max_actions_per_step=5,  # Allow more actions per step for complex tasks
			system_prompt_class=system_prompt_class,
			system_prompt_kwargs=system_prompt_kwargs,
			conversation_memory=conversation_memory,
			task_queue=task_queue,
			streaming_callback=streaming_callback,
			client_id=client_id,
			connection_manager=manager,
		)

		# Store agent and memory for potential stopping and persistence
		manager.chat_agents[client_id] = agent
		if not hasattr(manager, 'conversation_memories'):
			manager.conversation_memories = {}
		if not hasattr(manager, 'task_queues'):
			manager.task_queues = {}
		manager.conversation_memories[client_id] = conversation_memory
		manager.task_queues[client_id] = task_queue

		# Run conversational agent with multi-step execution
		results = await agent.run_conversational(max_steps=30)

		# Process final results
		if results['results']:
			final_result = results['results'][-1]
			response = final_result['result']
			success = final_result['success']

			# Prepare execution data for frontend
			execution_data = {'steps': [], 'actions_taken': []}

			# Extract steps and actions from agent history
			if hasattr(agent, 'history') and agent.history:
				for step_num, step in enumerate(agent.history.history):
					if step.result:
						for result in step.result:
							if hasattr(result, 'action_name'):
								execution_data['actions_taken'].append(result.action_name)
							if result.extracted_content:
								execution_data['steps'].append(
									{
										'step': step_num + 1,
										'message': result.extracted_content,
										'action': getattr(result, 'action_name', ''),
										'timestamp': datetime.now().isoformat(),
									}
								)

			# Send final completion message with execution data
			await manager.send_message(
				{
					'type': 'chat_complete',
					'data': {
						'status': 'completed',
						'response': response,
						'success': success,
						'queue_status': results['queue_status'],
						'total_tasks_completed': len([r for r in results['results'] if r['success']]),
						'execution_data': execution_data,
					},
				},
				client_id,
			)
		else:
			# No results - send error
			await manager.send_message(
				{
					'type': 'chat_complete',
					'data': {
						'status': 'error',
						'response': "I wasn't able to process your request properly.",
						'success': False,
						'queue_status': task_queue.get_queue_status(),
					},
				},
				client_id,
			)

	except Exception as e:
		logger.error(f'Error in chat message: {e}')
		await manager.send_message(
			{
				'type': 'chat_complete',
				'data': {
					'status': 'error',
					'response': f'Error: {str(e)}',
					'success': False,
					'queue_status': task_queue.get_queue_status() if 'task_queue' in locals() else {},
				},
			},
			client_id,
		)
	finally:
		# Note: Don't clean up chat agent session or memory here to maintain persistence
		# They will be cleaned up when the client disconnects
		pass


async def handle_stop_agent(client_id: str):
	"""Stop running agent for client"""
	if client_id in manager.agent_sessions:
		agent = manager.agent_sessions[client_id]
		agent._stopped = True
		logger.info(f'Stopping agent for client {client_id}')
		await manager.send_stream_update(
			{'status': 'stopped', 'message': 'Agent execution stopped by user', 'final_result': 'Execution stopped by user'},
			client_id,
		)
		# Clean up the session
		del manager.agent_sessions[client_id]


async def handle_stop_chat(client_id: str):
	"""Stop running chat agent for client"""
	if client_id in manager.chat_agents:
		agent = manager.chat_agents[client_id]
		agent._stopped = True
		logger.info(f'Stopping chat agent for client {client_id}')
		await manager.send_message(
			{
				'type': 'chat_response',
				'data': {
					'status': 'stopped',
					'message': 'Chat stopped by user',
					'success': False,
					'final_result': 'Chat execution stopped by user',
				},
			},
			client_id,
		)


async def handle_interrupt_chat(data: dict, client_id: str):
	"""Interrupt running chat agent for client"""
	if client_id in manager.chat_agents:
		agent = manager.chat_agents[client_id]
		agent.interrupt_execution()
		await manager.send_message(
			{'type': 'chat_stream_update', 'data': {'status': 'interrupted', 'message': 'Chat execution interrupted by user'}},
			client_id,
		)


async def handle_redirect_chat(data: dict, client_id: str):
	"""Redirect running chat agent to a new task"""
	new_task = data.get('task', '')
	if client_id in manager.chat_agents and new_task:
		agent = manager.chat_agents[client_id]
		agent.interrupt_execution(redirect_message=new_task)
		await manager.send_message(
			{'type': 'chat_stream_update', 'data': {'status': 'redirected', 'message': f'Redirecting to new task: {new_task}'}},
			client_id,
		)


async def handle_add_task(data: dict, client_id: str):
	"""Add a new task to the chat agent's queue"""
	task = data.get('task', '')
	priority = data.get('priority', 'normal')

	if task and hasattr(manager, 'task_queues') and client_id in manager.task_queues:
		task_queue = manager.task_queues[client_id]
		task_id = task_queue.add_task(task, priority)

		await manager.send_message(
			{
				'type': 'chat_stream_update',
				'data': {
					'status': 'task_added',
					'message': f'Added task to queue: {task}',
					'task_id': task_id,
					'queue_status': task_queue.get_queue_status(),
				},
			},
			client_id,
		)


async def handle_save_automation(data: dict, client_id: str):
	"""Handle saving automation from successful interaction"""
	try:
		# Extract automation data
		name = data.get('name', '')
		description = data.get('description')
		task = data.get('task', '')
		custom_system_message = data.get('custom_system_message')
		category = data.get('category')
		tags = data.get('tags', [])
		llm_provider = data.get('llm_provider', 'OpenAI')
		llm_model = data.get('llm_model', 'gpt-4')

		if not name or not task:
			await manager.send_message(
				{'type': 'automation_save_result', 'data': {'success': False, 'message': 'Name and task are required'}}, client_id
			)
			return

		# Get execution data from request
		execution_data = data.get('execution_data')
		conversation_history = data.get('conversation_history', [])

		# Check if we have a chat agent with history to save from
		if client_id in manager.chat_agents:
			agent = manager.chat_agents[client_id]

			# Create automation from agent history
			automation = automation_service.save_automation_from_successful_run(
				name=name,
				task=task,
				history=agent.history,
				agent_params={'llm_provider': llm_provider, 'llm_model': llm_model, 'max_steps': 100, 'max_actions_per_step': 10},
				custom_system_message=custom_system_message,
				description=description,
				category=category,
				tags=tags,
			)

			await manager.send_message(
				{
					'type': 'automation_save_result',
					'data': {
						'success': True,
						'automation_id': automation.id,
						'message': f"Automation '{name}' saved successfully with {len(automation.steps)} steps",
					},
				},
				client_id,
			)
		elif execution_data:
			# Try to create automation from execution data if no active agent
			try:
				# Create a simple automation that will use the task
				automation = SavedAutomation(
					id=str(uuid.uuid4()),
					name=name,
					description=description or f'Automation created from: {task}',
					task=task,
					metadata=AutomationMetadata(category=category or 'General', tags=tags or []),
					steps=[],  # Will be populated during execution
					agent_parameters={
						'llm_provider': llm_provider,
						'llm_model': llm_model,
						'max_steps': 100,
						'max_actions_per_step': 10,
					},
					system_prompt=custom_system_message,
					llm_provider=llm_provider,
					llm_model=llm_model,
					# Store execution data for reference
					execution_metadata={'execution_data': execution_data, 'conversation_history': conversation_history},
				)

				# Save the automation
				automation_service.save_automation(automation)

				await manager.send_message(
					{
						'type': 'automation_save_result',
						'data': {
							'success': True,
							'automation_id': automation.id,
							'message': f"Automation '{name}' saved successfully",
						},
					},
					client_id,
				)
			except Exception as e:
				logger.error(f'Error creating automation from execution data: {e}')
				await manager.send_message(
					{
						'type': 'automation_save_result',
						'data': {'success': False, 'message': f'Failed to save automation: {str(e)}'},
					},
					client_id,
				)
		else:
			await manager.send_message(
				{
					'type': 'automation_save_result',
					'data': {
						'success': False,
						'message': 'No active agent session to save from. Please run a successful task first.',
					},
				},
				client_id,
			)

	except Exception as e:
		logger.error(f'Error saving automation: {e}')
		await manager.send_message(
			{'type': 'automation_save_result', 'data': {'success': False, 'message': f'Error saving automation: {str(e)}'}},
			client_id,
		)


async def handle_execute_automation(data: dict, client_id: str):
	"""Handle executing a saved automation via WebSocket"""
	try:
		automation_id = data.get('automation_id')
		runtime_parameters = data.get('runtime_parameters', {})

		if not automation_id:
			await manager.send_message(
				{'type': 'automation_execute_result', 'data': {'success': False, 'message': 'Automation ID is required'}},
				client_id,
			)
			return

		# Load automation
		automation = automation_service.load_automation(automation_id)
		if not automation:
			await manager.send_message(
				{'type': 'automation_execute_result', 'data': {'success': False, 'message': 'Automation not found'}}, client_id
			)
			return

		# Send start message
		await manager.send_message(
			{
				'type': 'automation_status',
				'data': {
					'status': 'starting',
					'message': f'Starting automation: {automation.name}',
					'automation_id': automation_id,
				},
			},
			client_id,
		)

		# Create execution callback for streaming updates
		async def execution_callback(update):
			await manager.send_message({'type': 'automation_status', 'data': update}, client_id)

		# Execute automation
		result = await automation_executor.execute_automation(automation, runtime_parameters, callback=execution_callback)

		# Update automation stats
		automation.update_execution_stats(result.success)
		automation_service.save_automation(automation)

		# Save execution result
		automation_service.save_execution_result(result)

		# Send completion message
		await manager.send_message(
			{
				'type': 'automation_execute_result',
				'data': {
					'success': result.success,
					'message': 'Automation completed successfully' if result.success else f'Automation failed: {result.error}',
					'execution_id': result.execution_id,
					'duration': result.duration,
					'steps_executed': result.steps_executed,
					'actions_executed': result.actions_executed,
					'result_data': result.result_data,
				},
			},
			client_id,
		)

	except Exception as e:
		logger.error(f'Error executing automation: {e}')
		await manager.send_message(
			{'type': 'automation_execute_result', 'data': {'success': False, 'message': f'Error executing automation: {str(e)}'}},
			client_id,
		)


if __name__ == '__main__':
	import uvicorn

	uvicorn.run(app, host='0.0.0.0', port=8080)
