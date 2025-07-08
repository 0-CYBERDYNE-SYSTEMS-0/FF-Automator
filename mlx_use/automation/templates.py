"""
Pre-built automation templates for common tasks.
"""

from .models import (
	AutomationTemplate,
	SavedAutomation,
	AutomationStep,
	AutomationAction,
	AutomationMetadata,
	AutomationConfig
)


def create_calculator_template() -> AutomationTemplate:
	"""Template for basic calculator operations"""
	
	# Create automation steps
	steps = [
		AutomationStep(
			name="Open Calculator",
			description="Open the Calculator application",
			actions=[
				AutomationAction(
					action_type="open_app",
					parameters={"app_name": "Calculator"},
					description="Launch Calculator app"
				)
			]
		),
		AutomationStep(
			name="Perform Calculation",
			description="Enter numbers and operation",
			actions=[
				AutomationAction(
					action_type="click_element",
					parameters={"element_index": "{{ first_number_button }}"},
					description="Click first number"
				),
				AutomationAction(
					action_type="click_element",
					parameters={"element_index": "{{ operation_button }}"},
					description="Click operation (+, -, *, /)"
				),
				AutomationAction(
					action_type="click_element",
					parameters={"element_index": "{{ second_number_button }}"},
					description="Click second number"
				),
				AutomationAction(
					action_type="click_element",
					parameters={"element_index": "equals_button"},
					description="Click equals to get result"
				)
			]
		),
		AutomationStep(
			name="Complete",
			description="Mark calculation as complete",
			actions=[
				AutomationAction(
					action_type="done",
					parameters={"result": "Calculation completed"},
					description="Complete the automation"
				)
			]
		)
	]
	
	# Create template automation
	template_automation = SavedAutomation(
		name="Calculator Operation Template",
		description="Perform basic arithmetic operations using Calculator app",
		steps=steps,
		metadata=AutomationMetadata(source="template", category="Productivity"),
		original_task="Open Calculator and perform {{ operation }} operation with {{ first_number }} and {{ second_number }}"
	)
	
	# Create template
	template = AutomationTemplate(
		name="Calculator Operation",
		description="Perform basic arithmetic operations",
		category="Productivity",
		template_automation=template_automation,
		parameters=[
			{"name": "operation", "type": "select", "options": ["addition", "subtraction", "multiplication", "division"], "default": "addition"},
			{"name": "first_number", "type": "number", "default": 5},
			{"name": "second_number", "type": "number", "default": 3}
		]
	)
	
	return template


def create_notes_template() -> AutomationTemplate:
	"""Template for creating notes"""
	
	steps = [
		AutomationStep(
			name="Open Notes",
			description="Open the Notes application",
			actions=[
				AutomationAction(
					action_type="open_app",
					parameters={"app_name": "Notes"},
					description="Launch Notes app"
				)
			]
		),
		AutomationStep(
			name="Create New Note",
			description="Create a new note with title and content",
			actions=[
				AutomationAction(
					action_type="click_element",
					parameters={"element_index": "new_note_button"},
					description="Click new note button"
				),
				AutomationAction(
					action_type="type_text",
					parameters={"text": "{{ note_title }}"},
					description="Type note title"
				),
				AutomationAction(
					action_type="key_press",
					parameters={"key": "Return"},
					description="Press enter to move to content"
				),
				AutomationAction(
					action_type="type_text",
					parameters={"text": "{{ note_content }}"},
					description="Type note content"
				)
			]
		),
		AutomationStep(
			name="Save Note",
			description="Save the note",
			actions=[
				AutomationAction(
					action_type="key_press",
					parameters={"key": "cmd+s"},
					description="Save the note"
				),
				AutomationAction(
					action_type="done",
					parameters={"result": "Note '{{ note_title }}' created successfully"},
					description="Complete the automation"
				)
			]
		)
	]
	
	template_automation = SavedAutomation(
		name="Create Note Template",
		description="Create a new note with specified title and content",
		steps=steps,
		metadata=AutomationMetadata(source="template", category="Productivity"),
		original_task="Create a new note titled '{{ note_title }}' with content: {{ note_content }}"
	)
	
	template = AutomationTemplate(
		name="Create Note",
		description="Create a new note with custom title and content",
		category="Productivity",
		template_automation=template_automation,
		parameters=[
			{"name": "note_title", "type": "text", "default": "My Note"},
			{"name": "note_content", "type": "textarea", "default": "Enter your note content here..."}
		]
	)
	
	return template


