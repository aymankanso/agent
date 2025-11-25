"""
Terminal UI Component (refactored - pure UI logic)
Responsible for terminal screen rendering, floating functionality and other pure UI only
"""

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from typing import Dict, Any, List, Optional
from frontend.web.utils.constants import (
    CSS_PATH_TERMINAL,
    CSS_CLASS_TERMINAL_CONTAINER,
    CSS_CLASS_MAC_TERMINAL_HEADER
)


class TerminalUIComponent:
    """Terminal UI Rendering Component"""
    
    def __init__(self):
        """Initialize component"""
        self.placeholder = None
    
    def apply_terminal_css(self):
        """Apply terminal CSS styles"""
        try:
            with open(CSS_PATH_TERMINAL, "r", encoding="utf-8") as f:
                css = f.read()
                st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
        except Exception as e:
            print(f"Error loading terminal CSS: {e}")
    
    def create_terminal_header(self) -> str:
        """Generate Mac-style terminal header HTML
        
        Returns:
            str: Terminal header HTML
        """
        return '''
        <div class="mac-terminal-header">
            <div class="mac-buttons">
                <div class="terminal-header-button red"></div>
                <div class="terminal-header-button yellow"></div>
                <div class="terminal-header-button green"></div>
            </div>
        </div>
        '''
    
    def create_terminal(self, container):
        """Create terminal container
        
        Args:
            container: Streamlit container
            
        Returns:
            Streamlit placeholder
        """
        # Display Mac-style header
        container.markdown(self.create_terminal_header(), unsafe_allow_html=True)
        
        # Create terminal container
        self.placeholder = container.empty()
        
        return self.placeholder
    
    def render_terminal_display(self, terminal_history: List[Dict[str, Any]]):
        """Render terminal display
        
        Args:
            terminal_history: Terminal history list
        """
        if not self.placeholder:
            return
        
        terminal_content = ""
        for entry in terminal_history:
            entry_type = entry.get("type", "output")
            content = entry.get("content", "")
            
            if entry_type == "command":
                # Command display format
                terminal_content += (
                    f'<div class="terminal-prompt">'
                    f'<span class="terminal-user">root@kali</span>'
                    f'<span class="terminal-prompt-text">:~$ </span>'
                    f'<span class="terminal-command-text">{content}</span>'
                    f'</div>'
                )
            elif entry_type == "output":
                terminal_content += f'<div class="terminal-output">{content}</div>'
        
        # Add cursor
        terminal_content += (
            '<div class="terminal-prompt">'
            '<span class="terminal-user">root@kali</span>'
            '<span class="terminal-prompt-text">:~$ </span>'
            '<span class="terminal-cursor"></span>'
            '</div>'
        )
        
        # Generate terminal container HTML
        terminal_html = f'''
        <div class="{CSS_CLASS_TERMINAL_CONTAINER}" id="terminal-container">
            {terminal_content}
        </div>
        <script type="text/javascript">
        (function() {{
            const terminal = document.getElementById('terminal-container');
            if (terminal) {{
                terminal.scrollTop = terminal.scrollHeight;
            }}
        }})();
        </script>
        '''
        
        # Apply HTML to placeholder
        self.placeholder.markdown(terminal_html, unsafe_allow_html=True)
    
    def display_command_entry(self, command: str, timestamp: str = None):
        """Display single command entry
        
        Args:
            command: Command text
            timestamp: Timestamp (optional)
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M:%S")
        
        st.markdown(
            f'<div class="terminal-prompt">'
            f'<span class="terminal-user">root@kali</span>'
            f'<span class="terminal-prompt-text">:~$ </span>'
            f'<span class="terminal-command-text">{command}</span>'
            f'</div>',
            unsafe_allow_html=True
        )
    
    def display_output_entry(self, output: str):
        """Display single output entry
        
        Args:
            output: Output text
        """
        st.markdown(
            f'<div class="terminal-output">{output}</div>',
            unsafe_allow_html=True
        )
    
    def create_floating_terminal(self, terminal_history: List[Dict[str, Any]]) -> st.container:
        """Create floating terminal
        
        Args:
            terminal_history: Terminal history
            
        Returns:
            st.container: Terminal container
        """
        from frontend.web.utils.float import float_css_helper
        
        terminal_container = st.container()
        
        with terminal_container:
            # Reapply terminal CSS
            self.apply_terminal_css()
            
            # Use wrapper class to hide Streamlit default styles
            st.markdown('<div class="terminal-wrapper">', unsafe_allow_html=True)
            
            # Create terminal
            self.create_terminal(st.container())
            
            # Render terminal history
            self.render_terminal_display(terminal_history)
            
            # Close wrapper
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Debug info (debug mode only)
            if st.session_state.get("debug_mode", False):
                st.write(f"Debug - terminal_history: {len(terminal_history)}")
        
        # Apply Floating CSS
        terminal_css = float_css_helper(
            width="350px",
            height="500px",
            right="40px",
            top="50%",
            transform="translateY(-50%)",
            z_index="1000",
            border_radius="12px",
            box_shadow="0 25px 50px -12px rgba(0, 0, 0, 0.25)",
            backdrop_filter="blur(16px)",
            background="linear-gradient(145deg, #1f2937 0%, #111827 100%)",
            border="1px solid #374151",
            max_height="500px",
            overflow_y="auto"
        )
        
        terminal_container.float(terminal_css)
        
        return terminal_container
    
    def create_floating_toggle_button(self, is_visible: bool, disabled: bool = False) -> bool:
        """Create floating toggle button
        
        Args:
            is_visible: Whether terminal is visible
            disabled: Whether button is disabled
            
        Returns:
            bool: Whether toggle event occurred
        """
        from frontend.web.utils.float import float_css_helper
        
        toggle_container = st.container()
        clicked = False
        
        with toggle_container:
            # Button based on terminal state
            if is_visible:
                button_text = "💻 Hide Terminal"
                button_type = "secondary"
            else:
                button_text = "💻 Show Terminal"
                button_type = "primary"
            
            # Toggle button
            if st.button(button_text, type=button_type, use_container_width=True, disabled=disabled):
                clicked = True
        
        # Apply Floating CSS
        toggle_css = float_css_helper(
            width="140px",
            right="40px",
            bottom="20px",
            z_index="1001",
            border_radius="12px",
            box_shadow="0 8px 32px rgba(0,0,0,0.12)",
            backdrop_filter="blur(16px)",
            background="rgba(255, 255, 255, 0.9)"
        )
        
        toggle_container.float(toggle_css)
        
        return clicked
    
    def clear_terminal(self):
        """Initialize terminal display"""
        if self.placeholder:
            self.placeholder.empty()

    
    def display_terminal_in_container(self, container, terminal_history: List[Dict[str, Any]]):
        """Display terminal inside container
        
        Args:
            container: Container to display in
            terminal_history: Terminal history
        """
        with container:
            self.apply_terminal_css()
            # Use wrapper class
            st.markdown('<div class="terminal-wrapper">', unsafe_allow_html=True)
            placeholder = self.create_terminal(st.container())
            self.render_terminal_display(terminal_history)
            st.markdown('</div>', unsafe_allow_html=True)
    
    def show_terminal_loading(self, message: str = "Loading terminal..."):
        """Display terminal loading state
        
        Args:
            message: Loading message
        """
        if self.placeholder:
            with self.placeholder:
                st.spinner(message)
    
    def show_terminal_error(self, error_msg: str):
        """Display terminal error state
        
        Args:
            error_msg: Error message
        """
        if self.placeholder:
            with self.placeholder:
                st.error(f"Terminal Error: {error_msg}")
    
    def process_structured_messages(self, messages: List[Dict[str, Any]]):
        """Process structured messages into terminal format (for replay functionality)
        
        Args:
            messages: List of messages to process
        """
        # Process messages using terminal_processor
        try:
            from frontend.web.core.terminal_processor import get_terminal_processor
            terminal_processor = get_terminal_processor()
            
            # Initialize terminal history
            terminal_processor.initialize_terminal_state()
            
            # Process messages
            terminal_entries = terminal_processor.process_structured_messages(messages)
            
            # Update terminal history
            if terminal_entries:
                terminal_processor.update_terminal_history(terminal_entries)
            
            # Save terminal history as instance variable (used in replay)
            if not hasattr(self, 'terminal_history'):
                self.terminal_history = []
            self.terminal_history = terminal_processor.get_terminal_history()
            
        except Exception as e:
            # Initialize with empty list on error
            if not hasattr(self, 'terminal_history'):
                self.terminal_history = []
            print(f"Error processing structured messages: {e}")


# Helper functions
def load_terminal_css():
    """Load terminal CSS (global function)"""
    try:
        with open(CSS_PATH_TERMINAL, "r", encoding="utf-8") as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    except Exception as e:
        print(f"Warning: Could not load terminal.css: {e}")


def create_floating_terminal(terminal_ui_component, terminal_history: List[Dict[str, Any]]):
    """Create floating terminal (global function)
    
    Args:
        terminal_ui_component: TerminalUIComponent instance
        terminal_history: Terminal history
        
    Returns:
        st.container: Terminal container
    """
    return terminal_ui_component.create_floating_terminal(terminal_history)


def create_floating_toggle_button(terminal_ui_component, is_visible: bool, disabled: bool = False):
    """Create floating toggle button (global function)
    
    Args:
        terminal_ui_component: TerminalUIComponent instance
        is_visible: Whether terminal is visible
        disabled: Whether button is disabled
        
    Returns:
        bool: Whether toggle event occurred
    """
    return terminal_ui_component.create_floating_toggle_button(is_visible, disabled=disabled)