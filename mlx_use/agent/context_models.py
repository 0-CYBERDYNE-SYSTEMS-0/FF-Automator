"""
Pydantic models for the context bucket system.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
import uuid


class ContextItemType(str, Enum):
	"""Types of context items that can be stored."""
	DOCUMENT = 'document'
	CODE_SNIPPET = 'code_snippet'
	INSTRUCTION = 'instruction'
	REFERENCE = 'reference'
	URL = 'url'
	FILE = 'file'
	NOTE = 'note'
	TEMPLATE = 'template'


class ContextItemPriority(str, Enum):
	"""Priority levels for context items."""
	LOW = 'low'
	MEDIUM = 'medium'
	HIGH = 'high'
	CRITICAL = 'critical'


class ContextItem(BaseModel):
	"""Model for a single context item."""
	model_config = ConfigDict(
		str_strip_whitespace=True,
		json_encoders={datetime: lambda v: v.isoformat() if v else None}
	)
	
	id: str = Field(default_factory=lambda: str(uuid.uuid4()))
	type: ContextItemType
	title: str
	content: str
	metadata: Dict[str, Any] = Field(default_factory=dict)
	tags: List[str] = Field(default_factory=list)
	priority: ContextItemPriority = ContextItemPriority.MEDIUM
	created_at: datetime = Field(default_factory=datetime.utcnow)
	updated_at: datetime = Field(default_factory=datetime.utcnow)
	usage_count: int = 0
	last_used: Optional[datetime] = None
	token_count: Optional[int] = None
	source: Optional[str] = None  # File path, URL, or other source
	embedding: Optional[List[float]] = None  # For future semantic search
	
	def update_usage(self) -> None:
		"""Update usage statistics when item is accessed."""
		self.usage_count += 1
		self.last_used = datetime.utcnow()
		self.updated_at = datetime.utcnow()
	
	def calculate_relevance_score(self, current_time: Optional[datetime] = None) -> float:
		"""Calculate relevance score based on priority, usage, and recency."""
		if current_time is None:
			current_time = datetime.utcnow()
		
		# Priority score (0-40 points)
		priority_scores = {
			ContextItemPriority.LOW: 10,
			ContextItemPriority.MEDIUM: 20,
			ContextItemPriority.HIGH: 30,
			ContextItemPriority.CRITICAL: 40
		}
		priority_score = priority_scores[self.priority]
		
		# Usage score (0-30 points)
		usage_score = min(30, self.usage_count * 3)
		
		# Recency score (0-30 points)
		if self.last_used:
			hours_since_use = (current_time - self.last_used).total_seconds() / 3600
			recency_score = max(0, 30 - (hours_since_use / 24))  # Decay over days
		else:
			recency_score = 15  # Middle score for never-used items
		
		return priority_score + usage_score + recency_score


class ContextBucketState(BaseModel):
	"""Model for the entire context bucket state."""
	model_config = ConfigDict(str_strip_whitespace=True)
	
	items: List[ContextItem] = Field(default_factory=list)
	total_tokens: int = 0
	max_tokens: int = 8000  # Default max tokens for context
	created_at: datetime = Field(default_factory=datetime.utcnow)
	updated_at: datetime = Field(default_factory=datetime.utcnow)
	
	def add_item(self, item: ContextItem) -> bool:
		"""Add an item if it fits within token limit."""
		if item.token_count and (self.total_tokens + item.token_count > self.max_tokens):
			return False
		
		self.items.append(item)
		if item.token_count:
			self.total_tokens += item.token_count
		self.updated_at = datetime.utcnow()
		return True
	
	def remove_item(self, item_id: str) -> bool:
		"""Remove an item by ID."""
		for i, item in enumerate(self.items):
			if item.id == item_id:
				if item.token_count:
					self.total_tokens -= item.token_count
				self.items.pop(i)
				self.updated_at = datetime.utcnow()
				return True
		return False
	
	def get_items_by_type(self, item_type: ContextItemType) -> List[ContextItem]:
		"""Get all items of a specific type."""
		return [item for item in self.items if item.type == item_type]
	
	def get_items_by_tag(self, tag: str) -> List[ContextItem]:
		"""Get all items with a specific tag."""
		return [item for item in self.items if tag in item.tags]
	
	def get_sorted_items(self, limit: Optional[int] = None) -> List[ContextItem]:
		"""Get items sorted by relevance score."""
		sorted_items = sorted(
			self.items,
			key=lambda x: x.calculate_relevance_score(),
			reverse=True
		)
		
		if limit:
			return sorted_items[:limit]
		return sorted_items


class ContextBucketConfig(BaseModel):
	"""Configuration for the context bucket system."""
	model_config = ConfigDict(str_strip_whitespace=True)
	
	max_tokens: int = 8000
	auto_compress: bool = True
	enable_semantic_search: bool = False
	storage_path: Optional[str] = None
	compression_threshold: float = 0.8  # Compress when 80% full
	item_expiry_days: Optional[int] = None  # Auto-remove old items