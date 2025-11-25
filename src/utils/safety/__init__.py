"""
Safety and Ethics Module for AI Red Teaming System.
"""

from .pii_redactor import (
    redact_pii,
    redact_credentials,
    is_sensitive_output,
    sanitize_tool_output,
    SafetyGuard
)
from .human_in_loop import HumanApprovalRequired, HumanInLoopManager, ApprovalStatus, get_hil_manager
from .disclaimers import get_disclaimer, show_startup_disclaimer, get_tool_warning, get_legal_notice
from .prompt_defense import detect_prompt_injection, sanitize_user_input, get_input_guard, InputGuard

__all__ = [
    "redact_pii",
    "redact_credentials",
    "is_sensitive_output",
    "sanitize_tool_output",
    "SafetyGuard",
    "HumanApprovalRequired",
    "HumanInLoopManager",
    "ApprovalStatus",
    "get_hil_manager",
    "get_disclaimer",
    "show_startup_disclaimer",
    "get_tool_warning",
    "get_legal_notice",
    "detect_prompt_injection",
    "sanitize_user_input",
    "get_input_guard",
    "InputGuard"
]
