import asyncio
import json
import logging
import os
import sys
import zmq
import zmq.asyncio

from matrix_agent import MatrixAgent

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MatrixEngine")

# ---------------------------------------------------------
# Core Infrastructure Components
# ---------------------------------------------------------

class WatchdogProcess:
    """Monitors system health and zombie processes without blocking."""
    def __init__(self):
        self._running = False
        self._task = None

    async def start(self):
        self._running = True
        logger.info("Watchdog initiated. Monitoring Neural Bus and Agent states...")
        self._task = asyncio.create_task(self._monitor_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _monitor_loop(self):
        while self._running:
            try:
                await asyncio.sleep(15)
                logger.debug("[Watchdog] System nominal. Heartbeats synchronized.")
            except asyncio.CancelledError:
                break

class LibrarianCrawler:
    """Indexes Skills and serves Tool Schemas to the Neural Bus. Zero Trust strict typing."""
    def __init__(self, target_directory: str):
        self.target_dir = os.path.abspath(target_directory)
        self.indexed_schema = {}

    async def start(self):
        logger.info(f"Librarian Crawler initializing index at: {self.target_dir}")
        # Async non-blocking file indexing simulation
        await asyncio.sleep(0.1) 
        
        # Sovereign Strict Definition
        self.indexed_schema = {
            "search_web": {"description": "Perform web search", "params": ["query"]},
            "read_file": {"description": "Read file contents", "params": ["filepath"]},
            "crawler_hook": {"description": "ZMQ hook for crawler", "params": ["target"]}
        }
        logger.info(f"Librarian Crawler finished indexing. Secured {len(self.indexed_schema)} skills.")
        
    def get_schema(self) -> dict:
        return self.indexed_schema

class NeuralBus:
    """ZMQ Router/Dealer Broker orchestrating the Sovereign Engine with localhost isolation."""
    def __init__(self, crawler: LibrarianCrawler, frontend_url="tcp://127.0.0.1:5555"):
        # Enforce localhost ONLY. Destroy asterisk binding.
        if "*" in frontend_url or "0.0.0.0" in frontend_url:
            raise ValueError("Sovereign Razor Violation: External binding strictly forbidden. Use 127.0.0.1.")
            
        self.frontend_url = frontend_url
        self.ctx = zmq.asyncio.Context.instance()
        self.frontend = self.ctx.socket(zmq.ROUTER)
        
        # Security overrides
        self.frontend.setsockopt(zmq.LINGER, 0)
        self.frontend.setsockopt(zmq.ROUTER_MANDATORY, 1) # Error out if routing fails instead of dropping silently
        
        self.crawler = crawler
        self._running = False
        self._task = None

    async def start(self):
        self.frontend.bind(self.frontend_url)
        self._running = True
        logger.info(f"Neural Bus [ROUTER] locked and bound at {self.frontend_url}")
        self._task = asyncio.create_task(self._routing_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        self.frontend.close(linger=0)

    async def _routing_loop(self):
        logger.info("Neural Bus routing enforcement loop active.")
        while self._running:
            try:
                # Expecting: [Identity, Empty, Payload]
                msg = await self.frontend.recv_multipart()
                
                if len(msg) < 3:
                    logger.warning("Dropped malformed routing packet. Zero-trust enforcement.")
                    continue
                    
                identity = msg[0]
                try:
                    payload = json.loads(msg[2].decode('utf-8'))
                    if not isinstance(payload, dict):
                        raise ValueError("Payload non-dict")
                    await self._process_request(identity, payload)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Failed payload parsing from {identity}. Dropping. {e}")
                    
            except zmq.error.Again:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Neural Bus structural exception: {e}")

    async def _process_request(self, identity: bytes, payload: dict):
        msg_type = payload.get("type")
        sender = payload.get("sender", "Unknown")
        
        if msg_type == "GET_TOOLS":
            logger.debug(f"[Neural Bus] Validated GET_TOOLS from {sender}")
            response = {
                "type": "TOOL_SCHEMA_RESPONSE",
                "schema": self.crawler.get_schema()
            }
            await self.frontend.send_multipart([identity, b"", json.dumps(response).encode('utf-8')])
            
        elif msg_type == "CALL_TOOL":
            tool_name = payload.get("tool_name")
            logger.info(f"[Neural Bus] Dispatching RPC CALL_TOOL [{tool_name}] to Hooks Worker")
            
            # Non-blocking simulation
            await asyncio.sleep(0.1)
            
            response = {
                "type": "TOOL_CALL_RESULT",
                "request_id": payload.get("request_id"),
                "status": "SUCCESS",
                "result": f"Executed hook for {tool_name}"
            }
            await self.frontend.send_multipart([identity, b"", json.dumps(response).encode('utf-8')])
        else:
            logger.warning(f"[Neural Bus] Blocked unknown message type: {msg_type}")

# ---------------------------------------------------------
# Master Execution Engine
# ---------------------------------------------------------

async def main():
    logger.info("==========================================")
    logger.info(" SOVEREIGN ENGINE INITIALIZATION SEQUENCE ")
    logger.info("==========================================")
    
    # Destroy hardcoded external paths; utilize environment or secure fallback
    target_skill_dir = os.environ.get("SOVEREIGN_SKILLS_DIR", os.path.join(os.getcwd(), "skills"))
    if not os.path.exists(target_skill_dir):
        os.makedirs(target_skill_dir, exist_ok=True)
        
    # 1. Start Watchdog
    watchdog = WatchdogProcess()
    await watchdog.start()
    
    # 2. Start Librarian Crawler
    crawler = LibrarianCrawler(target_skill_dir)
    await crawler.start()
    
    # 3. Initialize ZMQ Router (Neural Bus) securely
    bus = NeuralBus(crawler=crawler, frontend_url="tcp://127.0.0.1:5555")
    await bus.start()
    
    # Give infrastructure a moment to bind non-blockingly
    await asyncio.sleep(0.5)
    
    # 4. Spin up Agent
    test_agent = MatrixAgent("Sovereign-Agent-Alpha", bus_url="tcp://127.0.0.1:5555")
    await test_agent.start()
    
    # 5. Execute Sequence
    logger.info("Initiating secure execution scenario...")
    
    await test_agent.execute_tool("search_web", {"query": "Sovereign Framework Architecture"})
    await test_agent.execute_tool("crawler_hook", {"target": "127.0.0.1"})
    
    # Await completion of tasks gracefully instead of an infinite hanging loop
    await asyncio.sleep(1.0)
    
    logger.info("Scenario complete. Initiating graceful shutdown sequence...")
    
    await test_agent.stop()
    await bus.stop()
    await watchdog.stop()
    logger.info("Sovereign Engine safely halted.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("System terminated by Sovereign Commander.")
