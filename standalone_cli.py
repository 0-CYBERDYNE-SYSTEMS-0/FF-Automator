#!/usr/bin/env python3
"""
Standalone Enhanced CLI for macOS-use
This version works without requiring the full package installation
"""

import asyncio
import json
import logging
import os
import readline
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Simple session manager for standalone CLI
class SimpleSessionManager:
	def __init__(self, session_dir: str = None):
		self.session_dir = Path(session_dir or os.path.expanduser("~/.macOS-use-sessions"))
		self.session_dir.mkdir(exist_ok=True)
		self.current_session = {
			"id": str(uuid.uuid4()),
			"created": datetime.now().isoformat(),
			"history": []
		}
	
	def add_interaction(self, user_input: str, agent_output: str = None, success: bool = True):
		self.current_session["history"].append({
			"timestamp": datetime.now().isoformat(),
			"user_input": user_input,
			"agent_output": agent_output,
			"success": success
		})
	
	def save_session(self, name: str = None):
		session_name = name or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
		session_file = self.session_dir / f"{session_name}.json"
		
		with open(session_file, 'w') as f:
			json.dump(self.current_session, f, indent=2)
		
		return session_name
	
	def list_sessions(self):
		sessions = []
		for session_file in self.session_dir.glob("*.json"):
			try:
				with open(session_file, 'r') as f:
					session_data = json.load(f)
				sessions.append({
					"name": session_file.stem,
					"created": session_data.get("created", "Unknown"),
					"interactions": len(session_data.get("history", []))
				})
			except Exception:
				continue
		return sessions

class StandaloneCLI:
	def __init__(self):
		self.session_manager = SimpleSessionManager()
		self._setup_readline()
		
		# Common command suggestions
		self.common_commands = [
			"open Calculator",
			"open Safari", 
			"open Finder",
			"take a screenshot",
			"open System Preferences",
			"open Terminal",
			"help",
			"sessions",
			"save session",
			"quit"
		]
	
	def _setup_readline(self):
		"""Setup readline for command history and completion"""
		history_file = self.session_manager.session_dir / "command_history"
		
		try:
			readline.read_history_file(str(history_file))
		except FileNotFoundError:
			pass
		
		readline.set_history_length(1000)
		readline.set_completer(self._completer)
		readline.parse_and_bind("tab: complete")
		
		import atexit
		atexit.register(lambda: readline.write_history_file(str(history_file)))
	
	def _completer(self, text: str, state: int):
		"""Auto-completion for common commands"""
		options = [cmd for cmd in self.common_commands if cmd.lower().startswith(text.lower())]
		
		if state < len(options):
			return options[state]
		return None
	
	def _print_banner(self):
		"""Print CLI banner"""
		print("\n" + "="*60)
		print("🤖 macOS-use Enhanced CLI (Standalone)")
		print("Natural Language Control for macOS Applications")
		print("="*60)
		print("Note: This is a demo version. For full functionality,")
		print("install the complete package and use: python mlx_use_cli.py")
		print("="*60)
		print("Type 'help' for commands, 'quit' to exit")
		print()
	
	def _print_help(self):
		"""Print help information"""
		help_text = """
Available Commands:
  help                 - Show this help message
  sessions             - List all saved sessions
  save session [name]  - Save current session
  clear                - Clear screen
  quit / exit          - Exit the CLI
  
Demo Commands (simulated):
  • "open Calculator"
  • "open Safari"
  • "take a screenshot"
  • "open Finder"
  
Note: This standalone version simulates responses.
For actual macOS automation, use the full package.
		"""
		print(help_text)
	
	def _simulate_task(self, task: str) -> tuple[bool, str]:
		"""Simulate task execution for demo purposes"""
		task_lower = task.lower()
		
		if "calculator" in task_lower:
			return True, "✅ Calculator app opened successfully"
		elif "safari" in task_lower:
			return True, "✅ Safari browser launched"
		elif "finder" in task_lower:
			return True, "✅ Finder window opened"
		elif "screenshot" in task_lower:
			return True, "✅ Screenshot captured and saved to Desktop"
		elif "system preferences" in task_lower or "settings" in task_lower:
			return True, "✅ System Preferences opened"
		elif "terminal" in task_lower:
			return True, "✅ Terminal application launched"
		else:
			return True, f"✅ Simulated execution of: {task}"
	
	async def _execute_task(self, task: str) -> bool:
		"""Execute a natural language task (simulated)"""
		print(f"🎯 Executing: {task}")
		print("─" * 50)
		
		# Simulate processing time
		print("🤖 Processing your request...")
		await asyncio.sleep(1)
		
		# Simulate task execution
		success, result = self._simulate_task(task)
		
		# Add to session history
		self.session_manager.add_interaction(task, result, success)
		
		print(f"\n{result}")
		return success
	
	def _handle_sessions_command(self):
		"""Handle sessions command"""
		sessions = self.session_manager.list_sessions()
		if not sessions:
			print("No saved sessions found.")
		else:
			print("\nSaved Sessions:")
			for session in sessions:
				print(f"  📁 {session['name']} (created: {session['created']}, {session['interactions']} interactions)")
	
	def _handle_save_session(self, args: List[str]):
		"""Handle save session command"""
		session_name = args[0] if args else None
		saved_name = self.session_manager.save_session(session_name)
		print(f"💾 Session saved as: {saved_name}")
	
	async def run(self):
		"""Main CLI loop"""
		self._print_banner()
		
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
				
				# Handle sessions command
				if user_input.lower() == "sessions":
					self._handle_sessions_command()
					continue
				
				# Handle save session command
				if user_input.lower().startswith("save session"):
					args = user_input.split()[2:] if len(user_input.split()) > 2 else []
					self._handle_save_session(args)
					continue
				
				# Handle natural language tasks
				await self._execute_task(user_input)
				
			except KeyboardInterrupt:
				print("\n\n👋 Goodbye!")
				break
			except EOFError:
				print("\n\n👋 Goodbye!")
				break
			except Exception as e:
				print(f"❌ Unexpected error: {e}")

def main():
	"""Entry point for the standalone CLI"""
	cli = StandaloneCLI()
	asyncio.run(cli.run())

if __name__ == "__main__":
	main()