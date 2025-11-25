"""
Minimal logger - Records only information needed for replay
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    """Minimal event types needed for replay"""
    USER_INPUT = "user_input"
    AGENT_RESPONSE = "agent_response"
    TOOL_COMMAND = "tool_command"
    TOOL_OUTPUT = "tool_output"

@dataclass
class Event:
    """Event information needed for replay"""
    event_type: EventType
    timestamp: str
    content: str
    agent_name: Optional[str] = None  # Used only for agent_response
    tool_name: Optional[str] = None   # Used only for tool_command, tool_output
    tool_calls: Optional[List[Dict[str, Any]]] = None  # Tool calls info from AI message
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "content": self.content
        }
        if self.agent_name:
            result["agent_name"] = self.agent_name
        if self.tool_name:
            result["tool_name"] = self.tool_name
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        return cls(
            event_type=EventType(data["event_type"]),
            timestamp=data["timestamp"],
            content=data["content"],
            agent_name=data.get("agent_name"),
            tool_name=data.get("tool_name"),
            tool_calls=data.get("tool_calls")  # Optional for compatibility with existing logs
        )

@dataclass
class Session:
    """Session information needed for replay"""
    session_id: str
    start_time: str
    events: List[Event]
    model: Optional[str] = None  # Added model information used
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "events": [event.to_dict() for event in self.events]
        }
        if self.model:
            result["model"] = self.model
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        return cls(
            session_id=data["session_id"],
            start_time=data["start_time"],
            events=[Event.from_dict(e) for e in data["events"]],
            model=data.get("model")  # Load model information (optional)
        )

class Logger:
    """Logging system needed for replay"""
    
    def __init__(self, base_path: str = "logs"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        self.current_session: Optional[Session] = None
    
    def _get_session_file_path(self, session_id: str) -> Path:
        """Generate session file path"""
        date_str = datetime.now().strftime("%Y/%m/%d")
        session_dir = self.base_path / date_str
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir / f"session_{session_id}.json"
    
    def start_session(self, model_info: Optional[str] = None) -> str:
        """Start new session - Include model information"""
        session_id = str(uuid.uuid4())
        start_time = datetime.now().isoformat()
        
        self.current_session = Session(
            session_id=session_id,
            start_time=start_time,
            events=[],
            model=model_info  # Save model information
        )
        return session_id
    
    def log_user_input(self, content: str):
        """Log user input"""
        if self.current_session:
            event = Event(
                event_type=EventType.USER_INPUT,
                timestamp=datetime.now().isoformat(),
                content=content
            )
            self.current_session.events.append(event)
    
    def log_agent_response(self, agent_name: str, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None):
        """Log agent response - Include tool_calls information"""
        if self.current_session:
            event = Event(
                event_type=EventType.AGENT_RESPONSE,
                timestamp=datetime.now().isoformat(),
                content=content,
                agent_name=agent_name,
                tool_calls=tool_calls
            )
            self.current_session.events.append(event)
    
    def log_tool_command(self, tool_name: str, command: str):
        """Log tool command"""
        if self.current_session:
            event = Event(
                event_type=EventType.TOOL_COMMAND,
                timestamp=datetime.now().isoformat(),
                content=command,
                tool_name=tool_name
            )
            self.current_session.events.append(event)
    
    def log_tool_output(self, tool_name: str, output: str):
        """Log tool output"""
        if self.current_session:
            event = Event(
                event_type=EventType.TOOL_OUTPUT,
                timestamp=datetime.now().isoformat(),
                content=output,
                tool_name=tool_name
            )
            self.current_session.events.append(event)
    
    def save_session(self) -> bool:
        """Save session - Don't save if no events"""
        if not self.current_session:
            return False
        
        # Don't save if no events
        if not self.current_session.events or len(self.current_session.events) == 0:
            print(f"Session {self.current_session.session_id} has no events, skipping save.")
            return False
        
        try:
            file_path = self._get_session_file_path(self.current_session.session_id)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.current_session.to_dict(), f, indent=2, ensure_ascii=False)
            print(f"Session {self.current_session.session_id} saved with {len(self.current_session.events)} events.")
            return True
        except Exception as e:
            print(f"Failed to save session: {e}")
            return False
    
    def end_session(self) -> Optional[str]:
        """End session"""
        if not self.current_session:
            return None
        
        session_id = self.current_session.session_id
        self.save_session()
        self.current_session = None
        return session_id
    
    def load_session(self, session_id: str) -> Optional[Session]:
        """Load session"""
        try:
            for session_file in self.base_path.rglob(f"session_{session_id}.json"):
                if session_file.exists():
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    return Session.from_dict(session_data)
            return None
        except Exception as e:
            print(f"Failed to load session {session_id}: {e}")
            return None
    
    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve session list"""
        sessions = []
        
        try:
            for session_file in self.base_path.rglob("session_*.json"):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    
                    # Extract basic information only
                    session_info = {
                        'session_id': session_data['session_id'],
                        'start_time': session_data['start_time'],
                        'event_count': len(session_data.get('events', [])),
                        'file_path': str(session_file)
                    }
                    
                    # Add model information (if available)
                    if session_data.get('model'):
                        session_info['model'] = session_data['model']
                    
                    # Generate preview with first user input
                    events = session_data.get('events', [])
                    preview = "No user input found"
                    for event in events:
                        if event.get('event_type') == 'user_input':
                            preview = event.get('content', '')[:100]
                            if len(preview) < len(event.get('content', '')):
                                preview += "..."
                            break
                    
                    session_info['preview'] = preview
                    sessions.append(session_info)
                    
                except Exception as e:
                    continue
            
            # Sort by time (newest first)
            sessions.sort(key=lambda x: x['start_time'], reverse=True)
            
        except Exception as e:
            print(f"Error listing sessions: {e}")
        
        return sessions[:limit]

# Global instance
_logger: Optional[Logger] = None

def get_logger() -> Logger:
    """Return global logger instance"""
    global _logger
    if _logger is None:
        _logger = Logger()
    return _logger
