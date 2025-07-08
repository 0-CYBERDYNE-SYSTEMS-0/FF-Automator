"""
Automation models for saved automation workflows.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from pathlib import Path
import json
import uuid


class AutomationAction(BaseModel):
	"""Single action in an automation workflow"""
	action_type: str = Field(description="Type of action (e.g. 'click_element', 'type_text', 'open_app')")
	parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the action")
	description: Optional[str] = Field(None, description="Human-readable description of the action")
	wait_before: Optional[float] = Field(None, description="Seconds to wait before executing this action")
	wait_after: Optional[float] = Field(None, description="Seconds to wait after executing this action")
	retry_count: int = Field(3, description="Number of retry attempts if action fails")
	timeout: Optional[float] = Field(None, description="Timeout in seconds for this action")


class AutomationStep(BaseModel):
	"""A step in an automation workflow containing one or more actions"""
	step_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for this step")
	name: str = Field(description="Name of the step")
	description: Optional[str] = Field(None, description="Description of what this step does")
	actions: List[AutomationAction] = Field(default_factory=list, description="Actions to execute in this step")
	condition: Optional[str] = Field(None, description="Condition that must be true to execute this step")
	on_error: str = Field("stop", description="What to do on error: 'stop', 'continue', 'retry', 'skip'")
	max_retries: int = Field(3, description="Maximum number of retries for this step")
	enabled: bool = Field(True, description="Whether this step is enabled")


class AutomationTrigger(BaseModel):
	"""Trigger configuration for when to run an automation"""
	trigger_type: str = Field(description="Type of trigger: 'manual', 'schedule', 'event', 'webhook'")
	schedule: Optional[str] = Field(None, description="Cron expression for scheduled triggers")
	event: Optional[str] = Field(None, description="Event name for event-based triggers")
	webhook_url: Optional[str] = Field(None, description="Webhook URL for webhook triggers")
	enabled: bool = Field(True, description="Whether this trigger is enabled")
	parameters: Dict[str, Any] = Field(default_factory=dict, description="Additional trigger parameters")


class AutomationVariable(BaseModel):
	"""Variable that can be used in automation workflows"""
	name: str = Field(description="Variable name")
	value: Any = Field(description="Variable value")
	type: str = Field("string", description="Variable type: 'string', 'number', 'boolean', 'array', 'object'")
	description: Optional[str] = Field(None, description="Description of the variable")
	secret: bool = Field(False, description="Whether this variable contains sensitive information")


class AutomationConfig(BaseModel):
	"""Configuration for automation execution"""
	max_execution_time: int = Field(300, description="Maximum execution time in seconds")
	max_retry_attempts: int = Field(3, description="Maximum retry attempts for failed actions")
	default_wait_time: float = Field(1.0, description="Default wait time between actions")
	error_handling: str = Field("stop", description="Default error handling: 'stop', 'continue', 'retry'")
	log_level: str = Field("info", description="Log level: 'debug', 'info', 'warning', 'error'")
	save_screenshots: bool = Field(False, description="Whether to save screenshots on errors")
	screenshot_path: Optional[str] = Field(None, description="Path to save screenshots")


class AutomationMetadata(BaseModel):
	"""Metadata about the automation"""
	created_at: datetime = Field(default_factory=datetime.now)
	updated_at: datetime = Field(default_factory=datetime.now)
	created_by: Optional[str] = Field(None, description="User who created the automation")
	version: str = Field("1.0.0", description="Version of the automation")
	tags: List[str] = Field(default_factory=list, description="Tags for categorization")
	category: Optional[str] = Field(None, description="Category of the automation")
	source: Optional[str] = Field(None, description="Source of the automation (e.g. 'recorded', 'manual')")
	success_count: int = Field(0, description="Number of successful executions")
	failure_count: int = Field(0, description="Number of failed executions")
	last_execution: Optional[datetime] = Field(None, description="Last execution time")
	last_success: Optional[datetime] = Field(None, description="Last successful execution time")
	last_failure: Optional[datetime] = Field(None, description="Last failed execution time")


class SavedAutomation(BaseModel):
	"""Complete saved automation workflow"""
	id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier")
	name: str = Field(description="Name of the automation")
	description: Optional[str] = Field(None, description="Description of what the automation does")
	
	# Core workflow
	steps: List[AutomationStep] = Field(default_factory=list, description="Steps in the automation")
	variables: List[AutomationVariable] = Field(default_factory=list, description="Variables used in the automation")
	
	# Execution configuration
	config: AutomationConfig = Field(default_factory=AutomationConfig, description="Execution configuration")
	triggers: List[AutomationTrigger] = Field(default_factory=list, description="Triggers for the automation")
	
	# System prompt and LLM configuration
	system_prompt: Optional[str] = Field(None, description="Custom system prompt for the automation")
	llm_provider: str = Field("OpenAI", description="LLM provider to use")
	llm_model: str = Field("gpt-4", description="LLM model to use")
	max_steps: int = Field(100, description="Maximum number of steps the agent can take")
	max_actions_per_step: int = Field(10, description="Maximum actions per step")
	
	# Metadata
	metadata: AutomationMetadata = Field(default_factory=AutomationMetadata, description="Automation metadata")
	
	# Original interaction data
	original_task: Optional[str] = Field(None, description="Original task description")
	original_conversation: Optional[List[Dict]] = Field(None, description="Original conversation history")
	agent_parameters: Dict[str, Any] = Field(default_factory=dict, description="Original agent parameters")
	
	def save_to_file(self, file_path: Union[str, Path]) -> None:
		"""Save automation to JSON file"""
		path = Path(file_path)
		path.parent.mkdir(parents=True, exist_ok=True)
		
		# Update metadata
		self.metadata.updated_at = datetime.now()
		
		with open(path, 'w') as f:
			json.dump(self.model_dump(), f, indent=2, default=str)
	
	@classmethod
	def load_from_file(cls, file_path: Union[str, Path]) -> 'SavedAutomation':
		"""Load automation from JSON file"""
		path = Path(file_path)
		if not path.exists():
			raise FileNotFoundError(f"Automation file not found: {path}")
		
		with open(path, 'r') as f:
			data = json.load(f)
		
		return cls(**data)
	
	def to_agent_params(self) -> Dict[str, Any]:
		"""Convert automation to agent parameters"""
		return {
			"task": self.original_task or self.name,
			"max_steps": self.max_steps,
			"max_actions_per_step": self.max_actions_per_step,
			"system_prompt_kwargs": {"custom_message": self.system_prompt} if self.system_prompt else {},
			**self.agent_parameters
		}
	
	def get_schedule_info(self) -> Optional[Dict[str, Any]]:
		"""Get scheduling information if automation has scheduled triggers"""
		scheduled_triggers = [t for t in self.triggers if t.trigger_type == "schedule" and t.enabled]
		if not scheduled_triggers:
			return None
		
		return {
			"schedules": [{"schedule": t.schedule, "parameters": t.parameters} for t in scheduled_triggers],
			"next_run": None  # Will be calculated by scheduler
		}
	
	def update_execution_stats(self, success: bool) -> None:
		"""Update execution statistics"""
		self.metadata.last_execution = datetime.now()
		if success:
			self.metadata.success_count += 1
			self.metadata.last_success = datetime.now()
		else:
			self.metadata.failure_count += 1
			self.metadata.last_failure = datetime.now()
		
		self.metadata.updated_at = datetime.now()


class AutomationExecutionResult(BaseModel):
	"""Result of an automation execution"""
	automation_id: str = Field(description="ID of the automation that was executed")
	execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique execution ID")
	started_at: datetime = Field(default_factory=datetime.now)
	completed_at: Optional[datetime] = Field(None)
	success: bool = Field(False, description="Whether the execution was successful")
	error: Optional[str] = Field(None, description="Error message if execution failed")
	steps_executed: int = Field(0, description="Number of steps executed")
	actions_executed: int = Field(0, description="Number of actions executed")
	duration: Optional[float] = Field(None, description="Execution duration in seconds")
	result_data: Dict[str, Any] = Field(default_factory=dict, description="Additional result data")
	logs: List[str] = Field(default_factory=list, description="Execution logs")
	screenshots: List[str] = Field(default_factory=list, description="Screenshot paths")
	
	def complete(self, success: bool, error: Optional[str] = None) -> None:
		"""Mark execution as completed"""
		self.completed_at = datetime.now()
		self.success = success
		self.error = error
		if self.started_at and self.completed_at:
			self.duration = (self.completed_at - self.started_at).total_seconds()


class AutomationTemplate(BaseModel):
	"""Template for creating new automations"""
	name: str = Field(description="Template name")
	description: str = Field(description="Template description")
	category: str = Field(description="Template category")
	template_automation: SavedAutomation = Field(description="Template automation")
	parameters: List[Dict[str, Any]] = Field(default_factory=list, description="Template parameters")
	preview_image: Optional[str] = Field(None, description="Preview image path")
	
	def create_automation(self, name: str, parameters: Dict[str, Any]) -> SavedAutomation:
		"""Create a new automation from this template"""
		automation = self.template_automation.model_copy(deep=True)
		automation.id = str(uuid.uuid4())
		automation.name = name
		automation.metadata = AutomationMetadata()
		automation.metadata.source = "template"
		automation.metadata.category = self.category
		
		# Apply parameters
		for param_name, param_value in parameters.items():
			# Replace placeholders in automation
			self._replace_parameter(automation, param_name, param_value)
		
		return automation
	
	def _replace_parameter(self, automation: SavedAutomation, param_name: str, param_value: Any) -> None:
		"""Replace parameter placeholders in automation"""
		placeholder = f"{{{{ {param_name} }}}}"
		
		# Replace in task description
		if automation.original_task:
			automation.original_task = automation.original_task.replace(placeholder, str(param_value))
		
		# Replace in steps
		for step in automation.steps:
			if step.description:
				step.description = step.description.replace(placeholder, str(param_value))
			
			for action in step.actions:
				if action.description:
					action.description = action.description.replace(placeholder, str(param_value))
				
				# Replace in action parameters
				for key, value in action.parameters.items():
					if isinstance(value, str):
						action.parameters[key] = value.replace(placeholder, str(param_value))