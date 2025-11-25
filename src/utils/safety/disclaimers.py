"""
Domain-appropriate disclaimers and legal notices for AI Red Teaming system.
"""

from typing import Optional


def get_disclaimer(disclaimer_type: str = "general") -> str:
    """
    Get appropriate disclaimer based on context.
    
    Args:
        disclaimer_type: Type of disclaimer (general, startup, tool_usage)
        
    Returns:
        Disclaimer text
    """
    disclaimers = {
        "general": """
╔══════════════════════════════════════════════════════════════════════════════╗
║                      ⚠️  LEGAL DISCLAIMER AND WARNING ⚠️                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

This AI Red Teaming Multi-Agent System is designed for AUTHORIZED SECURITY 
TESTING ONLY within controlled environments.

CRITICAL REQUIREMENTS:
✓ You MUST have WRITTEN AUTHORIZATION to test any target system
✓ Testing must be within scope of your security engagement
✓ You are SOLELY RESPONSIBLE for ensuring legal compliance
✓ Unauthorized access to computer systems is ILLEGAL

LEGAL NOTICE:
This tool is provided for educational and authorized security testing purposes.
Misuse of this system may violate:
• Computer Fraud and Abuse Act (CFAA) - 18 U.S.C. § 1030
• Electronic Communications Privacy Act (ECPA)
• State and local computer crime laws
• International cybercrime laws

PENALTIES:
Unauthorized access can result in:
• Federal criminal charges (up to 20 years imprisonment)
• Civil liability and monetary damages
• Professional license revocation
• Permanent criminal record

BY USING THIS SYSTEM, YOU ACKNOWLEDGE:
1. You have proper authorization for all testing activities
2. You understand the legal risks and consequences
3. You accept full responsibility for your actions
4. The developers are not liable for misuse

═══════════════════════════════════════════════════════════════════════════════
""",
        
        "startup": """
╔══════════════════════════════════════════════════════════════════════════════╗
║            AI RED TEAMING MULTI-AGENT SYSTEM - STARTUP NOTICE                ║
╚══════════════════════════════════════════════════════════════════════════════╝

⚠️  AUTHORIZED USE ONLY ⚠️

This system performs automated penetration testing using AI agents.

BEFORE PROCEEDING:
□ I have written authorization to test the target systems
□ I am testing within a controlled lab environment OR
□ I am testing systems I own OR
□ I have a formal penetration testing agreement

□ I understand unauthorized testing is ILLEGAL
□ I accept full legal responsibility for my actions

SAFETY FEATURES ENABLED:
✓ PII redaction in all outputs
✓ Human-in-the-loop for high-risk operations
✓ Tool execution logging and audit trail
✓ Target validation checks

If you do NOT have proper authorization, EXIT NOW.

═══════════════════════════════════════════════════════════════════════════════
Press ENTER to acknowledge and continue...
""",
        
        "tool_usage": """
⚠️  TOOL EXECUTION WARNING ⚠️

This operation will execute security testing tools that may:
• Actively scan network systems
• Attempt to identify vulnerabilities
• Generate network traffic that may trigger security alerts
• Potentially disrupt services if misconfigured

CONFIRM:
✓ Target is authorized for testing
✓ Testing is within engagement scope
✓ You have informed relevant parties (if required)

═══════════════════════════════════════════════════════════════════════════════
""",
        
        "high_risk": """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ⚠️⚠️⚠️  HIGH-RISK OPERATION  ⚠️⚠️⚠️                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

This operation involves EXPLOITATION or CREDENTIAL ATTACKS.

EXTREME CAUTION REQUIRED:
• This may modify target system state
• This may trigger security controls
• This may cause service disruption
• This requires EXPLICIT authorization

VERIFY:
□ Written authorization for EXPLOITATION (not just scanning)
□ Target is NOT a production system (unless explicitly authorized)
□ You have rollback/recovery plan
□ You have documented the engagement scope

LEGAL WARNING:
Unauthorized exploitation is a FEDERAL CRIME with severe penalties.

═══════════════════════════════════════════════════════════════════════════════
TYPE 'I UNDERSTAND THE RISKS' TO PROCEED:
""",
        
        "export_data": """
⚠️  DATA EXPORT NOTICE ⚠️

You are about to export security testing results that may contain:
• System vulnerabilities
• Network configurations
• Sensitive technical information

REQUIREMENTS:
✓ Ensure data is encrypted during transfer
✓ Store data in secure location
✓ Follow data handling guidelines from your engagement
✓ Delete data per retention policy

REMINDER:
Security testing data is confidential and must be protected according to 
your engagement terms and applicable data protection regulations.

═══════════════════════════════════════════════════════════════════════════════
"""
    }
    
    return disclaimers.get(disclaimer_type, disclaimers["general"])


