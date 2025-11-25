"""
Handoff Tool Prompts for Swarm Architecture

This file defines prompts for tools used to transfer work between agents in Swarm architecture.
"""

SWARM_HANDOFF_TOOLS_PROMPT = """
<swarm_handoff_tools>
## Agent Handoff Tools:

### transfer_to_Planner(task_description)
**When to use**: Need strategic planning, analysis, or tactical guidance
**Examples**: 
- Initial mission planning
- Strategy adjustment after obstacles
- Complex intelligence analysis

### transfer_to_Reconnaissance(task_description)  
**When to use**: Need specialized intelligence gathering or target enumeration
**Examples**:
- Deep service enumeration
- Network expansion discovery
- Verification of findings

### transfer_to_Initial_Access(task_description)
**When to use**: Ready for exploitation or credential attacks
**Examples**:
- Vulnerability exploitation campaign
- Authentication bypass attempts
- Post-reconnaissance exploitation

### transfer_to_Summary(task_description)
**When to use**: Need documentation of findings or phase completion
**Examples**:
- Phase completion reporting
- Critical finding documentation
- Final engagement summary

## Handoff Best Practices:
- Provide clear context and objectives
- Include all relevant findings and data
- Specify expected deliverables
- Maintain mission continuity

Use handoffs to leverage specialized expertise while maintaining operational flow.
</swarm_handoff_tools>
"""
