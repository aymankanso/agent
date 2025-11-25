"""
Reliable tool wrapper with timeout, retry, and validation.
Wraps MCP tools with reliability patterns.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Callable
from functools import wraps

from src.utils.reliability import (
    with_timeout,
    with_retry,
    validate_tool_output,
    CircuitBreaker,
    TimeoutError,
    RetryExhaustedError
)

logger = logging.getLogger(__name__)


class ReliableToolWrapper:
    """
    Wrapper for tools with built-in reliability features.
    
    Features:
    - Automatic timeouts
    - Exponential backoff retries
    - Output validation
    - Circuit breaker for cascading failure prevention
    - Graceful error handling
    """
    
    # Default configurations for different tool types
    TOOL_CONFIGS = {
        "nmap": {"timeout": 300.0, "max_retries": 2},  # Network scans can be slow
        "masscan": {"timeout": 180.0, "max_retries": 2},
        "nuclei": {"timeout": 300.0, "max_retries": 2},
        "hydra": {"timeout": 600.0, "max_retries": 1},  # Brute force is very slow
        "sqlmap": {"timeout": 300.0, "max_retries": 2},
        "msfconsole": {"timeout": 300.0, "max_retries": 2},
        "default": {"timeout": 60.0, "max_retries": 3}
    }
    
    def __init__(
        self,
        tool_name: str,
        tool_func: Callable,
        custom_timeout: Optional[float] = None,
        custom_max_retries: Optional[int] = None,
        enable_circuit_breaker: bool = True
    ):
        """
        Initialize reliable tool wrapper.
        
        Args:
            tool_name: Name of the tool
            tool_func: Async function to wrap
            custom_timeout: Override default timeout
            custom_max_retries: Override default retry count
            enable_circuit_breaker: Enable circuit breaker pattern
        """
        self.tool_name = tool_name
        self.tool_func = tool_func
        
        # Get config for this tool type
        config = self.TOOL_CONFIGS.get(
            tool_name.lower(),
            self.TOOL_CONFIGS["default"]
        )
        
        self.timeout = custom_timeout or config["timeout"]
        self.max_retries = custom_max_retries or config["max_retries"]
        
        # Circuit breaker for this tool
        self.circuit_breaker = None
        if enable_circuit_breaker:
            self.circuit_breaker = CircuitBreaker(
                failure_threshold=5,
                timeout=120.0  # 2 minutes before retry
            )
        
        # Statistics
        self.call_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.timeout_count = 0
        self.retry_count = 0
    
    async def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute tool with reliability features.
        
        Returns:
            Dict with 'success', 'output', 'error', 'metadata' keys
        """
        self.call_count += 1
        start_time = asyncio.get_event_loop().time()
        
        # Check circuit breaker
        if self.circuit_breaker and self.circuit_breaker.state == "OPEN":
            logger.warning(
                f"Circuit breaker OPEN for tool '{self.tool_name}'. "
                f"Skipping execution."
            )
            return {
                "success": False,
                "output": None,
                "error": f"Circuit breaker is OPEN for {self.tool_name}",
                "metadata": {
                    "circuit_breaker_state": "OPEN",
                    "failure_count": self.circuit_breaker.failure_count
                }
            }
        
        # Execute with retries
        last_error = None
        for attempt in range(self.max_retries):
            try:
                # Execute with circuit breaker if enabled
                if self.circuit_breaker:
                    async with self.circuit_breaker:
                        result = await self._execute_with_timeout(*args, **kwargs)
                else:
                    result = await self._execute_with_timeout(*args, **kwargs)
                
                # Success
                self.success_count += 1
                execution_time = asyncio.get_event_loop().time() - start_time
                
                return {
                    "success": True,
                    "output": result,
                    "error": None,
                    "metadata": {
                        "execution_time": execution_time,
                        "attempts": attempt + 1,
                        "tool_name": self.tool_name
                    }
                }
                
            except TimeoutError as e:
                last_error = e
                self.timeout_count += 1
                logger.warning(
                    f"Tool '{self.tool_name}' timed out (attempt {attempt + 1}/{self.max_retries})"
                )
                
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Tool '{self.tool_name}' failed: {e} "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
            
            # Retry with exponential backoff
            if attempt < self.max_retries - 1:
                self.retry_count += 1
                delay = min(2 ** attempt, 10)  # Max 10 seconds delay
                logger.info(f"Retrying in {delay}s...")
                await asyncio.sleep(delay)
        
        # All retries exhausted
        self.failure_count += 1
        execution_time = asyncio.get_event_loop().time() - start_time
        
        return {
            "success": False,
            "output": None,
            "error": str(last_error),
            "metadata": {
                "execution_time": execution_time,
                "attempts": self.max_retries,
                "tool_name": self.tool_name,
                "error_type": type(last_error).__name__
            }
        }
    
    async def _execute_with_timeout(self, *args, **kwargs) -> str:
        """Execute with timeout"""
        try:
            result = await asyncio.wait_for(
                self.tool_func(*args, **kwargs),
                timeout=self.timeout
            )
            
            # Validate output
            validation = validate_tool_output(str(result))
            if not validation["valid"]:
                logger.warning(
                    f"Tool '{self.tool_name}' output validation warnings: "
                    f"{validation['errors']}"
                )
            
            return validation["output"]
            
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Tool '{self.tool_name}' exceeded timeout of {self.timeout}s"
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get tool execution statistics"""
        success_rate = (
            (self.success_count / self.call_count * 100)
            if self.call_count > 0
            else 0
        )
        
        return {
            "tool_name": self.tool_name,
            "call_count": self.call_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "timeout_count": self.timeout_count,
            "retry_count": self.retry_count,
            "success_rate": round(success_rate, 2),
            "circuit_breaker_state": (
                self.circuit_breaker.state
                if self.circuit_breaker
                else "DISABLED"
            )
        }
    
    def reset_statistics(self):
        """Reset statistics counters"""
        self.call_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.timeout_count = 0
        self.retry_count = 0
        
        if self.circuit_breaker:
            self.circuit_breaker.reset()


def create_reliable_tool(
    tool_name: str,
    tool_func: Callable,
    **kwargs
) -> ReliableToolWrapper:
    """
    Factory function to create a reliable tool wrapper.
    
    Args:
        tool_name: Name of the tool
        tool_func: Async function to wrap
        **kwargs: Additional configuration options
        
    Returns:
        ReliableToolWrapper instance
        
    Example:
        reliable_nmap = create_reliable_tool("nmap", nmap_scan_async)
        result = await reliable_nmap.execute(target="192.168.1.1", ports="1-1000")
    """
    return ReliableToolWrapper(tool_name, tool_func, **kwargs)


# Global registry of reliable tools
_reliable_tools: Dict[str, ReliableToolWrapper] = {}


def register_reliable_tool(
    tool_name: str,
    tool_func: Callable,
    **kwargs
) -> ReliableToolWrapper:
    """
    Register a tool in the global reliable tools registry.
    
    Args:
        tool_name: Name of the tool
        tool_func: Async function to wrap
        **kwargs: Additional configuration options
        
    Returns:
        ReliableToolWrapper instance
    """
    wrapper = create_reliable_tool(tool_name, tool_func, **kwargs)
    _reliable_tools[tool_name] = wrapper
    logger.info(f"Registered reliable tool: {tool_name}")
    return wrapper


def get_reliable_tool(tool_name: str) -> Optional[ReliableToolWrapper]:
    """Get a registered reliable tool by name"""
    return _reliable_tools.get(tool_name)


def get_all_tool_statistics() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all registered tools"""
    return {
        name: wrapper.get_statistics()
        for name, wrapper in _reliable_tools.items()
    }


def reset_all_statistics():
    """Reset statistics for all registered tools"""
    for wrapper in _reliable_tools.values():
        wrapper.reset_statistics()
    logger.info("Reset statistics for all tools")
