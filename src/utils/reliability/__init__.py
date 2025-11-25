"""
Reliability utilities for the AI Red Teaming Multi-Agent System.
Provides timeout handling, retry logic, and schema validation.
"""

import time
import asyncio
from typing import Callable, Any, Optional, Dict, Type, TypeVar
from functools import wraps
from pydantic import BaseModel, ValidationError
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TimeoutError(Exception):
    """Raised when an operation times out"""
    pass


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted"""
    pass


class ValidationFailedError(Exception):
    """Raised when schema validation fails"""
    pass


def with_timeout(timeout_seconds: float):
    """
    Decorator to add timeout to async functions.
    
    Args:
        timeout_seconds: Maximum execution time in seconds
        
    Example:
        @with_timeout(30.0)
        async def long_running_task():
            await asyncio.sleep(100)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"Operation '{func.__name__}' timed out after {timeout_seconds}s"
                )
        return wrapper
    return decorator


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to add exponential backoff retry logic to async functions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        exceptions: Tuple of exceptions to catch and retry
        
    Example:
        @with_retry(max_attempts=3, initial_delay=1.0)
        async def flaky_api_call():
            response = await make_request()
            return response
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        # Last attempt failed
                        logger.error(
                            f"Function '{func.__name__}' failed after {max_attempts} attempts: {e}"
                        )
                        raise RetryExhaustedError(
                            f"Failed after {max_attempts} attempts. Last error: {e}"
                        ) from e
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        initial_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for '{func.__name__}'. "
                        f"Retrying in {delay:.2f}s... Error: {e}"
                    )
                    
                    await asyncio.sleep(delay)
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator


def validate_schema(schema: Type[BaseModel], strict: bool = True):
    """
    Decorator to validate function output against a Pydantic schema.
    
    Args:
        schema: Pydantic BaseModel class to validate against
        strict: If True, raise exception on validation failure. If False, log warning and return None.
        
    Example:
        class OutputSchema(BaseModel):
            result: str
            count: int
            
        @validate_schema(OutputSchema)
        async def get_data():
            return {"result": "success", "count": 42}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            try:
                # Validate output
                if isinstance(result, dict):
                    validated = schema(**result)
                    return validated.dict()
                elif isinstance(result, schema):
                    return result
                else:
                    # Try to convert to dict
                    validated = schema(**result.__dict__)
                    return validated.dict()
                    
            except ValidationError as e:
                error_msg = f"Schema validation failed for '{func.__name__}': {e}"
                
                if strict:
                    logger.error(error_msg)
                    raise ValidationFailedError(error_msg) from e
                else:
                    logger.warning(f"{error_msg}. Returning original result.")
                    return result
        
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for preventing cascading failures.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service recovered
    
    Example:
        breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        
        async def call_external_service():
            async with breaker:
                return await service.call()
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before trying again (OPEN -> HALF_OPEN)
            expected_exception: Exception type that counts as failure
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
        self._lock = asyncio.Lock()
    
    async def __aenter__(self):
        """Enter context manager"""
        async with self._lock:
            if self.state == "OPEN":
                # Check if timeout has passed
                if time.time() - self.last_failure_time >= self.timeout:
                    logger.info("Circuit breaker entering HALF_OPEN state")
                    self.state = "HALF_OPEN"
                else:
                    raise Exception(
                        f"Circuit breaker is OPEN. "
                        f"Tried {self.failure_count} times. "
                        f"Wait {self.timeout - (time.time() - self.last_failure_time):.1f}s"
                    )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager"""
        async with self._lock:
            if exc_type is None:
                # Success
                if self.state == "HALF_OPEN":
                    logger.info("Circuit breaker closing after successful test")
                    self.state = "CLOSED"
                    self.failure_count = 0
                    self.last_failure_time = None
            elif isinstance(exc_val, self.expected_exception):
                # Failure
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.state == "HALF_OPEN":
                    logger.warning("Circuit breaker re-opening after failed test")
                    self.state = "OPEN"
                elif self.failure_count >= self.failure_threshold:
                    logger.error(
                        f"Circuit breaker opening after {self.failure_count} failures"
                    )
                    self.state = "OPEN"
        
        return False  # Don't suppress exception
    
    def reset(self):
        """Manually reset circuit breaker"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"
        logger.info("Circuit breaker manually reset")


async def with_fallback(
    primary_func: Callable,
    fallback_func: Callable,
    *args,
    **kwargs
) -> Any:
    """
    Execute primary function with fallback on failure.
    
    Args:
        primary_func: Primary async function to try
        fallback_func: Fallback async function if primary fails
        *args: Arguments to pass to functions
        **kwargs: Keyword arguments to pass to functions
        
    Returns:
        Result from primary or fallback function
        
    Example:
        result = await with_fallback(
            expensive_api_call,
            cached_fallback,
            user_id=123
        )
    """
    try:
        return await primary_func(*args, **kwargs)
    except Exception as e:
        logger.warning(
            f"Primary function '{primary_func.__name__}' failed: {e}. "
            f"Using fallback '{fallback_func.__name__}'"
        )
        return await fallback_func(*args, **kwargs)


class RateLimiter:
    """
    Rate limiter using token bucket algorithm.
    
    Example:
        limiter = RateLimiter(rate=10, per=60)  # 10 requests per 60 seconds
        
        async def make_request():
            async with limiter:
                return await api.call()
    """
    
    def __init__(self, rate: int, per: float):
        """
        Initialize rate limiter.
        
        Args:
            rate: Number of tokens
            per: Time period in seconds
        """
        self.rate = rate
        self.per = per
        self.tokens = rate
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def __aenter__(self):
        """Acquire token"""
        async with self._lock:
            # Refill tokens
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(
                self.rate,
                self.tokens + (elapsed * self.rate / self.per)
            )
            self.last_update = now
            
            # Wait if no tokens available
            if self.tokens < 1:
                wait_time = (1 - self.tokens) * self.per / self.rate
                logger.info(f"Rate limit reached. Waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self.tokens = 1
                self.last_update = time.time()
            
            self.tokens -= 1
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager"""
        return False


# Helper function for tool output validation
def validate_tool_output(
    output: str,
    max_length: int = 100000,
    required_fields: Optional[list] = None
) -> Dict[str, Any]:
    """
    Validate and sanitize tool output.
    
    Args:
        output: Raw tool output string
        max_length: Maximum allowed output length
        required_fields: List of required fields if output is JSON
        
    Returns:
        Validation result dict with 'valid', 'output', 'errors' keys
        
    Example:
        result = validate_tool_output(tool_result, max_length=50000)
        if result['valid']:
            return result['output']
    """
    errors = []
    
    # Check length
    if len(output) > max_length:
        errors.append(f"Output too long: {len(output)} > {max_length} chars")
        output = output[:max_length] + "\n... [truncated]"
    
    # Try to parse as JSON if required_fields specified
    if required_fields:
        try:
            import json
            data = json.loads(output)
            
            for field in required_fields:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
        except json.JSONDecodeError:
            errors.append("Output is not valid JSON")
    
    return {
        "valid": len(errors) == 0,
        "output": output,
        "errors": errors
    }
