
import re
from datetime import datetime
from typing import Dict, Any, List
import streamlit as st


class TerminalProcessor:
    """Terminal data processing core logic"""
    
    def __init__(self):
        """Initialize terminal processor"""
        self.processed_messages = set() 
    
    def clean_command(self, command: str) -> str:
        """Command cleanup logic
        
        Args:
            command: Original command
            
        Returns:
            str: Cleaned command
        """
        if not isinstance(command, str):
            command = str(command)
        
        
        command = command.strip()
        
      
        if '\n' in command:
            command = command.split('\n')[0].strip()
        
       
        prefixes_to_remove = [
            'Running command:',
            'Executing:',
            'Command:',
            'Execute:',
            '$',
            '# '
        ]
        
        for prefix in prefixes_to_remove:
            if command.startswith(prefix):
                command = command[len(prefix):].strip()
        
        return command
    
    def sanitize_output(self, output: str) -> str:
        """Output content cleanup logic
        
        Args:
            output: Original output
            
        Returns:
            str: Cleaned output
        """
        if not isinstance(output, str):
            output = str(output)
        
    
        output = output.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
    
        output = output.replace("\n", "<br>")
        
        return output
    
    def extract_command_from_line(self, line: str) -> str:
        """Extract actual command from line
        
        Args:
            line: Line containing command
            
        Returns:
            str: Extracted command
        """
        line = line.strip()
        
   
        patterns = [
            r'(?:command|executing|running):\s*(.+)',
            r'\$\s*(.+)',
            r'#\s*(.+)',
            r'^(.+?)\s*$' 
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                command = match.group(1).strip()
                if command:
                    return command
        
        return line
    
    def process_frontend_messages(self, frontend_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process frontend messages to terminal history
        
        Args:
            frontend_messages: Message list to process
            
        Returns:
            List[Dict]: Terminal history entry list
        """
        terminal_entries = []
        
        if not frontend_messages:
            return terminal_entries
        
        for message in frontend_messages:
            message_id = message.get("id")
            
           
            if message_id in self.processed_messages:
                continue
                
            message_type = message.get("type")
            
         
            if message_type == "tool":
                tool_display_name = message.get("tool_display_name", "Tool")
                content = message.get("content", "")
                
              
                is_terminal_tool = self._is_terminal_tool(tool_display_name)
                
                if is_terminal_tool:
                    entries = self._process_terminal_tool_message(tool_display_name, content)
                    terminal_entries.extend(entries)
                else:
                 
                    if content and content.strip():
                        terminal_entries.append({
                            "type": "command",
                            "content": tool_display_name,
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        })
                        terminal_entries.append({
                            "type": "output",
                            "content": self.sanitize_output(content),
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        })
                
             
                self.processed_messages.add(message_id)
        
        return terminal_entries
    
    def _is_terminal_tool(self, tool_display_name: str) -> bool:
        """Check if terminal tool
        
        Args:
            tool_display_name: Tool display name
            
        Returns:
            bool: Whether terminal tool
        """
        return (
            "terminal" in tool_display_name.lower() or 
            "command" in tool_display_name.lower() or
            "exec" in tool_display_name.lower() or
            "shell" in tool_display_name.lower()
        )
    
    def _process_terminal_tool_message(self, tool_display_name: str, content: str) -> List[Dict[str, Any]]:
        """Process terminal tool message
        
        Args:
            tool_display_name: Tool display name
            content: Message content
            
        Returns:
            List[Dict]: Terminal entry list
        """
        entries = []
        
  
        lines = content.split('\n') if content else []
        
     
        command_found = False
        for i, line in enumerate(lines):
            line = line.strip()
            
            if any(indicator in line.lower() for indicator in ['$', '#', 'command:', 'executing:', 'running:']):
               
                cleaned_command = self.extract_command_from_line(line)
                if cleaned_command:
                    entries.append({
                        "type": "command",
                        "content": self.clean_command(cleaned_command),
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
                    command_found = True
                    
                
                    remaining_output = '\n'.join(lines[i+1:])
                    if remaining_output.strip():
                        entries.append({
                            "type": "output",
                            "content": self.sanitize_output(remaining_output.strip()),
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        })
                    break
        
       
        if not command_found and content.strip():
            
            entries.append({
                "type": "command",
                "content": self.clean_command(f"{tool_display_name.lower()}"),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
            entries.append({
                "type": "output",
                "content": self.sanitize_output(content),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
        
        return entries
    
    def process_structured_messages(self, structured_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process structured messages to terminal history
        
        Args:
            structured_messages: Structured message list
            
        Returns:
            List[Dict]: Terminal history entry list
        """
        terminal_entries = []
        
        if not structured_messages:
            return terminal_entries
   
        for message in structured_messages:
            message_id = message.get("id")
         
            if message_id in self.processed_messages:
                continue
                
            message_type = message.get("type")
       
            if message_type == "tool":
                tool_display_name = message.get("tool_display_name", "Tool")
                content = message.get("content", "")
                
                if tool_display_name and content:
               
                    terminal_entries.append({
                        "type": "command",
                        "content": self.clean_command(tool_display_name),
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
            
                    terminal_entries.append({
                        "type": "output",
                        "content": self.sanitize_output(content),
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
                    
                    self.processed_messages.add(message_id)
        
        return terminal_entries
    
    def initialize_terminal_state(self):
        """Initialize terminal state"""
        if "terminal_history" not in st.session_state:
            st.session_state.terminal_history = []
    
    def clear_terminal_state(self):
        """Complete terminal state initialization"""
        self.processed_messages = set()
        st.session_state.terminal_history = []
    
    def get_terminal_history(self) -> List[Dict[str, Any]]:
        """Return current terminal history"""
        return st.session_state.get("terminal_history", [])
    
    def update_terminal_history_realtime(self, new_entries: List[Dict[str, Any]]):
        """Real-time terminal history update (no longer used)
        
        Args:
            new_entries: New terminal entries to add
        """
        # Replaced with simple history update
        self.update_terminal_history(new_entries)
    
    def update_terminal_history(self, new_entries: List[Dict[str, Any]]):
        """Update terminal history (base version)
        
        Args:
            new_entries: New terminal entries to add
        """
        if "terminal_history" not in st.session_state:
            st.session_state.terminal_history = []
        
        st.session_state.terminal_history.extend(new_entries)
    
    def _trigger_terminal_ui_update(self):
        """Trigger terminal UI real-time update (no longer used)"""
        # No longer trigger real-time updates
        pass


# Global terminal processor instance
_terminal_processor = None

def get_terminal_processor() -> TerminalProcessor:
    """Return terminal processor singleton instance"""
    global _terminal_processor
    if _terminal_processor is None:
        _terminal_processor = TerminalProcessor()
    return _terminal_processor
