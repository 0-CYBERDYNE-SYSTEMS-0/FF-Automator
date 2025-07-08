"""
Automation executor for running saved automations.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from .models import (
	SavedAutomation, 
	AutomationExecutionResult,
	AutomationStep,
	AutomationAction
)
from ..agent.service import Agent
from ..controller.service import Controller
from ..agent.prompts import SystemPrompt

logger = logging.getLogger(__name__)


class AutomationSystemPrompt(SystemPrompt):
	"""System prompt for automation execution"""
	
	def __init__(self, action_description: str, current_date: datetime, max_actions_per_step: int = 10, 
				 automation_name: str = None, automation_description: str = None, custom_message: str = None):
		super().__init__(action_description, current_date, max_actions_per_step)
		self.automation_name = automation_name
		self.automation_description = automation_description
		self.custom_message = custom_message
	
	def important_rules(self) -> str:
		"""Enhanced rules for automation execution"""
		text = super().important_rules()
		
		automation_rules = """

8. AUTOMATION EXECUTION:
   - You are executing a saved automation workflow.
   - Follow the original task goals and parameters exactly.
   - Be consistent with the automation's intended behavior.
   - If the automation was designed for specific conditions, adapt carefully to current state.
"""
		
		if self.automation_name:
			automation_rules += f"   - Automation Name: {self.automation_name}\n"
		
		if self.automation_description:
			automation_rules += f"   - Automation Purpose: {self.automation_description}\n"
		
		if self.custom_message:
			automation_rules += f"\n9. CUSTOM AUTOMATION INSTRUCTIONS:\n   {self.custom_message}\n"
		
		return text + automation_rules


class AutomationExecutor:
	"""Executor for running saved automations"""
	
	def __init__(self):
		self.controller = Controller()
		logger.info("Automation executor initialized")
	
	async def execute_automation(
		self, 
		automation: SavedAutomation, 
		runtime_parameters: Optional[Dict[str, Any]] = None,
		callback: Optional[callable] = None
	) -> AutomationExecutionResult:
		"""Execute a saved automation"""
		
		execution_result = AutomationExecutionResult(
			automation_id=automation.id,
			started_at=datetime.now()
		)
		
		try:
			logger.info(f"Starting execution of automation: {automation.name}")
			
			# Merge runtime parameters with automation variables
			variables = self._prepare_variables(automation, runtime_parameters or {})
			
			# Get LLM instance
			llm = self._get_llm_for_automation(automation)
			
			# Create system prompt for automation
			system_prompt_kwargs = {
				"automation_name": automation.name,
				"automation_description": automation.description,
				"custom_message": automation.system_prompt
			}
			
			# Create agent with automation configuration
			agent = Agent(
				task=automation.original_task or f"Execute automation: {automation.name}",
				llm=llm,
				controller=self.controller,
				max_actions_per_step=automation.max_actions_per_step,
				system_prompt_class=AutomationSystemPrompt,
				system_prompt_kwargs=system_prompt_kwargs,
				**automation.agent_parameters
			)
			
			# Set up execution callback if provided
			if callback:
				def step_callback(state: str, output, step: int):
					callback({
						"type": "step_update",
						"step": step,
						"state": state,
						"output": output,
						"automation_id": automation.id
					})
				agent.register_new_step_callback = step_callback
			
			# Execute the automation
			history = await agent.run(max_steps=automation.max_steps)
			
			# Process results
			if history.is_done():
				execution_result.complete(success=True)
				final_result = history.history[-1].result[-1].extracted_content if history.history and history.history[-1].result else "Automation completed successfully"
				execution_result.result_data["final_result"] = final_result
				logger.info(f"Automation {automation.name} completed successfully")
			else:
				execution_result.complete(success=False, error="Automation failed to complete within maximum steps")
				logger.warning(f"Automation {automation.name} failed to complete")
			
			# Set execution statistics
			execution_result.steps_executed = len(history.history)
			execution_result.actions_executed = sum(len(step.result) for step in history.history if step.result)
			
			# Extract logs from history
			execution_result.logs = self._extract_logs_from_history(history)
			
		except Exception as e:
			logger.error(f"Error executing automation {automation.name}: {e}")
			execution_result.complete(success=False, error=str(e))
		
		return execution_result
	
	async def execute_automation_step_by_step(
		self,
		automation: SavedAutomation,
		runtime_parameters: Optional[Dict[str, Any]] = None,
		callback: Optional[callable] = None
	) -> AutomationExecutionResult:
		"""Execute automation using the defined steps (alternative to agent-based execution)"""
		
		execution_result = AutomationExecutionResult(
			automation_id=automation.id,
			started_at=datetime.now()
		)
		
		try:
			logger.info(f"Starting step-by-step execution of automation: {automation.name}")
			
			# Prepare variables
			variables = self._prepare_variables(automation, runtime_parameters or {})
			
			# Execute each step
			for step_index, step in enumerate(automation.steps):
				if not step.enabled:
					logger.info(f"Skipping disabled step: {step.name}")
					continue
				
				logger.info(f"Executing step {step_index + 1}: {step.name}")
				
				if callback:
					callback({
						"type": "step_start",
						"step_index": step_index,
						"step_name": step.name,
						"automation_id": automation.id
					})
				
				try:
					# Execute step actions
					step_success = await self._execute_step(step, variables, callback)
					
					if not step_success:
						if step.on_error == "stop":
							raise Exception(f"Step {step.name} failed and error handling is set to stop")
						elif step.on_error == "continue":
							logger.warning(f"Step {step.name} failed but continuing due to error handling setting")
							continue
						elif step.on_error == "skip":
							logger.info(f"Skipping remaining actions in step {step.name} due to error")
							continue
					
					execution_result.steps_executed += 1
					
				except Exception as e:
					logger.error(f"Error in step {step.name}: {e}")
					if step.on_error == "stop":
						raise e
					else:
						execution_result.logs.append(f"Step {step.name} failed: {str(e)}")
			
			execution_result.complete(success=True)
			logger.info(f"Step-by-step automation {automation.name} completed successfully")
			
		except Exception as e:
			logger.error(f"Error in step-by-step execution of {automation.name}: {e}")
			execution_result.complete(success=False, error=str(e))
		
		return execution_result
	
	async def _execute_step(self, step: AutomationStep, variables: Dict[str, Any], callback: Optional[callable] = None) -> bool:
		"""Execute a single automation step"""
		
		for action_index, action in enumerate(step.actions):
			try:
				logger.debug(f"Executing action {action_index + 1} in step {step.name}: {action.action_type}")
				
				# Wait before action if specified
				if action.wait_before:
					await asyncio.sleep(action.wait_before)
				
				# Replace variables in action parameters
				parameters = self._replace_variables_in_parameters(action.parameters, variables)
				
				# Execute action through controller
				# Note: This is simplified - in practice, you'd need to convert automation actions 
				# to the controller's action format
				action_model = self._create_action_model(action.action_type, parameters)
				if action_model:
					result = await self.controller.multi_act([action_model], None)
					
					if result and result[0].error:
						logger.error(f"Action {action.action_type} failed: {result[0].error}")
						
						# Retry logic
						for retry in range(action.retry_count):
							logger.info(f"Retrying action {action.action_type} (attempt {retry + 1})")
							await asyncio.sleep(1)  # Wait before retry
							
							result = await self.controller.multi_act([action_model], None)
							if result and not result[0].error:
								break
						else:
							# All retries failed
							return False
				
				# Wait after action if specified
				if action.wait_after:
					await asyncio.sleep(action.wait_after)
				
				if callback:
					callback({
						"type": "action_complete",
						"action_type": action.action_type,
						"success": True
					})
			
			except Exception as e:
				logger.error(f"Error executing action {action.action_type}: {e}")
				if callback:
					callback({
						"type": "action_complete",
						"action_type": action.action_type,
						"success": False,
						"error": str(e)
					})
				return False
		
		return True
	
	def _prepare_variables(self, automation: SavedAutomation, runtime_parameters: Dict[str, Any]) -> Dict[str, Any]:
		"""Prepare variables for automation execution"""
		variables = {}
		
		# Add automation variables
		for var in automation.variables:
			variables[var.name] = var.value
		
		# Override with runtime parameters
		variables.update(runtime_parameters)
		
		# Add system variables
		variables.update({
			"current_time": datetime.now().isoformat(),
			"automation_name": automation.name,
			"automation_id": automation.id
		})
		
		return variables
	
	def _replace_variables_in_parameters(self, parameters: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
		"""Replace variable placeholders in action parameters"""
		import re
		
		def replace_in_value(value):
			if isinstance(value, str):
				# Replace {{variable_name}} patterns
				pattern = r'\{\{\s*(\w+)\s*\}\}'
				
				def replacer(match):
					var_name = match.group(1)
					return str(variables.get(var_name, match.group(0)))
				
				return re.sub(pattern, replacer, value)
			elif isinstance(value, dict):
				return {k: replace_in_value(v) for k, v in value.items()}
			elif isinstance(value, list):
				return [replace_in_value(item) for item in value]
			else:
				return value
		
		return {k: replace_in_value(v) for k, v in parameters.items()}
	
	def _create_action_model(self, action_type: str, parameters: Dict[str, Any]):
		"""Create action model for controller execution"""
		# This would need to be implemented based on your controller's action model structure
		# For now, return a placeholder
		logger.warning("Action model creation not fully implemented - using placeholder")
		return None
	
	def _get_llm_for_automation(self, automation: SavedAutomation):
		"""Get LLM instance for automation execution"""
		from web_interface.api.main import get_llm
		
		try:
			return get_llm(automation.llm_provider, automation.llm_model)
		except Exception as e:
			logger.error(f"Failed to create LLM for automation: {e}")
			# Fallback to default
			return get_llm("OpenAI", "gpt-4")
	
	def _extract_logs_from_history(self, history) -> List[str]:
		"""Extract logs from agent execution history"""
		logs = []
		
		for i, step in enumerate(history.history):
			if step.model_output:
				logs.append(f"Step {i+1}: {step.model_output.current_state.next_goal}")
				
				for action in step.model_output.action:
					action_dict = action.model_dump(exclude_unset=True)
					action_type = next(iter(action_dict.keys()))
					logs.append(f"  Action: {action_type}")
			
			if step.result:
				for result in step.result:
					if result.error:
						logs.append(f"  Error: {result.error}")
					elif result.extracted_content:
						logs.append(f"  Result: {result.extracted_content}")
		
		return logs
	
	async def validate_automation(self, automation: SavedAutomation) -> List[str]:
		"""Validate automation before execution"""
		issues = []
		
		# Check basic structure
		if not automation.steps:
			issues.append("Automation has no steps defined")
		
		if not automation.original_task and not automation.name:
			issues.append("Automation has no task or name defined")
		
		# Check steps
		for i, step in enumerate(automation.steps):
			if not step.actions:
				issues.append(f"Step {i+1} ({step.name}) has no actions")
			
			# Check actions
			for j, action in enumerate(step.actions):
				if not action.action_type:
					issues.append(f"Step {i+1}, Action {j+1} has no action type")
		
		# Check LLM configuration
		try:
			self._get_llm_for_automation(automation)
		except Exception as e:
			issues.append(f"LLM configuration invalid: {str(e)}")
		
		return issues