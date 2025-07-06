import re
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class CommandParser:
	"""Parses user input to determine command type and intent"""
	
	def __init__(self):
		self.session_commands = {
			"sessions": r"^sessions?$",
			"new session": r"^new\s+session(?:\s+(.+))?$",
			"load session": r"^load\s+session\s+(.+)$",
			"save session": r"^save\s+session(?:\s+(.+))?$",
		}
		
		self.action_patterns = {
			"open": r"^open\s+(.+)$",
			"click": r"^click\s+(.+)$",
			"type": r"^type\s+(.+)$",
			"scroll": r"^scroll\s+(.+)$",
			"find": r"^find\s+(.+)$",
			"search": r"^search\s+(?:for\s+)?(.+)$",
			"wait": r"^wait\s+(.+)$",
			"close": r"^close\s+(.+)$",
			"switch": r"^switch\s+to\s+(.+)$",
			"take": r"^take\s+(?:a\s+)?screenshot",
			"get": r"^get\s+(.+)$",
		}
		
		self.intent_keywords = {
			"navigation": ["open", "switch", "go to", "navigate", "launch"],
			"interaction": ["click", "tap", "press", "select", "choose"],
			"input": ["type", "enter", "input", "write", "fill"],
			"information": ["find", "search", "look for", "get", "show", "display"],
			"control": ["close", "quit", "minimize", "maximize", "resize"],
			"wait": ["wait", "pause", "delay", "hold"]
		}
	
	def parse(self, user_input: str) -> Dict[str, Any]:
		"""Parse user input and return command information"""
		user_input = user_input.strip()
		
		# Check for session commands
		session_result = self._parse_session_command(user_input)
		if session_result:
			return session_result
		
		# Check for direct action commands
		action_result = self._parse_action_command(user_input)
		if action_result:
			return action_result
		
		# Analyze intent for natural language commands
		intent = self._analyze_intent(user_input)
		
		return {
			"type": "task",
			"command": "natural_language",
			"intent": intent,
			"original": user_input,
			"confidence": intent.get("confidence", 0.5)
		}
	
	def _parse_session_command(self, user_input: str) -> Optional[Dict[str, Any]]:
		"""Parse session management commands"""
		for command, pattern in self.session_commands.items():
			match = re.match(pattern, user_input, re.IGNORECASE)
			if match:
				args = [arg for arg in match.groups() if arg is not None]
				return {
					"type": "session",
					"command": command,
					"args": args,
					"original": user_input
				}
		return None
	
	def _parse_action_command(self, user_input: str) -> Optional[Dict[str, Any]]:
		"""Parse direct action commands"""
		for action, pattern in self.action_patterns.items():
			match = re.match(pattern, user_input, re.IGNORECASE)
			if match:
				args = [arg for arg in match.groups() if arg is not None]
				return {
					"type": "action",
					"command": action,
					"args": args,
					"original": user_input,
					"confidence": 0.9
				}
		return None
	
	def _analyze_intent(self, user_input: str) -> Dict[str, Any]:
		"""Analyze the intent of natural language input"""
		user_input_lower = user_input.lower()
		
		intent_scores = {}
		for intent, keywords in self.intent_keywords.items():
			score = 0
			for keyword in keywords:
				if keyword in user_input_lower:
					score += 1
			intent_scores[intent] = score / len(keywords) if keywords else 0
		
		# Find the most likely intent
		primary_intent = max(intent_scores, key=intent_scores.get) if intent_scores else "general"
		confidence = intent_scores.get(primary_intent, 0)
		
		# Extract potential targets/objects
		targets = self._extract_targets(user_input)
		
		# Determine complexity
		complexity = self._assess_complexity(user_input)
		
		return {
			"primary": primary_intent,
			"confidence": min(confidence * 2, 1.0),  # Scale confidence
			"targets": targets,
			"complexity": complexity,
			"keywords": self._extract_keywords(user_input)
		}
	
	def _extract_targets(self, user_input: str) -> List[str]:
		"""Extract potential targets/objects from the input"""
		# Common application names
		app_patterns = [
			r"(?:open|launch|start|switch to)\s+([A-Za-z\s]+?)(?:\s+app|\s+application|$)",
			r"(?:in|on)\s+([A-Za-z\s]+?)(?:\s+app|\s+application|$)",
		]
		
		targets = []
		for pattern in app_patterns:
			matches = re.findall(pattern, user_input, re.IGNORECASE)
			targets.extend([match.strip() for match in matches])
		
		# File/folder patterns
		file_patterns = [
			r"(?:file|folder|document)\s+(?:named\s+)?['\"]([^'\"]+)['\"]",
			r"['\"]([^'\"]+\.(?:txt|pdf|doc|jpg|png|mp4|mp3))['\"]",
		]
		
		for pattern in file_patterns:
			matches = re.findall(pattern, user_input, re.IGNORECASE)
			targets.extend(matches)
		
		return list(set(targets))  # Remove duplicates
	
	def _assess_complexity(self, user_input: str) -> str:
		"""Assess the complexity of the task"""
		complexity_indicators = {
			"simple": ["click", "open", "close", "type"],
			"medium": ["find", "search", "navigate", "scroll", "select"],
			"complex": ["and then", "after", "once", "if", "when", "while"]
		}
		
		user_input_lower = user_input.lower()
		
		for complexity, indicators in complexity_indicators.items():
			if any(indicator in user_input_lower for indicator in indicators):
				if complexity == "complex":
					return "complex"
		
		# Check for multiple actions
		action_count = len([action for action in self.action_patterns.keys() 
						  if action in user_input_lower])
		
		if action_count > 1:
			return "complex"
		elif action_count == 1:
			return "medium"
		else:
			return "simple"
	
	def _extract_keywords(self, user_input: str) -> List[str]:
		"""Extract important keywords from the input"""
		# Remove common stop words
		stop_words = {
			"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
			"of", "with", "by", "from", "up", "about", "into", "through", "during",
			"before", "after", "above", "below", "between", "among", "against",
			"within", "without", "toward", "towards", "throughout", "underneath",
			"i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
			"my", "your", "his", "its", "our", "their", "this", "that", "these", "those",
			"is", "am", "are", "was", "were", "be", "been", "being", "have", "has", "had",
			"do", "does", "did", "will", "would", "could", "should", "may", "might", "must",
			"can", "please", "just", "now", "then", "here", "there", "where", "when", "how", "why"
		}
		
		words = re.findall(r'\b\w+\b', user_input.lower())
		keywords = [word for word in words if word not in stop_words and len(word) > 2]
		
		return keywords[:10]  # Limit to top 10 keywords