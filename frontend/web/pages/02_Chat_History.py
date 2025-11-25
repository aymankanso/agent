
import streamlit as st
import os
import sys

# Add project root path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# New components
from frontend.web.components.chat_history import ChatHistoryComponent
from frontend.web.components.theme_ui import ThemeUIComponent

# Refactored business logic
from frontend.web.core.history_manager import get_history_manager
from frontend.web.core.app_state import get_app_state_manager

# Initialize global managers
history_manager = get_history_manager()
app_state = get_app_state_manager()

# Initialize UI components
theme_ui = ThemeUIComponent()
chat_history = ChatHistoryComponent()


def main():
    """Chat History page main"""
    
    # Initialize theme
    current_theme = "dark" if st.session_state.get('dark_mode', True) else "light"
    theme_ui.apply_theme_css(current_theme)
    
    # Define callback functions
    callbacks = {
        "on_back": _handle_back_button,
        "on_new_chat": _handle_new_chat,
        "on_replay": _handle_replay,
        "get_export_data": _get_export_data
    }
    
    # Load sessions and display UI
    _display_history_interface(callbacks)


def _display_history_interface(callbacks):
    """Display history interface"""
    
    # Show loading state
    chat_history.show_loading_state("Loading sessions...")
    
    # Load session data
    sessions_result = history_manager.load_sessions(limit=20)
    
    if not sessions_result["success"]:
        # Handle error state
        retry_clicked = chat_history.show_error_state(sessions_result["error"])
        if retry_clicked:
            st.rerun()
        return
    
    sessions = sessions_result["sessions"]
    
    # Render complete history page
    chat_history.render_complete_history_page(sessions, callbacks)


def _handle_back_button():
    """Handle back button"""
    st.switch_page("pages/01_Chat.py")


def _handle_new_chat():
    """Handle new chat button"""
    st.switch_page("pages/01_Chat.py")


def _handle_replay(session_id: str):
    """Handle replay button (Improved - Load conversation history immediately)
    
    Args:
        session_id: Session ID to replay
    """
    # Validate session ID
    if not history_manager.validate_session_id(session_id):
        st.error("Invalid session ID")
        return
    
    # Start replay
    replay_result = history_manager.start_replay(session_id)
    
    if replay_result["success"]:
        # Set replay mode
        st.session_state.replay_session_id = session_id
        st.session_state.replay_mode = True
        st.session_state.replay_completed = False
        
        # Go directly to main chat page (remove message)
        st.switch_page("pages/01_Chat.py")
    else:
        st.error(f"Failed to start replay: {replay_result['error']}")


def _get_export_data(session_id: str) -> str:
    """Get export data
    
    Args:
        session_id: Session ID
        
    Returns:
        str: Export data in JSON format
    """
    try:
        export_data = history_manager.prepare_export_data(session_id)
        return export_data
        
    except Exception as e:
        st.error(f"Export failed: {str(e)}")
        return None


if __name__ == "__main__":
    main()
