"""
Enhanced trace logging for multi-agent system observability.
Provides detailed execution traces, agent interactions, and decision flows.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum


class TraceLevel(Enum):
    """Trace detail levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class TraceEventType(Enum):
    """Types of trace events"""
    WORKFLOW_START = "workflow_start"
    WORKFLOW_END = "workflow_end"
    AGENT_INVOCATION = "agent_invocation"
    AGENT_RESPONSE = "agent_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    HANDOFF = "handoff"
    STATE_UPDATE = "state_update"
    ERROR = "error"
    DECISION = "decision"


@dataclass
class TraceEvent:
    """Individual trace event"""
    event_id: str
    event_type: TraceEventType
    timestamp: float
    level: TraceLevel
    agent_name: Optional[str] = None
    tool_name: Optional[str] = None
    content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_event_id: Optional[str] = None
    duration: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
            "level": self.level.value
        }
        
        if self.agent_name:
            data["agent_name"] = self.agent_name
        if self.tool_name:
            data["tool_name"] = self.tool_name
        if self.content:
            data["content"] = self.content
        if self.metadata:
            data["metadata"] = self.metadata
        if self.parent_event_id:
            data["parent_event_id"] = self.parent_event_id
        if self.duration is not None:
            data["duration"] = self.duration
        
        return data


