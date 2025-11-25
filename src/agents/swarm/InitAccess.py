from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langmem import create_manage_memory_tool, create_search_memory_tool
from src.prompts.prompt_loader import load_prompt
from src.tools.handoff import handoff_to_planner, handoff_to_reconnaissance, handoff_to_summary
from src.utils.llm.config_manager import get_current_llm
from src.utils.memory import get_store 
from langchain_anthropic import ChatAnthropic
from src.utils.mcp.mcp_loader import load_mcp_tools
import logging

logger = logging.getLogger(__name__)

async def make_initaccess_agent():
    llm = get_current_llm()
    
    if llm is None:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        logger.warning("Using default LLM model (GPT-4o Mini)")
    
    store = get_store()
    
    logger.info("🔧 Loading MCP tools for Initial_Access agent...")
    mcp_tools = await load_mcp_tools(agent_name=["initial_access"])
    logger.info(f"✅ Loaded {len(mcp_tools)} MCP tools for Initial_Access")

    swarm_tools = [
        handoff_to_reconnaissance,
        handoff_to_planner,
        handoff_to_summary,
    ]

    mem_tools = [
        create_manage_memory_tool(namespace=("memories",)),
        create_search_memory_tool(namespace=("memories",))
    ]

    tools = mcp_tools + swarm_tools + mem_tools
    
    logger.info(f"📋 Total tools for Initial_Access: {len(tools)} (MCP: {len(mcp_tools)}, Handoff: {len(swarm_tools)}, Memory: {len(mem_tools)})")
    if mcp_tools:
        tool_names = [t.name for t in mcp_tools]
        logger.info(f"🛠️  Available MCP tools: {', '.join(tool_names)}")
    else:
        logger.error("❌ WARNING: No MCP tools loaded for Initial_Access agent! Check if port 3002 is running.")

    agent = create_react_agent(
        llm,  # Standardized parameter usage
        tools=tools,
        store=store,
        name="Initial_Access",
        prompt=load_prompt("initial_access", "swarm"),
    )
    return agent