import os
import socket

import gradio as gr

from gradio_app.src.models.app import MacOSUseGradioApp
from gradio_app.src.ui.chat_interface import create_chat_tab
from gradio_app.src.ui.context_interface import create_context_tab
from gradio_app.src.ui.interface import create_agent_tab, create_automations_tab, create_configuration_tab


def create_interface(app_instance: MacOSUseGradioApp):
	"""Create the Gradio interface with all components."""
	with gr.Blocks(title='FF-Terminal:Desktop_ver Interface') as demo:
		gr.Markdown('# FF-Terminal:Desktop_ver - AI Desktop Control (Beta)')

		with gr.Tab('Chat'):
			chat_components = create_chat_tab(app_instance)
			(
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
			) = chat_components

		with gr.Tab('Agent'):
			agent_components = create_agent_tab(app_instance)
			(
				task_input,
				refine_prompt_btn,
				share_prompt,
				max_steps,
				max_actions,
				run_button,
				stop_button,
				result_output,
				terminal_output,
			) = agent_components

		with gr.Tab('Automations'):
			automation_components = create_automations_tab(app_instance)
			(
				automation_name,
				automation_description,
				add_automation_btn,
				automation_list,
				agent_prompt,
				add_agent_btn,
				remove_agent_btn,
				run_automation_btn,
				agents_list,
				automation_output,
			) = automation_components

		with gr.Tab('Context Bucket'):
			context_components = create_context_tab(app_instance)
			(
				context_item_type,
				context_title,
				context_content,
				context_priority,
				context_tags,
				context_session_id,
				context_add_button,
				context_clear_form_button,
				context_add_status,
				context_items_df,
				context_refresh_button,
				context_list_session_id,
				context_remove_button,
				context_clear_all_button,
				context_management_status,
			) = context_components

		with gr.Tab('Configuration'):
			config_components = create_configuration_tab(app_instance)
			(
				llm_provider,
				llm_model,
				api_key,
				share_terminal_cfg,
				provider_info,
				model_recommendations,
				api_help,
				provider_status,
				test_connection_btn,
				reasoning_provider,
				coding_provider,
				chat_provider,
				enable_cost_optimization,
				prefer_free_models,
				max_cost_per_request,
				refresh_models_btn,
			) = config_components

		# Event handlers
		def format_agents_list(agents):
			return [[i, agent['prompt']] for i, agent in enumerate(agents)]

		def add_automation_and_clear(name: str, description: str):
			result = app_instance.add_automation(name, description)
			return {automation_list: result, automation_name: '', automation_description: ''}

		def add_agent_and_update_list(automation_name, prompt):
			agents = app_instance.add_agent_to_automation(automation_name, prompt)
			return {agents_list: format_agents_list(agents), agent_prompt: ''}

		def remove_agent_and_update_list(automation_name, agent_index):
			if not agent_index or not isinstance(agent_index, list):
				return format_agents_list(app_instance.get_automation_agents(automation_name))
			try:
				index = int(agent_index[0][0])
				agents = app_instance.remove_agent_from_automation(automation_name, index)
				return format_agents_list(agents)
			except (ValueError, IndexError, TypeError):
				return format_agents_list(app_instance.get_automation_agents(automation_name))

		def update_agents_list(automation_name):
			if not automation_name:
				return []
			agents = app_instance.get_automation_agents(automation_name)
			return format_agents_list(agents)

		def update_provider(provider):
			# Import helper functions
			try:
				from gradio_app.src.models.llm_models import check_provider_availability, get_available_models
				from gradio_app.src.ui.interface import (
					_get_api_help_html,
					_get_model_recommendations_html,
					_get_provider_info_html,
				)

				# Get dynamic models for the provider (especially important for Ollama/LM Studio)
				models = get_available_models(provider)
				default_model = models[0] if models else None

				# Save the provider preference
				app_instance.update_llm_preferences(provider, default_model)

				provider_info_html = _get_provider_info_html(provider)
				api_help_html = _get_api_help_html(provider)
				model_rec_html = _get_model_recommendations_html(provider, default_model)

				# Check provider status
				is_available = check_provider_availability(provider)
				if is_available:
					if provider in ['Ollama', 'LM Studio'] and models and 'not running' in models[0].lower():
						status_html = f"<div style='color: orange;'>⚠️ {models[0]}</div>"
					elif provider in ['Ollama', 'LM Studio'] and models and 'no models' in models[0].lower():
						status_html = f"<div style='color: orange;'>⚠️ {models[0]}</div>"
					else:
						status_html = "<div style='color: green;'>✅ Provider ready</div>"
				else:
					status_html = "<div style='color: orange;'>⚠️ API key needed or service offline</div>"

			except ImportError:
				# Fallback - use static models
				models = app_instance.llm_models.get(provider, [])
				default_model = models[0] if models else None
				app_instance.update_llm_preferences(provider, default_model)
				provider_info_html = f'Provider: {provider}'
				api_help_html = ''
				model_rec_html = ''
				status_html = "<div style='color: gray;'>Status unknown</div>"

			return {
				llm_model: gr.update(choices=models, value=default_model),
				api_key: gr.update(value=app_instance.get_saved_api_key(provider)),
				provider_info: gr.update(value=provider_info_html),
				api_help: gr.update(value=api_help_html),
				model_recommendations: gr.update(value=model_rec_html),
				provider_status: gr.update(value=status_html),
			}

		def update_model(provider, model):
			# Save the model preference
			app_instance.update_llm_preferences(provider, model)

			# Update model recommendations
			try:
				from gradio_app.src.ui.interface import _get_model_recommendations_html

				model_rec_html = _get_model_recommendations_html(provider, model)
				return {model_recommendations: gr.update(value=model_rec_html)}
			except ImportError:
				return None

		def test_provider_connection(provider, model, api_key):
			"""Test connection to the selected provider"""
			try:
				from gradio_app.src.models.llm_models import check_provider_availability, get_llm

				# First check if provider is available
				if not check_provider_availability(provider):
					return "<div style='color: red;'>❌ Provider not available. Check API key or local service.</div>"

				# Try to initialize the LLM
				if not api_key and provider in ['OpenAI', 'Anthropic', 'Google', 'DeepSeek', 'OpenRouter']:
					return "<div style='color: orange;'>⚠️ API key required for this provider</div>"

				llm = get_llm(provider, model, api_key)

				# Test with a simple message
				test_response = llm.invoke("Hello, this is a connection test. Please respond with 'Test successful'.")

				if 'test successful' in test_response.content.lower():
					return "<div style='color: green;'>✅ Connection successful! Provider is working correctly.</div>"
				else:
					return "<div style='color: green;'>✅ Connection established. Provider responded.</div>"

			except Exception as e:
				error_msg = str(e)
				if 'rate limit' in error_msg.lower():
					return "<div style='color: orange;'>⚠️ Rate limit reached. Connection works but try again later.</div>"
				elif 'api key' in error_msg.lower():
					return "<div style='color: red;'>❌ Invalid API key. Please check your key.</div>"
				elif 'auth' in error_msg.lower():
					return "<div style='color: red;'>❌ Authentication failed. Check API key.</div>"
				else:
					return f"<div style='color: red;'>❌ Connection failed: {error_msg}</div>"

		def refresh_models(provider):
			"""Refresh the model list for the current provider"""
			try:
				from gradio_app.src.models.llm_models import get_available_models

				models = get_available_models(provider)
				default_model = models[0] if models else None
				app_instance.update_llm_preferences(provider, default_model)
				return {llm_model: gr.update(choices=models, value=default_model)}
			except Exception:
				# Fallback to static models
				models = app_instance.llm_models.get(provider, [])
				default_model = models[0] if models else None
				return {llm_model: gr.update(choices=models, value=default_model)}

		# Create a wrapper function for run_agent that gets share_terminal from preferences
		async def run_agent_wrapper(task, max_steps, max_actions, llm_provider, llm_model, api_key, share_prompt):
			"""Wrapper for run_agent that adds share_terminal from preferences"""
			# Get the current value of share_terminal from preferences
			share_terminal = app_instance.preferences.get('share_terminal', True)

			# The run_agent method returns an AsyncGenerator, so we need to yield each value
			async for output in app_instance.run_agent(
				task, max_steps, max_actions, llm_provider, llm_model, api_key, share_prompt, share_terminal
			):
				yield output

		# Function to refine user prompt using LLM
		async def refine_prompt(prompt, llm_provider, llm_model, api_key):
			"""Uses the LLM to refine the user's prompt based on examples."""
			if not prompt or not prompt.strip():
				return prompt

			if not api_key:
				return prompt

			# Create a system message that explains what the LLM should do
			system_message = f"""You are a helpful assistant that refines user prompts for a FF-Terminal:Desktop_ver agent.
The user has provided a prompt: "{prompt}"

Your task is to refine this prompt to make it more specific, clearer, and more likely to succeed when executed on macOS.
For this purpose the agent can preform the following actions:
- Open an app
- Click on an element
- Type text into a field
- Create an AppleScript
          
GENERAL PRINCIPLES:
1. Include useful details that make the task clear and executable (e.g Open [app name], click on the [element name])
2. Don't change the intent of the original prompt!
3. If the task involves multiple steps, break it down into smaller steps
4. When prompting for opening an app, ALWAYS prompt with "open 'app name'"
5. When prompting for opening a browser, prompt with "open a new window"
6. Dont take the user sequence as granted, decide for yourself what is the best way to accomplish the task

Only return the refined prompt text, nothing else.
"""

			# Try to use the agent's API to refine the prompt
			try:
				# Use the existing API connection
				app_instance.save_api_key_to_env(llm_provider, api_key)
				# Get the response from the LLM
				refined_prompt = await app_instance.get_llm_response(
					system_message=system_message, user_message=prompt, llm_provider=llm_provider, llm_model=llm_model
				)

				# Clean up the response - remove any quotes that may be present
				refined_prompt = refined_prompt.strip('"\'')

				return refined_prompt
			except Exception as e:
				print(f'Error refining prompt: {e}')
				return prompt  # Return original prompt if there's an error

		# Set up event handlers
		add_automation_btn.click(
			fn=add_automation_and_clear,
			inputs=[automation_name, automation_description],
			outputs=[automation_list, automation_name, automation_description],
		)

		add_agent_btn.click(
			fn=add_agent_and_update_list, inputs=[automation_list, agent_prompt], outputs=[agents_list, agent_prompt]
		)

		remove_agent_btn.click(fn=remove_agent_and_update_list, inputs=[automation_list, agents_list], outputs=[agents_list])

		automation_list.change(fn=update_agents_list, inputs=[automation_list], outputs=[agents_list])

		run_automation_btn.click(
			fn=app_instance.run_automation,
			inputs=[
				automation_list,
				llm_provider,
				llm_model,
				api_key,
			],
			outputs=[automation_output, run_automation_btn, stop_button],
			queue=True,
			api_name=False,
		)

		run_button.click(
			fn=run_agent_wrapper,
			inputs=[task_input, max_steps, max_actions, llm_provider, llm_model, api_key, share_prompt],
			outputs=[terminal_output, run_button, stop_button, result_output],
			queue=True,
			api_name=False,
		)

		# Add event handler for the refine prompt button
		refine_prompt_btn.click(
			fn=refine_prompt,
			inputs=[task_input, llm_provider, llm_model, api_key],
			outputs=[task_input],
			queue=True,
			api_name=False,
		)

		stop_button.click(fn=app_instance.stop_agent, outputs=[terminal_output, run_button, stop_button, result_output])

		share_prompt.change(fn=app_instance.update_share_prompt, inputs=[share_prompt], outputs=[])

		share_terminal_cfg.change(fn=app_instance.update_share_terminal, inputs=[share_terminal_cfg], outputs=[])

		llm_provider.change(
			fn=update_provider,
			inputs=llm_provider,
			outputs=[llm_model, api_key, provider_info, api_help, model_recommendations, provider_status],
		)

		llm_model.change(fn=update_model, inputs=[llm_provider, llm_model], outputs=[model_recommendations])

		# Test connection event handler
		test_connection_btn.click(
			fn=test_provider_connection, inputs=[llm_provider, llm_model, api_key], outputs=[provider_status]
		)

		# Refresh models event handler
		refresh_models_btn.click(fn=refresh_models, inputs=[llm_provider], outputs=[llm_model])

		return demo


def find_available_port(start_port: int, max_attempts: int = 100) -> int:
	"""Find an available port starting from start_port"""

	for port in range(start_port, start_port + max_attempts):
		try:
			with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
				s.bind(('0.0.0.0', port))
				return port
		except OSError:
			continue
	raise OSError(f'Could not find an available port in range {start_port}-{start_port + max_attempts}')


def main():
	# Try to use exactly the port we want
	port = int(os.getenv('SERVER_PORT', 7860))

	app = MacOSUseGradioApp()
	demo = create_interface(app)
	demo.queue(default_concurrency_limit=1)  # Limit to one concurrent task

	try:
		demo.launch(server_name='0.0.0.0', server_port=port, pwa=True, share=False, show_error=True)
	except Exception as e:
		print(f'Error launching application: {e}')
		# If we can't get the exact port, try finding an available one
		try:
			port = find_available_port(port + 1)  # Start looking from next port
			demo.launch(server_name='0.0.0.0', server_port=port, pwa=True, share=False, show_error=True)
		except Exception as e:
			print(f'Failed to launch on alternative port: {e}')


if __name__ == '__main__':
	main()
