"""
Context bucket manager and agent factory for universal context bucket support.
"""
import asyncio
import os
from pathlib import Path
from typing import Optional, Union
from datetime import datetime

from .context_bucket import ContextBucket
from .context_models import ContextBucketConfig
from .service import Agent
from .prompts import SystemPrompt
from mlx_use.controller.service import Controller


class ContextBucketManager:
	"""Manages context buckets for non-web usage (CLI, Gradio, examples)."""
	
	def __init__(self, storage_dir: Optional[Union[str, Path]] = None):
		"""
		Initialize context bucket manager.
		
		Args:
			storage_dir: Directory for context bucket storage. Defaults to ~/.mlx-use-context
		"""
		if storage_dir is None:
			storage_dir = Path.home() / ".mlx-use-context"
		
		self.storage_dir = Path(storage_dir)
		self.storage_dir.mkdir(parents=True, exist_ok=True)
		
		self._context_bucket: Optional[ContextBucket] = None
	
	async def get_context_bucket(
		self,
		session_id: str = "default",
		max_tokens: int = 8000,
		auto_compress: bool = True
	) -> ContextBucket:
		"""
		Get or create a context bucket for the given session.
		
		Args:
			session_id: Unique identifier for the session
			max_tokens: Maximum tokens for the context bucket
			auto_compress: Whether to auto-compress when approaching limits
		
		Returns:
			ContextBucket instance
		"""
		if self._context_bucket is None:
			config = ContextBucketConfig(
				max_tokens=max_tokens,
				auto_compress=auto_compress,
				storage_path=str(self.storage_dir / session_id)
			)
			
			self._context_bucket = ContextBucket(config)
			await self._context_bucket.load_state()
		
		return self._context_bucket
	
	async def save_context_bucket(self):
		"""Save the current context bucket state."""
		if self._context_bucket:
			await self._context_bucket._save_state()
	
	def clear_context_bucket(self):
		"""Clear the current context bucket."""
		self._context_bucket = None


class AgentFactory:
	"""Factory for creating context-aware agents."""
	
	@staticmethod
	async def create_agent_with_context(
		task: str,
		llm,
		session_id: str = "default",
		storage_dir: Optional[Union[str, Path]] = None,
		max_actions_per_step: int = 10,
		max_tokens: int = 8000,
		system_prompt_class: type = SystemPrompt,
		**kwargs
	) -> Agent:
		"""
		Create an agent with context bucket support.
		
		Args:
			task: Task description for the agent
			llm: Language model instance
			session_id: Unique session identifier
			storage_dir: Directory for context bucket storage
			max_actions_per_step: Maximum actions per step
			max_tokens: Maximum tokens for context bucket
			system_prompt_class: SystemPrompt class to use
			**kwargs: Additional arguments for Agent creation
		
		Returns:
			Agent instance with context bucket support
		"""
		# Create context bucket manager
		context_manager = ContextBucketManager(storage_dir)
		context_bucket = await context_manager.get_context_bucket(
			session_id=session_id,
			max_tokens=max_tokens
		)
		
		# Create controller if not provided
		if 'controller' not in kwargs:
			kwargs['controller'] = Controller()
		
		# Create agent with context bucket
		agent = Agent(
			task=task,
			llm=llm,
			max_actions_per_step=max_actions_per_step,
			system_prompt_class=system_prompt_class,
			system_prompt_kwargs={'context_bucket': context_bucket},
			**kwargs
		)
		
		# Attach context manager for saving later
		agent._context_manager = context_manager
		
		return agent
	
	@staticmethod
	async def create_simple_agent_with_context(
		task: str,
		llm,
		context_items: Optional[list] = None,
		**kwargs
	) -> Agent:
		"""
		Create a simple agent with optional pre-populated context.
		
		Args:
			task: Task description
			llm: Language model instance
			context_items: List of dict items to add to context
			**kwargs: Additional arguments
		
		Returns:
			Agent instance with context
		"""
		agent = await AgentFactory.create_agent_with_context(
			task=task,
			llm=llm,
			session_id="simple",
			**kwargs
		)
		
		# Add context items if provided
		if context_items:
			context_bucket = agent.system_prompt.context_bucket
			for item in context_items:
				await context_bucket.add_item(**item)
		
		return agent


# Convenience functions for easy usage
async def create_agent_with_context(
	task: str,
	llm,
	session_id: str = "default",
	storage_dir: Optional[Union[str, Path]] = None,
	**kwargs
) -> Agent:
	"""
	Convenience function to create an agent with context bucket support.
	
	Usage:
		agent = await create_agent_with_context(
			task="Open Calculator and compute 5+3",
			llm=my_llm,
			session_id="calc_session"
		)
		history = await agent.run()
	"""
	return await AgentFactory.create_agent_with_context(
		task=task,
		llm=llm,
		session_id=session_id,
		storage_dir=storage_dir,
		**kwargs
	)


async def add_context_to_session(
	session_id: str,
	context_type: str,
	title: str,
	content: str,
	priority: str = "medium",
	tags: Optional[list] = None,
	storage_dir: Optional[Union[str, Path]] = None
):
	"""
	Convenience function to add context to a session.
	
	Usage:
		await add_context_to_session(
			session_id="calc_session",
			context_type="instruction",
			title="Calculator Rules",
			content="Always verify results using context elements"
		)
	"""
	context_manager = ContextBucketManager(storage_dir)
	context_bucket = await context_manager.get_context_bucket(session_id)
	
	from .context_models import ContextItemType, ContextItemPriority
	
	await context_bucket.add_item(
		type=ContextItemType(context_type),
		title=title,
		content=content,
		priority=ContextItemPriority(priority),
		tags=tags or []
	)
	
	await context_manager.save_context_bucket()


async def get_context_from_session(session_id: str, storage_dir: Optional[Union[str, Path]] = None) -> str:
	"""
	Get formatted context content from a session.
	
	Usage:
		context = await get_context_from_session("calc_session")
		print(context)
	"""
	context_manager = ContextBucketManager(storage_dir)
	context_bucket = await context_manager.get_context_bucket(session_id)
	return context_bucket.get_context_for_prompt()