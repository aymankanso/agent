
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from frontend.web.utils.validation import validate_file_path


class ChatHistoryManager:
    """Chat History Management Business Logic"""
    
    def __init__(self):
        """Initialize history manager"""
        self.logger = None
        self._initialize_logger()
    
    def _initialize_logger(self):
        """Initialize logger"""
        try:
            from src.utils.logging.logger import get_logger
            self.logger = get_logger()
        except ImportError:
            self.logger = None
    
    def load_sessions(self, limit: int = 20) -> Dict[str, Any]:
        """Load session list
        
        Args:
            limit: Session count limit
            
        Returns:
            Dict: Load result
        """
        if not self.logger:
            return {
                "success": False,
                "error": "Logger not available",
                "sessions": []
            }
        
        try:
            sessions = self.logger.list_sessions(limit=limit)
            
            # Process session data
            processed_sessions = []
            for session in sessions:
                processed_session = self._process_session_data(session)
                processed_sessions.append(processed_session)
            
            return {
                "success": True,
                "sessions": processed_sessions,
                "total_count": len(sessions)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "sessions": []
            }
    
    def _process_session_data(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Process session data
        
        Args:
            session: Original session data
            
        Returns:
            Dict: Processed session data
        """
        processed = session.copy()
        
        # Format time
        if 'start_time' in session:
            processed['formatted_time'] = self._format_session_time(session['start_time'])
        
        # Process preview text
        if 'preview' in session and session['preview']:
            preview = session['preview']
            if len(preview) > 100:
                processed['preview'] = preview[:100] + "..."
            else:
                processed['preview'] = preview
        else:
            processed['preview'] = "No user input found"
        
        # Shorten session ID
        if 'session_id' in session:
            processed['short_session_id'] = session['session_id'][:16] + "..."
        
        return processed
    
    def _format_session_time(self, time_str: str) -> str:
        """Format session time
        
        Args:
            time_str: Original time string
            
        Returns:
            str: Formatted time string
        """
        try:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return time_str[:19] if len(time_str) > 19 else time_str
    
    def filter_sessions(
        self, 
        sessions: List[Dict[str, Any]], 
        date_filter: str = "All",
        sort_option: str = "Newest First"
    ) -> List[Dict[str, Any]]:
        """Filter and sort sessions
        
        Args:
            sessions: Session list
            date_filter: Date filter ("All", "Today", "Last 7 days", "Last 30 days")
            sort_option: Sort option ("Newest First", "Oldest First", "Most Events")
            
        Returns:
            List: Filtered session list
        """
        filtered_sessions = sessions.copy()
        
        # Apply date filter
        if date_filter != "All":
            filtered_sessions = self._apply_date_filter(filtered_sessions, date_filter)
        
        # Apply sorting
        filtered_sessions = self._apply_sorting(filtered_sessions, sort_option)
        
        return filtered_sessions
    
    def _apply_date_filter(self, sessions: List[Dict[str, Any]], date_filter: str) -> List[Dict[str, Any]]:
        """Apply date filter
        
        Args:
            sessions: Session list
            date_filter: Date filter
            
        Returns:
            List: Filtered session list
        """
        now = datetime.now()
        filtered = []
        
        for session in sessions:
            try:
                session_time = datetime.fromisoformat(session['start_time'].replace('Z', '+00:00'))
                days_diff = (now - session_time).days
                
                if date_filter == "Today" and days_diff == 0:
                    filtered.append(session)
                elif date_filter == "Last 7 days" and days_diff <= 7:
                    filtered.append(session)
                elif date_filter == "Last 30 days" and days_diff <= 30:
                    filtered.append(session)
                    
            except:
                # Include on date parsing failure
                filtered.append(session)
        
        return filtered
    
    def _apply_sorting(self, sessions: List[Dict[str, Any]], sort_option: str) -> List[Dict[str, Any]]:
        """Apply sorting
        
        Args:
            sessions: Session list
            sort_option: Sort option
            
        Returns:
            List: Sorted session list
        """
        if sort_option == "Newest First":
            return sorted(sessions, key=lambda x: x.get('start_time', ''), reverse=True)
        elif sort_option == "Oldest First":
            return sorted(sessions, key=lambda x: x.get('start_time', ''))
        elif sort_option == "Most Events":
            return sorted(sessions, key=lambda x: x.get('event_count', 0), reverse=True)
        
        return sessions
    
    def prepare_export_data(self, session_id: str) -> Optional[str]:
        """Prepare session export data
        
        Args:
            session_id: Session ID
            
        Returns:
            Optional[str]: Export data in JSON format
        """
        if not self.logger:
            return None
        
        try:
            # Load session data
            session = self.logger.load_session(session_id)
            if not session:
                # Try direct file search
                session = self._load_session_from_file(session_id)
                
                if not session:
                    return None
            
            # Handle both MinimalSession object and dict cases
            if hasattr(session, 'events'):  # MinimalSession object
                events_data = [
                    event.to_dict() if hasattr(event, 'to_dict') else event 
                    for event in session.events
                ]
                session_info = {
                    "session_id": session.session_id,
                    "start_time": session.start_time,
                    "total_events": len(session.events)
                }
                # Add model info
                if hasattr(session, 'model') and session.model:
                    session_info["model"] = session.model
            else:  # dict data
                events_data = session.get('events', [])
                session_info = {
                    "session_id": session.get('session_id', session_id),
                    "start_time": session.get('start_time', 'Unknown'),
                    "total_events": len(events_data)
                }
                # Add model info
                if session.get('model'):
                    session_info["model"] = session.get('model')
            
            # Create export data structure
            export_data = {
                "session_info": session_info,
                "events": events_data,
                "export_metadata": {
                    "exported_at": datetime.now().isoformat(),
                    "exported_by": "AI Red Teaming Multi-Agent Log Manager",
                    "version": "1.0"
                }
            }
            
            # Convert to JSON string
            return json.dumps(export_data, indent=2, ensure_ascii=False)
            
        except Exception as e:
            print(f"Export error: {e}")
            return None
    
    def _load_session_from_file(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data directly from file
        
        Args:
            session_id: Session ID
            
        Returns:
            Optional[Dict]: Session data
        """
        try:
            # Search for session file in logs folder
            logs_path = Path("logs")
            for session_file in logs_path.rglob(f"session_{session_id}.json"):
                with open(session_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading session file: {e}")
        
        return None
    
    def start_replay(self, session_id: str) -> Dict[str, Any]:
        """Start session replay
        
        Args:
            session_id: Session ID to replay
            
        Returns:
            Dict: Replay start result
        """
        # Check if session exists
        session_data = self._load_session_from_file(session_id)
        if not session_data and self.logger:
            session_data = self.logger.load_session(session_id)
        
        if not session_data:
            return {
                "success": False,
                "error": f"Session {session_id} not found"
            }
        
        return {
            "success": True,
            "session_id": session_id,
            "message": f"Starting replay for session {session_id[:16]}..."
        }
    
    def get_session_details(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session details
        
        Args:
            session_id: Session ID
            
        Returns:
            Optional[Dict]: Session details
        """
        if not self.logger:
            return None
        
        try:
            session = self.logger.load_session(session_id)
            if session:
                return self._process_session_data(session.__dict__ if hasattr(session, '__dict__') else session)
        except Exception as e:
            print(f"Error loading session details: {e}")
        
        return None
    
    def validate_session_id(self, session_id: str) -> bool:
        """Validate session ID
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            bool: Validation result
        """
        if not session_id or len(session_id) < 8:
            return False
        
        # Simple UUID format check
        return len(session_id) >= 32 and all(c.isalnum() or c == '-' for c in session_id)


# Global history manager instance
_history_manager = None

def get_history_manager() -> ChatHistoryManager:
    """Return history manager singleton instance"""
    global _history_manager
    if _history_manager is None:
        _history_manager = ChatHistoryManager()
    return _history_manager
