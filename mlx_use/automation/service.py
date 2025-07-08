"""
Automation service for managing saved automations.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from .models import (
	SavedAutomation,
	AutomationExecutionResult,
	AutomationTemplate,
	AutomationMetadata,
	AutomationStep,
	AutomationAction,
	AutomationTrigger
)
from ..agent.service import Agent
from ..agent.views import AgentHistoryList
from ..controller.service import Controller

logger = logging.getLogger(__name__)


class AutomationService:
	"""Service for managing saved automations"""
	
	def __init__(self, storage_path: Optional[Union[str, Path]] = None):
		self.storage_path = Path(storage_path) if storage_path else Path.home() / ".macOS-use-automations"
		self.storage_path.mkdir(parents=True, exist_ok=True)
		
		# Initialize subdirectories
		self.automations_dir = self.storage_path / "automations"
		self.templates_dir = self.storage_path / "templates"
		self.executions_dir = self.storage_path / "executions"
		self.recordings_dir = self.storage_path / "recordings"
		
		for dir_path in [self.automations_dir, self.templates_dir, self.executions_dir, self.recordings_dir]:
			dir_path.mkdir(exist_ok=True)
		
		logger.info(f"Automation service initialized with storage at: {self.storage_path}")
	
	def save_automation_from_successful_run(
		self,
		name: str,
		task: str,
		history: AgentHistoryList,
		agent_params: Dict[str, Any],
		custom_system_message: Optional[str] = None,
		description: Optional[str] = None,
		category: Optional[str] = None,
		tags: Optional[List[str]] = None
	) -> SavedAutomation:
		"""Save a successful agent run as a reusable automation"""
		
		# Extract steps from agent history
		steps = []
		for i, history_item in enumerate(history.history):
			if history_item.model_output and history_item.model_output.action:
				step_actions = []
				
				for action in history_item.model_output.action:
					# Convert agent action to automation action
					action_dict = action.model_dump(exclude_unset=True)
					action_type = next(iter(action_dict.keys()))  # Get first key as action type
					parameters = action_dict[action_type]
					
					automation_action = AutomationAction(
						action_type=action_type,
						parameters=parameters,
						description=f"Step {i+1}: {action_type}"
					)
					step_actions.append(automation_action)
				
				if step_actions:
					step = AutomationStep(
						name=f"Step {i+1}",
						description=history_item.model_output.current_state.next_goal,
						actions=step_actions
					)
					steps.append(step)
		
		# Create automation metadata
		metadata = AutomationMetadata(
			created_at=datetime.now(),
			created_by="agent_run",
			source="successful_run",
			category=category,
			tags=tags or [],
			success_count=1,
			last_execution=datetime.now(),
			last_success=datetime.now()
		)
		
		# Create the automation
		automation = SavedAutomation(
			name=name,
			description=description or f"Automation created from successful execution of: {task}",
			steps=steps,
			system_prompt=custom_system_message,
			llm_provider=agent_params.get("llm_provider", "OpenAI"),
			llm_model=agent_params.get("llm_model", "gpt-4"),
			max_steps=agent_params.get("max_steps", 100),
			max_actions_per_step=agent_params.get("max_actions_per_step", 10),
			metadata=metadata,
			original_task=task,
			agent_parameters=agent_params
		)
		
		# Save to file
		self.save_automation(automation)
		
		logger.info(f"Saved automation '{name}' from successful run with {len(steps)} steps")
		return automation
	
	def save_automation(self, automation: SavedAutomation) -> None:
		"""Save automation to storage"""
		file_path = self.automations_dir / f"{automation.id}.json"
		automation.save_to_file(file_path)
		logger.debug(f"Saved automation {automation.name} to {file_path}")
	
	def load_automation(self, automation_id: str) -> Optional[SavedAutomation]:
		"""Load automation by ID"""
		file_path = self.automations_dir / f"{automation_id}.json"
		if not file_path.exists():
			return None
		
		try:
			return SavedAutomation.load_from_file(file_path)
		except Exception as e:
			logger.error(f"Failed to load automation {automation_id}: {e}")
			return None
	
	def list_automations(self) -> List[Dict[str, Any]]:
		"""List all saved automations with metadata"""
		automations = []
		
		for file_path in self.automations_dir.glob("*.json"):
			try:
				automation = SavedAutomation.load_from_file(file_path)
				automations.append({
					"id": automation.id,
					"name": automation.name,
					"description": automation.description,
					"category": automation.metadata.category,
					"tags": automation.metadata.tags,
					"created_at": automation.metadata.created_at,
					"updated_at": automation.metadata.updated_at,
					"success_count": automation.metadata.success_count,
					"failure_count": automation.metadata.failure_count,
					"last_execution": automation.metadata.last_execution,
					"steps_count": len(automation.steps),
					"has_schedule": bool(automation.get_schedule_info())
				})
			except Exception as e:
				logger.error(f"Failed to load automation metadata from {file_path}: {e}")
		
		# Sort by updated date, newest first
		automations.sort(key=lambda x: x["updated_at"], reverse=True)
		return automations
	
	def delete_automation(self, automation_id: str) -> bool:
		"""Delete automation by ID"""
		file_path = self.automations_dir / f"{automation_id}.json"
		if file_path.exists():
			file_path.unlink()
			logger.info(f"Deleted automation {automation_id}")
			return True
		return False
	
	def duplicate_automation(self, automation_id: str, new_name: str) -> Optional[SavedAutomation]:
		"""Duplicate an existing automation with a new name"""
		original = self.load_automation(automation_id)
		if not original:
			return None
		
		duplicate = original.model_copy(deep=True)
		duplicate.id = str(uuid.uuid4())
		duplicate.name = new_name
		duplicate.metadata = AutomationMetadata()
		duplicate.metadata.source = "duplicate"
		duplicate.metadata.category = original.metadata.category
		duplicate.metadata.tags = original.metadata.tags.copy()
		
		self.save_automation(duplicate)
		logger.info(f"Duplicated automation {automation_id} as {duplicate.id}")
		return duplicate
	
	def update_automation(self, automation_id: str, updates: Dict[str, Any]) -> Optional[SavedAutomation]:
		"""Update an existing automation"""
		automation = self.load_automation(automation_id)
		if not automation:
			return None
		
		# Update fields
		for key, value in updates.items():
			if hasattr(automation, key):
				setattr(automation, key, value)
		
		automation.metadata.updated_at = datetime.now()
		self.save_automation(automation)
		
		logger.info(f"Updated automation {automation_id}")
		return automation
	
	def search_automations(self, query: str, category: Optional[str] = None, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
		"""Search automations by name, description, category, or tags"""
		all_automations = self.list_automations()
		results = []
		
		query_lower = query.lower() if query else ""
		
		for automation in all_automations:
			# Check name and description
			match_text = (
				query_lower in automation["name"].lower() or
				(automation["description"] and query_lower in automation["description"].lower())
			)
			
			# Check category
			match_category = (
				category is None or 
				(automation["category"] and automation["category"].lower() == category.lower())
			)
			
			# Check tags
			match_tags = (
				tags is None or
				any(tag.lower() in [t.lower() for t in automation["tags"]] for tag in tags)
			)
			
			if match_text and match_category and match_tags:
				results.append(automation)
		
		return results
	
	def get_automation_by_name(self, name: str) -> Optional[SavedAutomation]:
		"""Get automation by name (useful for scheduled executions)"""
		for file_path in self.automations_dir.glob("*.json"):
			try:
				automation = SavedAutomation.load_from_file(file_path)
				if automation.name == name:
					return automation
			except Exception as e:
				logger.error(f"Failed to load automation from {file_path}: {e}")
		return None
	
	def save_execution_result(self, result: AutomationExecutionResult) -> None:
		"""Save automation execution result"""
		file_path = self.executions_dir / f"{result.execution_id}.json"
		
		with open(file_path, 'w') as f:
			json.dump(result.model_dump(), f, indent=2, default=str)
		
		logger.debug(f"Saved execution result {result.execution_id}")
	
	def get_execution_history(self, automation_id: str, limit: int = 50) -> List[AutomationExecutionResult]:
		"""Get execution history for an automation"""
		results = []
		
		for file_path in self.executions_dir.glob("*.json"):
			try:
				with open(file_path, 'r') as f:
					data = json.load(f)
				
				if data.get("automation_id") == automation_id:
					result = AutomationExecutionResult(**data)
					results.append(result)
			except Exception as e:
				logger.error(f"Failed to load execution result from {file_path}: {e}")
		
		# Sort by start time, newest first
		results.sort(key=lambda x: x.started_at, reverse=True)
		return results[:limit]
	
	def get_categories(self) -> List[str]:
		"""Get all unique categories"""
		categories = set()
		for automation in self.list_automations():
			if automation["category"]:
				categories.add(automation["category"])
		return sorted(list(categories))
	
	def get_tags(self) -> List[str]:
		"""Get all unique tags"""
		tags = set()
		for automation in self.list_automations():
			tags.update(automation["tags"])
		return sorted(list(tags))
	
	def export_automation(self, automation_id: str, file_path: Union[str, Path]) -> bool:
		"""Export automation to file"""
		automation = self.load_automation(automation_id)
		if not automation:
			return False
		
		try:
			automation.save_to_file(file_path)
			logger.info(f"Exported automation {automation_id} to {file_path}")
			return True
		except Exception as e:
			logger.error(f"Failed to export automation {automation_id}: {e}")
			return False
	
	def import_automation(self, file_path: Union[str, Path]) -> Optional[SavedAutomation]:
		"""Import automation from file"""
		try:
			automation = SavedAutomation.load_from_file(file_path)
			
			# Generate new ID to avoid conflicts
			automation.id = str(uuid.uuid4())
			automation.metadata.created_at = datetime.now()
			automation.metadata.updated_at = datetime.now()
			automation.metadata.source = "import"
			
			self.save_automation(automation)
			logger.info(f"Imported automation {automation.name} from {file_path}")
			return automation
		except Exception as e:
			logger.error(f"Failed to import automation from {file_path}: {e}")
			return None
	
	def create_automation_from_template(self, template_name: str, automation_name: str, parameters: Dict[str, Any]) -> Optional[SavedAutomation]:
		"""Create automation from template"""
		template = self.load_template(template_name)
		if not template:
			return None
		
		automation = template.create_automation(automation_name, parameters)
		self.save_automation(automation)
		
		logger.info(f"Created automation {automation_name} from template {template_name}")
		return automation
	
	def save_template(self, template: AutomationTemplate) -> None:
		"""Save automation template"""
		file_path = self.templates_dir / f"{template.name}.json"
		
		with open(file_path, 'w') as f:
			json.dump(template.model_dump(), f, indent=2, default=str)
		
		logger.debug(f"Saved template {template.name}")
	
	def load_template(self, template_name: str) -> Optional[AutomationTemplate]:
		"""Load automation template"""
		file_path = self.templates_dir / f"{template_name}.json"
		if not file_path.exists():
			return None
		
		try:
			with open(file_path, 'r') as f:
				data = json.load(f)
			return AutomationTemplate(**data)
		except Exception as e:
			logger.error(f"Failed to load template {template_name}: {e}")
			return None
	
	def list_templates(self) -> List[Dict[str, Any]]:
		"""List all available templates"""
		templates = []
		
		for file_path in self.templates_dir.glob("*.json"):
			try:
				template = self.load_template(file_path.stem)
				if template:
					templates.append({
						"name": template.name,
						"description": template.description,
						"category": template.category,
						"parameters": template.parameters,
						"preview_image": template.preview_image
					})
			except Exception as e:
				logger.error(f"Failed to load template metadata from {file_path}: {e}")
		
		return templates