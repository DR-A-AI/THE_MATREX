import asyncio
import subprocess
import logging
import sys

logger = logging.getLogger("Sovereign.MCP_Gateway")
logging.basicConfig(level=logging.INFO)

async def launch_mcp_node(name: str, command: list):
    """Launches an MCP Server Node in the background"""
    logger.info(f"[{name}] Igniting MCP Server...")
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        logger.info(f"[{name}] MCP Node Online. PID: {process.pid}")
        return process
    except Exception as e:
        logger.error(f"[{name}] Failed to start: {e}")
        return None

async def run_sovereign_mcp_gateway():
    logger.info("=========================================")
    logger.info("🛡️ SOVEREIGN MCP GATEWAY INITIATED 🛡️")
    logger.info("=========================================")
    
    # 1. Chrome DevTools MCP (Puppeteer)
    # Using npx to launch the official Model Context Protocol Puppeteer server
    puppeteer_cmd = ["npx.cmd", "-y", "@modelcontextprotocol/server-puppeteer"]
    
    # 2. GitHub MCP
    github_cmd = ["npx.cmd", "-y", "@modelcontextprotocol/server-github"]
    
    # 3. Chrome direct launch with DevTools port open (as backup visualizer)
    chrome_cmd = [
        "cmd.exe", "/c", "start", "chrome", 
        "--remote-debugging-port=9222", 
        "http://localhost:5173"
    ]
    
    # Launch nodes concurrently
    await asyncio.gather(
        launch_mcp_node("Chrome_DevTools_MCP", puppeteer_cmd),
        launch_mcp_node("GitHub_MCP", github_cmd),
        launch_mcp_node("Syncfusion_Dashboard_View", chrome_cmd)
    )
    
    logger.info("=========================================")
    logger.info("✅ All Sovereign MCP Nodes are now running in the background.")
    logger.info("The Matrix is now connected to the web, GitHub, and the UI.")
    logger.info("=========================================")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_sovereign_mcp_gateway())
