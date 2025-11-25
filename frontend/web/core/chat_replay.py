"""
Chat screen automatic session replay feature (simplified)
Optimized for placeholder-based terminal UI
"""

import streamlit as st
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

from src.utils.logging.replay import get_replay_system
from frontend.web.core.message_processor import MessageProcessor

class ReplayManager:
    """Auto-replay manager - simplified terminal UI applied"""
    
    def __init__(self):
        self.replay_system = get_replay_system()
        self.message_processor = MessageProcessor()
    
    def is_replay_mode(self) -> bool:
        """Check if in replay mode"""
        return st.session_state.get("replay_mode", False)
    
    def handle_replay_in_main_app(self, chat_area, agents_container, chat_ui, terminal_ui) -> bool:
        """Handle replay in main app - duplicate calls removed"""
        if not self.is_replay_mode():
            return False
        
        replay_session_id = st.session_state.get("replay_session_id")
        if not replay_session_id:
            return False
        
        try:
            # Call ReplaySystem.start_replay() directly (handles load_session internally)
            if self.replay_system.start_replay(replay_session_id):
                # Execute simplified replay
                # Use existing event loop or create new one for Windows compatibility
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                loop.run_until_complete(self._execute_replay_simplified(chat_area, agents_container, chat_ui, terminal_ui))
                
                # Clean up after replay
                self.replay_system.stop_replay()
                
                return True
            else:
                st.error(f"Session {replay_session_id} not found.")
                return False
            
        except Exception as e:
            st.error(f"Replay error: {e}")
            # Exit replay mode on error
            self.replay_system.stop_replay()
        
        return False
    
    async def _execute_replay_simplified(self, chat_area, agents_container, chat_ui, terminal_ui):
        """Execute simplified replay - get data from session state"""
        # Session data already saved to session state by ReplaySystem.start_replay()
        session = st.session_state.get("replay_session")
        if not session or not session.events:
            st.error("No session data to replay.")
            return
        
        # Replay start message
        with st.status("🎬 Replaying session...", expanded=True) as status:
            
            replay_messages = []
            terminal_messages = []
            event_history = []
            agent_activity = {}
            
            status.update(label=f"Processing {len(session.events)} events...", state="running")
            
            # Process events
            for i, event in enumerate(session.events):
                try:
                    # Convert event to Executor-style event
                    executor_event = self._convert_to_executor_event(event)
                    
                    if executor_event:
                        # Convert to frontend message using MessageProcessor
                        frontend_message = self.message_processor.process_cli_event(executor_event)
                        
                        # Check for duplicates
                        if not self.message_processor.is_duplicate_message(
                            frontend_message, replay_messages
                        ):
                            replay_messages.append(frontend_message)
                            
                            # For tool messages, add to terminal messages as well
                            if frontend_message.get("type") == "tool":
                                terminal_messages.append(frontend_message)
                            
                            event_history.append(executor_event)
                            
                            # Track agent activity
                            agent_name = executor_event.get("agent_name", "Unknown")
                            if agent_name not in agent_activity:
                                agent_activity[agent_name] = 0
                            agent_activity[agent_name] += 1
                    
                    # Update progress
                    if (i + 1) % 10 == 0:
                        status.update(label=f"Processed {i + 1}/{len(session.events)} events...", state="running")
                        
                except Exception as e:
                    print(f"Error processing event {i}: {e}")
                    continue
            
            # Set messages to session state
            st.session_state.frontend_messages = replay_messages
            st.session_state.structured_messages = replay_messages
            st.session_state.terminal_messages = terminal_messages
            st.session_state.event_history = event_history
            
            # Display replayed messages in chat_area
            if replay_messages:
                # Display all messages at once to prevent rerun issues
                with chat_area:
                    for message in replay_messages:
                        message_type = message.get("type", "")
                        if message_type == "user":
                            chat_ui.display_user_message(message)
                        elif message_type == "ai":
                            chat_ui.display_agent_message(message, streaming=False)  # Disable streaming for replay
                        elif message_type == "tool":
                            chat_ui.display_tool_message(message)
            
            # Terminal UI processing (simplified)
            if terminal_ui and terminal_messages:
                try:
                    # Initialize terminal
                    terminal_ui.clear_terminal()
                    
                    # Process terminal messages - simplified approach
                    terminal_ui.process_structured_messages(terminal_messages)
                    
                    # Debug info
                    if st.session_state.get("debug_mode", False):
                        print(f"🎬 Replay: {len(terminal_messages)} terminal messages processed")
                    
                except Exception as term_error:
                    st.error(f"Terminal processing error during replay: {term_error}")
                    print(f"Terminal processing error during replay: {term_error}")
            
            # Update agent status
            if agent_activity:
                completed_agents = []
                active_agent = None
                
                agent_list = list(agent_activity.keys())
                if len(agent_list) > 1:
                    completed_agents = [agent.lower() for agent in agent_list[:-1]]
                    active_agent = agent_list[-1].lower()
                elif len(agent_list) == 1:
                    active_agent = agent_list[0].lower()
                
                st.session_state.completed_agents = completed_agents
                st.session_state.active_agent = active_agent
                
                # Display agent status
                if hasattr(chat_ui, 'display_agent_status'):
                    chat_ui.display_agent_status(
                        agents_container,
                        active_agent,
                        None,
                        completed_agents
                    )
            
            # Show replay completion
            st.session_state.replay_completed = True
            
            # Complete
            status.update(
                label=f"✅ Replay Complete! Loaded {len(replay_messages)} messages, {len(terminal_messages)} terminal events, {len(agent_activity)} agents", 
                state="complete"
            )
    
    def _convert_to_executor_event(self, event) -> Optional[Dict[str, Any]]:
        """Convert event to Executor-style event"""
        timestamp = datetime.now().isoformat()
        
        if event.event_type.value == "user_input":
            return {
                "type": "message",
                "message_type": "user",
                "agent_name": "User",
                "content": event.content,
                "timestamp": timestamp
            }
        
        elif event.event_type.value == "agent_response":
            executor_event = {
                "type": "message",
                "message_type": "ai",
                "agent_name": event.agent_name or "Agent",
                "content": event.content,
                "timestamp": timestamp
            }
            
            # Restore tool calls info
            if hasattr(event, 'tool_calls') and event.tool_calls:
                executor_event["tool_calls"] = event.tool_calls
            
            return executor_event
        
        elif event.event_type.value == "tool_command":
            return {
                "type": "message",
                "message_type": "tool",
                "agent_name": "Tool",
                "tool_name": event.tool_name or "Unknown Tool",
                "content": f"Command: {event.content}",
                "timestamp": timestamp
            }
        
        elif event.event_type.value == "tool_output":
            return {
                "type": "message",
                "message_type": "tool",
                "agent_name": "Tool",
                "tool_name": event.tool_name or "Tool Output",
                "content": event.content,
                "timestamp": timestamp
            }
        
        return None
