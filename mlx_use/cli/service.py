import asyncio
import json
import logging
import os
import readline
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from mlx_use import Agent
from mlx_use.controller.service import Controller
from .session_manager import SessionManager
from .command_parser import CommandParser
from .streaming_handler import StreamingOutputHandler, ProgressCallback, StreamCapture

logger = logging.getLogger(__name__)


class InteractiveCLI:
	def __init__(self, session_dir: Optional[str] = None):
		self.session_dir = Path(session_dir or os.path.expanduser("~/.macOS-use-sessions"))
		self.session_dir.mkdir(exist_ok=True)
		
		self.controller = Controller()
		self.session_manager = SessionManager(self.session_dir)
		self.command_parser = CommandParser()
		self.streaming_handler = StreamingOutputHandler()
		
		self.llm = self._initialize_llm()
		self.current_session_id: Optional[str] = None
		
		self._setup_readline()
		
	def _initialize_llm(self):
		"""Initialize LLM based on available API keys"""
		if os.getenv('GEMINI_API_KEY'):
			return ChatGoogleGenerativeAI(
				model='gemini-2.0-flash-exp', 
				api_key=SecretStr(os.getenv('GEMINI_API_KEY'))
			)
		elif os.getenv('OPENAI_API_KEY'):
			return ChatOpenAI(
				model='gpt-4o', 
				api_key=SecretStr(os.getenv('OPENAI_API_KEY'))
			)
		elif os.getenv('ANTHROPIC_API_KEY'):
			return ChatAnthropic(
				model='claude-3-5-sonnet-20241022', 
				api_key=SecretStr(os.getenv('ANTHROPIC_API_KEY'))
			)
		else:
			raise ValueError(
				"No API keys found. Please set at least one of: "
				"GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY"
			)
	
	def _setup_readline(self):
		"""Setup readline for command history and completion"""
		history_file = self.session_dir / "command_history"
		
		try:
			readline.read_history_file(str(history_file))
		except FileNotFoundError:
			pass
		
		readline.set_history_length(1000)
		
		def save_history():
			readline.write_history_file(str(history_file))
		
		import atexit
		atexit.register(save_history)
		
		readline.set_completer(self._completer)
		readline.parse_and_bind("tab: complete")
	
	def _completer(self, text: str, state: int):
		"""Auto-completion for common commands"""
		common_commands = [
			"open ", "click ", "type ", "scroll ", "find ",
			"wait ", "close ", "switch to ", "search for ",
			"take a screenshot", "get text from ", "help",
			"sessions", "new session", "load session", "save session"
		]
		
		options = [cmd for cmd in common_commands if cmd.startswith(text)]
		
		if state < len(options):
			return options[state]
		return None
	
	def _print_banner(self):
		"""Print CLI banner"""
		print("\n" + "="*60)
		print("🤖 macOS-use Interactive CLI")
		print("Natural Language Control for macOS Applications")
		print("="*60)
		print("Type 'help' for commands, 'quit' to exit")
		if self.current_session_id:
			print(f"📁 Session: {self.current_session_id}")
		print()
	
	def _print_help(self):
		"""Print help information"""
		help_text = """
Available Commands:
  help                 - Show this help message
  sessions             - List all saved sessions
  new session [name]   - Start a new session
  load session <name>  - Load an existing session
  save session [name]  - Save current session
  clear                - Clear screen
  quit / exit          - Exit the CLI
  
Natural Language Commands:
  Just type what you want to do in natural language!
  
Examples:
  • "Open Calculator app"
  • "Type 2 + 2 and press enter"
  • "Take a screenshot of the current window"
  • "Find all PDF files in Downloads folder"
  • "Switch to Safari and go to google.com"
  
Tips:
  • Use Tab for auto-completion
  • Commands are saved in history (use up/down arrows)
  • Sessions preserve conversation context
		"""
		print(help_text)
	
	async def _execute_task(self, task: str) -> bool:
		"""Execute a natural language task with streaming output"""
		try:
			# Add task to session context
			if self.current_session_id:
				self.session_manager.add_to_session(self.current_session_id, {
					"timestamp": datetime.now().isoformat(),
					"type": "user_command",
					"content": task
				})
			
			# Start streaming output
			self.streaming_handler.start_streaming(task)
			
			# Create progress callback
			progress_callback = ProgressCallback(self.streaming_handler)
			
			# Execute task with streaming
			with StreamCapture(self.streaming_handler):
				agent = Agent(
					task=task,
					llm=self.llm,
					controller=self.controller,
					use_vision=True,
					max_actions_per_step=4,
					max_failures=3
				)
				
				result = await agent.run(max_steps=25)
			
			# Stop streaming and show final result
			self.streaming_handler.stop_streaming()
			self.streaming_handler.print_final_message("Task completed successfully!", True)
			
			# Add result to session context
			if self.current_session_id:
				self.session_manager.add_to_session(self.current_session_id, {
					"timestamp": datetime.now().isoformat(),
					"type": "agent_result",
					"content": str(result),
					"success": True
				})
			
			return True
			
		except Exception as e:
			# Stop streaming and show error
			self.streaming_handler.stop_streaming()
			self.streaming_handler.print_final_message(f"Error: {e}", False)
			logger.error(f"Error executing task: {e}")
			
			# Add error to session context
			if self.current_session_id:
				self.session_manager.add_to_session(self.current_session_id, {
					"timestamp": datetime.now().isoformat(),
					"type": "agent_error",
					"content": str(e),
					"success": False
				})
			
			return False
	
	def _handle_session_command(self, command: str, args: List[str]):
		"""Handle session-related commands"""
		if command == "sessions":
			sessions = self.session_manager.list_sessions()
			if not sessions:
				print("No saved sessions found.")
			else:
				print("\nSaved Sessions:")
				for session_id, info in sessions.items():
					created = info.get("created", "Unknown")
					count = len(info.get("history", []))
					print(f"  📁 {session_id} (created: {created}, {count} interactions)")
		
		elif command == "new session":
			session_name = args[0] if args else None
			self.current_session_id = self.session_manager.create_session(session_name)
			print(f"📁 Created new session: {self.current_session_id}")
		
		elif command == "load session":
			if not args:
				print("Please specify a session name to load.")
				return
			
			session_name = args[0]
			if self.session_manager.load_session(session_name):
				self.current_session_id = session_name
				print(f"📁 Loaded session: {session_name}")
			else:
				print(f"Session '{session_name}' not found.")
		
		elif command == "save session":
			if not self.current_session_id:
				print("No active session to save.")
				return
			
			session_name = args[0] if args else self.current_session_id
			self.session_manager.save_session(self.current_session_id, session_name)
			print(f"💾 Session saved as: {session_name}")
	
	async def run(self):
		"""Main CLI loop"""
		self._print_banner()
		
		# Create default session
		self.current_session_id = self.session_manager.create_session()
		
		while True:
			try:
				user_input = input("🤖 > ").strip()
				
				if not user_input:
					continue
				
				# Handle quit commands
				if user_input.lower() in ["quit", "exit", "q"]:
					print("👋 Goodbye!")
					break
				
				# Handle clear command
				if user_input.lower() == "clear":
					os.system('clear' if os.name == 'posix' else 'cls')
					self._print_banner()
					continue
				
				# Handle help command
				if user_input.lower() == "help":
					self._print_help()
					continue
				
				# Parse command
				parsed = self.command_parser.parse(user_input)
				
				# Handle session commands
				if parsed["type"] == "session":
					self._handle_session_command(parsed["command"], parsed["args"])
					continue
				
				# Handle natural language tasks
				if parsed["type"] == "task":
					await self._execute_task(user_input)
					continue
				
				# Default: treat as natural language task
				await self._execute_task(user_input)
				
			except KeyboardInterrupt:
				print("\n\n👋 Goodbye!")
				break
			except EOFError:
				print("\n\n👋 Goodbye!")
				break
			except Exception as e:
				logger.error(f"Unexpected error: {e}")
				print(f"❌ Unexpected error: {e}")


def main():
	"""Entry point for the CLI"""
	import argparse
	
	parser = argparse.ArgumentParser(description="macOS-use Interactive CLI")
	parser.add_argument(
		"--session-dir", 
		type=str, 
		help="Directory to store session files"
	)
	
	args = parser.parse_args()
	
	cli = InteractiveCLI(session_dir=args.session_dir)
	asyncio.run(cli.run())


if __name__ == "__main__":
	main()