def create_system_info_template() -> AutomationTemplate:
	"""Template for gathering system information"""
	
	steps = [
		AutomationStep(
			name="Open Terminal",
			description="Open Terminal application",
			actions=[
				AutomationAction(
					action_type="open_app",
					parameters={"app_name": "Terminal"},
					description="Launch Terminal app"
				)
			]
		),
		AutomationStep(
			name="Get System Information",
			description="Run system profiler command",
			actions=[
				AutomationAction(
					action_type="type_text",
					parameters={"text": "system_profiler SPHardwareDataType"},
					description="Type system profiler command"
				),
				AutomationAction(
					action_type="key_press",
					parameters={"key": "Return"},
					description="Execute command"
				),
				AutomationAction(
					action_type="wait",
					parameters={"seconds": 3},
					description="Wait for command to complete"
				)
			]
		),
		AutomationStep(
			name="Copy Results",
			description="Select and copy the system information",
			actions=[
				AutomationAction(
					action_type="key_press",
					parameters={"key": "cmd+a"},
					description="Select all output"
				),
				AutomationAction(
					action_type="key_press",
					parameters={"key": "cmd+c"},
					description="Copy to clipboard"
				),
				AutomationAction(
					action_type="done",
					parameters={"result": "System information copied to clipboard"},
					description="Complete the automation"
				)
			]
		)
	]
	
	template_automation = SavedAutomation(
		name="System Information Template",
		description="Gather system hardware information using Terminal",
		steps=steps,
		metadata=AutomationMetadata(source="template", category="System"),
		original_task="Get system hardware information and copy to clipboard"
	)
	
	template = AutomationTemplate(
		name="System Information",
		description="Gather and copy system hardware information",
		category="System",
		template_automation=template_automation,
		parameters=[]
	)
	
	return template


def create_email_template() -> AutomationTemplate:
	"""Template for composing emails"""
	
	steps = [
		AutomationStep(
			name="Open Mail",
			description="Open the Mail application",
			actions=[
				AutomationAction(
					action_type="open_app",
					parameters={"app_name": "Mail"},
					description="Launch Mail app"
				)
			]
		),
		AutomationStep(
			name="Compose Email",
			description="Create new email with recipient and subject",
			actions=[
				AutomationAction(
					action_type="key_press",
					parameters={"key": "cmd+n"},
					description="Create new email"
				),
				AutomationAction(
					action_type="type_text",
					parameters={"text": "{{ recipient_email }}"},
					description="Enter recipient email"
				),
				AutomationAction(
					action_type="key_press",
					parameters={"key": "Tab"},
					description="Move to subject field"
				),
				AutomationAction(
					action_type="type_text",
					parameters={"text": "{{ email_subject }}"},
					description="Enter email subject"
				),
				AutomationAction(
					action_type="key_press",
					parameters={"key": "Tab"},
					description="Move to body field"
				),
				AutomationAction(
					action_type="type_text",
					parameters={"text": "{{ email_body }}"},
					description="Enter email body"
				)
			]
		),
		AutomationStep(
			name="Send Email",
			description="Send the composed email",
			actions=[
				AutomationAction(
					action_type="key_press",
					parameters={"key": "cmd+shift+d"},
					description="Send email"
				),
				AutomationAction(
					action_type="done",
					parameters={"result": "Email sent to {{ recipient_email }}"},
					description="Complete the automation"
				)
			],
			condition="{{ send_immediately }}"
		)
	]
	
	template_automation = SavedAutomation(
		name="Email Composition Template",
		description="Compose and optionally send an email",
		steps=steps,
		metadata=AutomationMetadata(source="template", category="Communication"),
		original_task="Compose email to {{ recipient_email }} with subject '{{ email_subject }}'"
	)
	
	template = AutomationTemplate(
		name="Compose Email",
		description="Compose and send an email with custom content",
		category="Communication",
		template_automation=template_automation,
		parameters=[
			{"name": "recipient_email", "type": "email", "default": "example@email.com"},
			{"name": "email_subject", "type": "text", "default": "Quick Message"},
			{"name": "email_body", "type": "textarea", "default": "Hello,\n\nI hope this message finds you well.\n\nBest regards"},
			{"name": "send_immediately", "type": "checkbox", "default": False}
		]
	)
	
	return template