def show_startup_disclaimer() -> bool:
    """
    Display startup disclaimer and wait for user acknowledgment.
    
    Returns:
        True if user acknowledged, False otherwise
    """
    print(get_disclaimer("startup"))
    
    try:
        response = input()
        return True
    except (KeyboardInterrupt, EOFError):
        print("\n⛔ Startup cancelled by user")
        return False


def get_tool_warning(tool_name: str, target: str, risk_level: str) -> str:
    """
    Generate context-specific warning for tool execution.
    
    Args:
        tool_name: Name of the tool
        target: Target system
        risk_level: Risk level (low, medium, high, critical)
        
    Returns:
        Warning message
    """
    risk_emoji = {
        "low": "ℹ️",
        "medium": "⚠️",
        "high": "⚠️⚠️",
        "critical": "🚨"
    }
    
    emoji = risk_emoji.get(risk_level, "⚠️")
    
    warning = f"""
{emoji} TOOL EXECUTION: {tool_name} {emoji}

Target: {target}
Risk Level: {risk_level.upper()}

"""
    
    if risk_level == "critical":
        warning += """This is a HIGH-RISK exploitation tool.
Ensure you have EXPLICIT authorization for exploitation attempts.
Unauthorized use is a FEDERAL CRIME.

"""
    elif risk_level == "high":
        warning += """This tool performs active attacks (credential testing, exploitation).
Verify authorization and ensure target is in scope.

"""
    elif risk_level == "medium":
        warning += """This tool performs active reconnaissance.
Confirm authorization before proceeding.

"""
    else:
        warning += """This is a passive reconnaissance tool.
Minimal risk but ensure target is authorized.

"""
    
    warning += "═" * 79
    
    return warning


def get_legal_notice() -> str:
    """Get comprehensive legal notice for documentation"""
    return """
LEGAL NOTICE AND TERMS OF USE

This AI Red Teaming Multi-Agent System is a security testing tool intended 
exclusively for authorized security professionals conducting legitimate 
penetration testing activities.

AUTHORIZED USE ONLY:
Users must have explicit written authorization from system owners before 
conducting any testing activities. This tool should only be used:
• In controlled laboratory environments
• On systems you own and operate
• Under formal penetration testing engagements with proper authorization
• For educational purposes in isolated environments

PROHIBITED USES:
The following uses are strictly prohibited and may result in criminal prosecution:
• Unauthorized access to computer systems
• Testing without proper authorization
• Malicious or harmful activities
• Violation of computer crime laws
• Breach of confidentiality or privacy

LIABILITY DISCLAIMER:
This software is provided "as is" without warranty of any kind. The developers 
and contributors are not responsible for any damages, legal consequences, or 
misuse of this tool. Users assume all risks and legal liability for their actions.

COMPLIANCE:
Users are responsible for ensuring compliance with all applicable laws including:
• Computer Fraud and Abuse Act (CFAA)
• Electronic Communications Privacy Act (ECPA)
• General Data Protection Regulation (GDPR)
• State and local laws
• Industry-specific regulations

For full license terms, see LICENSE file.
For security research ethics, consult: https://www.eff.org/issues/coders/vulnerability-reporting-faq
"""


def get_ethics_guidelines() -> str:
    """Get ethical guidelines for security testing"""
    return """
ETHICAL SECURITY TESTING GUIDELINES

Professional security testing must adhere to ethical standards:

1. AUTHORIZATION:
   ✓ Obtain written permission before testing
   ✓ Clearly define scope and boundaries
   ✓ Respect time windows and constraints

2. CONFIDENTIALITY:
   ✓ Protect sensitive information discovered
   ✓ Follow responsible disclosure practices
   ✓ Secure testing data and results

3. INTEGRITY:
   ✓ Do not cause unnecessary damage or disruption
   ✓ Report findings honestly and completely
   ✓ Maintain professional standards

4. RESPONSIBLE DISCLOSURE:
   ✓ Report vulnerabilities to system owners first
   ✓ Allow reasonable time for remediation
   ✓ Coordinate public disclosure appropriately

5. LEGAL COMPLIANCE:
   ✓ Follow all applicable laws and regulations
   ✓ Respect intellectual property rights
   ✓ Honor contractual obligations

For more information:
• SANS Ethics: https://www.sans.org/code-of-ethics/
• EC-Council Code of Ethics: https://www.eccouncil.org/code-of-ethics/
• (ISC)² Ethics: https://www.isc2.org/Ethics
"""
