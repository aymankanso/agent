from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langmem import create_manage_memory_tool, create_search_memory_tool
from src.prompts.prompt_loader import load_prompt
from src.tools.handoff import handoff_to_initial_access, handoff_to_reconnaissance, handoff_to_planner
from src.utils.llm.config_manager import get_current_llm
from src.utils.memory import get_store

from src.utils.mcp.mcp_loader import load_mcp_tools

async def make_summary_agent():
    # Load LLM from memory (use default if not available)
    llm = get_current_llm()
    if llm is None:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        print("Warning: Using default LLM model (GPT-4o Mini)")
    
    # Use centralized store
    store = get_store()
    
    mcp_tools = await load_mcp_tools(agent_name=["summary"])

    swarm_tools = [
        handoff_to_reconnaissance, 
        handoff_to_initial_access,
        handoff_to_planner,
    ]

    mem_tools = [
        create_manage_memory_tool(namespace=("memories",)),
        create_search_memory_tool(namespace=("memories",))
    ]

    tools = mcp_tools + swarm_tools + mem_tools

    agent = create_react_agent(
        llm,
        tools=tools,
        store=store,
        name="Summary",
        prompt=load_prompt("summary", "swarm"),
    )
    return agent
