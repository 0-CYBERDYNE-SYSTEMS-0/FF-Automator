from typing import List

import gradio as gr


def create_agent_tab(app_instance) -> List[gr.components.Component]:
	with gr.Row():
		# Left Column (scale=2)
		with gr.Column(scale=2):
			gr.Markdown('### Examples: How to prompt the agent')
			# Category Selection Buttons
			with gr.Row():
				quick_tasks_btn = gr.Button('Quick Tasks', variant='secondary')
				multi_step_btn = gr.Button('Multi-Step Tasks', variant='primary')
				advanced_btn = gr.Button('Advanced Workflows', variant='secondary')

			gr.Markdown("This is <span style='color: red; font-weight: bold;'>NOT a chat</span> - Check our prompt examples!")

			with gr.Group():
				with gr.Row():
					gr.Markdown("<div style='text-align: center; width: 100%; padding-top: 3px;'>Task Prompt</div>")
					refine_prompt_btn = gr.Button('Refine Prompt', size='sm')
				with gr.Row():
					task_input = gr.Textbox(label='', placeholder="Enter task (e.g., 'open calculator')", lines=3)

			share_prompt = gr.Checkbox(
				label='Share prompt (only!) anonymously',
				value=app_instance.preferences['share_prompt'],
				info='Sharing your prompt (and prompt only) ANONYMOUSLY will help us improve our agent.',
			)
			with gr.Row():
				max_steps = gr.Slider(minimum=1, maximum=100, value=25, step=1, label='Max Run Steps')
				max_actions = gr.Slider(minimum=1, maximum=20, value=5, step=1, label='Max Actions per Step')
			with gr.Row():
				run_button = gr.Button('Run', variant='primary')
				stop_button = gr.Button('Stop', interactive=False)

		# Right Column (scale=3)
		with gr.Column(scale=3):
			result_output = gr.Textbox(label='Result', lines=3, interactive=False, autoscroll=True)

			with gr.Accordion('Steps & Actions', open=False) as terminal_accordion:
				terminal_output = gr.Textbox(label='Terminal Output', lines=25, interactive=False, autoscroll=True)

			# Dynamic Example Containers
			with gr.Column() as examples_box:
				gr.Markdown('#### Task prompts examples, Try all of them!')

				# Level description markdown that will be updated
				level_description = gr.Markdown(visible=False)

				# Scrollable container for all example categories
				with gr.Column(elem_classes='scrollable-container') as examples_container:
					# Quick Tasks Container
					with gr.Column(visible=False) as quick_tasks_container:
						quick_tasks = app_instance.example_categories.get('Quick Tasks', [])
						quick_buttons = []
						for example in quick_tasks:
							btn = gr.Button(value=example['name'], variant='secondary')
							quick_buttons.append(btn)
							btn.click(fn=lambda p=example['prompt']: p, outputs=task_input)

					# Multi-Step Tasks Container
					with gr.Column(visible=True) as multi_step_container:
						multi_step_tasks = app_instance.example_categories.get('Multi-Step Tasks', [])
						for task in multi_step_tasks:
							# Task name as a header
							gr.Markdown(f'### {task["name"]}')
							# Buttons in a horizontal row below the task name
							if 'levels' in task:
								with gr.Row():
									for level_dict in task['levels']:
										level = level_dict['level']
										prompt = level_dict['prompt']
										level_descriptions = {
											'Bad': "Might work, but since this is not a chat, it's probably not the best way to do it.",
											'Good': 'Will probably work, good enough for short prompt tasks',
											'Expert': 'Most likely to work, for complex apps and tasks, use that!',
										}
										btn = gr.Button(value=f'{level} Example', variant='secondary')
										btn.click(
											fn=lambda p=prompt, l=level, desc=level_descriptions.get(level, ''): (p, desc),
											outputs=[task_input, level_description],
										).then(fn=lambda: gr.update(visible=True), outputs=level_description)
								# Add some spacing between tasks
								gr.Markdown('---')

					# Advanced Workflows Container
					with gr.Column(visible=False) as advanced_tasks_container:
						advanced_tasks = app_instance.example_categories.get('Advanced Workflows', [])
						for example in advanced_tasks:
							btn = gr.Button(value=example['name'], variant='secondary')
							btn.click(fn=lambda p=example['prompt']: p, outputs=task_input)

			# Add CSS for scrollable container to the interface
			gr.HTML("""
                <style>
                    .scrollable-container {
                        height: 400px;
                        overflow-y: auto;
                        padding-right: 10px;
                        margin-top: 10px;
                    }
                    /* Style the scrollbar */
                    .scrollable-container::-webkit-scrollbar {
                        width: 8px;
                    }
                    .scrollable-container::-webkit-scrollbar-track {
                        background: #f1f1f1;
                        border-radius: 4px;
                    }
                    .scrollable-container::-webkit-scrollbar-thumb {
                        background: #888;
                        border-radius: 4px;
                    }
                    .scrollable-container::-webkit-scrollbar-thumb:hover {
                        background: #555;
                    }
                </style>
            """)

			# Category selection handlers
			def update_category_visibility(category):
				return {
					quick_tasks_container: gr.update(visible=category == 'Quick Tasks'),
					advanced_tasks_container: gr.update(visible=category == 'Advanced Workflows'),
					multi_step_container: gr.update(visible=category == 'Multi-Step Tasks'),
					quick_tasks_btn: gr.update(variant='primary' if category == 'Quick Tasks' else 'secondary'),
					multi_step_btn: gr.update(variant='primary' if category == 'Multi-Step Tasks' else 'secondary'),
					advanced_btn: gr.update(variant='primary' if category == 'Advanced Workflows' else 'secondary'),
					examples_box: gr.update(visible=True),
				}

			# Set up category button click handlers
			quick_tasks_btn.click(
				fn=lambda: update_category_visibility('Quick Tasks'),
				outputs=[
					quick_tasks_container,
					advanced_tasks_container,
					multi_step_container,
					quick_tasks_btn,
					multi_step_btn,
					advanced_btn,
					examples_box,
				],
			)

			multi_step_btn.click(
				fn=lambda: update_category_visibility('Multi-Step Tasks'),
				outputs=[
					quick_tasks_container,
					advanced_tasks_container,
					multi_step_container,
					quick_tasks_btn,
					multi_step_btn,
					advanced_btn,
					examples_box,
				],
			)

			advanced_btn.click(
				fn=lambda: update_category_visibility('Advanced Workflows'),
				outputs=[
					quick_tasks_container,
					advanced_tasks_container,
					multi_step_container,
					quick_tasks_btn,
					multi_step_btn,
					advanced_btn,
					examples_box,
				],
			)

	return [
		task_input,
		refine_prompt_btn,
		share_prompt,
		max_steps,
		max_actions,
		run_button,
		stop_button,
		result_output,
		terminal_output,
	]


