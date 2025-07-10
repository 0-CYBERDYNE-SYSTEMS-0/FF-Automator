import asyncio
import logging
import os
import readline
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from mlx_use.agent.context_manager import ContextBucketManager, create_agent_with_context
from mlx_use.controller.service import Controller

from .command_parser import CommandParser
from .session_manager import SessionManager
from .streaming_handler import StreamCapture, StreamingOutputHandler

logger = logging.getLogger(__name__)


class InteractiveCLI:
	def __init__(self, session_dir: Optional[str] = None):
		self.session_dir = Path(session_dir or os.path.expanduser('~/.FF-Terminal-sessions'))
		self.session_dir.mkdir(exist_ok=True)

		self.controller = Controller()
		self.session_manager = SessionManager(self.session_dir)
		self.command_parser = CommandParser()
		self.streaming_handler = StreamingOutputHandler()

		# Initialize context bucket manager
		context_storage_dir = self.session_dir / 'context_buckets'
		self.context_manager = ContextBucketManager(context_storage_dir)

		self.llm = self._initialize_llm()
		self.current_session_id: Optional[str] = None

		self._setup_readline()

	def _initialize_llm(self):
		"""Initialize LLM based on available API keys with support for all 2025 providers"""

		sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

		try:
			from gradio_app.src.models.llm_models import (
				PROVIDER_CONFIGS,
				check_provider_availability,
				get_llm,
			)
		except ImportError:
			# Fallback to basic configuration if gradio app not available
			return self._initialize_llm_fallback()

		# Check environment preferences first
		preferred_provider = os.getenv('DEFAULT_LLM_PROVIDER')
		preferred_model = os.getenv('DEFAULT_LLM_MODEL')

		if preferred_provider and preferred_model:
			if check_provider_availability(preferred_provider):
				api_key = self._get_api_key_for_provider(preferred_provider)
				if api_key or not PROVIDER_CONFIGS[preferred_provider].get('requires_auth'):
					try:
						return get_llm(preferred_provider, preferred_model, api_key)
					except Exception:
						pass

		# Try providers in priority order with their best models
		provider_priority = [
			('OpenAI', 'gpt-4.1-mini', os.getenv('OPENAI_API_KEY')),
			('Anthropic', 'claude-4-sonnet', os.getenv('ANTHROPIC_API_KEY')),
			('Google', 'gemini-2.5-flash', os.getenv('GEMINI_API_KEY')),
			('DeepSeek', 'deepseek-chat', os.getenv('DEEPSEEK_API_KEY')),
			('OpenRouter', 'anthropic/claude-3.5-sonnet', os.getenv('OPENROUTER_API_KEY')),
			('Ollama', 'llama3.2', None),
			('LM Studio', 'Available models will be detected', None),
		]

		available_providers = []
		for provider, model, api_key in provider_priority:
			if check_provider_availability(provider):
				if api_key or not PROVIDER_CONFIGS[provider].get('requires_auth'):
					try:
						llm = get_llm(provider, model, api_key)
						print(f'✅ Using {provider} with model {model}')
						return llm
					except Exception as e:
						print(f'⚠️ Failed to initialize {provider}: {e}')
						continue
				else:
					available_providers.append(provider)

		# If no working provider found, show helpful message
		if available_providers:
			providers_str = ', '.join(available_providers)
			raise ValueError(
				f'Providers available but missing API keys: {providers_str}\n'
				f'Please set the appropriate environment variables in your .env file:\n'
				f'- OpenAI: OPENAI_API_KEY\n'
				f'- Anthropic: ANTHROPIC_API_KEY\n'
				f'- Google: GEMINI_API_KEY\n'
				f'- DeepSeek: DEEPSEEK_API_KEY\n'
				f'- OpenRouter: OPENROUTER_API_KEY\n'
				f"Local providers (Ollama, LM Studio) don't require API keys."
			)
		else:
			raise ValueError(
				'No LLM providers available. Please:\n'
				'1. Set API keys in .env file for cloud providers, OR\n'
				'2. Start Ollama (port 11434) or LM Studio (port 1234) for local models'
			)

	def _get_api_key_for_provider(self, provider: str) -> Optional[str]:
		"""Get API key for a specific provider"""
		api_key_mapping = {
			'OpenAI': 'OPENAI_API_KEY',
			'Anthropic': 'ANTHROPIC_API_KEY',
			'Google': 'GEMINI_API_KEY',
			'DeepSeek': 'DEEPSEEK_API_KEY',
			'OpenRouter': 'OPENROUTER_API_KEY',
		}
		env_var = api_key_mapping.get(provider)
		return os.getenv(env_var) if env_var else None

	def _initialize_llm_fallback(self):
		"""Fallback LLM initialization if gradio app imports fail"""
		if os.getenv('GEMINI_API_KEY'):
			return ChatGoogleGenerativeAI(model='gemini-2.0-flash-exp', api_key=SecretStr(os.getenv('GEMINI_API_KEY')))
		elif os.getenv('OPENAI_API_KEY'):
			return ChatOpenAI(model='gpt-4o', api_key=SecretStr(os.getenv('OPENAI_API_KEY')))
		elif os.getenv('ANTHROPIC_API_KEY'):
			return ChatAnthropic(model='claude-3-5-sonnet-20241022', api_key=SecretStr(os.getenv('ANTHROPIC_API_KEY')))
		else:
			raise ValueError(
				'No API keys found. Please set at least one of: GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY'
			)

	def _setup_readline(self):
		"""Setup readline for command history and completion"""
		history_file = self.session_dir / 'command_history'

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
		readline.parse_and_bind('tab: complete')

	def _completer(self, text: str, state: int):
		"""Auto-completion for common commands"""
		common_commands = [
			'open ',
			'click ',
			'type ',
			'scroll ',
			'find ',
			'wait ',
			'close ',
			'switch to ',
			'search for ',
			'take a screenshot',
			'get text from ',
			'help',
			'sessions',
			'new session',
			'load session',
			'save session',
			'providers',
			'switch provider',
			'list models',
			'provider status',
			'context add',
			'context list',
			'context clear',
			'context remove',
			'context export',
			'context import',
		]

		options = [cmd for cmd in common_commands if cmd.startswith(text)]

		if state < len(options):
			return options[state]
		return None

	def _print_banner(self):
		"""Print CLI banner"""
		print('\n' + '=' * 60)
		print('🤖 FF-Terminal:Desktop_ver Interactive CLI')
		print('Natural Language Control for macOS Applications')
		print('=' * 60)
		print("Type 'help' for commands, 'quit' to exit")
		if self.current_session_id:
			print(f'📁 Session: {self.current_session_id}')
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
  
