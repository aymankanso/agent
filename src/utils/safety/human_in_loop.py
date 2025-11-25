"""
Human-in-the-loop safety mechanism for high-risk operations.
Requires explicit user approval before executing dangerous actions.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Status of approval request"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


@dataclass
class ApprovalRequest:
    """Request for human approval"""
    request_id: str
    tool_name: str
    target: str
    operation: str
    risk_level: str  # low, medium, high, critical
    timestamp: datetime
    status: ApprovalStatus = ApprovalStatus.PENDING
    user_response: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "target": self.target,
            "operation": self.operation,
            "risk_level": self.risk_level,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "user_response": self.user_response,
            "metadata": self.metadata or {}
        }


class HumanApprovalRequired(Exception):
    """Exception raised when human approval is required"""
    def __init__(self, request: ApprovalRequest):
        self.request = request
        super().__init__(f"Human approval required for {request.tool_name} on {request.target}")


class HumanInLoopManager:
    """
    Manages human-in-the-loop approvals for high-risk operations.
    
    Features:
    - Risk-based approval requirements
    - Approval request tracking
    - Timeout handling
    - Audit logging
    """
    
    # Tools requiring approval by risk level
    RISK_LEVELS = {
        "critical": [
            "msfconsole",
            "msfvenom",
            "exploit",
        ],
        "high": [
            "sqlmap",
            "hydra",
            "medusa",
            "john",
            "hashcat",
        ],
        "medium": [
            "nikto",
            "dirb",
            "gobuster",
            "wpscan",
        ],
        "low": [
            "nmap",
            "masscan",
            "nuclei",
            "whois",
            "dig",
        ]
    }
    
    def __init__(self, auto_approve_low_risk: bool = True):
        """
        Initialize human-in-loop manager.
        
        Args:
            auto_approve_low_risk: Auto-approve low-risk operations
        """
        self.auto_approve_low_risk = auto_approve_low_risk
        self.pending_requests: Dict[str, ApprovalRequest] = {}
        self.approval_history: List[ApprovalRequest] = []
        
        # Callback for UI integration
        self.approval_callback: Optional[Callable] = None
    
    def set_approval_callback(self, callback: Callable):
        """
        Set callback function for approval requests.
        
        Callback should accept ApprovalRequest and return ApprovalStatus.
        This allows UI integration for user prompts.
        """
        self.approval_callback = callback
    
    def get_risk_level(self, tool_name: str) -> str:
        """Determine risk level of a tool"""
        tool_lower = tool_name.lower()
        
        for risk_level, tools in self.RISK_LEVELS.items():
            if any(risky_tool in tool_lower for risky_tool in tools):
                return risk_level
        
        # Unknown tools default to medium risk
        return "medium"
    
    def requires_approval(self, tool_name: str, target: str) -> bool:
        """
        Check if operation requires human approval.
        
        Args:
            tool_name: Name of the tool
            target: Target system
            
        Returns:
            True if approval required
        """
        risk_level = self.get_risk_level(tool_name)
        
        # Auto-approve low risk if configured
        if risk_level == "low" and self.auto_approve_low_risk:
            return False
        
        # Check if target is production-like
        from .pii_redactor import SafetyGuard
        if not SafetyGuard.is_authorized_target(target):
            logger.warning(f"Target '{target}' appears to be unauthorized or production")
            return True
        
        # High and critical always require approval
        if risk_level in ["high", "critical"]:
            return True
        
        return False
    
    async def request_approval(
        self,
        tool_name: str,
        target: str,
        operation: str,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: float = 300.0  # 5 minutes default
    ) -> ApprovalStatus:
        """
        Request human approval for an operation.
        
        Args:
            tool_name: Name of the tool
            target: Target system
            operation: Description of operation
            metadata: Additional context
            timeout: Timeout in seconds
            
        Returns:
            ApprovalStatus
            
        Raises:
            HumanApprovalRequired: If approval callback not set
        """
        risk_level = self.get_risk_level(tool_name)
        
        # Create approval request
        request = ApprovalRequest(
            request_id=f"approval_{int(datetime.now().timestamp() * 1000)}",
            tool_name=tool_name,
            target=target,
            operation=operation,
            risk_level=risk_level,
            timestamp=datetime.now(),
            metadata=metadata
        )
        
        self.pending_requests[request.request_id] = request
        
        logger.info(
            f"Approval requested: {tool_name} on {target} "
            f"(risk: {risk_level}, id: {request.request_id})"
        )
        
        # If no callback, raise exception for manual handling
        if self.approval_callback is None:
            raise HumanApprovalRequired(request)
        
        # Use callback to get approval
        try:
            status = await asyncio.wait_for(
                self._get_approval_via_callback(request),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Approval request {request.request_id} timed out")
            status = ApprovalStatus.TIMEOUT
        
        # Update request
        request.status = status
        del self.pending_requests[request.request_id]
        self.approval_history.append(request)
        
        logger.info(f"Approval {request.request_id} result: {status.value}")
        
        return status
    
    async def _get_approval_via_callback(self, request: ApprovalRequest) -> ApprovalStatus:
        """Get approval via callback function"""
        if asyncio.iscoroutinefunction(self.approval_callback):
            return await self.approval_callback(request)
        else:
            return self.approval_callback(request)
    
    def approve_request(self, request_id: str, user_response: Optional[str] = None):
        """Manually approve a pending request"""
        if request_id in self.pending_requests:
            request = self.pending_requests[request_id]
            request.status = ApprovalStatus.APPROVED
            request.user_response = user_response
            logger.info(f"Request {request_id} approved")
    
    def reject_request(self, request_id: str, user_response: Optional[str] = None):
        """Manually reject a pending request"""
        if request_id in self.pending_requests:
            request = self.pending_requests[request_id]
            request.status = ApprovalStatus.REJECTED
            request.user_response = user_response
            logger.info(f"Request {request_id} rejected")
    
    def get_pending_requests(self) -> List[ApprovalRequest]:
        """Get all pending approval requests"""
        return list(self.pending_requests.values())
    
    def get_approval_history(self, limit: int = 50) -> List[ApprovalRequest]:
        """Get approval history"""
        return self.approval_history[-limit:]
    
    def get_approval_statistics(self) -> Dict[str, Any]:
        """Get approval statistics"""
        total = len(self.approval_history)
        if total == 0:
            return {
                "total_requests": 0,
                "approved": 0,
                "rejected": 0,
                "timeout": 0,
                "approval_rate": 0.0
            }
        
        approved = sum(1 for r in self.approval_history if r.status == ApprovalStatus.APPROVED)
        rejected = sum(1 for r in self.approval_history if r.status == ApprovalStatus.REJECTED)
        timeout = sum(1 for r in self.approval_history if r.status == ApprovalStatus.TIMEOUT)
        
        return {
            "total_requests": total,
            "approved": approved,
            "rejected": rejected,
            "timeout": timeout,
            "approval_rate": round(approved / total * 100, 2)
        }


# Global manager instance
_hil_manager: Optional[HumanInLoopManager] = None


def get_hil_manager(auto_approve_low_risk: bool = True) -> HumanInLoopManager:
    """
    Get global human-in-loop manager (singleton).
    
    Args:
        auto_approve_low_risk: Auto-approve low-risk operations
        
    Returns:
        HumanInLoopManager instance
    """
    global _hil_manager
    if _hil_manager is None:
        _hil_manager = HumanInLoopManager(auto_approve_low_risk=auto_approve_low_risk)
    return _hil_manager
