import json
from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio
import logging
import httpx
from datetime import timedelta

logger = logging.getLogger(__name__)

async def check_server_health(url: str, max_retries: int = 3, retry_delay: float = 1.0) -> bool:
    """Check if MCP server is reachable with retry logic"""
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                # We accept any response (even 404/405) as proof the server is running
                await client.get(url)
                return True
        except Exception as e:
            if attempt < max_retries - 1:
                logger.debug(f"Health check attempt {attempt + 1}/{max_retries} failed for {url}, retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                logger.debug(f"Health check failed for {url} after {max_retries} attempts: {str(e)}")
    return False

async def load_mcp_tools(agent_name=None):
    try:
        with open("mcp_config.json", "r") as f:
            config = json.load(f)

        if agent_name:
            selected_agents = {agent: config[agent] for agent in agent_name if agent in config}
        else:
            selected_agents = config

        tools = []

        for agent_name, servers in selected_agents.items():
            if not servers:
                logger.info(f"No MCP servers configured for agent: {agent_name}")
                continue

            for server_name, server_config in servers.items():
                try:
                    logger.info(f"Connecting to MCP server: {server_name} at {server_config.get('url', 'N/A')}")
                    
                    # Pre-flight health check for HTTP servers with retry
                    if "url" in server_config:
                        logger.info(f"🔍 Checking health of {server_name}...")
                        if not await check_server_health(server_config["url"], max_retries=5, retry_delay=2.0):
                            logger.error(f"❌ MCP Server {server_name} is unreachable at {server_config['url']} after 5 attempts. Skipping.")
                            continue
                        else:
                            logger.info(f"✅ MCP Server {server_name} is healthy")

                    if "transport" not in server_config:
                        server_config["transport"] = "streamable_http" if "url" in server_config else "stdio"

                    # Increase timeout for long-running tools (e.g. nikto, nmap)
                    if server_config.get("transport") == "streamable_http":
                        # Set timeout to 30 minutes to match server-side timeout
                        server_config["timeout"] = timedelta(seconds=1800)
                        server_config["sse_read_timeout"] = timedelta(seconds=1800)

                    # Retry logic for flaky connections
                    max_retries = 2
                    current_tools = []
                    
                    for attempt in range(max_retries):
                        try:
                            client = MultiServerMCPClient({server_name: server_config})
                            
                            # Add timeout to prevent hanging (increased to 30 seconds)
                            current_tools = await asyncio.wait_for(
                                client.get_tools() if client else [],
                                timeout=30.0
                            )
                            
                            if current_tools:
                                break
                        except asyncio.TimeoutError:
                            if attempt < max_retries - 1:
                                logger.warning(f"Timeout on attempt {attempt + 1}, retrying...")
                                await asyncio.sleep(2)
                            else:
                                raise

                    if current_tools:
                        logger.info(f"Loaded {len(current_tools)} tools from {server_name}")
                        tools.extend(current_tools)
                    else:
                        logger.warning(f"No tools returned from {server_name}")
                        
                except asyncio.TimeoutError:
                    logger.error(f"Timeout connecting to MCP server: {server_name}")
                except httpx.HTTPError as e:
                    logger.error(f"HTTP error connecting to MCP server {server_name}: {str(e)}")
                except Exception as e:
                    logger.error(f"Failed to load tools from {server_name}: {str(e)}")

        logger.info(f"Total MCP tools loaded: {len(tools)}")
        return tools if tools else []
        
    except Exception as e:
        logger.error(f"Failed to load MCP tools: {str(e)}")
        return []