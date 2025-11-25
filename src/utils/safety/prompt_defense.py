"""
Prompt injection detection and input sanitization for AI Red Teaming system.
Protects against adversarial inputs that could manipulate agent behavior.
"""

import re
from typing import List, Tuple, Optional


# Prompt injection patterns
INJECTION_PATTERNS = [
    # Direct instruction injection
    (r"ignore (previous|above|prior) (instructions?|prompts?|commands?)", "instruction_override"),
    (r"disregard (your|the) (instructions?|system prompt)", "instruction_override"),
    (r"forget (everything|all|your instructions?)", "instruction_override"),
    
    # Role manipulation
    (r"you are now", "role_manipulation"),
    (r"act as (if )?you (are|were)", "role_manipulation"),
    (r"pretend (to be|you are)", "role_manipulation"),
    (r"simulate (being )?a", "role_manipulation"),
    
    # System prompt extraction
    (r"(show|reveal|print|display|output) (your|the) (system prompt|instructions?)", "prompt_extraction"),
    (r"what (is|are) your (instructions?|system prompt|rules)", "prompt_extraction"),
    (r"repeat (your|the) (instructions?|system prompt)", "prompt_extraction"),
    
    # Jailbreak attempts
    (r"developer mode", "jailbreak"),
    (r"DAN mode", "jailbreak"),
    (r"do anything now", "jailbreak"),
    (r"without (any )?restrictions?", "jailbreak"),
    (r"bypass (your|the) (limitations?|restrictions?|safety)", "jailbreak"),
    
    # Token manipulation
    (r"<\|.*?\|>", "token_injection"),
    (r"\[SYSTEM\]", "token_injection"),
    (r"\[INST\]", "token_injection"),
    
    # Code injection attempts
    (r"```python.*?import os.*?```", "code_injection"),
    (r"```.*?exec\(", "code_injection"),
    (r"```.*?eval\(", "code_injection"),
    
    # Excessive special characters (possible obfuscation)
    (r"[^a-zA-Z0-9\s]{20,}", "obfuscation"),
]


def detect_prompt_injection(user_input: str) -> Tuple[bool, List[str], float]:
    """
    Detect potential prompt injection attempts.
    
    Args:
        user_input: User's input text
        
    Returns:
        Tuple of (is_suspicious, detected_patterns, risk_score)
        - is_suspicious: True if injection detected
        - detected_patterns: List of detected pattern types
        - risk_score: 0.0-1.0 risk score
    """
    if not user_input:
        return False, [], 0.0
    
    user_input_lower = user_input.lower()
    detected_patterns = []
    
    # Check each pattern
    for pattern, pattern_type in INJECTION_PATTERNS:
        if re.search(pattern, user_input_lower, re.IGNORECASE | re.DOTALL):
            detected_patterns.append(pattern_type)
    
    # Calculate risk score
    if not detected_patterns:
        risk_score = 0.0
    else:
        # Different patterns have different weights
        pattern_weights = {
            "instruction_override": 0.9,
            "role_manipulation": 0.8,
            "prompt_extraction": 0.7,
            "jailbreak": 0.95,
            "token_injection": 0.85,
            "code_injection": 0.9,
            "obfuscation": 0.6
        }
        
        # Max weight of detected patterns
        risk_score = max(
            pattern_weights.get(p, 0.5) for p in detected_patterns
        )
    
    is_suspicious = risk_score >= 0.7
    
    return is_suspicious, detected_patterns, risk_score


def sanitize_user_input(user_input: str, aggressive: bool = False) -> str:
    """
    Sanitize user input to remove potentially dangerous content.
    
    Args:
        user_input: Raw user input
        aggressive: If True, apply more aggressive filtering
        
    Returns:
        Sanitized input
    """
    if not user_input:
        return user_input
    
    sanitized = user_input
    
    # Remove special tokens that could confuse the model
    special_tokens = [
        r"<\|.*?\|>",
        r"\[SYSTEM\]",
        r"\[/SYSTEM\]",
        r"\[INST\]",
        r"\[/INST\]",
        r"<s>",
        r"</s>",
        r"<<<",
        r">>>",
    ]
    
    for token in special_tokens:
        sanitized = re.sub(token, "", sanitized, flags=re.IGNORECASE)
    
    if aggressive:
        # Remove code blocks in aggressive mode
        sanitized = re.sub(r"```.*?```", "[CODE BLOCK REMOVED]", sanitized, flags=re.DOTALL)
        
        # Limit excessive special characters
        sanitized = re.sub(r"[^a-zA-Z0-9\s.,:;!?'\"-_()]{10,}", "[SPECIAL CHARS REMOVED]", sanitized)
    
    # Trim whitespace
    sanitized = sanitized.strip()
    
    return sanitized


