import uuid
from datetime import datetime
from typing import Dict, List, Tuple

import gradio as gr

from ..services.session_storage import ChatSessionStorage


def create_chat_tab(app_instance) -> List[gr.components.Component]:
	"""Create a chat-style interface tab for natural language conversations"""

	# Initialize session storage
	session_storage = ChatSessionStorage()

	# Chat state management
	initial_session_id = str(uuid.uuid4())
	session_storage.create_session(initial_session_id, 'New Chat Session')

	chat_state = gr.State(
		value={'session_id': initial_session_id, 'messages': [], 'agent_running': False, 'storage': session_storage}
	)

	with gr.Row():
		# Left column - Chat interface
		with gr.Column(scale=3):
			gr.Markdown('### 🤖 Chat with macOS Agent')
			gr.Markdown('Have a natural conversation with your macOS automation agent!')

			# Chat history display
			with gr.Group():
				chat_history = gr.Chatbot(
					label='Conversation', height=400, show_label=False, avatar_images=('🧑‍💻', '🤖'), bubble_full_width=False
				)

			# Chat input area
			with gr.Row():
				with gr.Column(scale=5):
					chat_input = gr.Textbox(
						label='',
						placeholder="Type your command or question... (e.g., 'Open Calculator and compute 25 * 4')",
						lines=2,
						container=False,
					)
				with gr.Column(scale=1, min_width=100):
					send_button = gr.Button('Send', variant='primary', size='lg')

			# Action buttons
			with gr.Row():
				clear_chat_btn = gr.Button('Clear Chat', variant='secondary', size='sm')
				save_session_btn = gr.Button('Save Session', variant='secondary', size='sm')
				load_session_btn = gr.Button('Load Session', variant='secondary', size='sm')
				stop_chat_btn = gr.Button('Stop Agent', variant='stop', size='sm', interactive=False)

		# Right column - Quick actions and session management
		with gr.Column(scale=1):
			gr.Markdown('### Quick Actions')

			# Predefined quick actions
			with gr.Group():
				gr.Markdown('**Common Tasks**')
				open_calc_btn = gr.Button('📱 Open Calculator', size='sm')
				screenshot_btn = gr.Button('📸 Take Screenshot', size='sm')
				finder_btn = gr.Button('📁 Open Finder', size='sm')
				safari_btn = gr.Button('🌐 Open Safari', size='sm')

			with gr.Group():
				gr.Markdown('**System Actions**')
				volume_up_btn = gr.Button('🔊 Volume Up', size='sm')
				volume_down_btn = gr.Button('🔉 Volume Down', size='sm')
				minimize_all_btn = gr.Button('📦 Minimize All', size='sm')
				show_desktop_btn = gr.Button('🖥️ Show Desktop', size='sm')

			# Session management
			gr.Markdown('### Session Management')
			with gr.Group():
				session_name_input = gr.Textbox(label='Session Name', placeholder='My automation session', lines=1)

				# Session list
				session_choices = [(s['name'], s['id']) for s in session_storage.get_recent_sessions()]
				session_list = gr.Dropdown(label='Saved Sessions', choices=session_choices, interactive=True)

				# Session info
				session_info = gr.JSON(label='Session Info', visible=False)

			# Settings
			gr.Markdown('### Settings')
			with gr.Group():
				auto_save = gr.Checkbox(label='Auto-save conversations', value=True)
				show_reasoning = gr.Checkbox(label='Show agent reasoning', value=False)
				max_chat_steps = gr.Slider(minimum=1, maximum=50, value=15, step=1, label='Max Steps per Task')

	# Quick action functions
	def quick_action(action_text: str, chat_state_value: Dict, history: List[Tuple[str, str]]):
		"""Handle quick action button clicks"""
		return process_chat_message(action_text, chat_state_value, history)

	def process_chat_message(
		message: str, chat_state_value: Dict, history: List[Tuple[str, str]]
	) -> Tuple[str, List[Tuple[str, str]], Dict, gr.update, gr.update]:
		"""Process a chat message and execute the agent"""
		if not message.strip():
			return '', history, chat_state_value, gr.update(), gr.update()

		# Add user message to history
		history.append((message, None))

		# Update chat state
		chat_state_value['messages'].append({'timestamp': datetime.now().isoformat(), 'type': 'user', 'content': message})
		chat_state_value['agent_running'] = True

		# Save user message to persistent storage
		if 'storage' in chat_state_value:
			chat_state_value['storage'].save_session(chat_state_value['session_id'], chat_state_value['messages'])

		# Show that agent is processing
		processing_history = history[:]
		processing_history[-1] = (message, '🤖 Processing your request...')

		return '', processing_history, chat_state_value, gr.update(interactive=False), gr.update(interactive=True)

	async def execute_agent_task(
		message: str, chat_state_value: Dict, history: List[Tuple[str, str]], max_steps: int
	) -> Tuple[List[Tuple[str, str]], Dict, gr.update, gr.update]:
		"""Execute the agent task asynchronously"""
		try:
			# Get current LLM configuration from app instance
			provider = app_instance.preferences.get('llm_provider', 'OpenAI')

			# Get model with proper dynamic detection for local providers
			saved_model = app_instance.preferences.get('llm_model')
			if provider in ['Ollama', 'LM Studio']:
				try:
					from ..models.llm_models import get_available_models

					available_models = get_available_models(provider)
					if available_models and available_models[0]:
						# Use first available model if saved model isn't available
						if saved_model not in available_models:
							model = available_models[0]
						else:
							model = saved_model
					else:
						model = saved_model or 'llama3.2'  # fallback
				except:
					model = saved_model or 'llama3.2'  # fallback
			else:
				model = saved_model or 'gpt-4o'

			api_key = app_instance.get_saved_api_key(provider)

			# Check if provider requires API key
			try:
				from ..models.llm_models import PROVIDER_CONFIGS, check_provider_availability

				config = PROVIDER_CONFIGS.get(provider, {})
				requires_auth = config.get('requires_auth', True)
				is_local = config.get('local_provider', False)

				# For providers that require auth, check API key
				if requires_auth and not api_key:
					error_msg = f'No API key found for {provider}. Please configure it in the Configuration tab.'
					history[-1] = (message, f'❌ {error_msg}')
					chat_state_value['agent_running'] = False
					return history, chat_state_value, gr.update(interactive=True), gr.update(interactive=False)

				# For local providers, check if they're running
				if is_local and not check_provider_availability(provider):
					service_name = 'Ollama' if provider == 'Ollama' else 'LM Studio'
					error_msg = f'{service_name} is not running. Please start {service_name} first.'
					history[-1] = (message, f'❌ {error_msg}')
					chat_state_value['agent_running'] = False
					return history, chat_state_value, gr.update(interactive=True), gr.update(interactive=False)

			except ImportError:
				# Fallback check for basic providers
				if not api_key and provider in ['OpenAI', 'Anthropic', 'Google']:
					error_msg = f'No API key found for {provider}. Please configure it in the Configuration tab.'
					history[-1] = (message, f'❌ {error_msg}')
					chat_state_value['agent_running'] = False
					return history, chat_state_value, gr.update(interactive=True), gr.update(interactive=False)

			# Execute the agent
			result_messages = []
			async for output in app_instance.run_agent(message, max_steps, 4, provider, model, api_key, False, False):
				if isinstance(output, tuple) and len(output) >= 4:
					terminal_output, run_btn_state, stop_btn_state, result_output = output
					# Extract the actual value from gr.update object if present
					if isinstance(result_output, dict) and 'value' in result_output:
						result_text = result_output['value']
					else:
						result_text = result_output

					# Only add non-empty results
					if result_text and isinstance(result_text, str) and result_text.strip():
						result_messages.append(result_text.strip())

			# Combine all result messages
			final_result = '\n'.join(result_messages) if result_messages else 'Task completed successfully!'

			# Update history with final result
			history[-1] = (message, f'✅ {final_result}')

			# Add to chat state
			chat_state_value['messages'].append(
				{'timestamp': datetime.now().isoformat(), 'type': 'agent', 'content': final_result, 'success': True}
			)

			# Save to persistent storage
			if 'storage' in chat_state_value:
				chat_state_value['storage'].save_session(chat_state_value['session_id'], chat_state_value['messages'])

		except Exception as e:
			import traceback

			error_msg = f'Error executing task: {str(e)}'
			traceback_msg = traceback.format_exc()
			print(f'Chat interface error: {error_msg}')
			print(f'Traceback: {traceback_msg}')
			history[-1] = (message, f'❌ {error_msg}')

			# Add error to chat state
			chat_state_value['messages'].append(
				{'timestamp': datetime.now().isoformat(), 'type': 'agent', 'content': error_msg, 'success': False}
			)

			# Save to persistent storage
			if 'storage' in chat_state_value:
				chat_state_value['storage'].save_session(chat_state_value['session_id'], chat_state_value['messages'])

		finally:
			chat_state_value['agent_running'] = False

		return history, chat_state_value, gr.update(interactive=True), gr.update(interactive=False)

	def clear_chat(chat_state_value: Dict) -> Tuple[List, Dict, str]:
		"""Clear the chat history"""
		# Create new session
		new_session_id = str(uuid.uuid4())
		if 'storage' in chat_state_value:
			chat_state_value['storage'].create_session(new_session_id, 'New Chat Session')

		chat_state_value['messages'] = []
		chat_state_value['session_id'] = new_session_id
		return [], chat_state_value, ''

	def save_session(session_name: str, chat_state_value: Dict) -> Tuple[gr.update, str, gr.update]:
		"""Save the current chat session"""
		if not session_name.strip():
			session_name = f'Session_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

		try:
			if 'storage' in chat_state_value:
				# Create new session with the given name
				new_session_id = str(uuid.uuid4())
				chat_state_value['storage'].create_session(new_session_id, session_name)
				chat_state_value['storage'].save_session(new_session_id, chat_state_value['messages'])

				# Update session list
				session_choices = [(s['name'], s['id']) for s in chat_state_value['storage'].get_recent_sessions()]

				return (gr.update(info=f"Session '{session_name}' saved successfully!"), '', gr.update(choices=session_choices))
			else:
				return gr.update(info='Storage not available'), session_name, gr.update()

		except Exception as e:
			return gr.update(info=f'Error saving session: {e}'), session_name, gr.update()

	def load_session(selected_session_id: str, chat_state_value: Dict) -> Tuple[List[Tuple[str, str]], Dict, str]:
		"""Load a selected session"""
		if not selected_session_id or 'storage' not in chat_state_value:
			return [], chat_state_value, ''

		try:
			session_data = chat_state_value['storage'].load_session(selected_session_id)
			if not session_data:
				return [], chat_state_value, ''

			# Update chat state
			chat_state_value['session_id'] = selected_session_id
			chat_state_value['messages'] = session_data.get('messages', [])

			# Convert messages to chat history format
			history = []
			for msg in chat_state_value['messages']:
				if msg.get('type') == 'user':
					# Add user message with pending agent response
					history.append((msg.get('content', ''), None))
				elif msg.get('type') == 'agent' and history:
					# Complete the last user message with agent response
					user_msg, _ = history[-1]
					success_icon = '✅' if msg.get('success', True) else '❌'
					agent_response = f'{success_icon} {msg.get("content", "")}'
					history[-1] = (user_msg, agent_response)

			return history, chat_state_value, ''

		except Exception as e:
			return [], chat_state_value, f'Error loading session: {e}'

	def stop_agent(chat_state_value: Dict) -> Tuple[Dict, gr.update, gr.update]:
		"""Stop the running agent"""
		try:
			app_instance.stop_agent()
			chat_state_value['agent_running'] = False
			return chat_state_value, gr.update(interactive=True), gr.update(interactive=False)
		except Exception:
			return chat_state_value, gr.update(), gr.update()

	# Set up event handlers

	# Main chat input
	send_button.click(
		fn=process_chat_message,
		inputs=[chat_input, chat_state, chat_history],
		outputs=[chat_input, chat_history, chat_state, send_button, stop_chat_btn],
		queue=True,
	).then(
		fn=execute_agent_task,
		inputs=[chat_input, chat_state, chat_history, max_chat_steps],
		outputs=[chat_history, chat_state, send_button, stop_chat_btn],
		queue=True,
	)

	# Enter key support
	chat_input.submit(
		fn=process_chat_message,
		inputs=[chat_input, chat_state, chat_history],
		outputs=[chat_input, chat_history, chat_state, send_button, stop_chat_btn],
		queue=True,
	).then(
		fn=execute_agent_task,
		inputs=[chat_input, chat_state, chat_history, max_chat_steps],
		outputs=[chat_history, chat_state, send_button, stop_chat_btn],
		queue=True,
	)

	# Quick action buttons
	open_calc_btn.click(
		fn=lambda cs, h: quick_action('Open Calculator app', cs, h),
		inputs=[chat_state, chat_history],
		outputs=[chat_input, chat_history, chat_state, send_button, stop_chat_btn],
		queue=True,
	).then(
		fn=execute_agent_task,
		inputs=[gr.State('Open Calculator app'), chat_state, chat_history, max_chat_steps],
		outputs=[chat_history, chat_state, send_button, stop_chat_btn],
		queue=True,
	)

	screenshot_btn.click(
		fn=lambda cs, h: quick_action('Take a screenshot of the current screen', cs, h),
		inputs=[chat_state, chat_history],
		outputs=[chat_input, chat_history, chat_state, send_button, stop_chat_btn],
		queue=True,
	).then(
		fn=execute_agent_task,
		inputs=[gr.State('Take a screenshot of the current screen'), chat_state, chat_history, max_chat_steps],
		outputs=[chat_history, chat_state, send_button, stop_chat_btn],
		queue=True,
	)

	finder_btn.click(
		fn=lambda cs, h: quick_action('Open Finder', cs, h),
		inputs=[chat_state, chat_history],
		outputs=[chat_input, chat_history, chat_state, send_button, stop_chat_btn],
		queue=True,
	).then(
		fn=execute_agent_task,
		inputs=[gr.State('Open Finder'), chat_state, chat_history, max_chat_steps],
		outputs=[chat_history, chat_state, send_button, stop_chat_btn],
		queue=True,
	)

	safari_btn.click(
		fn=lambda cs, h: quick_action('Open Safari browser', cs, h),
		inputs=[chat_state, chat_history],
		outputs=[chat_input, chat_history, chat_state, send_button, stop_chat_btn],
		queue=True,
	).then(
		fn=execute_agent_task,
		inputs=[gr.State('Open Safari browser'), chat_state, chat_history, max_chat_steps],
		outputs=[chat_history, chat_state, send_button, stop_chat_btn],
		queue=True,
	)

	# System action buttons
	volume_up_btn.click(
		fn=lambda cs, h: quick_action('Increase system volume', cs, h),
		inputs=[chat_state, chat_history],
		outputs=[chat_input, chat_history, chat_state, send_button, stop_chat_btn],
		queue=True,
	).then(
		fn=execute_agent_task,
		inputs=[gr.State('Increase system volume'), chat_state, chat_history, max_chat_steps],
		outputs=[chat_history, chat_state, send_button, stop_chat_btn],
		queue=True,
	)

	volume_down_btn.click(
		fn=lambda cs, h: quick_action('Decrease system volume', cs, h),
		inputs=[chat_state, chat_history],
		outputs=[chat_input, chat_history, chat_state, send_button, stop_chat_btn],
		queue=True,
	).then(
		fn=execute_agent_task,
		inputs=[gr.State('Decrease system volume'), chat_state, chat_history, max_chat_steps],
		outputs=[chat_history, chat_state, send_button, stop_chat_btn],
		queue=True,
	)

	# Session management
	clear_chat_btn.click(fn=clear_chat, inputs=[chat_state], outputs=[chat_history, chat_state, chat_input])

	save_session_btn.click(
		fn=save_session, inputs=[session_name_input, chat_state], outputs=[session_name_input, session_name_input, session_list]
	)

	# Load session handler
	load_session_btn.click(fn=load_session, inputs=[session_list, chat_state], outputs=[chat_history, chat_state, chat_input])

	stop_chat_btn.click(fn=stop_agent, inputs=[chat_state], outputs=[chat_state, send_button, stop_chat_btn])

	return [
		chat_history,
		chat_input,
		send_button,
		clear_chat_btn,
		save_session_btn,
		load_session_btn,
		stop_chat_btn,
		session_name_input,
		session_list,
		chat_state,
	]