def create_automations_tab(app_instance) -> List[gr.components.Component]:
	with gr.Row():
		with gr.Column(scale=2):
			automation_name = gr.Textbox(label='Automation Name', placeholder='Enter automation name')
			automation_description = gr.Textbox(label='Description', placeholder='Enter automation description', lines=2)
			add_automation_btn = gr.Button('Add Automation', variant='primary')

			automation_list = gr.Dropdown(
				label='Select Automation', choices=list(app_instance.automations.keys()), interactive=True
			)

			agent_prompt = gr.Textbox(label='Agent Prompt', placeholder='Enter agent prompt', lines=3, interactive=True)

			with gr.Row():
				add_agent_btn = gr.Button('Add Agent', variant='primary')
				remove_agent_btn = gr.Button('Remove Selected Agent', variant='stop')

			run_automation_btn = gr.Button('Run Automation', variant='primary')

		with gr.Column(scale=3):
			agents_list = gr.List(label='Agents in Flow', headers=['#', 'Prompt'], type='array', interactive=True, col_count=2)
			automation_output = gr.Textbox(label='Automation Output', lines=25, interactive=False, autoscroll=True)

	return [
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
	]


def create_configuration_tab(app_instance) -> List[gr.components.Component]:
	with gr.Row():
		# Left column - Provider Selection
		with gr.Column(scale=2):
			gr.Markdown('### 🌐 LLM Provider Configuration')

			# Get saved provider and model from preferences, or use defaults
			default_provider = app_instance.preferences.get('llm_provider', 'OpenAI')

			# Enhanced provider dropdown with status indicators
			try:
				from ..models.llm_models import PROVIDER_CONFIGS, check_provider_availability

				print("🔍 DEBUG: Creating provider dropdown in Gradio UI")
				print(f"🔍 DEBUG: app_instance.llm_models keys: {list(app_instance.llm_models.keys())}")

				provider_choices = []
				for provider in app_instance.llm_models.keys():
					print(f"🔍 DEBUG: Processing provider: {provider}")
					try:
						is_available = check_provider_availability(provider)
						config = PROVIDER_CONFIGS.get(provider, {})
						print(f"🔍 DEBUG: {provider} - available: {is_available}, config: {bool(config)}")

						# Add status indicators
						if config.get('local_provider'):
							status = '💻 ' if is_available else '⚫ '
							provider_display = f'{status}{provider} (Local)'
						elif config.get('free_models_available'):
							status = '✅ ' if is_available else '❌ '
							provider_display = f'{status}{provider} (Free Options)'
						else:
							status = '✅ ' if is_available else '❌ '
							provider_display = f'{status}{provider}'

						provider_choices.append((provider_display, provider))
						print(f"🔍 DEBUG: Added provider choice: '{provider_display}' -> '{provider}'")
					except Exception as e:
						print(f"🔍 DEBUG: Error processing {provider}: {e}")

				print(f"🔍 DEBUG: Final provider_choices ({len(provider_choices)}): {provider_choices}")
			except Exception as e:
				print(f"🔍 DEBUG: Exception in provider creation: {e}")
				import traceback
				traceback.print_exc()
				# Fallback if imports fail
				print("🔍 DEBUG: Using fallback provider list")
				provider_choices = [(provider, provider) for provider in app_instance.llm_models.keys()]
				print(f"🔍 DEBUG: Fallback provider_choices: {provider_choices}")

			llm_provider = gr.Dropdown(
				choices=provider_choices,
				label='LLM Provider',
				value=default_provider,
				info='✅ Available, ❌ Needs API key, 💻 Local, ⚫ Offline',
			)

			# Provider info display
			provider_info = gr.HTML(value=_get_provider_info_html(default_provider), label='Provider Information')

			# Get the models for the current provider (use dynamic detection)
			try:
				from ..models.llm_models import get_available_models

				available_models = get_available_models(default_provider)
			except ImportError:
				# Fallback to static models
				available_models = app_instance.llm_models.get(default_provider, [])

			default_model = app_instance.preferences.get('llm_model', available_models[0] if available_models else None)

			# Enhanced model dropdown with categories
			with gr.Row():
				llm_model = gr.Dropdown(
					choices=available_models,
					label='Model',
					value=default_model,
					info='Select the specific model variant to use',
					scale=4,
				)
				refresh_models_btn = gr.Button('🔄', scale=1, size='sm', elem_id='refresh-models', elem_classes='refresh-button')

			# Model recommendations
			model_recommendations = gr.HTML(
				value=_get_model_recommendations_html(default_provider, default_model), label='Model Recommendations'
			)

		# Right column - API Configuration
		with gr.Column(scale=1):
			gr.Markdown('### 🔑 API Configuration')

			api_key = gr.Textbox(
				label='API Key',
				type='password',
				placeholder='Enter your API key (if required)',
				value=app_instance.get_saved_api_key(default_provider),
				info="Local providers (Ollama, LM Studio) don't need API keys",
			)

			# API key help links
			api_help = gr.HTML(value=_get_api_help_html(default_provider), label='Get API Key')

			# Provider status
			provider_status = gr.HTML(value="<div style='color: green;'>✅ Provider ready</div>", label='Status')

			# Test connection button
			test_connection_btn = gr.Button('Test Connection', variant='secondary')

			gr.Markdown('### 📊 Advanced Settings')

			# Task-specific provider preferences
			with gr.Accordion('Task-Specific Preferences', open=False):
				reasoning_provider = gr.Dropdown(
					choices=list(app_instance.llm_models.keys()),
					label='Reasoning Tasks',
					value=app_instance.preferences.get('reasoning_provider', 'OpenAI'),
					info='Best for math, logic, complex analysis',
				)

				coding_provider = gr.Dropdown(
					choices=list(app_instance.llm_models.keys()),
					label='Coding Tasks',
					value=app_instance.preferences.get('coding_provider', 'Anthropic'),
					info='Best for programming and code generation',
				)

				chat_provider = gr.Dropdown(
					choices=list(app_instance.llm_models.keys()),
					label='General Chat',
					value=app_instance.preferences.get('chat_provider', 'Google'),
					info='Best for general conversation and quick tasks',
				)

			# Cost optimization
			with gr.Accordion('Cost Optimization', open=False):
				enable_cost_optimization = gr.Checkbox(
					label='Enable cost optimization',
					value=app_instance.preferences.get('enable_cost_optimization', False),
					info='Automatically select cheaper models when possible',
				)

				prefer_free_models = gr.Checkbox(
					label='Prefer free models',
					value=app_instance.preferences.get('prefer_free_models', False),
					info='Use free OpenRouter models when available',
				)

				max_cost_per_request = gr.Slider(
					minimum=0.01,
					maximum=1.0,
					value=app_instance.preferences.get('max_cost_per_request', 0.1),
					step=0.01,
					label='Max cost per request ($)',
					info='Skip expensive requests above this threshold',
				)

	# Bottom section - Sharing Settings
	gr.Markdown('### 🔄 Sharing Settings')

	share_terminal = gr.Checkbox(
		label='Share terminal output anonymously',
		value=app_instance.preferences.get('share_terminal', True),
		info='Sharing terminal output helps us understand how the agent performs tasks.',
	)

	return [
		llm_provider,
		llm_model,
		api_key,
		share_terminal,
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
	]