def create_screenshot_template() -> AutomationTemplate:
	"""Template for taking and saving screenshots"""
	
	steps = [
		AutomationStep(
			name="Take Screenshot",
			description="Capture screenshot using system shortcut",
			actions=[
				AutomationAction(
					action_type="key_press",
					parameters={"key": "cmd+shift+3"},
					description="Take full screen screenshot"
				),
				AutomationAction(
					action_type="wait",
					parameters={"seconds": 1},
					description="Wait for screenshot to be taken"
				)
			]
		),
		AutomationStep(
			name="Open Finder",
			description="Navigate to Desktop to find screenshot",
			actions=[
				AutomationAction(
					action_type="open_app",
					parameters={"app_name": "Finder"},
					description="Open Finder"
				),
				AutomationAction(
					action_type="key_press",
					parameters={"key": "cmd+shift+d"},
					description="Go to Desktop"
				)
			]
		),
		AutomationStep(
			name="Rename Screenshot",
			description="Rename the screenshot file if requested",
			actions=[
				AutomationAction(
					action_type="click_element",
					parameters={"element_index": "latest_screenshot"},
					description="Select latest screenshot"
				),
				AutomationAction(
					action_type="key_press",
					parameters={"key": "Return"},
					description="Start renaming"
				),
				AutomationAction(
					action_type="type_text",
					parameters={"text": "{{ screenshot_name }}"},
					description="Enter new name"
				),
				AutomationAction(
					action_type="key_press",
					parameters={"key": "Return"},
					description="Confirm rename"
				),
				AutomationAction(
					action_type="done",
					parameters={"result": "Screenshot saved as {{ screenshot_name }}"},
					description="Complete the automation"
				)
			],
			condition="{{ rename_screenshot }}"
		)
	]
	
	template_automation = SavedAutomation(
		name="Screenshot Template",
		description="Take and optionally rename a screenshot",
		steps=steps,
		metadata=AutomationMetadata(source="template", category="Utility"),
		original_task="Take a screenshot and save it as {{ screenshot_name }}"
	)
	
	template = AutomationTemplate(
		name="Take Screenshot",
		description="Capture and manage screenshots",
		category="Utility",
		template_automation=template_automation,
		parameters=[
			{"name": "screenshot_name", "type": "text", "default": "My Screenshot"},
			{"name": "rename_screenshot", "type": "checkbox", "default": True}
		]
	)
	
	return template


# Registry of all available templates
AUTOMATION_TEMPLATES = {
	"calculator": create_calculator_template,
	"notes": create_notes_template,
	"system_info": create_system_info_template,
	"email": create_email_template,
	"screenshot": create_screenshot_template
}


def get_all_templates() -> list[AutomationTemplate]:
	"""Get all available automation templates"""
	return [template_func() for template_func in AUTOMATION_TEMPLATES.values()]


def get_template_by_name(name: str) -> AutomationTemplate:
	"""Get a specific template by name"""
	if name in AUTOMATION_TEMPLATES:
		return AUTOMATION_TEMPLATES[name]()
	raise ValueError(f"Template '{name}' not found")


def get_templates_by_category(category: str) -> list[AutomationTemplate]:
	"""Get templates filtered by category"""
	all_templates = get_all_templates()
	return [template for template in all_templates if template.category.lower() == category.lower()]