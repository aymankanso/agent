"""
Message Processing Logic (refactored - pure business logic)
Core logic for converting CLI messages to frontend messages
"""

from datetime import datetime
from typing import Dict, Any, List
import os
import sys

# Add project root path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# Direct import of CLI message utilities
from src.utils.message import parse_tool_name, extract_tool_calls
# Refactored agent manager
from src.utils.agents import AgentManager


class MessageProcessor:
    """Message processing core logic class"""
    
    def __init__(self):
        """Initialize message processor"""
        self.default_avatar = "🤖"
    
    def process_cli_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert CLI event to frontend message
        
        Args:
            event_data: Event data from CLI
            
        Returns:
            Dict: Converted frontend message
        """
        message_type = event_data.get("message_type", "")
        agent_name = event_data.get("agent_name", "Unknown")
        content = event_data.get("content", "")
        raw_message = event_data.get("raw_message")
        
        # Generate agent display info
        display_name = AgentManager.get_display_name(agent_name)
        avatar = AgentManager.get_avatar(agent_name)
        
        if message_type == "ai":
            return self._create_ai_message(
                agent_name, display_name, avatar, content, raw_message, event_data
            )
        elif message_type == "tool":
            return self._create_tool_message(event_data, content)
        elif message_type == "user":
            return self._create_user_message(content)
        
        # Default message - handle as AI
        return self._create_ai_message(
            agent_name, display_name, avatar, content, raw_message, event_data
        )
    
    def _create_ai_message(
        self, 
        agent_name: str, 
        display_name: str, 
        avatar: str, 
        content: str, 
        raw_message: Any,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create AI message"""
        message = {
            "type": "ai",
            "agent_id": agent_name.lower(),
            "display_name": display_name,
            "avatar": avatar,
            "content": content,
            "id": f"ai_{agent_name.lower()}_{hash(content[:100])}_{datetime.now().timestamp()}"
        }
        
        # Extract tool calls info
        tool_calls = extract_tool_calls(raw_message, event_data)
        if tool_calls:
            message["tool_calls"] = tool_calls
        
        return message
    
    def _create_tool_message(self, event_data: Dict[str, Any], content: str) -> Dict[str, Any]:
        """Create tool message"""
        tool_name = event_data.get("tool_name", "Unknown Tool")
        tool_display_name = event_data.get("tool_display_name", parse_tool_name(tool_name))
        
        return {
            "type": "tool",
            "tool_name": tool_name,
            "tool_display_name": tool_display_name,
            "content": content,
            "id": f"tool_{tool_name}_{hash(content[:100])}_{datetime.now().timestamp()}"
        }
    
    def _create_user_message(self, content: str) -> Dict[str, Any]:
        """Create user message"""
        return {
            "type": "user",
            "content": content,
            "id": f"user_{hash(content)}_{datetime.now().timestamp()}"
        }
    
    def extract_agent_status(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract agent status info from events"""
        status = {
            "active_agent": None,
            "completed_agents": [],
            "current_step": 0
        }
        
        # Find active agent from recent events
        for event in reversed(events):
            if event.get("type") == "message" and event.get("message_type") == "ai":
                agent_name = event.get("agent_name")
                if agent_name and agent_name != "Unknown":
                    status["active_agent"] = agent_name.lower()
                    break
        
        # Calculate total steps
        status["current_step"] = len([e for e in events if e.get("type") == "message"])
        
        return status
    
    def is_duplicate_message(
        self, 
        new_message: Dict[str, Any], 
        existing_messages: List[Dict[str, Any]]
    ) -> bool:
        """Check for duplicate message"""
        new_id = new_message.get("id")
        if not new_id:
            return False
        
        # ID-based duplicate check
        for msg in existing_messages:
            if msg.get("id") == new_id:
                return True
        
        # Content-based duplicate check (same agent, same content)
        new_agent = new_message.get("agent_id")
        new_content = new_message.get("content", "")
        
        for msg in existing_messages:
            if (msg.get("agent_id") == new_agent and 
                msg.get("type") == new_message.get("type") and
                msg.get("content") == new_content):
                return True
        
        return False


# Global message processor instance
_message_processor = None

def get_message_processor() -> MessageProcessor:
    """Return message processor singleton instance"""
    global _message_processor
    if _message_processor is None:
        _message_processor = MessageProcessor()
    return _message_processor
