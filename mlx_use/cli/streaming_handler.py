import asyncio
import logging
import sys
import threading
import time
from typing import Any, Callable, Optional
from io import StringIO

logger = logging.getLogger(__name__)


class StreamingOutputHandler:
	"""Handles real-time output streaming for CLI"""
	
	def __init__(self):
		self.active = False
		self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
		self.spinner_index = 0
		self.spinner_thread: Optional[threading.Thread] = None
		self.stop_spinner = False
		self.current_status = ""
		self.log_buffer = StringIO()
		self.original_stdout = sys.stdout
		self.original_stderr = sys.stderr
		
		# Setup custom log handler
		self.setup_log_capture()
	
	def setup_log_capture(self):
		"""Setup log capture to intercept agent output"""
		class CLILogHandler(logging.Handler):
			def __init__(self, streaming_handler):
				super().__init__()
				self.streaming_handler = streaming_handler
			
			def emit(self, record):
				if self.streaming_handler.active:
					log_entry = self.format(record)
					self.streaming_handler.process_log_entry(log_entry)
		
		# Add handler to mlx_use logger
		mlx_logger = logging.getLogger('mlx_use')
		self.cli_handler = CLILogHandler(self)
		self.cli_handler.setLevel(logging.INFO)
		formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
		self.cli_handler.setFormatter(formatter)
		mlx_logger.addHandler(self.cli_handler)
	
	def start_streaming(self, task_description: str):
		"""Start streaming output for a task"""
		self.active = True
		self.current_status = f"Starting: {task_description}"
		self.print_status_line()
		self.start_spinner()
	
	def stop_streaming(self):
		"""Stop streaming output"""
		self.active = False
		self.stop_spinner_animation()
		self.clear_status_line()
	
	def update_status(self, status: str):
		"""Update the current status message"""
		if self.active:
			self.current_status = status
			self.print_status_line()
	
	def process_log_entry(self, log_entry: str):
		"""Process a log entry and update status if relevant"""
		if not self.active:
			return
		
		# Extract meaningful status updates from logs
		if "Step" in log_entry:
			step_match = log_entry.split("Step")[-1].strip()
			self.update_status(f"Executing step {step_match}")
		elif "📍" in log_entry:
			self.update_status(log_entry.split("📍")[-1].strip())
		elif "✅" in log_entry:
			self.update_status("✅ Task completed successfully")
		elif "❌" in log_entry:
			self.update_status(f"❌ {log_entry}")
		elif any(action in log_entry.lower() for action in ["clicking", "typing", "opening", "scrolling"]):
			action_desc = log_entry.split("-")[-1].strip() if "-" in log_entry else log_entry
			self.update_status(f"🎯 {action_desc}")
	
	def start_spinner(self):
		"""Start the spinner animation"""
		self.stop_spinner = False
		self.spinner_thread = threading.Thread(target=self._spinner_animation)
		self.spinner_thread.daemon = True
		self.spinner_thread.start()
	
	def stop_spinner_animation(self):
		"""Stop the spinner animation"""
		self.stop_spinner = True
		if self.spinner_thread:
			self.spinner_thread.join(timeout=1)
	
	def _spinner_animation(self):
		"""Run the spinner animation in a separate thread"""
		while not self.stop_spinner:
			self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
			if self.active:
				self.print_status_line()
			time.sleep(0.1)
	
	def print_status_line(self):
		"""Print the current status line with spinner"""
		if not self.active:
			return
		
		spinner = self.spinner_chars[self.spinner_index]
		status_line = f"\r{spinner} {self.current_status}"
		
		# Clear line and print status
		print("\r" + " " * 80, end="")  # Clear line
		print(f"\r{status_line}", end="", flush=True)
	
	def clear_status_line(self):
		"""Clear the current status line"""
		print("\r" + " " * 80, end="")  # Clear line
		print("\r", end="", flush=True)
	
	def print_final_message(self, message: str, success: bool = True):
		"""Print a final message after clearing the status line"""
		self.clear_status_line()
		icon = "✅" if success else "❌"
		print(f"{icon} {message}")


class ProgressCallback:
	"""Callback class for agent progress updates"""
	
	def __init__(self, streaming_handler: StreamingOutputHandler):
		self.streaming_handler = streaming_handler
	
	def on_step_start(self, step_number: int, description: str):
		"""Called when a step starts"""
		self.streaming_handler.update_status(f"Step {step_number}: {description}")
	
	def on_action_start(self, action_type: str, details: str):
		"""Called when an action starts"""
		self.streaming_handler.update_status(f"🎯 {action_type}: {details}")
	
	def on_step_complete(self, step_number: int, success: bool):
		"""Called when a step completes"""
		status = "✅" if success else "❌"
		self.streaming_handler.update_status(f"{status} Step {step_number} completed")
	
	def on_task_complete(self, success: bool, message: str):
		"""Called when the entire task completes"""
		self.streaming_handler.print_final_message(message, success)


class StreamCapture:
	"""Context manager to capture stdout/stderr"""
	
	def __init__(self, streaming_handler: StreamingOutputHandler):
		self.streaming_handler = streaming_handler
		self.captured_output = StringIO()
	
	def __enter__(self):
		self.original_stdout = sys.stdout
		self.original_stderr = sys.stderr
		sys.stdout = self.captured_output
		sys.stderr = self.captured_output
		return self
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		sys.stdout = self.original_stdout
		sys.stderr = self.original_stderr
		
		# Process any captured output
		output = self.captured_output.getvalue()
		if output.strip() and self.streaming_handler.active:
			# Process output for relevant information
			lines = output.strip().split('\n')
			for line in lines:
				self.streaming_handler.process_log_entry(line)