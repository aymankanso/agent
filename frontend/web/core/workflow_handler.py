
import streamlit as st
import asyncio
from typing import Dict, Any, List, Optional, Callable
import os
import sys

# Add project root path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from frontend.web.core.message_processor import MessageProcessor
from frontend.web.core.executor_manager import get_executor_manager
from src.utils.memory import clear_thread_checkpoint


class WorkflowHandler:
    """Workflow Execution Handler - Pure Business Logic"""
    
    # Message history limits
    MAX_STRUCTURED_MESSAGES = 20  # Keep last 20 messages in UI
    MAX_EVENT_HISTORY = 50  # Keep last 50 events
    
    def __init__(self):
        """Initialize workflow handler"""
        self.message_processor = MessageProcessor()
        self.executor_manager = get_executor_manager()
    
    def _trim_message_history(self):
        """Trim message history to prevent memory bloat
        
        Keeps only recent messages while preserving conversation flow.
        This prevents LangGraph state from growing too large after multiple turns.
        """
        # Count conversation turns (user messages)
        user_message_count = sum(1 for msg in st.session_state.structured_messages if msg.get("type") == "user")
        
        # After 30+ conversation turns, aggressively clear checkpoint to prevent memory corruption
        if user_message_count >= 30:
            thread_id = st.session_state.thread_config.get("configurable", {}).get("thread_id")
            if thread_id:
                clear_thread_checkpoint(thread_id)
                if st.session_state.debug_mode:
                    print(f"🧹 Cleared LangGraph checkpoint for thread {thread_id} (30+ turns)")
        
        # After 40+ conversation turns, suggest creating new chat
        if user_message_count >= 40:
            st.warning(
                "💡 **Tip**: You've had 40+ conversation turns. "
                "For optimal performance, consider clicking '✨ New Chat' in the sidebar to start fresh. "
                "This prevents memory bloat and keeps responses fast."
            )
        
        # Trim structured messages (UI display)
        if len(st.session_state.structured_messages) > self.MAX_STRUCTURED_MESSAGES:
            # Keep the most recent messages
            st.session_state.structured_messages = st.session_state.structured_messages[-self.MAX_STRUCTURED_MESSAGES:]
            if st.session_state.debug_mode:
                print(f"📉 Trimmed structured_messages to {self.MAX_STRUCTURED_MESSAGES} most recent")
        
        # Trim event history
        if len(st.session_state.event_history) > self.MAX_EVENT_HISTORY:
            st.session_state.event_history = st.session_state.event_history[-self.MAX_EVENT_HISTORY:]
            if st.session_state.debug_mode:
                print(f"📉 Trimmed event_history to {self.MAX_EVENT_HISTORY} most recent")
    
    def validate_execution_state(self) -> Dict[str, Any]:
        """Validate if execution is possible
        
        Returns:
            Dict: {"can_execute": bool, "error_message": str}
        """
        if not self.executor_manager.is_ready():
            return {
                "can_execute": False,
                "error_message": "AI agents not ready. Please initialize first."
            }
        
        if st.session_state.workflow_running:
            return {
                "can_execute": False,
                "error_message": "Another workflow is already running. Please wait."
            }
        
        return {"can_execute": True, "error_message": ""}
    
    def prepare_user_input(self, user_input: str) -> Dict[str, Any]:
        """Prepare user input for workflow
        
        Args:
            user_input: User input text
            
        Returns:
            Dict: Processed user message
        """
        # Trim message history before adding new message
        self._trim_message_history()
        
        user_message = self.message_processor._create_user_message(user_input)
        st.session_state.structured_messages.append(user_message)
        return user_message
    
    async def execute_workflow_logic(
        self, 
        user_input: str,
        ui_callbacks: Dict[str, Callable] = None,
        terminal_ui = None
    ) -> Dict[str, Any]:
        """Workflow execution core logic
        
        Args:
            user_input: User input text
            ui_callbacks: UI callback functions
            
        Returns:
            Dict: Execution result
        """
        # Set UI callback defaults
        if ui_callbacks is None:
            ui_callbacks = {}
        
        # Set workflow running state
        st.session_state.workflow_running = True
        
        execution_result = {
            "success": False,
            "event_count": 0,
            "agent_activity": {},
            "error_message": "",
            "terminal_ui": terminal_ui  # Store terminal UI instance
        }
        
        try:
            event_count = 0
            agent_activity = {}
            last_event_time = asyncio.get_event_loop().time()
            max_idle_time = 3600  # 60 minutes without events = timeout (increased from 15 min)
            
            # Store async generator for proper cleanup
            workflow_stream = None
            try:
                workflow_stream = self.executor_manager.execute_workflow(
                    user_input,
                    config=st.session_state.thread_config
                )
                
                async for event in workflow_stream:
                    # Check if workflow was stopped
                    if not st.session_state.workflow_running:
                        break
                    
                    # Check for idle timeout
                    current_time = asyncio.get_event_loop().time()
                    if current_time - last_event_time > max_idle_time:
                        execution_result["error_message"] = (
                            f"⏱️ Workflow timeout: No activity for {max_idle_time/60:.0f} minutes. "
                            "The agent may be stuck on a slow tool or infinite loop. "
                            "Try clicking 'New Chat' and using faster tools."
                        )
                        break
                    
                    event_count += 1
                    last_event_time = current_time  # Reset timer on each event
                    st.session_state.event_history.append(event)
                    
                    try:
                        # Process event
                        success = await self._process_event_logic(
                            event, 
                            agent_activity,
                            ui_callbacks,
                            terminal_ui
                        )
                        
                        if not success:
                            break
                        
                        # Update agent status (pure logic)
                        self._update_agent_status_logic()
                        
                    except Exception as e:
                        if st.session_state.debug_mode:
                            execution_result["error_message"] = f"Event processing error: {str(e)}"
            
            finally:
                # Properly close async generator
                if workflow_stream is not None:
                    try:
                        await workflow_stream.aclose()
                    except (StopAsyncIteration, GeneratorExit, RuntimeError, AttributeError):
                        pass  # Normal cleanup - ignore all expected exceptions
            
            # Set execution result
            execution_result.update({
                "success": True,
                "event_count": event_count,
                "agent_activity": agent_activity
            })
        
        except Exception as e:
            execution_result["error_message"] = f"Workflow execution error: {str(e)}"
            
            # If error is about invalid chat history, suggest creating new chat
            if "INVALID_CHAT_HISTORY" in str(e) or "tool_calls that do not have a corresponding ToolMessage" in str(e):
                execution_result["error_message"] = (
                    "⚠️ Chat history corruption detected. "
                    "This happens when a previous agent handoff was interrupted. "
                    "Please click '✨ New Chat' in the sidebar to start fresh."
                )
        
        finally:
            st.session_state.workflow_running = False
            # Auto-save session
            if "logger" in st.session_state and st.session_state.logger:
                st.session_state.logger.save_session()
        
        return execution_result
    
    async def _process_event_logic(
        self,
        event: Dict[str, Any],
        agent_activity: Dict[str, int],
        ui_callbacks: Dict[str, Callable],
        terminal_ui = None
    ) -> bool:
        """Event processing pure logic
        
        Args:
            event: Event to process
            agent_activity: Agent activity tracking
            ui_callbacks: UI callback functions
            
        Returns:
            bool: Processing success
        """
        event_type = event.get("type", "")
        
        if event_type == "message":
            return await self._process_message_event_logic(
                event, agent_activity, ui_callbacks, terminal_ui
            )
        elif event_type == "workflow_complete":
            if "on_workflow_complete" in ui_callbacks:
                ui_callbacks["on_workflow_complete"]()
            return True
        elif event_type == "error":
            error_msg = event.get("error", "Unknown error")
            if "on_error" in ui_callbacks:
                ui_callbacks["on_error"](error_msg)
            return False
        
        return True
    
    async def _process_message_event_logic(
        self,
        event: Dict[str, Any],
        agent_activity: Dict[str, int],
        ui_callbacks: Dict[str, Callable],
        terminal_ui = None
    ) -> bool:
        """Message event processing pure logic"""
        # Convert message
        frontend_message = self.message_processor.process_cli_event(event)
        
        # Check for duplicate message
        if self.message_processor.is_duplicate_message(
            frontend_message, st.session_state.structured_messages
        ):
            return True
        
        # Save message
        st.session_state.structured_messages.append(frontend_message)
        
        # Logging
        self._log_message_event(event, frontend_message)
        
        # Track agent activity
        agent_name = event.get("agent_name", "Unknown")
        if agent_name not in agent_activity:
            agent_activity[agent_name] = 0
        agent_activity[agent_name] += 1
        
        # Call UI callback (display message)
        if "on_message_ready" in ui_callbacks:
            ui_callbacks["on_message_ready"](frontend_message)
        
        # Process terminal message - unified approach
        if frontend_message.get("type") == "tool":
            # Handle with terminal message logic (save to session_state)
            self._process_terminal_message_logic(frontend_message, ui_callbacks)
        
        return True
    
    def _process_terminal_message_logic(
        self, 
        frontend_message: Dict[str, Any], 
        ui_callbacks: Dict[str, Callable]
    ):
        """Terminal message processing pure logic - immediate processing approach"""
        from frontend.web.core.terminal_processor import get_terminal_processor
        from datetime import datetime
        
        # Debug log
        tool_name = frontend_message.get("tool_display_name", "Tool")
        content = frontend_message.get("content", "")
        print(f"[DEBUG] Processing terminal message: {tool_name} - Content length: {len(content) if content else 0}")
        
        # Add directly to terminal history
        terminal_processor = get_terminal_processor()
        
        # Add command entry
        terminal_processor.update_terminal_history([{
            "type": "command",
            "content": tool_name,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }])
        
        # Add output entry
        if content:
            # HTML escape processing
            escaped_content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            escaped_content = escaped_content.replace("\n", "<br>")
            
            terminal_processor.update_terminal_history([{
                "type": "output",
                "content": escaped_content,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }])
            
        print(f"[DEBUG] Terminal history now has {len(terminal_processor.get_terminal_history())} entries")
    
    def _log_message_event(self, event: Dict[str, Any], frontend_message: Dict[str, Any]):
        """Message event logging logic"""
        if "logger" not in st.session_state or not st.session_state.logger:
            return
        
        logger = st.session_state.logger
        agent_name = event.get("agent_name", "Unknown")
        message_type = event.get("message_type", "unknown")
        content = event.get("content", "")
        
        if message_type == "ai":
            logger.log_agent_response(
                agent_name=agent_name,
                content=content,
                tool_calls=frontend_message.get("tool_calls")
            )
        elif message_type == "tool":
            tool_name = event.get("tool_name", "Unknown Tool")
            if "command" in event:  # Tool command
                logger.log_tool_command(
                    tool_name=tool_name,
                    command=event.get("command", content)
                )
            else:  # Tool output
                logger.log_tool_output(
                    tool_name=tool_name,
                    output=content
                )
    
    def _update_agent_status_logic(self):
        """Agent status update pure logic"""
        # Find active agent from recent events
        active_agent = None
        for event in reversed(st.session_state.event_history):
            if event.get("type") == "message" and event.get("message_type") == "ai":
                agent_name = event.get("agent_name")
                if agent_name and agent_name != "Unknown":
                    active_agent = agent_name.lower()
                    break
        
        # Update active agent
        if active_agent and active_agent != st.session_state.active_agent:
            if st.session_state.active_agent and st.session_state.active_agent not in st.session_state.completed_agents:
                st.session_state.completed_agents.append(st.session_state.active_agent)
            
            st.session_state.active_agent = active_agent
        
        # Update initial UI state
        if st.session_state.get("keep_initial_ui", True) and (
            st.session_state.active_agent or st.session_state.completed_agents
        ):
            st.session_state.keep_initial_ui = False
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Return current agent status"""
        return {
            "active_agent": st.session_state.active_agent,
            "completed_agents": st.session_state.completed_agents,
            "keep_initial_ui": st.session_state.get("keep_initial_ui", True)
        }


# Global workflow handler instance
_workflow_handler = None

def get_workflow_handler() -> WorkflowHandler:
    """Return workflow handler singleton instance"""
    global _workflow_handler
    if _workflow_handler is None:
        _workflow_handler = WorkflowHandler()
    return _workflow_handler