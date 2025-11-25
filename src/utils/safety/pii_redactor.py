"""
PII Redaction and Safety Utilities
Protects sensitive information in tool outputs
"""

import re
from typing import Pattern, List, Tuple


# PII Patterns
PII_PATTERNS: List[Tuple[str, Pattern, str]] = [
    # Social Security Numbers (US)
    ("SSN", re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), "[SSN REDACTED]"),
    ("SSN_ALT", re.compile(r'\b\d{9}\b'), "[SSN REDACTED]"),
    
    # Credit Card Numbers
    ("CC_VISA", re.compile(r'\b4\d{3}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'), "[CREDIT CARD REDACTED]"),
    ("CC_MASTER", re.compile(r'\b5[1-5]\d{2}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'), "[CREDIT CARD REDACTED]"),
    ("CC_AMEX", re.compile(r'\b3[47]\d{2}[\s-]?\d{6}[\s-]?\d{5}\b'), "[CREDIT CARD REDACTED]"),
    ("CC_GENERIC", re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'), "[CREDIT CARD REDACTED]"),
    
    # Email Addresses
    ("EMAIL", re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), "[EMAIL REDACTED]"),
    
    # Phone Numbers (US)
    ("PHONE_US", re.compile(r'\b\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b'), "[PHONE REDACTED]"),
    
    # IP Addresses (Private ranges - might contain PII in logs)
    ("IP_PRIVATE", re.compile(r'\b192\.168\.\d{1,3}\.\d{1,3}\b'), "[IP REDACTED]"),
    ("IP_PRIVATE_10", re.compile(r'\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'), "[IP REDACTED]"),
    
    # API Keys (generic patterns)
    ("API_KEY", re.compile(r'\b[A-Za-z0-9]{32,}\b'), "[API KEY REDACTED]"),
    
    # Passwords in common formats
    ("PASSWORD_FIELD", re.compile(r'password[\s:=]+[^\s]+', re.IGNORECASE), "password=[REDACTED]"),
    ("PASS_FIELD", re.compile(r'pass[\s:=]+[^\s]+', re.IGNORECASE), "pass=[REDACTED]"),
    
    # AWS Keys
    ("AWS_KEY", re.compile(r'AKIA[0-9A-Z]{16}'), "[AWS KEY REDACTED]"),
    
    # Private SSH Keys
    ("SSH_PRIVATE", re.compile(r'-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----.*?-----END (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----', re.DOTALL), "[SSH PRIVATE KEY REDACTED]"),
]


def redact_pii(text: str, aggressive: bool = False) -> str:
    """
    Redact personally identifiable information from text
    
    Args:
        text: Input text potentially containing PII
        aggressive: If True, redact more aggressively (may have false positives)
    
    Returns:
        Text with PII redacted
    """
    if not text:
        return text
    
    redacted = text
    
    # Apply all PII patterns
    for pattern_name, pattern, replacement in PII_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    
    if aggressive:
        # Additional aggressive patterns (higher false positive rate)
        # Redact anything that looks like a password hash
        redacted = re.sub(r'\$[0-9a-z]+\$[^$]+\$[A-Za-z0-9+/=]+', '[PASSWORD HASH REDACTED]', redacted)
        
        # Redact long alphanumeric strings (potential tokens/secrets)
        redacted = re.sub(r'\b[A-Za-z0-9]{40,}\b', '[TOKEN REDACTED]', redacted)
    
    return redacted


def redact_credentials(text: str) -> str:
    """
    Specifically redact usernames and passwords from tool outputs
    
    Args:
        text: Tool output text
    
    Returns:
        Text with credentials redacted
    """
    if not text:
        return text
    
    redacted = text
    
    # Common credential patterns in tool outputs
    patterns = [
        (r'username[\s:=]+[^\s\n]+', 'username=[REDACTED]'),
        (r'user[\s:=]+[^\s\n]+', 'user=[REDACTED]'),
        (r'password[\s:=]+[^\s\n]+', 'password=[REDACTED]'),
        (r'passwd[\s:=]+[^\s\n]+', 'passwd=[REDACTED]'),
        (r'pwd[\s:=]+[^\s\n]+', 'pwd=[REDACTED]'),
        (r'token[\s:=]+[^\s\n]+', 'token=[REDACTED]'),
        (r'api[_-]?key[\s:=]+[^\s\n]+', 'api_key=[REDACTED]'),
        (r'secret[\s:=]+[^\s\n]+', 'secret=[REDACTED]'),
    ]
    
    for pattern, replacement in patterns:
        redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
    
    return redacted