def get_injection_warning(detected_patterns: List[str]) -> str:
    """
    Generate warning message for detected injection attempts.
    
    Args:
        detected_patterns: List of detected pattern types
        
    Returns:
        Warning message
    """
    pattern_descriptions = {
        "instruction_override": "Instruction Override - Attempting to change system behavior",
        "role_manipulation": "Role Manipulation - Trying to change agent identity",
        "prompt_extraction": "Prompt Extraction - Attempting to reveal system instructions",
        "jailbreak": "Jailbreak Attempt - Trying to bypass safety restrictions",
        "token_injection": "Token Injection - Using special model tokens",
        "code_injection": "Code Injection - Embedded executable code",
        "obfuscation": "Obfuscation - Unusual character patterns"
    }
    
    warning = "⚠️  PROMPT INJECTION DETECTED ⚠️\n\n"
    warning += "Detected suspicious patterns:\n"
    
    for pattern in detected_patterns:
        desc = pattern_descriptions.get(pattern, pattern)
        warning += f"  • {desc}\n"
    
    warning += "\nYour input has been flagged for security review.\n"
    warning += "If this was unintentional, please rephrase your request.\n"
    
    return warning


def validate_safe_input(user_input: str, max_length: int = 10000) -> Tuple[bool, Optional[str]]:
    """
    Comprehensive validation of user input.
    
    Args:
        user_input: User's input
        max_length: Maximum allowed length
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not user_input or not user_input.strip():
        return False, "Input is empty"
    
    if len(user_input) > max_length:
        return False, f"Input too long ({len(user_input)} > {max_length} characters)"
    
    # Check for prompt injection
    is_suspicious, detected_patterns, risk_score = detect_prompt_injection(user_input)
    
    if is_suspicious:
        warning = get_injection_warning(detected_patterns)
        return False, warning
    
    return True, None


class InputGuard:
    """
    Input guard with configurable security levels.
    """
    
    def __init__(self, security_level: str = "medium"):
        """
        Initialize input guard.
        
        Args:
            security_level: low, medium, high
        """
        self.security_level = security_level
        self.blocked_count = 0
        self.total_count = 0
    
    def check_input(self, user_input: str) -> Tuple[bool, str, Optional[str]]:
        """
        Check if input is safe.
        
        Args:
            user_input: User's input
            
        Returns:
            Tuple of (is_safe, sanitized_input, warning)
        """
        self.total_count += 1
        
        # Validate
        is_valid, error = validate_safe_input(user_input)
        
        if not is_valid:
            self.blocked_count += 1
            return False, user_input, error
        
        # Sanitize based on security level
        if self.security_level == "high":
            sanitized = sanitize_user_input(user_input, aggressive=True)
        elif self.security_level == "medium":
            sanitized = sanitize_user_input(user_input, aggressive=False)
        else:  # low
            sanitized = user_input.strip()
        
        # Check if sanitization changed the input significantly
        if len(sanitized) < len(user_input) * 0.5:
            self.blocked_count += 1
            return False, sanitized, "Input was heavily modified by sanitization. Please rephrase."
        
        return True, sanitized, None
    
    def get_statistics(self) -> dict:
        """Get input guard statistics"""
        block_rate = (
            (self.blocked_count / self.total_count * 100)
            if self.total_count > 0
            else 0
        )
        
        return {
            "total_inputs": self.total_count,
            "blocked_inputs": self.blocked_count,
            "block_rate": round(block_rate, 2),
            "security_level": self.security_level
        }


# Global input guard
_input_guard: Optional[InputGuard] = None


def get_input_guard(security_level: str = "medium") -> InputGuard:
    """
    Get global input guard instance (singleton).
    
    Args:
        security_level: low, medium, high
        
    Returns:
        InputGuard instance
    """
    global _input_guard
    if _input_guard is None:
        _input_guard = InputGuard(security_level=security_level)
    return _input_guard
