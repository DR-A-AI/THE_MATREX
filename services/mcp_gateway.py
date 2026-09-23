import asyncio
import logging
import subprocess  # nosec: B404  # list-only Popen helper, shell never enabled
import sys

logger = logging.getLogger("Sovereign.MCP_Gateway")
logging.basicConfig(level=logging.INFO)


def _spawn_detached(command: list, creationflags: int) -> subprocess.Popen:
    """Blocking Popen helper run in a thread to keep the event loop reactive."""
    return subprocess.Popen(  # nosec: B603  # argv list, no shell; callers pass fixed command lists
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
        start_new_session=(sys.platform != "win32"),
    )


async def launch_mcp_node_detached(name: str, command: list) -> int:
    """Launches an MCP Server Node in detached background process"""
    logger.info(f"[{name}] Igniting MCP Server...")
    try:
        # Windows: CREATE_NEW_PROCESS_GROUP
        # Unix: preexec_fn=os.setsid
        creationflags = 0x00000008 if sys.platform == "win32" else 0  # CREATE_NEW_PROCESS_GROUP

        process = await asyncio.to_thread(_spawn_detached, command, creationflags)
        logger.info(f"[{name}] MCP Node Online. PID: {process.pid}")
        return process.pid
    except Exception:
        logger.exception(f"[{name}] Failed to start")
        return -1


async def run_sovereign_mcp_gateway() -> None:
    logger.info("=" * 50)
    logger.info("🛡️ SOVEREIGN MCP GATEWAY INITIATED 🛡️")
    logger.info("=" * 50)

    # 1. Chrome DevTools MCP (Puppeteer)
    puppeteer_cmd = ["npx.cmd", "-y", "@modelcontextprotocol/server-puppeteer"]

    # 2. GitHub MCP
    github_cmd = ["npx.cmd", "-y", "@modelcontextprotocol/server-github"]

    # 3. UI WebSocket Bridge (FastAPI)
    _ui_bridge_cmd = ["python", "-m", "services.ui_bridge"]

    # Launch nodes concurrently with detached processes
    pids = await asyncio.gather(
        launch_mcp_node_detached("Chrome_DevTools_MCP", puppeteer_cmd),
        launch_mcp_node_detached("GitHub_MCP", github_cmd),
    )

    logger.info("=" * 50)
    logger.info("✅ All MCP Nodes are detached and running.")
    logger.info(f"   PIDs: {pids}")
    logger.info("=" * 50)

    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("Sovereign MCP Gateway shutting down.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run_sovereign_mcp_gateway())