def is_sensitive_output(text: str) -> bool:
    """
    Check if text contains potentially sensitive information
    
    Args:
        text: Text to check
    
    Returns:
        True if sensitive content detected
    """
    if not text:
        return False
    
    text_lower = text.lower()
    
    # Keywords indicating sensitive data
    sensitive_keywords = [
        'password', 'passwd', 'pwd',
        'secret', 'api key', 'token',
        'credit card', 'ssn', 'social security',
        'private key', 'certificate',
        'credential', 'auth',
    ]
    
    return any(keyword in text_lower for keyword in sensitive_keywords)


def sanitize_tool_output(output: str, tool_name: str = None) -> str:
    """
    Comprehensive sanitization of tool outputs
    
    Args:
        output: Raw tool output
        tool_name: Name of the tool (for context-specific sanitization)
    
    Returns:
        Sanitized output safe for display/logging
    """
    if not output:
        return output
    
    # Start with PII redaction
    sanitized = redact_pii(output)
    
    # Redact credentials
    sanitized = redact_credentials(sanitized)
    
    # Tool-specific sanitization
    if tool_name:
        tool_lower = tool_name.lower()
        
        if 'hydra' in tool_lower or 'crack' in tool_lower:
            # Redact found credentials from brute force tools
            sanitized = re.sub(r'login:\s*[^\s]+\s+password:\s*[^\s]+', 
                             'login:[REDACTED] password:[REDACTED]', 
                             sanitized, flags=re.IGNORECASE)
        
        elif 'msfconsole' in tool_lower or 'metasploit' in tool_lower:
            # Redact session tokens and IDs that might be sensitive
            sanitized = re.sub(r'session\s+\d+\s+opened', 'session [ID] opened', sanitized)
        
        elif 'sqlmap' in tool_lower:
            # Redact database credentials found by sqlmap
            sanitized = re.sub(r'database management system users password hashes:.*?(?=\n\n|\Z)', 
                             'database management system users password hashes: [REDACTED]', 
                             sanitized, flags=re.DOTALL)
    
    return sanitized


class SafetyGuard:
    """Safety guard for high-risk operations"""
    
    @staticmethod
    def requires_confirmation(tool_name: str) -> bool:
        """
        Check if tool requires user confirmation before execution
        
        Args:
            tool_name: Name of the tool
        
        Returns:
            True if confirmation needed
        """
        high_risk_tools = [
            'msfconsole',  # Metasploit exploitation
            'msfvenom',    # Payload generation
            'sqlmap',      # SQL injection (can modify data)
        ]
        
        return any(risky in tool_name.lower() for risky in high_risk_tools)
    
    @staticmethod
    def get_confirmation_message(tool_name: str, target: str) -> str:
        """
        Generate confirmation message for high-risk operations
        
        Args:
            tool_name: Name of the tool
            target: Target system
        
        Returns:
            Confirmation message
        """
        return f"""
⚠️  HIGH-RISK OPERATION DETECTED ⚠️

Tool: {tool_name}
Target: {target}

This operation may modify the target system or attempt exploitation.

IMPORTANT:
✓ Ensure you have WRITTEN AUTHORIZATION to test this target
✓ Confirm this is NOT a production system
✓ Verify this is within the scope of your engagement

Do you want to proceed? (This requires user confirmation)
"""
    
    @staticmethod
    def is_authorized_target(target: str) -> bool:
        """
        Basic check if target appears to be authorized
        
        Args:
            target: Target IP/domain
        
        Returns:
            True if appears authorized (basic heuristics)
        """
        # Production-like domains (should require extra confirmation)
        production_keywords = [
            'production', 'prod', 'live',
            'api.', 'www.',
            '.gov', '.mil',  # Government/military
        ]
        
        target_lower = target.lower()
        
        # If contains production keywords, flag for review
        if any(keyword in target_lower for keyword in production_keywords):
            return False
        
        # Private IP ranges are usually OK for testing
        private_ranges = [
            r'^192\.168\.',
            r'^10\.',
            r'^172\.(1[6-9]|2[0-9]|3[01])\.',
            r'^127\.',
        ]
        
        for pattern in private_ranges:
            if re.match(pattern, target):
                return True
        
        # localhost variations
        if target in ['localhost', '127.0.0.1', '::1']:
            return True
        
        # Default: require confirmation for unknown targets
        return False


# Export main functions
__all__ = [
    'redact_pii',
    'redact_credentials',
    'is_sensitive_output',
    'sanitize_tool_output',
    'SafetyGuard'
]
