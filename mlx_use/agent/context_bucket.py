"""
Context bucket system for managing persistent context across conversations.
"""
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
import asyncio
import aiofiles
import tiktoken
from pydantic import BaseModel

from .context_models import (
	ContextItem,
	ContextBucketState,
	ContextBucketConfig,
	ContextItemType,
	ContextItemPriority
)


class ContextBucket:
	"""Manages a collection of context items for AI agents."""
	
	def __init__(self, config: Optional[ContextBucketConfig] = None):
		self.config = config or ContextBucketConfig()
		self.state = ContextBucketState(max_tokens=self.config.max_tokens)
		self.tokenizer = tiktoken.get_encoding('cl100k_base')
		self._lock = asyncio.Lock()
		
		# Set up storage path if provided
		if self.config.storage_path:
			self.storage_path = Path(self.config.storage_path)
			self.storage_path.mkdir(parents=True, exist_ok=True)
		else:
			self.storage_path = None
	
	def _count_tokens(self, text: str) -> int:
		"""Count tokens in a text string."""
		return len(self.tokenizer.encode(text))
	
	async def add_item(
		self,
		type: ContextItemType,
		title: str,
		content: str,
		**kwargs
	) -> Optional[ContextItem]:
		"""Add a new context item."""
		async with self._lock:
			# Create the item
			item = ContextItem(
				type=type,
				title=title,
				content=content,
				**kwargs
			)
			
			# Calculate token count
			item.token_count = self._count_tokens(f"{title}\n{content}")
			
			# Check if auto-compression is needed
			if self.config.auto_compress and self._should_compress():
				await self._compress_context()
			
			# Try to add the item
			if self.state.add_item(item):
				await self._save_state()
				return item
			
			# If failed, try compression and retry once
			if self.config.auto_compress:
				await self._compress_context()
				if self.state.add_item(item):
					await self._save_state()
					return item
			
			return None
	
	async def remove_item(self, item_id: str) -> bool:
		"""Remove a context item by ID."""
		async with self._lock:
			success = self.state.remove_item(item_id)
			if success:
				await self._save_state()
			return success
	
	async def update_item(
		self,
		item_id: str,
		**updates
	) -> Optional[ContextItem]:
		"""Update an existing context item."""
		async with self._lock:
			for item in self.state.items:
				if item.id == item_id:
					# Update fields
					for key, value in updates.items():
						if hasattr(item, key):
							setattr(item, key, value)
					
					# Recalculate token count if content changed
					if 'content' in updates or 'title' in updates:
						old_tokens = item.token_count or 0
						new_tokens = self._count_tokens(f"{item.title}\n{item.content}")
						item.token_count = new_tokens
						self.state.total_tokens += (new_tokens - old_tokens)
					
					item.updated_at = datetime.utcnow()
					await self._save_state()
					return item
			return None
	
	def get_item(self, item_id: str) -> Optional[ContextItem]:
		"""Get a specific context item."""
		for item in self.state.items:
			if item.id == item_id:
				item.update_usage()
				return item
		return None
	
	def get_all_items(self) -> List[ContextItem]:
		"""Get all context items."""
		return self.state.items
	
	def get_items_by_type(self, item_type: ContextItemType) -> List[ContextItem]:
		"""Get items filtered by type."""
		return self.state.get_items_by_type(item_type)
	
	def get_items_by_tag(self, tag: str) -> List[ContextItem]:
		"""Get items filtered by tag."""
		return self.state.get_items_by_tag(tag)
	
	def get_relevant_items(self, limit: Optional[int] = None) -> List[ContextItem]:
		"""Get items sorted by relevance."""
		return self.state.get_sorted_items(limit)
	
	async def clear(self) -> None:
		"""Clear all context items."""
		async with self._lock:
			self.state = ContextBucketState(max_tokens=self.config.max_tokens)
			await self._save_state()
	
	def get_context_for_prompt(
		self,
		max_tokens: Optional[int] = None,
		types: Optional[List[ContextItemType]] = None,
		tags: Optional[List[str]] = None
	) -> str:
		"""Get formatted context for inclusion in prompts."""
		max_tokens = max_tokens or self.config.max_tokens
		
		# Filter items
		items = self.state.items
		if types:
			items = [i for i in items if i.type in types]
		if tags:
			items = [i for i in items if any(tag in i.tags for tag in tags)]
		
		# Sort by relevance
		items = sorted(items, key=lambda x: x.calculate_relevance_score(), reverse=True)
		
		# Build context within token limit
		context_parts = []
		used_tokens = 0
		
		for item in items:
			item_text = f"## {item.title}\n{item.content}\n"
			item_tokens = item.token_count or self._count_tokens(item_text)
			
			if used_tokens + item_tokens <= max_tokens:
				context_parts.append(item_text)
				used_tokens += item_tokens
				item.update_usage()
			else:
				break
		
		if not context_parts:
			return ""
		
		return "# Context Information\n\n" + "\n".join(context_parts)
	
	def _should_compress(self) -> bool:
		"""Check if compression is needed."""
		return self.state.total_tokens >= self.config.max_tokens * self.config.compression_threshold
	
	async def _compress_context(self) -> None:
		"""Compress context by removing least relevant items."""
		# Remove expired items first
		if self.config.item_expiry_days:
			cutoff_date = datetime.utcnow() - timedelta(days=self.config.item_expiry_days)
			self.state.items = [
				item for item in self.state.items
				if item.created_at > cutoff_date
			]
		
		# Sort by relevance and remove lowest scoring items
		sorted_items = sorted(
			self.state.items,
			key=lambda x: x.calculate_relevance_score()
		)
		
		# Keep removing items until we're below 60% capacity
		target_tokens = int(self.config.max_tokens * 0.6)
		self.state.items = []
		self.state.total_tokens = 0
		
		for item in reversed(sorted_items):
			if self.state.total_tokens + (item.token_count or 0) <= target_tokens:
				self.state.items.append(item)
				self.state.total_tokens += item.token_count or 0
			else:
				break
	
	async def _save_state(self) -> None:
		"""Save state to storage."""
		if not self.storage_path:
			return
		
		state_file = self.storage_path / 'context_bucket.json'
		state_dict = self.state.model_dump(mode='json')
		
		async with aiofiles.open(state_file, 'w') as f:
			await f.write(json.dumps(state_dict, indent=2, default=str))
	
	async def load_state(self) -> None:
		"""Load state from storage."""
		if not self.storage_path:
			return
		
		state_file = self.storage_path / 'context_bucket.json'
		if not state_file.exists():
			return
		
		async with self._lock:
			async with aiofiles.open(state_file, 'r') as f:
				state_dict = json.loads(await f.read())
			
			# Convert datetime strings back to datetime objects
			for item in state_dict.get('items', []):
				for field in ['created_at', 'updated_at', 'last_used']:
					if field in item and item[field]:
						item[field] = datetime.fromisoformat(item[field].replace('Z', '+00:00'))
			
			self.state = ContextBucketState(**state_dict)
	
	async def export_to_json(self) -> str:
		"""Export the context bucket to JSON."""
		return json.dumps(self.state.model_dump(mode='json'), indent=2, default=str)
	
	async def import_from_json(self, json_str: str) -> None:
		"""Import context bucket from JSON."""
		async with self._lock:
			data = json.loads(json_str)
			
			# Convert datetime strings
			for item in data.get('items', []):
				for field in ['created_at', 'updated_at', 'last_used']:
					if field in item and item[field]:
						item[field] = datetime.fromisoformat(item[field].replace('Z', '+00:00'))
			
			self.state = ContextBucketState(**data)
			await self._save_state()
	
	def get_stats(self) -> Dict[str, Any]:
		"""Get statistics about the context bucket."""
		type_counts = {}
		for item_type in ContextItemType:
			type_counts[item_type.value] = len(self.get_items_by_type(item_type))
		
		return {
			'total_items': len(self.state.items),
			'total_tokens': self.state.total_tokens,
			'max_tokens': self.config.max_tokens,
			'usage_percentage': (self.state.total_tokens / self.config.max_tokens) * 100,
			'type_counts': type_counts,
			'created_at': self.state.created_at,
			'updated_at': self.state.updated_at
		}