"""
Automation recorder for capturing user interactions as automations.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable

from .models import (
	SavedAutomation,
	AutomationStep,
	AutomationAction,
	AutomationMetadata,
	AutomationConfig
)
from ..agent.views import AgentHistoryList, AgentHistory

logger = logging.getLogger(__name__)


class AutomationRecorder:
	"""Records user interactions and agent executions as reusable automations"""
	
	def __init__(self):
		self.recording_sessions = {}  # session_id -> recording data
		self.is_recording = False
		self.current_session_id = None
		
		logger.info("Automation recorder initialized")
	
	def start_recording(self, session_id: str, description: Optional[str] = None) -> bool:
		"""Start recording a new automation session"""
		if self.is_recording:
			logger.warning("Recording already in progress")
			return False
		
		self.current_session_id = session_id
		self.is_recording = True
		
		self.recording_sessions[session_id] = {
			"started_at": datetime.now(),
			"description": description,
			"actions": [],
			"steps": [],
			"metadata": {
				"session_id": session_id,
				"user_actions": 0,
				"agent_actions": 0
			}
		}
		
		logger.info(f"Started recording session: {session_id}")
		return True
	
	def stop_recording(self, session_id: Optional[str] = None) -> bool:
		"""Stop the current recording session"""
		if not self.is_recording:
			logger.warning("No recording in progress")
			return False
		
		session_id = session_id or self.current_session_id
		if session_id not in self.recording_sessions:
			logger.error(f"Recording session not found: {session_id}")
			return False
		
		self.recording_sessions[session_id]["completed_at"] = datetime.now()
		self.is_recording = False
		self.current_session_id = None
		
		logger.info(f"Stopped recording session: {session_id}")
		return True
	
	def record_user_action(self, action_type: str, parameters: Dict[str, Any], description: Optional[str] = None) -> None:
		"""Record a user action during the recording session"""
		if not self.is_recording or not self.current_session_id:
			return
		
		session = self.recording_sessions[self.current_session_id]
		
		action = {
			"timestamp": datetime.now(),
			"source": "user",
			"action_type": action_type,
			"parameters": parameters,
			"description": description
		}
		
		session["actions"].append(action)
		session["metadata"]["user_actions"] += 1
		
		logger.debug(f"Recorded user action: {action_type}")
	
	def record_agent_history(self, history: AgentHistoryList, task: str) -> None:
		"""Record agent execution history during the recording session"""
		if not self.is_recording or not self.current_session_id:
			return
		
		session = self.recording_sessions[self.current_session_id]
		
		# Convert agent history to recorded actions
		for i, history_item in enumerate(history.history):
			if history_item.model_output and history_item.model_output.action:
				for action in history_item.model_output.action:
					action_dict = action.model_dump(exclude_unset=True)
					action_type = next(iter(action_dict.keys()))
					parameters = action_dict[action_type]
					
					recorded_action = {
						"timestamp": datetime.now(),
						"source": "agent",
						"action_type": action_type,
						"parameters": parameters,
						"description": f"Agent step {i+1}: {history_item.model_output.current_state.next_goal}",
						"step_index": i,
						"goal": history_item.model_output.current_state.next_goal,
						"state": history_item.state if hasattr(history_item, 'state') else None
					}
					
					session["actions"].append(recorded_action)
					session["metadata"]["agent_actions"] += 1
		
		# Store the original task
		session["original_task"] = task
		
		logger.info(f"Recorded agent history with {len(history.history)} steps")
	
	def create_automation_from_recording(
		self, 
		session_id: str, 
		name: str,
		description: Optional[str] = None,
		llm_provider: str = "OpenAI",
		llm_model: str = "gpt-4",
		custom_system_message: Optional[str] = None
	) -> Optional[SavedAutomation]:
		"""Create a SavedAutomation from a recorded session"""
		
		if session_id not in self.recording_sessions:
			logger.error(f"Recording session not found: {session_id}")
			return None
		
		session = self.recording_sessions[session_id]
		
		# Group actions into steps
		steps = self._group_actions_into_steps(session["actions"])
		
		# Create automation metadata
		metadata = AutomationMetadata(
			created_at=datetime.now(),
			created_by="recording",
			source="recorded",
			category="recorded",
			tags=["recorded"],
			version="1.0.0"
		)
		
		# Create automation config
		config = AutomationConfig(
			max_execution_time=300,
			default_wait_time=1.0,
			error_handling="stop",
			log_level="info"
		)
		
		# Create the automation
		automation = SavedAutomation(
			name=name,
			description=description or session.get("description", f"Recorded automation from session {session_id}"),
			steps=steps,
			config=config,
			metadata=metadata,
			system_prompt=custom_system_message,
			llm_provider=llm_provider,
			llm_model=llm_model,
			original_task=session.get("original_task", name),
			agent_parameters={
				"recorded_session_id": session_id,
				"recorded_at": session["started_at"].isoformat()
			}
		)
		
		logger.info(f"Created automation '{name}' from recording session {session_id} with {len(steps)} steps")
		return automation
	
	def _group_actions_into_steps(self, actions: List[Dict[str, Any]]) -> List[AutomationStep]:
		"""Group recorded actions into logical steps"""
		steps = []
		current_step_actions = []
		current_step_name = "Step 1"
		current_step_description = None
		step_counter = 1
		
		for action in actions:
			# Create automation action
			automation_action = AutomationAction(
				action_type=action["action_type"],
				parameters=action["parameters"],
				description=action.get("description"),
				retry_count=3
			)
			
			# Determine if we should start a new step
			should_start_new_step = (
				# Different source (user vs agent)
				len(current_step_actions) > 0 and 
				action.get("source") != actions[actions.index(action) - 1].get("source") if actions.index(action) > 0 else False
			) or (
				# Agent step change
				action.get("step_index") is not None and 
				len(current_step_actions) > 0 and
				action.get("step_index") != getattr(current_step_actions[-1], "step_index", None)
			) or (
				# Maximum actions per step reached
				len(current_step_actions) >= 5
			)
			
			if should_start_new_step and current_step_actions:
				# Save current step
				step = AutomationStep(
					name=current_step_name,
					description=current_step_description,
					actions=current_step_actions.copy(),
					enabled=True
				)
				steps.append(step)
				
				# Start new step
				step_counter += 1
				current_step_name = f"Step {step_counter}"
				current_step_description = action.get("goal") or action.get("description")
				current_step_actions = []
			
			# Add action to current step
			current_step_actions.append(automation_action)
			
			# Update step description if available
			if action.get("goal") and not current_step_description:
				current_step_description = action["goal"]
		
		# Add final step if there are remaining actions
		if current_step_actions:
			step = AutomationStep(
				name=current_step_name,
				description=current_step_description,
				actions=current_step_actions,
				enabled=True
			)
			steps.append(step)
		
		return steps
	
	def get_recording_sessions(self) -> List[Dict[str, Any]]:
		"""Get list of all recording sessions"""
		sessions = []
		
		for session_id, session_data in self.recording_sessions.items():
			sessions.append({
				"session_id": session_id,
				"description": session_data.get("description"),
				"started_at": session_data["started_at"],
				"completed_at": session_data.get("completed_at"),
				"is_active": session_id == self.current_session_id and self.is_recording,
				"action_count": len(session_data["actions"]),
				"user_actions": session_data["metadata"]["user_actions"],
				"agent_actions": session_data["metadata"]["agent_actions"],
				"original_task": session_data.get("original_task")
			})
		
		# Sort by start time, newest first
		sessions.sort(key=lambda x: x["started_at"], reverse=True)
		return sessions
	
	def get_recording_session(self, session_id: str) -> Optional[Dict[str, Any]]:
		"""Get detailed recording session data"""
		if session_id not in self.recording_sessions:
			return None
		
		session = self.recording_sessions[session_id]
		return {
			"session_id": session_id,
			"description": session.get("description"),
			"started_at": session["started_at"],
			"completed_at": session.get("completed_at"),
			"is_active": session_id == self.current_session_id and self.is_recording,
			"original_task": session.get("original_task"),
			"metadata": session["metadata"],
			"actions": session["actions"]
		}
	
	def delete_recording_session(self, session_id: str) -> bool:
		"""Delete a recording session"""
		if session_id in self.recording_sessions:
			del self.recording_sessions[session_id]
			
			if self.current_session_id == session_id:
				self.is_recording = False
				self.current_session_id = None
			
			logger.info(f"Deleted recording session: {session_id}")
			return True
		
		return False
	
	def export_recording_session(self, session_id: str, file_path: str) -> bool:
		"""Export recording session to file"""
		if session_id not in self.recording_sessions:
			return False
		
		try:
			import json
			from pathlib import Path
			
			session_data = self.recording_sessions[session_id]
			
			# Convert datetime objects to strings for JSON serialization
			def json_serial(obj):
				if isinstance(obj, datetime):
					return obj.isoformat()
				raise TypeError(f"Type {type(obj)} not serializable")
			
			Path(file_path).parent.mkdir(parents=True, exist_ok=True)
			
			with open(file_path, 'w') as f:
				json.dump(session_data, f, indent=2, default=json_serial)
			
			logger.info(f"Exported recording session {session_id} to {file_path}")
			return True
			
		except Exception as e:
			logger.error(f"Failed to export recording session {session_id}: {e}")
			return False
	
	def import_recording_session(self, file_path: str, session_id: Optional[str] = None) -> Optional[str]:
		"""Import recording session from file"""
		try:
			import json
			from pathlib import Path
			
			if not Path(file_path).exists():
				logger.error(f"Recording file not found: {file_path}")
				return None
			
			with open(file_path, 'r') as f:
				session_data = json.load(f)
			
			# Convert datetime strings back to datetime objects
			for key in ["started_at", "completed_at"]:
				if key in session_data and session_data[key]:
					session_data[key] = datetime.fromisoformat(session_data[key])
			
			for action in session_data.get("actions", []):
				if "timestamp" in action:
					action["timestamp"] = datetime.fromisoformat(action["timestamp"])
			
			# Generate session ID if not provided
			if not session_id:
				session_id = f"imported_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
			
			self.recording_sessions[session_id] = session_data
			
			logger.info(f"Imported recording session from {file_path} as {session_id}")
			return session_id
			
		except Exception as e:
			logger.error(f"Failed to import recording session from {file_path}: {e}")
			return None