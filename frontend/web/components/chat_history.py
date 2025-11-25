"""
Chat History UI Component (refactored - pure UI logic)
Session list display, replay button, export and other history UI rendering
"""

import streamlit as st
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from frontend.web.utils.constants import ICON, ICON_TEXT, COMPANY_LINK
import time

class ChatHistoryComponent:
    """Chat History UI Component"""
    
    def __init__(self):
        """Initialize component"""
        pass
    
    def render_page_header(self):
        """Render page header"""
        # Display logo
        # st.logo(ICON_TEXT, icon_image=ICON, size="large", link=COMPANY_LINK)
        st.title("📊 :red[Session Logs]")
    
    def render_back_button(self, callback: Callable = None) -> bool:
        """Render back button
        
        Args:
            callback: Click callback function
            
        Returns:
            bool: Whether the button was clicked
        """
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("← Back", use_container_width=True):
                if callback:
                    callback()
                return True
        return False
    
    def render_empty_state(self):
        """Render empty state when no sessions exist
        
        Returns:
            bool: Whether the new chat button was clicked
        """
        st.info("📭 No chat sessions found")
        st.markdown("""
        Start a new conversation to see your chat history here.
        """)
        
        # Start new chat button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Start New Chat", use_container_width=True, type="primary"):
                return True
        return False
    
    def render_sessions_header(self, session_count: int, total_count: int = None):
        """Render session list header
        
        Args:
            session_count: Number of sessions to display
            total_count: Total session count (optional)
        """
        st.subheader("📋 Recent Sessions")
        if total_count and total_count > session_count:
            st.caption(f"Showing {session_count} of {total_count} sessions")
        else:
            st.caption(f"Showing {session_count} recent sessions")
    
    def render_filter_options(self) -> Dict[str, str]:
        """Render filter options
        
        Returns:
            Dict: Selected filter options
        """
        with st.expander("🔍 Filter Options", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                date_filter = st.selectbox(
                    "Filter by Date",
                    options=["All", "Today", "Last 7 days", "Last 30 days"],
                    index=0
                )
            
            with col2:
                sort_option = st.selectbox(
                    "Sort by",
                    options=["Newest First", "Oldest First", "Most Events"],
                    index=0
                )
        
        return {
            "date_filter": date_filter,
            "sort_option": sort_option
        }
    
    def format_session_time(self, session_time: str) -> str:
        """Format session time
        
        Args:
            session_time: Original time string
            
        Returns:
            str: Formatted time string
        """
        try:
            dt = datetime.fromisoformat(session_time.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return session_time[:19] if len(session_time) > 19 else session_time
    
    def render_session_card(
        self, 
        session: Dict[str, Any], 
        index: int,
        callbacks: Optional[Dict[str, Callable]] = None
    ) -> Optional[str]:
        """Render session card
        
        Args:
            session: Session data
            index: Session index
            callbacks: Callback functions
            
        Returns:
            Optional[str]: Action that occurred ("replay", "details", "export")
        """
        if callbacks is None:
            callbacks = {}
        
        session_id = session.get('session_id', 'Unknown')
        
        with st.container():
            # Session header
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                # Display time
                time_str = self.format_session_time(session.get('start_time', ''))
                st.markdown(f"**🕒 {time_str}**")
                st.caption(f"Session: {session_id[:16]}...")
                
                # Content preview
                preview_text = session.get('preview', "No user input found")
                if len(preview_text) > 100:
                    preview_text = preview_text[:100] + "..."
                st.caption(f"💬 {preview_text}")
                
                # Display model information
                model_info = session.get('model')
                if model_info:
                    st.caption(f"🤖 Model: {model_info}")
            
            with col2:
                st.metric("Events", session.get('event_count', 0))
            
            with col3:
                # Session details button
                if st.button("📄 Details", key=f"details_{index}", use_container_width=True):
                    return "details"
            
            with col4:
                # Replay button (core feature)
                if st.button("🎬 Replay", key=f"replay_{index}", use_container_width=True, type="primary"):
                    if "on_replay" in callbacks:
                        callbacks["on_replay"](session_id)
                    return "replay"
            
            # Export feature (separate row)
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col4:
                export_filename = f"session_{session_id[:8]}_{datetime.now().strftime('%Y%m%d')}.json"
                
                if "get_export_data" in callbacks:
                    export_data = callbacks["get_export_data"](session_id)
                    if export_data:
                        st.download_button(
                            label="💾 Export",
                            data=export_data,
                            file_name=export_filename,
                            mime="application/json",
                            key=f"export_{index}",
                            use_container_width=True
                        )
                    else:
                        st.button("❌ Export", disabled=True, key=f"export_disabled_{index}", use_container_width=True)
            
            st.divider()
        
        return None
    
    def render_session_details(self, session: Dict[str, Any]):
        """Render session details
        
        Args:
            session: Session data
        """
        session_id = session.get('session_id', 'Unknown')
        
        with st.expander(f"Session Details - {session_id[:16]}...", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Session Info:**")
                session_info = {
                    "Session ID": session_id,
                    "Start Time": session.get('start_time', 'Unknown'),
                    "Event Count": session.get('event_count', 0),
                    "Model": session.get('model', 'Unknown')
                }
                st.json(session_info)
            
            with col2:
                st.markdown("**Preview:**")
                preview = session.get('preview', 'No preview available')
                st.text_area("Content", value=preview, height=100, disabled=True)
    
    def render_sessions_list(
        self, 
        sessions: List[Dict[str, Any]], 
        callbacks: Optional[Dict[str, Callable]] = None
    ):
        """Render session list
        
        Args:
            sessions: Session list
            callbacks: Callback functions
        """
        # Filter options
        filter_options = self.render_filter_options()
        
        # Actual filtering is handled in business logic, only UI is displayed here
        filtered_sessions = sessions  # Filtered sessions
        
        st.divider()
        
        # Session cards
        for i, session in enumerate(filtered_sessions):
            action = self.render_session_card(session, i, callbacks)
            
            # Display session details
            if action == "details":
                self.render_session_details(session)
    
    def render_complete_history_page(
        self,
        sessions: List[Dict[str, Any]] = None,
        callbacks: Optional[Dict[str, Callable]] = None
    ):
        """Render complete history page
        
        Args:
            sessions: Session list
            callbacks: Callback functions
        """
        # Hide sidebar
        self.hide_sidebar()
        
        # Page header
        self.render_page_header()
        
        # Back button
        if self.render_back_button():
            if callbacks and "on_back" in callbacks:
                callbacks["on_back"]()
        
        # Process session list
        if not sessions:
            if self.render_empty_state():
                if callbacks and "on_new_chat" in callbacks:
                    callbacks["on_new_chat"]()
        else:
            # Session list header
            self.render_sessions_header(len(sessions))
            
            # Display session list
            self.render_sessions_list(sessions, callbacks)
    
    def hide_sidebar(self):
        """Hide sidebar"""
        st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {
                display: none;
            }
            
            section[data-testid="stSidebar"] {
                display: none !important;
            }
            
            /* Expand main content to full screen */
            .main .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
                max-width: none;
            }
        </style>
        """, unsafe_allow_html=True)
    
    def show_loading_state(self, message: str = "Loading sessions..."):
        """Display loading state
        
        Args:
            message: Loading message
        """
        with st.spinner(message):
            time.sleep(0.1)
    
    def show_error_state(self, error_msg: str):
        """Display error state
        
        Args:
            error_msg: Error message
            
        Returns:
            bool: Whether the retry button was clicked
        """
        st.error(f"Error loading sessions: {error_msg}")
        
        if st.button("🔄 Retry", use_container_width=True):
            return True
        return False
    
    def show_replay_start_message(self, session_id: str):
        """Display replay start message (removed - replay directly)
        
        Args:
            session_id: Session ID
        """
        # Message output removed - replay previous conversation history directly
        pass