Provider Management:
  providers            - List all available LLM providers
  provider status      - Show current provider and model info
  switch provider      - Interactive provider/model selection
  list models          - Show available models for current provider
  
Context Management:
  context help         - Show context commands help
  context add          - Add context item (interactive)
  context list         - List all context items
  context clear        - Clear all context items
  context remove <id>  - Remove context item by ID
  context export [file]- Export context to JSON file
  context import <file>- Import context from JSON file
  
Natural Language Commands:
  Just type what you want to do in natural language!
  
Examples:
  • "Open Calculator app"
  • "Type 2 + 2 and press enter"
  • "Take a screenshot of the current window"
  • "Find all PDF files in Downloads folder"
  • "Switch to Safari and go to google.com"
  
Supported Providers (2025):
  🌐 Cloud: OpenAI (GPT-4.1, o3, o4-mini), Anthropic (Claude 4), Google (Gemini 2.5)
  🌐 Alternative: DeepSeek (V3, R1), OpenRouter (400+ models, free options)
  💻 Local: Ollama, LM Studio (no API keys needed)
  
Tips:
  • Use Tab for auto-completion
  • Commands are saved in history (use up/down arrows)
  • Sessions preserve conversation context
  • Set DEFAULT_LLM_PROVIDER in .env for preferred provider
		"""
		print(help_text)

	async def _execute_task(self, task: str) -> bool:
		"""Execute a natural language task with streaming output"""
		try:
			# Add task to session context
			if self.current_session_id:
				self.session_manager.add_to_session(
					self.current_session_id, {'timestamp': datetime.now().isoformat(), 'type': 'user_command', 'content': task}
				)

			# Start streaming output
			self.streaming_handler.start_streaming(task)

			# Execute task with streaming
			with StreamCapture(self.streaming_handler):
				# Create agent with context bucket support
				session_id = self.current_session_id or 'default'
				agent = await create_agent_with_context(
					task=task,
					llm=self.llm,
					session_id=session_id,
					storage_dir=self.context_manager.storage_dir,
					controller=self.controller,
					use_vision=True,
					max_actions_per_step=4,
					max_failures=3,
				)

				result = await agent.run(max_steps=25)

			# Stop streaming and show final result
			self.streaming_handler.stop_streaming()
			self.streaming_handler.print_final_message('Task completed successfully!', True)

			# Add result to session context
			if self.current_session_id:
				self.session_manager.add_to_session(
					self.current_session_id,
					{'timestamp': datetime.now().isoformat(), 'type': 'agent_result', 'content': str(result), 'success': True},
				)

			return True

		except Exception as e:
			# Stop streaming and show error
			self.streaming_handler.stop_streaming()
			self.streaming_handler.print_final_message(f'Error: {e}', False)
			logger.error(f'Error executing task: {e}')

			# Add error to session context
			if self.current_session_id:
				self.session_manager.add_to_session(
					self.current_session_id,
					{'timestamp': datetime.now().isoformat(), 'type': 'agent_error', 'content': str(e), 'success': False},
				)

			return False

	def _handle_session_command(self, command: str, args: List[str]):
		"""Handle session-related commands"""
		if command == 'sessions':
			sessions = self.session_manager.list_sessions()
			if not sessions:
				print('No saved sessions found.')
			else:
				print('\nSaved Sessions:')
				for session_id, info in sessions.items():
					created = info.get('created', 'Unknown')
					count = len(info.get('history', []))
					print(f'  📁 {session_id} (created: {created}, {count} interactions)')

		elif command == 'new session':
			session_name = args[0] if args else None
			self.current_session_id = self.session_manager.create_session(session_name)
			print(f'📁 Created new session: {self.current_session_id}')

		elif command == 'load session':
			if not args:
				print('Please specify a session name to load.')
				return

			session_name = args[0]
			if self.session_manager.load_session(session_name):
				self.current_session_id = session_name
				print(f'📁 Loaded session: {session_name}')
			else:
				print(f"Session '{session_name}' not found.")

		elif command == 'save session':
			if not self.current_session_id:
				print('No active session to save.')
				return

			session_name = args[0] if args else self.current_session_id
			self.session_manager.save_session(self.current_session_id, session_name)
			print(f'💾 Session saved as: {session_name}')

	async def _handle_provider_command(self, command: str):
		"""Handle provider management commands"""
		try:
			import sys

			sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

			from gradio_app.src.models.llm_models import (
				LLM_MODELS,
				PROVIDER_CONFIGS,
				check_provider_availability,
				get_available_models,
			)
		except ImportError:
			print('❌ Provider management requires full package installation')
			return

		if command == 'providers':
			print('\n🌐 Available LLM Providers:')
			print('=' * 50)

			for provider, config in PROVIDER_CONFIGS.items():
				status = '✅' if check_provider_availability(provider) else '❌'
				auth_info = 'API Key Required' if config.get('requires_auth') else 'No Auth'
				local_info = ' (Local)' if config.get('local_provider') else ''

				print(f'{status} {provider}{local_info} - {auth_info}')
				if provider in LLM_MODELS:
					model_count = len(LLM_MODELS[provider])
					print(f'    📊 {model_count} models available')

			print()

		elif command == 'provider status':
			print('\n🔍 Current Provider Status:')
			print('=' * 40)

			# Try to determine current provider from LLM instance
			current_provider = 'Unknown'
			current_model = 'Unknown'

			if hasattr(self.llm, 'model_name'):
				current_model = self.llm.model_name
			elif hasattr(self.llm, 'model'):
				current_model = self.llm.model

			# Determine provider based on LLM class
			llm_class = self.llm.__class__.__name__
			if 'OpenAI' in llm_class:
				current_provider = 'OpenAI (or compatible)'
			elif 'Anthropic' in llm_class:
				current_provider = 'Anthropic'
			elif 'GoogleGenerativeAI' in llm_class:
				current_provider = 'Google'

			print(f'🤖 Provider: {current_provider}')
			print(f'📋 Model: {current_model}')
			print(f'🔗 Base URL: {getattr(self.llm, "base_url", "Default")}')
			print()

		elif command == 'list models':
			print('\n📋 Available Models by Provider:')
			print('=' * 45)

			for provider in LLM_MODELS:
				if check_provider_availability(provider):
					models = get_available_models(provider)
					print(f'\n🔧 {provider}:')
					for model in models[:10]:  # Limit to first 10 models
						print(f'  • {model}')
					if len(models) > 10:
						print(f'  ... and {len(models) - 10} more')
			print()

		elif command == 'switch provider':
			print('\n🔄 Provider Selection:')
			print('=' * 35)

			available_providers = []
			for provider in PROVIDER_CONFIGS:
				if check_provider_availability(provider):
					available_providers.append(provider)

			if not available_providers:
				print('❌ No providers available. Please check your API keys or start local providers.')
				return

			print('Available providers:')
			for i, provider in enumerate(available_providers, 1):
				print(f'  {i}. {provider}')

			try:
				choice = input('\nSelect provider (number): ').strip()
				provider_idx = int(choice) - 1

				if 0 <= provider_idx < len(available_providers):
					selected_provider = available_providers[provider_idx]
					models = get_available_models(selected_provider)

					print(f'\nAvailable models for {selected_provider}:')
					for i, model in enumerate(models[:10], 1):
						print(f'  {i}. {model}')

					model_choice = input('\nSelect model (number): ').strip()
					model_idx = int(model_choice) - 1

					if 0 <= model_idx < len(models):
						selected_model = models[model_idx]
						print(f'\n✅ To use {selected_provider} with {selected_model}, add to your .env:')
						print(f'DEFAULT_LLM_PROVIDER={selected_provider}')
						print(f'DEFAULT_LLM_MODEL={selected_model}')
						print('\nRestart the CLI to apply changes.')
					else:
						print('❌ Invalid model selection')
				else:
					print('❌ Invalid provider selection')
			except (ValueError, KeyboardInterrupt):
				print('\n❌ Selection cancelled')

	async def run(self):
		"""Main CLI loop"""
		self._print_banner()

		# Create default session
		self.current_session_id = self.session_manager.create_session()

		while True:
			try:
				user_input = input('🤖 > ').strip()

				if not user_input:
					continue

				# Handle quit commands
				if user_input.lower() in ['quit', 'exit', 'q']:
					print('👋 Goodbye!')
					break

				# Handle clear command
				if user_input.lower() == 'clear':
					os.system('clear' if os.name == 'posix' else 'cls')
					self._print_banner()
					continue

				# Handle help command
				if user_input.lower() == 'help':
					self._print_help()
					continue

				# Parse command
				parsed = self.command_parser.parse(user_input)

				# Handle session commands
				if parsed['type'] == 'session':
					self._handle_session_command(parsed['command'], parsed['args'])
					continue

				# Handle provider commands
				if user_input.lower() in ['providers', 'provider status', 'switch provider', 'list models']:
					await self._handle_provider_command(user_input.lower())
					continue

				# Handle context bucket commands
				if user_input.lower().startswith('context ') or user_input.lower() == 'context':
					if user_input.lower() == 'context':
						user_input = 'context help'
					await self._handle_context_command(user_input)
					continue

				# Handle natural language tasks
				if parsed['type'] == 'task':
					await self._execute_task(user_input)
					continue

				# Default: treat as natural language task
				await self._execute_task(user_input)

			except KeyboardInterrupt:
				print('\n\n👋 Goodbye!')
				break
			except EOFError:
				print('\n\n👋 Goodbye!')
				break
			except Exception as e:
				logger.error(f'Unexpected error: {e}')
				print(f'❌ Unexpected error: {e}')

	async def _handle_context_command(self, command: str):
		"""Handle context bucket commands"""
		parts = command.strip().split()
		if len(parts) < 2:
			print("❌ Invalid context command. Use 'context help' for available commands.")
			return

		subcommand = parts[1].lower()
		session_id = self.current_session_id or 'default'

		try:
			context_bucket = await self.context_manager.get_context_bucket(session_id=session_id)

			if subcommand == 'help':
				self._print_context_help()

			elif subcommand == 'add':
				await self._context_add_interactive(context_bucket)

			elif subcommand == 'list':
				await self._context_list(context_bucket)

			elif subcommand == 'clear':
				await self._context_clear(context_bucket)

			elif subcommand == 'remove':
				if len(parts) < 3:
					print('❌ Usage: context remove <item_id>')
					return
				try:
					item_id = int(parts[2])
					await self._context_remove(context_bucket, item_id)
				except ValueError:
					print('❌ Item ID must be a number')

			elif subcommand == 'export':
				filename = parts[2] if len(parts) > 2 else f'context_{session_id}.json'
				await self._context_export(context_bucket, filename)

			elif subcommand == 'import':
				if len(parts) < 3:
					print('❌ Usage: context import <filename>')
					return
				await self._context_import(context_bucket, parts[2])

			else:
				print(f"❌ Unknown context command: {subcommand}. Use 'context help' for available commands.")

		except Exception as e:
			logger.error(f'Context command error: {e}')
			print(f'❌ Context command failed: {e}')

	def _print_context_help(self):
		"""Print context bucket help"""
		help_text = """
