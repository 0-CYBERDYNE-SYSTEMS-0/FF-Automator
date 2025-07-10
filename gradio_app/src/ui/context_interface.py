"""Context Bucket UI for Gradio app"""


import gradio as gr


def create_context_tab(app_instance):
	"""Create the context bucket management tab"""

	with gr.Column():
		gr.Markdown('## 📦 Context Bucket Management')
		gr.Markdown('Add and manage context information that will be available to all agent conversations.')

		with gr.Row():
			with gr.Column(scale=1):
				# Context item form
				gr.Markdown('### Add Context Item')

				item_type = gr.Dropdown(
					choices=['document', 'instruction', 'reference', 'background', 'constraint', 'goal'],
					value='reference',
					label='Type',
					info='The type of context item',
				)

				title = gr.Textbox(label='Title', placeholder='Enter a descriptive title...', max_lines=1)

				content = gr.Textbox(label='Content', placeholder='Enter the context information...', lines=5, max_lines=20)

				priority = gr.Dropdown(
					choices=['high', 'medium', 'low'],
					value='medium',
					label='Priority',
					info='High priority items are always included in prompts',
				)

				tags = gr.Textbox(label='Tags (optional)', placeholder='comma, separated, tags', max_lines=1)

				session_id = gr.Textbox(
					label='Session ID', value='default', info='Context will be available to this session', max_lines=1
				)

				with gr.Row():
					add_button = gr.Button('Add Context Item', variant='primary')
					clear_form_button = gr.Button('Clear Form')

				add_status = gr.Markdown('')

			with gr.Column(scale=2):
				# Context items list
				gr.Markdown('### Current Context Items')

				with gr.Row():
					refresh_button = gr.Button('Refresh', size='sm')
					list_session_id = gr.Textbox(label='Session ID to view', value='default', max_lines=1, scale=2)

				context_items = gr.DataFrame(
					headers=['Title', 'Type', 'Priority', 'Tags', 'Tokens', 'Usage'],
					datatype=['str', 'str', 'str', 'str', 'number', 'number'],
					label='Context Items',
					interactive=False,
					height=400,
				)

				with gr.Row():
					remove_button = gr.Button('Remove Selected', variant='stop')
					clear_all_button = gr.Button('Clear All', variant='stop')

				management_status = gr.Markdown('')

	# Event handlers
	async def add_context_item_handler(item_type, title, content, priority, tags, session_id):
		"""Add a new context item"""
		if not title or not content:
			return '❌ Title and content are required', gr.update()

		tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()] if tags else []

		success = await app_instance.add_context_item(
			session_id=session_id, item_type=item_type, title=title, content=content, priority=priority, tags=tags_list
		)

		if success:
			# Clear form and refresh list
			items = await get_context_items_handler(session_id)
			return ('✅ Context item added successfully', gr.update(value=items))
		else:
			return '❌ Failed to add context item', gr.update()

	async def get_context_items_handler(session_id):
		"""Get context items for display"""
		items = await app_instance.get_context_items(session_id)

		# Format for DataFrame
		formatted_items = []
		for item in items:
			formatted_items.append(
				[
					item['title'],
					item['type'],
					item['priority'],
					', '.join(item['tags']) if item['tags'] else '',
					item['token_count'] or 0,
					item['usage_count'],
				]
			)

		return formatted_items

	def clear_form_handler():
		"""Clear the form fields"""
		return ('', '', '', 'default', '')

	async def remove_context_items_handler(session_id, selected_rows):
		"""Remove selected context items"""
		if not selected_rows:
			return '❌ No items selected', gr.update()

		items = await app_instance.get_context_items(session_id)
		removed_count = 0

		# Get selected indices and remove items
		for row_index in selected_rows:
			if 0 <= row_index < len(items):
				item_id = items[row_index]['id']
				success = await app_instance.remove_context_item(session_id, item_id)
				if success:
					removed_count += 1

		if removed_count > 0:
			# Refresh the list
			updated_items = await get_context_items_handler(session_id)
			return (f'✅ Removed {removed_count} context item(s)', gr.update(value=updated_items))
		else:
			return '❌ Failed to remove context items', gr.update()

	async def clear_all_context_handler(session_id):
		"""Clear all context items"""
		success = await app_instance.clear_context_items(session_id)

		if success:
			return ('✅ All context items cleared', gr.update(value=[]))
		else:
			return '❌ Failed to clear context items', gr.update()

	# Set up event handlers
	add_button.click(
		fn=add_context_item_handler,
		inputs=[item_type, title, content, priority, tags, session_id],
		outputs=[add_status, context_items],
		queue=True,
	)

	clear_form_button.click(fn=clear_form_handler, outputs=[title, content, tags, session_id, add_status])

	refresh_button.click(fn=get_context_items_handler, inputs=[list_session_id], outputs=[context_items], queue=True)

	list_session_id.change(fn=get_context_items_handler, inputs=[list_session_id], outputs=[context_items], queue=True)

	remove_button.click(
		fn=remove_context_items_handler,
		inputs=[list_session_id, context_items],
		outputs=[management_status, context_items],
		queue=True,
	)

	clear_all_button.click(
		fn=clear_all_context_handler, inputs=[list_session_id], outputs=[management_status, context_items], queue=True
	)

	return (
		item_type,
		title,
		content,
		priority,
		tags,
		session_id,
		add_button,
		clear_form_button,
		add_status,
		context_items,
		refresh_button,
		list_session_id,
		remove_button,
		clear_all_button,
		management_status,
	)