def _get_provider_info_html(provider: str) -> str:
	"""Get HTML info for a provider"""
	provider_info = {
		'OpenAI': '🚀 Latest models: GPT-4.1, o3, o4-mini. Best for reasoning and general tasks.',
		'Anthropic': '🧠 Claude 4 available. Excellent for complex reasoning and coding.',
		'Google': '⚡ Gemini 2.5 models. Fast and efficient for most tasks.',
		'DeepSeek': '💡 V3 and R1 models. Great value for reasoning tasks.',
		'OpenRouter': '🌐 Access to 400+ models. <strong>Dynamic loading:</strong> With API key, all models are fetched live. Without API key, shows 12 popular models. Click refresh (🔄) to reload.',
		'Ollama': '💻 Local models. <strong>Dynamic loading:</strong> Shows your actual installed models. Click refresh (🔄) after installing new models.',
		'LM Studio': '🖥️ Local models. <strong>Dynamic loading:</strong> Shows loaded models from your LM Studio instance.',
		'Z.AI': '🤖 GLM-4.5 and GLM-4.5-Air models with Vision capabilities. <strong>Vision MCP:</strong> Screen analysis and UI automation. <strong>Prompt Caching:</strong> 90% cost reduction. Compatible with Claude/OpenAI model names.',
	}

	info = provider_info.get(provider, 'Select a provider to see information.')
	return f"<div style='padding: 10px; background-color: #f5f5f5; border-radius: 5px;'>{info}</div>"


