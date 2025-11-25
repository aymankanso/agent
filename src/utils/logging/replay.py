"""
Simple replay system - Plays back in the same way as existing workflow
"""

import streamlit as st
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from src.utils.logging.logger import get_logger, Session

class ReplaySystem:
    """Replay system - Plays back like existing workflow without additional UI"""
    
    def __init__(self):
        self.logger = get_logger()
    
    def start_replay(self, session_id: str) -> bool:
        """Start replay - Completely replace existing messages to prevent duplicate output"""
        try:
            # Load session
            session = self.logger.load_session(session_id)
            if not session:
                return False
            
            # Set replay mode
            st.session_state.replay_mode = True
            st.session_state.replay_session = session
            st.session_state.replay_session_id = session_id
            
            # Backup existing messages (for restoration after replay completion)
            if "frontend_messages" in st.session_state:  # ✅ Correct variable name
                st.session_state.backup_frontend_messages = st.session_state.frontend_messages.copy()
            else:
                st.session_state.backup_frontend_messages = []
            
            # Backup existing terminal messages
            if "terminal_messages" in st.session_state:
                st.session_state.backup_terminal_messages = st.session_state.terminal_messages.copy()
            else:
                st.session_state.backup_terminal_messages = []
            
            # Backup existing event history
            if "event_history" in st.session_state:
                st.session_state.backup_event_history = st.session_state.event_history.copy()
            else:
                st.session_state.backup_event_history = []
            
            # Backup agent state
            st.session_state.backup_active_agent = st.session_state.get("active_agent")
            st.session_state.backup_completed_agents = st.session_state.get("completed_agents", []).copy()
            
            # 🔥 Prevent duplicate output: Completely initialize existing messages when starting replay
            st.session_state.frontend_messages = []  # ✅ Correct variable name
            st.session_state.terminal_messages = []
            st.session_state.event_history = []
            st.session_state.active_agent = None
            st.session_state.completed_agents = []
            
            return True
            
        except Exception as e:
            return False
    
    def stop_replay(self):
        """Stop replay - Keep only replayed messages (don't restore existing messages)"""
        st.session_state.replay_mode = False
        
        # Set replay completion flag
        st.session_state.replay_completed = True
        
        # Keep replayed agent state (to show replayed agents)
        # Don't restore backed-up agent state
        
        # Delete backup data (don't restore)
        for backup_key in ["backup_frontend_messages", "backup_terminal_messages", 
                          "backup_event_history", "backup_active_agent", "backup_completed_agents"]:
            if backup_key in st.session_state:
                del st.session_state[backup_key]
        
        # Clean up replay-related state
        for key in ["replay_session", "replay_session_id"]:
            if key in st.session_state:
                del st.session_state[key]
    
    def is_replay_mode(self) -> bool:
        """Check if in replay mode"""
        return st.session_state.get("replay_mode", False)
    
    async def execute_replay(self, chat_area, agents_container, chat_ui):
        """Execute replay - Process all messages at once (remove sequential output)"""
        session = st.session_state.get("replay_session")
        if not session or not session.events:
            return
        
        # Replay start message
        with st.status("Loading replay session...", expanded=True) as status:
            
            # Convert all events at once
            replay_messages = []
            terminal_messages = []
            agents_involved = set()
            
            # Process all events at once
            for event in session.events:
                try:
                    # Convert event to frontend message
                    frontend_message = self._convert_to_frontend_message(event)
                    
                    if frontend_message:
                        # Collect messages
                        replay_messages.append(frontend_message)
                        
                        # Also collect in terminal messages if tool message
                        if frontend_message.get("type") == "tool":
                            terminal_messages.append(frontend_message)
                        
                        # Collect agent information
                        if event.agent_name:
                            agents_involved.add(event.agent_name)
                        
                except Exception as e:
                    print(f"Error processing event: {e}")
                    continue
            
            # Set messages to session state at once (replace existing messages)
            if replay_messages:
                st.session_state.frontend_messages = replay_messages  # ✅ Correct variable name
            
            # Also set terminal messages at once (replace existing messages)
            if terminal_messages:
                st.session_state.terminal_messages = terminal_messages
            
            # Update agent state (activate last agent)
            if agents_involved:
                completed_agents = list(agents_involved)[:-1] if len(agents_involved) > 1 else []
                active_agent = list(agents_involved)[-1].lower() if agents_involved else None
                
                st.session_state.completed_agents = completed_agents
                st.session_state.active_agent = active_agent
            
            # Complete
            status.update(label=f"✅ Replay Complete! Loaded {len(replay_messages)} messages from {len(session.events)} events.", state="complete")
    
    def _convert_to_frontend_message(self, event) -> Optional[Dict[str, Any]]:
        """Convert event to frontend message - Same format as normal workflow"""
        timestamp = datetime.now().isoformat()
        
        if event.event_type.value == "user_input":
            return {
                "type": "user",
                "content": event.content,
                "timestamp": timestamp
            }
        
        elif event.event_type.value == "agent_response":
            # Same AI message format as normal workflow
            frontend_message = {
                "type": "ai",  # Same as normal workflow
                "agent_id": event.agent_name.lower() if event.agent_name else "agent",
                "display_name": event.agent_name or "Agent",
                "avatar": self._get_agent_avatar(event.agent_name),
                "content": event.content,  # Same as normal format
                "timestamp": timestamp,
                "id": f"replay_agent_{event.agent_name}_{timestamp}"
            }
            
            # Restore tool_calls information (if stored in event)
            if hasattr(event, 'tool_calls') and event.tool_calls:
                frontend_message["tool_calls"] = event.tool_calls
            
            return frontend_message
        
        elif event.event_type.value == "tool_command":
            # Tool command - Same as normal tool message format
            return {
                "type": "tool",
                "tool_display_name": event.tool_name or "Tool",
                "content": f"Command: {event.content}",
                "timestamp": timestamp,
                "id": f"replay_tool_cmd_{event.tool_name}_{timestamp}"
            }
        
        elif event.event_type.value == "tool_output":
            # Tool output - Same as normal tool message format
            return {
                "type": "tool",
                "tool_display_name": event.tool_name or "Tool Output",
                "content": event.content,
                "timestamp": timestamp,
                "id": f"replay_tool_out_{event.tool_name}_{timestamp}"
            }
        
        return None
    

    
    def _get_agent_avatar(self, agent_name: str) -> str:
        """Return agent avatar"""
        if not agent_name:
            return "🤖"
        
        agent_avatars = {
            "supervisor": "👨‍💼",
            "planner": "🧠",
            "reconnaissance": "🔍",
            "initial_access": "🔑",
            "summary": "📋"
        }
        
        agent_key = agent_name.lower()
        for key, avatar in agent_avatars.items():
            if key in agent_key:
                return avatar
        
        return "🤖"

# Global instance
_replay_system: Optional[ReplaySystem] = None

def get_replay_system() -> ReplaySystem:
    """Return global replay system instance"""
    global _replay_system
    if _replay_system is None:
        _replay_system = ReplaySystem()
    return _replay_system
