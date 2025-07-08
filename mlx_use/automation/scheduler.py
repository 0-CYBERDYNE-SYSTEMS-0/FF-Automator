"""
Automation scheduler for running automations on schedule.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from threading import Thread
from typing import Dict, List, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor

try:
	import schedule
except ImportError:
	schedule = None

from .models import SavedAutomation, AutomationExecutionResult
from .service import AutomationService
from .executor import AutomationExecutor

logger = logging.getLogger(__name__)


class AutomationScheduler:
	"""Scheduler for running automations based on triggers"""
	
	def __init__(self, automation_service: AutomationService, executor: AutomationExecutor):
		self.automation_service = automation_service
		self.executor = executor
		self.is_running = False
		self.thread_pool = ThreadPoolExecutor(max_workers=5)
		self.scheduled_jobs = {}  # automation_id -> schedule job
		self.scheduler_thread = None
		
		logger.info("Automation scheduler initialized")
	
	def start(self) -> None:
		"""Start the scheduler"""
		if not schedule:
			logger.warning("Schedule library not available - scheduler will not start")
			return
			
		if self.is_running:
			logger.warning("Scheduler is already running")
			return
		
		self.is_running = True
		self._load_scheduled_automations()
		
		# Start scheduler thread
		self.scheduler_thread = Thread(target=self._run_scheduler, daemon=True)
		self.scheduler_thread.start()
		
		logger.info("Automation scheduler started")
	
	def stop(self) -> None:
		"""Stop the scheduler"""
		self.is_running = False
		if schedule:
			schedule.clear()
		self.scheduled_jobs.clear()
		
		if self.scheduler_thread:
			self.scheduler_thread.join(timeout=5)
		
		self.thread_pool.shutdown(wait=True)
		logger.info("Automation scheduler stopped")
	
	def _run_scheduler(self) -> None:
		"""Main scheduler loop"""
		while self.is_running:
			try:
				schedule.run_pending()
				time.sleep(1)
			except Exception as e:
				logger.error(f"Error in scheduler loop: {e}")
				time.sleep(5)
	
	def _load_scheduled_automations(self) -> None:
		"""Load all automations with scheduled triggers"""
		automations = self.automation_service.list_automations()
		
		for automation_info in automations:
			automation = self.automation_service.load_automation(automation_info["id"])
			if automation and automation.get_schedule_info():
				self.schedule_automation(automation)
	
	def schedule_automation(self, automation: SavedAutomation) -> bool:
		"""Schedule an automation based on its triggers"""
		schedule_info = automation.get_schedule_info()
		if not schedule_info:
			return False
		
		try:
			# Clear existing schedule for this automation
			self.unschedule_automation(automation.id)
			
			jobs = []
			for schedule_config in schedule_info["schedules"]:
				cron_expression = schedule_config["schedule"]
				parameters = schedule_config.get("parameters", {})
				
				job = self._parse_and_schedule_cron(
					cron_expression, 
					automation, 
					parameters
				)
				if job:
					jobs.append(job)
			
			if jobs:
				self.scheduled_jobs[automation.id] = jobs
				logger.info(f"Scheduled automation '{automation.name}' with {len(jobs)} triggers")
				return True
			
		except Exception as e:
			logger.error(f"Failed to schedule automation {automation.name}: {e}")
		
		return False
	
	def unschedule_automation(self, automation_id: str) -> None:
		"""Remove automation from scheduler"""
		if automation_id in self.scheduled_jobs:
			jobs = self.scheduled_jobs[automation_id]
			for job in jobs:
				schedule.cancel_job(job)
			del self.scheduled_jobs[automation_id]
			logger.info(f"Unscheduled automation {automation_id}")
	
	def _parse_and_schedule_cron(self, cron_expression: str, automation: SavedAutomation, parameters: Dict[str, Any]):
		"""Parse cron expression and create schedule job"""
		# This is a simplified cron parser. For production, use a proper cron library like croniter
		parts = cron_expression.strip().split()
		
		if not schedule or len(parts) != 5:
			logger.error(f"Invalid cron expression or schedule not available: {cron_expression}")
			return None
		
		minute, hour, day, month, weekday = parts
		
		# Create execution function
		def execute_automation():
			self._execute_scheduled_automation(automation, parameters)
		
		try:
			# Handle daily schedules (most common case)
			if hour != "*" and minute != "*" and day == "*" and month == "*" and weekday == "*":
				time_str = f"{hour.zfill(2)}:{minute.zfill(2)}"
				job = schedule.every().day.at(time_str).do(execute_automation)
				logger.info(f"Scheduled daily at {time_str} for automation {automation.name}")
				return job
			
			# Handle weekly schedules
			elif weekday != "*" and hour != "*" and minute != "*":
				time_str = f"{hour.zfill(2)}:{minute.zfill(2)}"
				weekday_map = {
					"0": "sunday", "1": "monday", "2": "tuesday", "3": "wednesday",
					"4": "thursday", "5": "friday", "6": "saturday"
				}
				day_name = weekday_map.get(weekday, weekday.lower())
				
				if day_name in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
					job = getattr(schedule.every(), day_name).at(time_str).do(execute_automation)
					logger.info(f"Scheduled weekly on {day_name} at {time_str} for automation {automation.name}")
					return job
			
			# Handle hourly schedules
			elif minute != "*" and hour == "*":
				job = schedule.every().hour.at(f":{minute.zfill(2)}").do(execute_automation)
				logger.info(f"Scheduled hourly at minute {minute} for automation {automation.name}")
				return job
			
			# Handle interval schedules (simplified)
			elif cron_expression.startswith("*/"):
				interval = int(cron_expression[2:].split()[0])
				if "minute" in cron_expression or len(parts) == 1:
					job = schedule.every(interval).minutes.do(execute_automation)
					logger.info(f"Scheduled every {interval} minutes for automation {automation.name}")
					return job
				elif "hour" in cron_expression:
					job = schedule.every(interval).hours.do(execute_automation)
					logger.info(f"Scheduled every {interval} hours for automation {automation.name}")
					return job
			
			logger.warning(f"Unsupported cron expression: {cron_expression}")
			return None
			
		except Exception as e:
			logger.error(f"Failed to parse cron expression {cron_expression}: {e}")
			return None
	
	def _execute_scheduled_automation(self, automation: SavedAutomation, parameters: Dict[str, Any]) -> None:
		"""Execute a scheduled automation"""
		logger.info(f"Executing scheduled automation: {automation.name}")
		
		# Submit to thread pool to avoid blocking scheduler
		future = self.thread_pool.submit(
			self._run_automation_async, 
			automation, 
			parameters
		)
		
		# Log any exceptions
		def handle_result(fut):
			try:
				fut.result()
			except Exception as e:
				logger.error(f"Scheduled automation {automation.name} failed: {e}")
		
		future.add_done_callback(handle_result)
	
	def _run_automation_async(self, automation: SavedAutomation, parameters: Dict[str, Any]) -> None:
		"""Run automation in thread pool"""
		try:
			# Create new event loop for this thread
			loop = asyncio.new_event_loop()
			asyncio.set_event_loop(loop)
			
			# Execute the automation
			result = loop.run_until_complete(
				self.executor.execute_automation(automation, parameters)
			)
			
			# Update automation stats
			automation.update_execution_stats(result.success)
			self.automation_service.save_automation(automation)
			
			logger.info(f"Scheduled automation {automation.name} completed with success={result.success}")
			
		except Exception as e:
			logger.error(f"Error executing scheduled automation {automation.name}: {e}")
		finally:
			loop.close()
	
	def get_scheduled_automations(self) -> List[Dict[str, Any]]:
		"""Get list of scheduled automations with next run times"""
		scheduled_list = []
		
		for automation_id, jobs in self.scheduled_jobs.items():
			automation = self.automation_service.load_automation(automation_id)
			if automation:
				next_run = None
				if jobs:
					# Get earliest next run time
					next_runs = [job.next_run for job in jobs if job.next_run]
					if next_runs:
						next_run = min(next_runs)
				
				scheduled_list.append({
					"automation_id": automation_id,
					"name": automation.name,
					"description": automation.description,
					"schedules": len(jobs),
					"next_run": next_run,
					"last_execution": automation.metadata.last_execution,
					"success_count": automation.metadata.success_count,
					"failure_count": automation.metadata.failure_count
				})
		
		return scheduled_list
	
	def add_schedule_to_automation(self, automation_id: str, cron_expression: str, parameters: Optional[Dict[str, Any]] = None) -> bool:
		"""Add a new schedule to an existing automation"""
		automation = self.automation_service.load_automation(automation_id)
		if not automation:
			return False
		
		from .models import AutomationTrigger
		
		# Create new schedule trigger
		trigger = AutomationTrigger(
			trigger_type="schedule",
			schedule=cron_expression,
			parameters=parameters or {},
			enabled=True
		)
		
		# Add to automation
		automation.triggers.append(trigger)
		automation.metadata.updated_at = datetime.now()
		
		# Save and reschedule
		self.automation_service.save_automation(automation)
		self.schedule_automation(automation)
		
		logger.info(f"Added schedule {cron_expression} to automation {automation.name}")
		return True
	
	def remove_schedule_from_automation(self, automation_id: str, schedule_index: int) -> bool:
		"""Remove a schedule from an automation"""
		automation = self.automation_service.load_automation(automation_id)
		if not automation:
			return False
		
		# Find and remove schedule trigger
		schedule_triggers = [t for t in automation.triggers if t.trigger_type == "schedule"]
		if 0 <= schedule_index < len(schedule_triggers):
			trigger_to_remove = schedule_triggers[schedule_index]
			automation.triggers.remove(trigger_to_remove)
			automation.metadata.updated_at = datetime.now()
			
			# Save and reschedule
			self.automation_service.save_automation(automation)
			
			# Reschedule with remaining triggers
			if any(t.trigger_type == "schedule" for t in automation.triggers):
				self.schedule_automation(automation)
			else:
				self.unschedule_automation(automation_id)
			
			logger.info(f"Removed schedule from automation {automation.name}")
			return True
		
		return False
	
	def is_automation_scheduled(self, automation_id: str) -> bool:
		"""Check if automation is currently scheduled"""
		return automation_id in self.scheduled_jobs
	
	def get_next_run_time(self, automation_id: str) -> Optional[datetime]:
		"""Get next run time for scheduled automation"""
		if automation_id not in self.scheduled_jobs:
			return None
		
		jobs = self.scheduled_jobs[automation_id]
		next_runs = [job.next_run for job in jobs if job.next_run]
		
		if next_runs:
			return min(next_runs)
		
		return None