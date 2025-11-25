"""
Chat Message Rendering Component (refactored - pure UI logic)
Responsible for pure UI rendering only, including message display and typing animation
"""

import streamlit as st
import re
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from frontend.web.utils.constants import CSS_PATH_CHAT_UI, CSS_PATH_AGENT_STATUS
from src.utils.agents import AgentManager


class ChatMessagesComponent:
    """Chat Message Rendering Component"""
    
    def __init__(self):
        """Initialize component"""
        self._setup_styles()
        # Message unique ID counter
        if "message_counter" not in st.session_state:
            st.session_state.message_counter = 0
    
    def _setup_styles(self):
        """Setup CSS styles"""
        try:
            # Load chat UI CSS
            with open(CSS_PATH_CHAT_UI, "r", encoding="utf-8") as f:
                chat_css = f.read()
            st.html(f"<style>{chat_css}</style>")
            
            # Load agent status CSS
            with open(CSS_PATH_AGENT_STATUS, "r", encoding="utf-8") as f:
                agent_status_css = f.read()
            st.html(f"<style>{agent_status_css}</style>")
            
        except Exception as e:
            print(f"Error loading CSS: {e}")
    
    
    def simulate_typing(self, text: str, placeholder, speed: float = 0.005):
        """Simulate typing animation
        
        Args:
            text: Text to display
            placeholder: Streamlit placeholder
            speed: Typing speed
        """
        # Find code block positions
        code_blocks = []
        code_block_pattern = r'```.*?```'
        for match in re.finditer(code_block_pattern, text, re.DOTALL):
            code_blocks.append((match.start(), match.end()))
        
        result = ""
        i = 0
        chars_per_update = 5  # Performance optimization
        
        while i < len(text):
            # Check if current position is inside code block
            code_block_to_add = None
            
            for start, end in code_blocks:
                if i == start:
                    code_block_to_add = text[start:end]
                    break
                elif start < i < end:
                    i += 1
                    continue
            
            if code_block_to_add:
                result += code_block_to_add
                i = end
                placeholder.markdown(result)
                time.sleep(speed * 2)
            else:
                end_pos = min(i + chars_per_update, len(text))
                
                # Add only up to next code block
                for block_start, _ in code_blocks:
                    if block_start > i:
                        end_pos = min(end_pos, block_start)
                        break
                
                result += text[i:end_pos]
                i = end_pos
                
                placeholder.markdown(result)
                time.sleep(speed)
    
    def display_messages(self, structured_messages: List[Dict[str, Any]], container=None):
        """Display structured message list in UI
        
        Args:
            structured_messages: List of messages to display
            container: Container to display in (default: st)
        """
        if container is None:
            container = st
            
        for message in structured_messages:
            message_type = message.get("type", "")
            
            if message_type == "user":
                self.display_user_message(message, container)
            elif message_type == "ai":
                self.display_agent_message(message, container, streaming=False)
            elif message_type == "tool":
                self.display_tool_message(message, container)
    
    def display_user_message(self, message: Dict[str, Any], container=None):
        """Display user message UI
        
        Args:
            message: User message data
            container: Container to display in
        """
        if container is None:
            container = st
            
        content = message.get("content", "")
        
        with container.chat_message("user"):
            st.markdown(f'<div style="text-align: left;">{content}</div>', unsafe_allow_html=True)
    
    def display_agent_message(self, message: Dict[str, Any], container=None, streaming: bool = True):
        """Display AI agent message UI
        
        Args:
            message: Agent message data
            container: Container to display in
            streaming: Whether in streaming mode
        """
        if container is None:
            container = st
            
        display_name = message.get("display_name", "Agent")
        avatar = message.get("avatar", "🤖")
        
        # Compatible with both replay system and general system
        if "data" in message and isinstance(message["data"], dict):
            content = message["data"].get("content", "")
            tool_calls = message.get("tool_calls", [])
        else:
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])
        
        # Generate agent color and class
        namespace = message.get("namespace", "")
        if namespace:
            if isinstance(namespace, str):
                namespace_list = [namespace]
            else:
                namespace_list = namespace
            
            from src.utils.message import get_agent_name
            agent_name_for_color = get_agent_name(namespace_list)
            if agent_name_for_color == "Unknown":
                agent_name_for_color = display_name
        else:
            agent_name_for_color = display_name
        
        agent_color = AgentManager.get_frontend_color(agent_name_for_color)
        agent_class = AgentManager.get_css_class(agent_name_for_color)
        
        # Generate unique message ID
        st.session_state.message_counter += 1
        
        # Display message
        with container.chat_message("assistant", avatar=avatar):
            # Agent header
            st.markdown(
                f'<div class="agent-header {agent_class}"><strong style="color: {agent_color}">{display_name}</strong></div>', 
                unsafe_allow_html=True
            )
            
            # Display content
            if content:
                text_placeholder = st.empty()
                
                # Disable typing animation in replay mode
                is_replay_mode = st.session_state.get("replay_mode", False)
                if streaming and len(content) > 50 and not is_replay_mode:
                    self.simulate_typing(content, text_placeholder, speed=0.005)
                else:
                    text_placeholder.write(content)
            elif not tool_calls:
                st.write("No content available")
            
            # Display tool calls information
            if tool_calls:
                for i, tool_call in enumerate(tool_calls):
                    self._display_tool_call(tool_call)
    
    def _display_tool_call(self, tool_call: Dict[str, Any]):
        """Display tool call information
        
        Args:
            tool_call: Tool call data
        """
        tool_name = tool_call.get("name", "Unknown Tool")
        tool_args = tool_call.get("args", {})
        
        # Generate tool call message
        try:
            from src.utils.message import parse_tool_call
            tool_call_message = parse_tool_call(tool_call)
        except Exception as e:
            tool_call_message = f"Tool call error: {str(e)}"
        
        # Expandable UI
        with st.expander(f"**{tool_call_message}**", expanded=False):
            col1, col2 = st.columns([1, 3])
            
            with col1:
                st.markdown("**Tool:**")
                st.markdown("**ID:**")
                if tool_args:
                    st.markdown("**Arguments:**")
            
            with col2:
                st.markdown(f"`{tool_name}`")
                st.markdown(f"`{tool_call.get('id', 'N/A')}`")
                if tool_args:
                    import json
                    st.code(json.dumps(tool_args, indent=2), language="json")
                else:
                    st.markdown("`No arguments`")
    
    def display_tool_message(self, message: Dict[str, Any], container=None):
        """Display tool message UI
        
        Args:
            message: Tool message data
            container: Container to display in
        """
        if container is None:
            container = st
            
        tool_display_name = message.get("tool_display_name", "Tool")
        content = message.get("content", "")
        
        # Use tool color
        tool_color = AgentManager.get_frontend_color("tool")
        tool_class = "tool-message"
        
        # Generate unique message ID
        st.session_state.message_counter += 1
        
        # Display message
        with container.chat_message("tool", avatar="🔧"):
            # Tool header
            st.markdown(
                f'<div class="agent-header {tool_class}"><strong style="color: {tool_color}">{tool_display_name}</strong></div>', 
                unsafe_allow_html=True
            )
            
            # Display content
            if content:
                # Limit long output
                if len(content) > 5000:
                    st.code(content[:5000] + "\n[Output truncated...]")
                    with st.expander("More.."):
                        st.text(content)
                else:
                    st.code(content)
    
    def show_processing_status(self, label: str = "Processing...", expanded: bool = True):
        """Display processing status
        
        Args:
            label: Status label
            expanded: Whether to expand
            
        Returns:
            Streamlit status object
        """
        return st.status(label, expanded=expanded)
    
    def display_loading_message(self, message: str = "Loading..."):
        """Display loading message
        
        Args:
            message: Loading message
        """
        with st.spinner(message):
            time.sleep(0.1)  # Minimum display time
    
    def display_error_message(self, error_msg: str):
        """Display error message
        
        Args:
            error_msg: Error message
        """
        st.error(error_msg)
    
    def display_success_message(self, success_msg: str):
        """Display success message
        
        Args:
            success_msg: Success message
        """
        st.success(success_msg)
    
    def display_warning_message(self, warning_msg: str):
        """Display warning message
        
        Args:
            warning_msg: Warning message
        """
        st.warning(warning_msg)
    
    def display_info_message(self, info_msg: str):
        """Display info message
        
        Args:
            info_msg: Info message
        """
        st.info(info_msg)
