"""
Automation system for macOS-use.
"""

from .models import (
	SavedAutomation,
	AutomationStep,
	AutomationAction,
	AutomationTrigger,
	AutomationVariable,
	AutomationConfig,
	AutomationMetadata,
	AutomationExecutionResult,
	AutomationTemplate
)

from .service import AutomationService
from .scheduler import AutomationScheduler
from .recorder import AutomationRecorder
from .executor import AutomationExecutor
from .templates import get_all_templates, get_template_by_name

__all__ = [
	'SavedAutomation',
	'AutomationStep',
	'AutomationAction',
	'AutomationTrigger',
	'AutomationVariable',
	'AutomationConfig',
	'AutomationMetadata',
	'AutomationExecutionResult',
	'AutomationTemplate',
	'AutomationService',
	'AutomationScheduler',
	'AutomationRecorder',
	'AutomationExecutor',
	'get_all_templates',
	'get_template_by_name'
]