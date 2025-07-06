import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class ChatSessionStorage:
	"""Handles persistent storage for chat sessions in the web UI"""
	
	def __init__(self, storage_dir: Optional[str] = None):
		self.storage_dir = Path(storage_dir or os.path.expanduser("~/.macOS-use-web-sessions"))
		self.storage_dir.mkdir(exist_ok=True)
		
		self.sessions_file = self.storage_dir / "sessions.json"
		self.sessions: Dict[str, Dict[str, Any]] = {}
		
		self._load_sessions()
	
	def _load_sessions(self):
		"""Load existing sessions from disk"""
		try:
			if self.sessions_file.exists():
				with open(self.sessions_file, 'r') as f:
					self.sessions = json.load(f)
		except Exception as e:
			logger.error(f"Error loading sessions: {e}")
			self.sessions = {}
	
	def _save_sessions(self):
		"""Save sessions to disk"""
		try:
			with open(self.sessions_file, 'w') as f:
				json.dump(self.sessions, f, indent=2)
		except Exception as e:
			logger.error(f"Error saving sessions: {e}")
	
	def create_session(self, session_id: str, name: Optional[str] = None) -> bool:
		"""Create a new session"""
		session_name = name or f"Chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
		
		self.sessions[session_id] = {
			"id": session_id,
			"name": session_name,
			"created": datetime.now().isoformat(),
			"last_updated": datetime.now().isoformat(),
			"messages": [],
			"metadata": {
				"total_interactions": 0,
				"successful_tasks": 0,
				"failed_tasks": 0
			}
		}
		
		self._save_sessions()
		return True
	
	def save_session(self, session_id: str, messages: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> bool:
		"""Save or update a session"""
		if session_id not in self.sessions:
			self.create_session(session_id)
		
		self.sessions[session_id]["messages"] = messages
		self.sessions[session_id]["last_updated"] = datetime.now().isoformat()
		
		if metadata:
			self.sessions[session_id]["metadata"].update(metadata)
		
		# Update statistics
		successful = sum(1 for msg in messages if msg.get("type") == "agent" and msg.get("success", False))
		failed = sum(1 for msg in messages if msg.get("type") == "agent" and not msg.get("success", True))
		
		self.sessions[session_id]["metadata"].update({
			"total_interactions": len([msg for msg in messages if msg.get("type") == "user"]),
			"successful_tasks": successful,
			"failed_tasks": failed
		})
		
		self._save_sessions()
		return True
	
	def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
		"""Load a session by ID"""
		return self.sessions.get(session_id)
	
	def list_sessions(self) -> List[Dict[str, Any]]:
		"""List all sessions with summary info"""
		sessions_list = []
		for session_id, session_data in self.sessions.items():
			sessions_list.append({
				"id": session_id,
				"name": session_data.get("name", session_id),
				"created": session_data.get("created"),
				"last_updated": session_data.get("last_updated"),
				"message_count": len(session_data.get("messages", [])),
				"metadata": session_data.get("metadata", {})
			})
		
		# Sort by last updated (most recent first)
		sessions_list.sort(key=lambda x: x["last_updated"], reverse=True)
		return sessions_list
	
	def delete_session(self, session_id: str) -> bool:
		"""Delete a session"""
		if session_id in self.sessions:
			del self.sessions[session_id]
			self._save_sessions()
			return True
		return False
	
	def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
		"""Get the most recent sessions"""
		all_sessions = self.list_sessions()
		return all_sessions[:limit]
	
	def export_session(self, session_id: str, export_path: Optional[str] = None) -> Optional[str]:
		"""Export a session to a JSON file"""
		if session_id not in self.sessions:
			return None
		
		if not export_path:
			export_path = str(self.storage_dir / f"{session_id}_export.json")
		
		try:
			session_data = self.sessions[session_id]
			
			# Format for export
			export_data = {
				"session_info": {
					"id": session_data["id"],
					"name": session_data["name"],
					"created": session_data["created"],
					"exported": datetime.now().isoformat()
				},
				"conversation": []
			}
			
			for msg in session_data.get("messages", []):
				if msg.get("type") == "user":
					export_data["conversation"].append({
						"timestamp": msg.get("timestamp"),
						"speaker": "User",
						"message": msg.get("content")
					})
				elif msg.get("type") == "agent":
					status = "✅" if msg.get("success", False) else "❌"
					export_data["conversation"].append({
						"timestamp": msg.get("timestamp"),
						"speaker": "Agent",
						"message": f"{status} {msg.get('content')}",
						"success": msg.get("success", False)
					})
			
			with open(export_path, 'w') as f:
				json.dump(export_data, f, indent=2)
			
			return export_path
		
		except Exception as e:
			logger.error(f"Error exporting session {session_id}: {e}")
			return None
	
	def import_session(self, import_path: str) -> Optional[str]:
		"""Import a session from a JSON file"""
		try:
			with open(import_path, 'r') as f:
				import_data = json.load(f)
			
			session_info = import_data.get("session_info", {})
			conversation = import_data.get("conversation", [])
			
			# Create new session
			new_session_id = f"imported_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
			session_name = f"Imported: {session_info.get('name', 'Unknown')}"
			
			messages = []
			for entry in conversation:
				if entry.get("speaker") == "User":
					messages.append({
						"timestamp": entry.get("timestamp", datetime.now().isoformat()),
						"type": "user",
						"content": entry.get("message")
					})
				elif entry.get("speaker") == "Agent":
					messages.append({
						"timestamp": entry.get("timestamp", datetime.now().isoformat()),
						"type": "agent",
						"content": entry.get("message"),
						"success": entry.get("success", True)
					})
			
			self.create_session(new_session_id, session_name)
			self.save_session(new_session_id, messages)
			
			return new_session_id
		
		except Exception as e:
			logger.error(f"Error importing session from {import_path}: {e}")
			return None
	
	def search_sessions(self, query: str) -> List[Dict[str, Any]]:
		"""Search sessions by content or name"""
		results = []
		query_lower = query.lower()
		
		for session_id, session_data in self.sessions.items():
			# Check session name
			if query_lower in session_data.get("name", "").lower():
				results.append({
					"session_id": session_id,
					"match_type": "name",
					"match_text": session_data.get("name"),
					"session_info": self._get_session_summary(session_data)
				})
				continue
			
			# Check message content
			for msg in session_data.get("messages", []):
				if query_lower in msg.get("content", "").lower():
					results.append({
						"session_id": session_id,
						"match_type": "message",
						"match_text": msg.get("content")[:100] + "...",
						"timestamp": msg.get("timestamp"),
						"session_info": self._get_session_summary(session_data)
					})
					break  # Only include each session once
		
		return results
	
	def _get_session_summary(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
		"""Get a summary of session info"""
		return {
			"name": session_data.get("name"),
			"created": session_data.get("created"),
			"last_updated": session_data.get("last_updated"),
			"message_count": len(session_data.get("messages", [])),
			"metadata": session_data.get("metadata", {})
		}