📦 Context Bucket Commands:

  context help           - Show this help message
  context add            - Add new context item (interactive)
  context list           - List all context items
  context clear          - Clear all context items
  context remove <id>    - Remove specific context item by ID
  context export [file]  - Export context to JSON file
  context import <file>  - Import context from JSON file

Context Types:
  • document    - Documents, files, references
  • instruction - Guidelines, rules, procedures
  • reference   - Quick facts, data, examples
  • background  - Context information
  • constraint  - Limitations, requirements
  • goal        - Objectives, targets

Priorities:
  • high   - Always included in prompts
  • medium - Included when space allows
  • low    - Used for overflow/backup context

Example:
  context add
  > Type: instruction
  > Title: Calculator Rules
  > Content: Always verify results using context elements
  > Priority: high
  > Tags: math,verification
		"""
		print(help_text)

	async def _context_add_interactive(self, context_bucket):
		"""Interactive context item addition"""
		try:
			print('\n📦 Add Context Item')
			print('=' * 25)

			# Get item type
			print('Available types: document, instruction, reference, background, constraint, goal')
			item_type = input('Type: ').strip().lower()
			if not item_type:
				item_type = 'reference'

			# Get title
			title = input('Title: ').strip()
			if not title:
				print('❌ Title is required')
				return

			# Get content
			print('Content (press Enter twice to finish):')
			content_lines = []
			empty_count = 0
			while empty_count < 2:
				line = input()
				if line.strip() == '':
					empty_count += 1
				else:
					empty_count = 0
				content_lines.append(line)

			content = '\n'.join(content_lines[:-2]).strip()  # Remove last two empty lines
			if not content:
				print('❌ Content is required')
				return

			# Get priority
			priority = input('Priority (high/medium/low) [medium]: ').strip().lower()
			if not priority:
				priority = 'medium'

			# Get tags
			tags_input = input('Tags (comma-separated): ').strip()
			tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()] if tags_input else []

			# Add item
			from mlx_use.agent.context_models import ContextItemPriority, ContextItemType

			item = await context_bucket.add_item(
				type=ContextItemType(item_type), title=title, content=content, priority=ContextItemPriority(priority), tags=tags
			)

			if item:
				await self.context_manager.save_context_bucket()
				print(f'✅ Added context item: {title}')
			else:
				print('❌ Failed to add context item')

		except KeyboardInterrupt:
			print('\n❌ Context addition cancelled')
		except Exception as e:
			print(f'❌ Error adding context: {e}')

	async def _context_list(self, context_bucket):
		"""List all context items"""
		items = context_bucket.get_sorted_items()

		if not items:
			print('📦 No context items found')
			return

		print(f'\n📦 Context Items ({len(items)} total)')
		print('=' * 50)

		for i, item in enumerate(items):
			tags_str = f' #{", #".join(item.tags)}' if item.tags else ''
			token_info = f' ({item.token_count} tokens)' if item.token_count else ''
			print(f'\n{i + 1}. {item.title} [{item.type.value}] [{item.priority.value}]{token_info}')
			print(f'   {item.content[:100]}{"..." if len(item.content) > 100 else ""}')
			if tags_str:
				print(f'   Tags:{tags_str}')

		print(f'\n💾 Total tokens: {context_bucket.get_total_tokens()}')
		print(f'📊 Token limit: {context_bucket.config.max_tokens}')

	async def _context_clear(self, context_bucket):
		"""Clear all context items"""
		items = context_bucket.get_sorted_items()
		if not items:
			print('📦 No context items to clear')
			return

		confirm = input(f'⚠️  Clear all {len(items)} context items? (yes/no): ').strip().lower()
		if confirm in ['yes', 'y']:
			context_bucket.clear_all_items()
			await self.context_manager.save_context_bucket()
			print('✅ All context items cleared')
		else:
			print('❌ Clear cancelled')

	async def _context_remove(self, context_bucket, item_index):
		"""Remove specific context item"""
		items = context_bucket.get_sorted_items()
		if not items:
			print('📦 No context items to remove')
			return

		if item_index < 1 or item_index > len(items):
			print(f'❌ Invalid item ID. Use 1-{len(items)}')
			return

		item = items[item_index - 1]
		confirm = input(f"⚠️  Remove '{item.title}'? (yes/no): ").strip().lower()
		if confirm in ['yes', 'y']:
			context_bucket.remove_item(item.id)
			await self.context_manager.save_context_bucket()
			print(f'✅ Removed context item: {item.title}')
		else:
			print('❌ Remove cancelled')

	async def _context_export(self, context_bucket, filename):
		"""Export context to JSON file"""
		try:
			export_path = self.session_dir / filename
			await context_bucket.export_context(str(export_path))
			print(f'✅ Context exported to: {export_path}')
		except Exception as e:
			print(f'❌ Export failed: {e}')

	async def _context_import(self, context_bucket, filename):
		"""Import context from JSON file"""
		try:
			import_path = self.session_dir / filename
			if not import_path.exists():
				# Try as absolute path
				import_path = Path(filename)
				if not import_path.exists():
					print(f'❌ File not found: {filename}')
					return

			await context_bucket.import_context(str(import_path))
			await self.context_manager.save_context_bucket()
			print(f'✅ Context imported from: {import_path}')
		except Exception as e:
			print(f'❌ Import failed: {e}')


def main():
	"""Entry point for the CLI"""
	import argparse

	parser = argparse.ArgumentParser(description='FF-Terminal:Desktop_ver Interactive CLI')
	parser.add_argument('--session-dir', type=str, help='Directory to store session files')

	args = parser.parse_args()

	cli = InteractiveCLI(session_dir=args.session_dir)
	asyncio.run(cli.run())


if __name__ == '__main__':
	main()
