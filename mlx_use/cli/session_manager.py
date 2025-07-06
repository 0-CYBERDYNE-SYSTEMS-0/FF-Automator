import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class SessionManager:
	"""Manages CLI sessions with persistent conversation context"""
	
	def __init__(self, session_dir: Path):
		self.session_dir = Path(session_dir)
		self.session_dir.mkdir(exist_ok=True)
		self.sessions: Dict[str, Dict[str, Any]] = {}
		self._load_existing_sessions()
	
	def _load_existing_sessions(self):
		"""Load existing sessions from disk"""
		try:
			for session_file in self.session_dir.glob("*.json"):
				session_id = session_file.stem
				with open(session_file, 'r') as f:
					self.sessions[session_id] = json.load(f)
		except Exception as e:
			logger.error(f"Error loading sessions: {e}")
	
	def create_session(self, name: Optional[str] = None) -> str:
		"""Create a new session"""
		session_id = name or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
		
		self.sessions[session_id] = {
			"id": session_id,
			"created": datetime.now().isoformat(),
			"last_updated": datetime.now().isoformat(),
			"history": [],
			"metadata": {}
		}
		
		self._save_session(session_id)
		return session_id
	
	def load_session(self, session_id: str) -> bool:
		"""Load an existing session"""
		session_file = self.session_dir / f"{session_id}.json"
		
		if not session_file.exists():
			return False
		
		try:
			with open(session_file, 'r') as f:
				self.sessions[session_id] = json.load(f)
			return True
		except Exception as e:
			logger.error(f"Error loading session {session_id}: {e}")
			return False
	
	def save_session(self, session_id: str, new_name: Optional[str] = None) -> bool:
		"""Save session to disk, optionally with a new name"""
		if session_id not in self.sessions:
			return False
		
		target_id = new_name or session_id
		
		if new_name and new_name != session_id:
			# Copy session with new name
			self.sessions[target_id] = self.sessions[session_id].copy()
			self.sessions[target_id]["id"] = target_id
		
		return self._save_session(target_id)
	
	def _save_session(self, session_id: str) -> bool:
		"""Internal method to save session to disk"""
		if session_id not in self.sessions:
			return False
		
		try:
			session_file = self.session_dir / f"{session_id}.json"
			self.sessions[session_id]["last_updated"] = datetime.now().isoformat()
			
			with open(session_file, 'w') as f:
				json.dump(self.sessions[session_id], f, indent=2)
			
			return True
		except Exception as e:
			logger.error(f"Error saving session {session_id}: {e}")
			return False
	
	def add_to_session(self, session_id: str, entry: Dict[str, Any]) -> bool:
		"""Add an entry to session history"""
		if session_id not in self.sessions:
			return False
		
		self.sessions[session_id]["history"].append(entry)
		return self._save_session(session_id)
	
	def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
		"""Get session history"""
		if session_id not in self.sessions:
			return []
		
		return self.sessions[session_id].get("history", [])
	
	def list_sessions(self) -> Dict[str, Dict[str, Any]]:
		"""List all available sessions"""
		return {
			session_id: {
				"created": session_data.get("created"),
				"last_updated": session_data.get("last_updated"),
				"history": session_data.get("history", [])
			}
			for session_id, session_data in self.sessions.items()
		}
	
	def delete_session(self, session_id: str) -> bool:
		"""Delete a session"""
		if session_id not in self.sessions:
			return False
		
		try:
			session_file = self.session_dir / f"{session_id}.json"
			if session_file.exists():
				session_file.unlink()
			
			del self.sessions[session_id]
			return True
		except Exception as e:
			logger.error(f"Error deleting session {session_id}: {e}")
			return False
	
	def get_session_context(self, session_id: str, max_entries: int = 10) -> str:
		"""Get formatted context from recent session history"""
		if session_id not in self.sessions:
			return ""
		
		history = self.sessions[session_id].get("history", [])
		recent_history = history[-max_entries:] if history else []
		
		if not recent_history:
			return ""
		
		context_parts = []
		for entry in recent_history:
			timestamp = entry.get("timestamp", "")
			entry_type = entry.get("type", "")
			content = entry.get("content", "")
			
			if entry_type == "user_command":
				context_parts.append(f"User: {content}")
			elif entry_type == "agent_result":
				success = entry.get("success", False)
				status = "✅" if success else "❌"
				context_parts.append(f"Agent {status}: {content}")
		
		return "\n".join(context_parts)