@dataclass
class ExecutionTrace:
    """Complete execution trace for a workflow"""
    trace_id: str
    workflow_name: str
    start_time: float
    end_time: Optional[float] = None
    events: List[TraceEvent] = field(default_factory=list)
    user_input: Optional[str] = None
    final_output: Optional[str] = None
    status: str = "running"  # running, completed, failed
    error: Optional[str] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Total execution duration"""
        if self.end_time is None:
            return None
        return self.end_time - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "trace_id": self.trace_id,
            "workflow_name": self.workflow_name,
            "start_time": self.start_time,
            "start_time_iso": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": self.end_time,
            "end_time_iso": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "duration": self.duration,
            "user_input": self.user_input,
            "final_output": self.final_output,
            "status": self.status,
            "error": self.error,
            "event_count": len(self.events),
            "events": [event.to_dict() for event in self.events]
        }


class TraceLogger:
    """
    Enhanced trace logger for multi-agent system observability.
    
    Features:
    - Hierarchical event tracing
    - Agent interaction tracking
    - Tool execution monitoring
    - Decision flow visualization
    - Performance metrics
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize trace logger.
        
        Args:
            output_dir: Directory to save traces (default: logs/traces)
        """
        if output_dir is None:
            output_dir = Path("logs/traces")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_trace: Optional[ExecutionTrace] = None
        self.event_counter = 0
    
    def start_workflow(
        self,
        workflow_name: str,
        user_input: str,
        trace_id: Optional[str] = None
    ) -> str:
        """
        Start tracing a workflow execution.
        
        Args:
            workflow_name: Name of the workflow
            user_input: User's input message
            trace_id: Optional trace ID (generated if not provided)
            
        Returns:
            Trace ID
        """
        if trace_id is None:
            trace_id = f"trace_{int(time.time() * 1000)}"
        
        self.current_trace = ExecutionTrace(
            trace_id=trace_id,
            workflow_name=workflow_name,
            start_time=time.time(),
            user_input=user_input
        )
        
        self.event_counter = 0
        
        # Log workflow start event
        self._add_event(
            event_type=TraceEventType.WORKFLOW_START,
            level=TraceLevel.INFO,
            content=f"Workflow '{workflow_name}' started",
            metadata={"user_input": user_input}
        )
        
        return trace_id
    
    def end_workflow(
        self,
        final_output: Optional[str] = None,
        status: str = "completed",
        error: Optional[str] = None
    ) -> Optional[ExecutionTrace]:
        """
        End workflow tracing.
        
        Args:
            final_output: Final workflow output
            status: Workflow status (completed, failed)
            error: Error message if failed
            
        Returns:
            Completed trace
        """
        if self.current_trace is None:
            return None
        
        self.current_trace.end_time = time.time()
        self.current_trace.final_output = final_output
        self.current_trace.status = status
        self.current_trace.error = error
        
        # Log workflow end event
        self._add_event(
            event_type=TraceEventType.WORKFLOW_END,
            level=TraceLevel.INFO if status == "completed" else TraceLevel.ERROR,
            content=f"Workflow ended with status: {status}",
            metadata={
                "duration": self.current_trace.duration,
                "event_count": len(self.current_trace.events)
            }
        )
        
        # Save trace
        self.save_trace()
        
        trace = self.current_trace
        self.current_trace = None
        
        return trace
    
    def log_agent_invocation(
        self,
        agent_name: str,
        input_data: str,
        parent_event_id: Optional[str] = None
    ) -> str:
        """
        Log agent invocation.
        
        Args:
            agent_name: Name of the agent
            input_data: Input provided to agent
            parent_event_id: Parent event ID for hierarchical tracing
            
        Returns:
            Event ID
        """
        return self._add_event(
            event_type=TraceEventType.AGENT_INVOCATION,
            level=TraceLevel.INFO,
            agent_name=agent_name,
            content=input_data,
            parent_event_id=parent_event_id
        )
    
    def log_agent_response(
        self,
        agent_name: str,
        response: str,
        parent_event_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log agent response.
        
        Args:
            agent_name: Name of the agent
            response: Agent's response
            parent_event_id: Parent event ID
            metadata: Additional metadata (tokens, model, etc.)
            
        Returns:
            Event ID
        """
        return self._add_event(
            event_type=TraceEventType.AGENT_RESPONSE,
            level=TraceLevel.INFO,
            agent_name=agent_name,
            content=response,
            metadata=metadata or {},
            parent_event_id=parent_event_id
        )
    
    def log_tool_call(
        self,
        tool_name: str,
        agent_name: str,
        arguments: Dict[str, Any],
        parent_event_id: Optional[str] = None
    ) -> str:
        """
        Log tool call.
        
        Args:
            tool_name: Name of the tool
            agent_name: Agent making the call
            arguments: Tool arguments
            parent_event_id: Parent event ID
            
        Returns:
            Event ID
        """
        return self._add_event(
            event_type=TraceEventType.TOOL_CALL,
            level=TraceLevel.DEBUG,
            agent_name=agent_name,
            tool_name=tool_name,
            content=json.dumps(arguments, indent=2),
            metadata={"arguments": arguments},
            parent_event_id=parent_event_id
        )
    
    def log_tool_result(
        self,
        tool_name: str,
        result: str,
        success: bool = True,
        duration: Optional[float] = None,
        parent_event_id: Optional[str] = None
    ) -> str:
        """
        Log tool execution result.
        
        Args:
            tool_name: Name of the tool
            result: Tool output
            success: Whether execution succeeded
            duration: Execution duration in seconds
            parent_event_id: Parent event ID
            
        Returns:
            Event ID
        """
        return self._add_event(
            event_type=TraceEventType.TOOL_RESULT,
            level=TraceLevel.INFO if success else TraceLevel.ERROR,
            tool_name=tool_name,
            content=result,
            metadata={"success": success},
            duration=duration,
            parent_event_id=parent_event_id
        )
    
    def log_handoff(
        self,
        from_agent: str,
        to_agent: str,
        reason: str,
        parent_event_id: Optional[str] = None
    ) -> str:
        """
        Log agent handoff.
        
        Args:
            from_agent: Source agent
            to_agent: Target agent
            reason: Handoff reason
            parent_event_id: Parent event ID
            
        Returns:
            Event ID
        """
        return self._add_event(
            event_type=TraceEventType.HANDOFF,
            level=TraceLevel.INFO,
            content=f"Handoff from {from_agent} to {to_agent}: {reason}",
            metadata={"from_agent": from_agent, "to_agent": to_agent, "reason": reason},
            parent_event_id=parent_event_id
        )
    
    def log_decision(
        self,
        agent_name: str,
        decision: str,
        reasoning: str,
        parent_event_id: Optional[str] = None
    ) -> str:
        """
        Log agent decision.
        
        Args:
            agent_name: Agent making decision
            decision: Decision made
            reasoning: Reasoning behind decision
            parent_event_id: Parent event ID
            
        Returns:
            Event ID
        """
        return self._add_event(
            event_type=TraceEventType.DECISION,
            level=TraceLevel.INFO,
            agent_name=agent_name,
            content=decision,
            metadata={"reasoning": reasoning},
            parent_event_id=parent_event_id
        )
    
    def log_error(
        self,
        error_message: str,
        agent_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        exception: Optional[Exception] = None,
        parent_event_id: Optional[str] = None
    ) -> str:
        """
        Log error.
        
        Args:
            error_message: Error description
            agent_name: Agent where error occurred
            tool_name: Tool where error occurred
            exception: Exception object
            parent_event_id: Parent event ID
            
        Returns:
            Event ID
        """
        metadata = {}
        if exception:
            metadata["exception_type"] = type(exception).__name__
            metadata["exception_message"] = str(exception)
        
        return self._add_event(
            event_type=TraceEventType.ERROR,
            level=TraceLevel.ERROR,
            agent_name=agent_name,
            tool_name=tool_name,
            content=error_message,
            metadata=metadata,
            parent_event_id=parent_event_id
        )
    
    def _add_event(
        self,
        event_type: TraceEventType,
        level: TraceLevel,
        content: Optional[str] = None,
        agent_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_event_id: Optional[str] = None,
        duration: Optional[float] = None
    ) -> str:
        """Add event to current trace"""
        if self.current_trace is None:
            raise RuntimeError("No active trace. Call start_workflow() first.")
        
        self.event_counter += 1
        event_id = f"evt_{self.event_counter}"
        
        event = TraceEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=time.time(),
            level=level,
            agent_name=agent_name,
            tool_name=tool_name,
            content=content,
            metadata=metadata or {},
            parent_event_id=parent_event_id,
            duration=duration
        )
        
        self.current_trace.events.append(event)
        
        return event_id
    
    def save_trace(self, trace: Optional[ExecutionTrace] = None) -> Optional[Path]:
        """
        Save trace to JSON file.
        
        Args:
            trace: Trace to save (uses current_trace if None)
            
        Returns:
            Path to saved file
        """
        if trace is None:
            trace = self.current_trace
        
        if trace is None:
            return None
        
        # Create date-based subdirectory
        date_str = datetime.now().strftime("%Y/%m/%d")
        trace_dir = self.output_dir / date_str
        trace_dir.mkdir(parents=True, exist_ok=True)
        
        # Save trace
        trace_file = trace_dir / f"{trace.trace_id}.json"
        with open(trace_file, 'w') as f:
            json.dump(trace.to_dict(), f, indent=2)
        
        return trace_file
    
    def load_trace(self, trace_id: str) -> Optional[ExecutionTrace]:
        """
        Load trace from file.
        
        Args:
            trace_id: Trace ID to load
            
        Returns:
            ExecutionTrace object or None
        """
        # Search for trace file
        for trace_file in self.output_dir.rglob(f"{trace_id}.json"):
            with open(trace_file, 'r') as f:
                data = json.load(f)
            
            # Reconstruct trace
            trace = ExecutionTrace(
                trace_id=data["trace_id"],
                workflow_name=data["workflow_name"],
                start_time=data["start_time"],
                end_time=data.get("end_time"),
                user_input=data.get("user_input"),
                final_output=data.get("final_output"),
                status=data.get("status", "unknown"),
                error=data.get("error")
            )
            
            # Reconstruct events
            for event_data in data.get("events", []):
                event = TraceEvent(
                    event_id=event_data["event_id"],
                    event_type=TraceEventType(event_data["event_type"]),
                    timestamp=event_data["timestamp"],
                    level=TraceLevel(event_data["level"]),
                    agent_name=event_data.get("agent_name"),
                    tool_name=event_data.get("tool_name"),
                    content=event_data.get("content"),
                    metadata=event_data.get("metadata", {}),
                    parent_event_id=event_data.get("parent_event_id"),
                    duration=event_data.get("duration")
                )
                trace.events.append(event)
            
            return trace
        
        return None
    
    def get_agent_statistics(self, trace: Optional[ExecutionTrace] = None) -> Dict[str, Any]:
        """
        Get agent interaction statistics from trace.
        
        Args:
            trace: Trace to analyze (uses current_trace if None)
            
        Returns:
            Dictionary of statistics
        """
        if trace is None:
            trace = self.current_trace
        
        if trace is None:
            return {}
        
        stats = {
            "total_events": len(trace.events),
            "agents": {},
            "tools": {},
            "handoffs": []
        }
        
        for event in trace.events:
            # Count agent activity
            if event.agent_name:
                if event.agent_name not in stats["agents"]:
                    stats["agents"][event.agent_name] = {
                        "invocations": 0,
                        "responses": 0,
                        "tool_calls": 0
                    }
                
                if event.event_type == TraceEventType.AGENT_INVOCATION:
                    stats["agents"][event.agent_name]["invocations"] += 1
                elif event.event_type == TraceEventType.AGENT_RESPONSE:
                    stats["agents"][event.agent_name]["responses"] += 1
                elif event.event_type == TraceEventType.TOOL_CALL:
                    stats["agents"][event.agent_name]["tool_calls"] += 1
            
            # Count tool usage
            if event.tool_name:
                if event.tool_name not in stats["tools"]:
                    stats["tools"][event.tool_name] = {"calls": 0, "successes": 0, "failures": 0}
                
                if event.event_type == TraceEventType.TOOL_CALL:
                    stats["tools"][event.tool_name]["calls"] += 1
                elif event.event_type == TraceEventType.TOOL_RESULT:
                    if event.metadata.get("success", True):
                        stats["tools"][event.tool_name]["successes"] += 1
                    else:
                        stats["tools"][event.tool_name]["failures"] += 1
            
            # Track handoffs
            if event.event_type == TraceEventType.HANDOFF:
                stats["handoffs"].append({
                    "from": event.metadata.get("from_agent"),
                    "to": event.metadata.get("to_agent"),
                    "reason": event.metadata.get("reason"),
                    "timestamp": event.timestamp
                })
        
        return stats


# Global instance
_trace_logger: Optional[TraceLogger] = None


def get_trace_logger(output_dir: Optional[Path] = None) -> TraceLogger:
    """
    Get global trace logger instance (singleton pattern).
    
    Args:
        output_dir: Directory to save traces (only used on first call)
        
    Returns:
        Global TraceLogger instance
    """
    global _trace_logger
    if _trace_logger is None:
        _trace_logger = TraceLogger(output_dir=output_dir)
    return _trace_logger
