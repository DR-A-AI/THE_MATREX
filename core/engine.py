import os
import sys
import zmq
import zmq.asyncio
import asyncio
import logging
import time

from config.settings import settings
from core.neural_bus import NeuralBusBroker
from core.models import EventPayload, EventType, AgentState
from services.librarian import SkillCrawler

logging.basicConfig(
    level=settings.log_level, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MatrixEngine")

class WatchdogProcess:
    """Monitors system health and zombie processes without blocking."""
    def __init__(self, bus: NeuralBusBroker):
        self.bus = bus
        self._running = False
        self._task = None
        self.agents = {}
        
        self.bus.register_handler(EventType.AGENT_HEARTBEAT.value, self.handle_heartbeat)

    async def handle_heartbeat(self, identity: bytes, event: EventPayload):
        agent_id = event.source_agent_id
        if identity not in self.agents:
            logger.info(f"Agent {agent_id} (Identity: {identity}) connected.")
            
        self.agents[identity] = {
            "source_id": agent_id,
            "last_seen": time.time(),
            "state": event.payload.get("state", AgentState.ACTIVE)
        }

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
                # We use settings.zmq_heartbeat_interval from SovereignSettings
                await asyncio.sleep(settings.zmq_heartbeat_interval)
                now = time.time()
                dead_agents = []
                
                for identity, data in self.agents.items():
                    if now - data["last_seen"] > settings.zmq_heartbeat_timeout:
                        logger.warning(f"[Watchdog] Agent {data['source_id']} timed out! Purging...")
                        dead_agents.append(identity)
                
                for identity in dead_agents:
                    del self.agents[identity]
                    
            except asyncio.CancelledError:
                break

async def main():
    logger.info("==========================================")
    logger.info(" SOVEREIGN ENGINE INITIALIZATION SEQUENCE ")
    logger.info("==========================================")
    
    # 1. Initialize ZMQ Router (Neural Bus)
    bus = NeuralBusBroker(endpoint=settings.zmq_endpoint)
    await bus.start()
    
    # 2. Start Watchdog
    watchdog = WatchdogProcess(bus)
    await watchdog.start()
    
    # 3. Start Librarian Crawler
    skills_dir = os.environ.get("SOVEREIGN_SKILLS_DIR", "J:\\antigravity-awesome-skills-main")
    crawler = SkillCrawler(skills_dir, bus)
    
    # Crawl immediately
    await crawler.crawl_skills()
    
    # We could hook up a request event to the librarian
    # The event type "skill_request" is just an example. If we need to, we can use STATE_UPDATE
    bus.register_handler("skill_request", crawler.handle_skill_request)
    
    logger.info("Sovereign Engine is alive and awaiting agents.")
    
    # The true Sovereign architecture runs indefinitely
    try:
        # Instead of fake sleeping and terminating, we keep the loop alive until cancelled
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Initiating graceful shutdown sequence...")
        await watchdog.stop()
        await bus.stop()
        logger.info("Sovereign Engine safely halted.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("System terminated by Sovereign Commander.")
