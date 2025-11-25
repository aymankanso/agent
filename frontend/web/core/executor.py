
import asyncio
import uuid
import time
from datetime import datetime
from typing import Optional, Dict, Any, AsyncGenerator, Union, List, Tuple

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from src.graphs.swarm import create_dynamic_swarm
from src.utils.llm.config_manager import (
    update_llm_config, 
    get_current_llm_config,
    get_current_llm
)
from src.utils.message import (
    extract_message_content,
    get_message_type,
    get_agent_name,
    parse_tool_name
)
from src.utils.metrics import get_cost_tracker
from src.utils.observability import get_trace_logger, TraceEventType


class Executor:
    def __init__(self):
 
        self._initialized = False
        self._swarm = None
        self._config: Optional[RunnableConfig] = None
        self._thread_id = None
        self._current_model = None
        self._current_llm = None
        self._processed_message_ids = set()
    
    @property
    def swarm(self):
        return self._swarm
    
    @property
    def thread_id(self):
        return self._thread_id
    
    @property
    def current_model(self):
        return self._current_model
    
    async def initialize_swarm(self, model_info: Optional[Dict[str, Any]] = None, thread_config: Optional[Dict[str, Any]] = None):
        """Initialize swarm"""
        try:
           
            self._initialized = False
            self._swarm = None
            
            if thread_config:
               
                if isinstance(thread_config, dict) and "configurable" in thread_config:
                    self._config = RunnableConfig(
                        configurable=thread_config["configurable"],
                        recursion_limit=100
                    )
                    self._thread_id = thread_config["configurable"]["thread_id"]
                else:
                  
                    self._thread_id = str(uuid.uuid4())
                    self._config = RunnableConfig(
                        configurable={"thread_id": self._thread_id},
                        recursion_limit=100
                    )
            else:
               
                self._thread_id = str(uuid.uuid4())
                self._config = RunnableConfig(
                    configurable={"thread_id": self._thread_id},
                    recursion_limit=100
                )
            
           
            if model_info:
                self._current_model = model_info
                
                
                update_llm_config(
                    model_name=model_info['model_name'],
                    provider=model_info['provider'],
                    display_name=model_info['display_name'],
                    temperature=0.0
                )
            
           
            self._current_llm = get_current_llm()
            
           
            self._swarm = await create_dynamic_swarm()
            
          
            self._initialized = True
            
            return self._thread_id
            
        except Exception as e:
            self._initialized = False
            self._swarm = None
            raise Exception(f"Swarm initialization failed: {str(e)}")
    
    async def execute_workflow(self, user_input: str, config: Optional[RunnableConfig] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute workflow
        """
        if not self.is_ready():
            raise Exception("Executor not ready - swarm not initialized")
        
     
        if self._swarm is None:
            raise Exception("Swarm is None - initialization failed")
        
      
        execution_config: Optional[RunnableConfig] = None
        if config is not None:
            execution_config = config
        else:
            execution_config = self._config
        
        # Initialize cost tracking
        cost_tracker = get_cost_tracker()
        task_id = f"workflow_{int(time.time())}"
        cost_tracker.start_task(task_id)
        workflow_start_time = time.time()
        
        # Initialize trace logging
        trace_logger = get_trace_logger()
        trace_id = trace_logger.start_workflow("red_team_swarm", user_input)
        
     
        self._processed_message_ids = set()
        
        inputs = {"messages": [HumanMessage(content=user_input)]}
        
        try:
            step_count = 0
            
            stream_result = self._swarm.astream(
                inputs,
                stream_mode="updates",
                config=execution_config,
                subgraphs=True
            )
            
            async for stream_item in stream_result:
        
                if not isinstance(stream_item, tuple) or len(stream_item) != 2:
                    continue
                    
                namespace, output = stream_item
                step_count += 1
              
                if not isinstance(output, dict):
                    continue
                    
                for node, value in output.items():
                 
                    agent_name = get_agent_name(namespace)
                    
                   
                    if isinstance(value, dict) and "messages" in value and value["messages"]:
                        messages = value["messages"]
                        if messages and isinstance(messages, list):
                            latest_message = messages[-1]
                            
                            # Track LLM calls for cost monitoring and tracing
                            if isinstance(latest_message, AIMessage) and hasattr(latest_message, 'usage_metadata'):
                                usage = latest_message.usage_metadata
                                if usage:
                                    model = getattr(latest_message, 'response_metadata', {}).get('model_name', 'gpt-4o-mini')
                                    cost_tracker.log_llm_call(
                                        model=model,
                                        input_tokens=usage.get("input_tokens", 0),
                                        output_tokens=usage.get("output_tokens", 0)
                                    )
                                    
                                    # Log agent response in trace
                                    trace_logger.log_agent_response(
                                        agent_name=agent_name,
                                        response=extract_message_content(latest_message),
                                        metadata={
                                            "model": model,
                                            "input_tokens": usage.get("input_tokens", 0),
                                            "output_tokens": usage.get("output_tokens", 0)
                                        }
                                    )
                            
                            should_display, message_type = self._should_display_message(
                                latest_message, agent_name, step_count
                            )
                            
                            if should_display:
                                
                                event_data = {
                                    "type": "message",
                                    "message_type": message_type,
                                    "agent_name": agent_name,
                                    "namespace": namespace,
                                    "content": extract_message_content(latest_message),
                                    "raw_message": latest_message,
                                    "step_count": step_count,
                                    "timestamp": datetime.now().isoformat()
                                }
                                
                              
                                if message_type == "tool":
                                    tool_name = getattr(latest_message, 'name', 'Unknown Tool')
                                    event_data["tool_name"] = tool_name
                                    event_data["tool_display_name"] = parse_tool_name(tool_name)
                                
                                yield event_data
            
            # End cost tracking and trace logging
            metrics = cost_tracker.end_task(task_id)
            workflow_duration = time.time() - workflow_start_time
            
            trace = trace_logger.end_workflow(status="completed")
            
            yield {
                "type": "workflow_complete",
                "step_count": step_count,
                "timestamp": datetime.now().isoformat(),
                "trace_id": trace_id,
                "metrics": {
                    "total_tokens": metrics.total_tokens,
                    "input_tokens": metrics.total_input_tokens,
                    "output_tokens": metrics.total_output_tokens,
                    "total_cost": metrics.total_cost,
                    "duration": workflow_duration,
                    "num_llm_calls": len(metrics.llm_calls)
                }
            }
            
        except asyncio.CancelledError:
            # Log error in trace
            trace_logger.log_error("Workflow execution cancelled")
            trace_logger.end_workflow(status="failed", error="Workflow cancelled")
            
            yield {
                "type": "error",
                "error": "Workflow execution cancelled",
                "timestamp": datetime.now().isoformat()
            }
            raise  
            
        except Exception as e:
            # Log error in trace
            trace_logger.log_error(str(e), exception=e)
            trace_logger.end_workflow(status="failed", error=str(e))
            
            yield {
                "type": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _should_display_message(self, message, agent_name: str, step_count: int) -> Tuple[bool, Optional[str]]:
        """Determine whether to display message"""
        
        message_id = getattr(message, 'id', None)
        if not message_id:
            content = extract_message_content(message)
          
            message_id = f"{agent_name}_{hash(str(content))}"
        
      
        if isinstance(message, HumanMessage):
            if message_id not in self._processed_message_ids:
                self._processed_message_ids.add(message_id)
                return True, "user"
            return False, None
        
        elif isinstance(message, AIMessage):
            if message_id not in self._processed_message_ids:
                self._processed_message_ids.add(message_id)
                return True, "ai"
            return False, None
        
        elif isinstance(message, ToolMessage):
            if message_id not in self._processed_message_ids:
                self._processed_message_ids.add(message_id)
                return True, "tool"
            return False, None
        
        return False, None
    
    def get_current_model_info(self) -> Dict[str, str]:
        """Return current model info"""
        if self._current_model:
            return self._current_model
        
        try:
            config = get_current_llm_config()
            return {
                "display_name": config.display_name,
                "provider": config.provider,
                "model_name": config.model_name
            }
        except:
            return {
                "display_name": "Unknown Model",
                "provider": "Unknown",
                "model_name": "unknown"
            }
    
    async def change_model(self, model_info: Dict[str, Any]) -> bool:
        """Change model"""
        try:
            self._current_model = model_info
            
            update_llm_config(
                model_name=model_info['model_name'],
                provider=model_info['provider'],
                display_name=model_info['display_name'],
                temperature=0.0
            )
            
    
            self._current_llm = get_current_llm()
     
            self._swarm = await create_dynamic_swarm()
            
            return True
            
        except Exception as e:
            raise Exception(f"Model change failed: {str(e)}")
    
    def is_ready(self) -> bool:
        """Check execution ready state"""
        return (self._initialized and 
                self._swarm is not None and 
                hasattr(self._swarm, 'astream'))
    
    def reset_session(self) -> None:
        """Initialize session"""
        self._thread_id = None
        self._config = None
        self._processed_message_ids = set()
        self._initialized = False
    
    def get_state_dict(self) -> Dict[str, Any]:
        """Return state as dictionary (for session saving)"""
        return {
            "initialized": self._initialized,
            "thread_id": self._thread_id,
            "current_model": self._current_model,
            "has_swarm": self._swarm is not None
        }