def _get_model_recommendations_html(provider: str, model: str) -> str:
	"""Get HTML recommendations for a model"""
	recommendations = {
		'o3': '🧠 Best for complex reasoning, math, and scientific tasks',
		'o4-mini': '⚡ Fast reasoning model, good balance of speed and intelligence',
		'gpt-4.1-mini': '⚡ Cost-effective and fast, excellent for most automation tasks',
		'gpt-4.1': '🎯 Excellent all-around model for coding and general tasks',
		'claude-4-opus': '🧠 Top-tier reasoning and analysis capabilities',
		'claude-4-sonnet': '⚡ Fast and intelligent, great for coding',
		'gemini-2.5-pro': '🧠 Excellent for complex tasks and long context',
		'gemini-2.5-flash': '⚡ Very fast, good for quick tasks',
		'deepseek-reasoner': '🧠 Excellent for step-by-step reasoning',
		'deepseek-chat': '💬 Great general purpose model, cost-effective',
		# Z.AI model recommendations
		'GLM-4.5': '🤖 High-performance GLM model with Vision capabilities. Best for complex tasks.',
		'glm-4.5': '🤖 High-performance GLM model with Vision capabilities. Best for complex tasks.',
		'GLM-4.5-Air': '⚡ Fast and cost-effective GLM model. Great for quick tasks and automation.',
		'glm-4.5-air': '⚡ Fast and cost-effective GLM model. Great for quick tasks and automation.',
		'claude-3-5-sonnet-20241022': '🤖 Maps to GLM-4.5. Use Z.AI\'s high-performance model with Claude compatibility.',
		'claude-3-5-haiku-20241022': '⚡ Maps to GLM-4.5-Air. Fast model with Claude compatibility.',
		'gpt-4': '🤖 Maps to GLM-4.5. Use Z.AI\'s high-performance model with OpenAI compatibility.',
	}

	if model in recommendations:
		return f"<div style='padding: 8px; background-color: #e8f4fd; border-radius: 5px; font-size: 12px;'>{recommendations[model]}</div>"
	return ''


def _get_api_help_html(provider: str) -> str:
	"""Get HTML links for API key acquisition"""
	api_links = {
		'OpenAI': "<a href='https://platform.openai.com/api-keys' target='_blank'>Get OpenAI API Key</a>",
		'Anthropic': "<a href='https://console.anthropic.com/account/keys' target='_blank'>Get Anthropic API Key</a>",
		'Google': "<a href='https://console.cloud.google.com/apis/credentials' target='_blank'>Get Google API Key</a>",
		'DeepSeek': "<a href='https://platform.deepseek.com/api_keys' target='_blank'>Get DeepSeek API Key</a>",
		'OpenRouter': "<a href='https://openrouter.ai/keys' target='_blank'>Get OpenRouter API Key</a>",
		'Ollama': "<a href='https://ollama.ai/' target='_blank'>Install Ollama</a>",
		'LM Studio': "<a href='https://lmstudio.ai/' target='_blank'>Download LM Studio</a>",
		'Z.AI': "<a href='https://z.ai/manage-apikey/apikey-list' target='_blank'>Get Z.AI API Key</a><br><small>Vision MCP requires Node.js/npm</small>",
	}

	link = api_links.get(provider, '')
	if link:
		return f"<div style='padding: 5px;'>{link}</div>"
	return ''
