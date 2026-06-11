import asyncio
import logging
import uuid
import time
from core.neural_bus import NeuralBusClient
from core.models import EventPayload, EventType
from core.memory_manager import AgentMemoryDB
from agents.aegis_qa import AsymmetricQA  # Ensure we verify any stored code/skills

logger = logging.getLogger("Sovereign.MemoryCrawler")

class MemoryCrawler:
    """
    Memory Crawler (Main Crawler for memory).
    Listens for MEMORY_STORE_REQUEST and MEMORY_RECALL_REQUEST events.
    Sorts, filters, sanitizes, and writes memories to SQLite databases.
    Injects recalled memories back to agents.
    """
    def __init__(self, bus_url: str = "tcp://127.0.0.1:5555"):
        self.crawler_id = f"memory-crawler-{uuid.uuid4().hex[:8]}"
        self.client = NeuralBusClient(identity=self.crawler_id, endpoint=bus_url)
        self.memory_databases = {}
        self._running = False

    def _get_db(self, agent_name: str) -> AgentMemoryDB:
        """Cache database connections per agent name."""
        name = agent_name.lower().strip()
        if name not in self.memory_databases:
            self.memory_databases[name] = AgentMemoryDB(agent_name=name)
        return self.memory_databases[name]

    async def start(self):
        logger.info("[MemoryCrawler] Igniting Memory Crawler service...")
        self.client.register_handler(EventType.MEMORY_STORE_REQUEST.value, self._handle_store_request)
        self.client.register_handler(EventType.MEMORY_RECALL_REQUEST.value, self._handle_recall_request)
        await self.client.start()
        self._running = True

    async def stop(self):
        logger.info("[MemoryCrawler] Shutting down.")
        self._running = False
        await self.client.stop()

    def _extract_and_sort_important_data(self, raw_content: str) -> str:
        """
        Heuristic filter to extract key facts and clean up conversational noise.
        If the memory represents a skill/code, it must pass Aegis validation.
        """
        content = raw_content.strip()
        
        # Simple heuristic cleanup
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            line_str = line.strip()
            # Strip conversational greetings
            if any(greet in line_str.lower() for greet in ["أرجوك", "يا صديقي", "خزن هذا", "تذكر هذا", "please store", "remember this"]):
                continue
            cleaned_lines.append(line)
            
        cleaned_content = "\n".join(cleaned_lines).strip()
        return cleaned_content if cleaned_content else content

    async def _handle_store_request(self, event: EventPayload):
        payload = event.payload
        agent_name = event.source_agent_id.split('-')[0] # Extract base agent name
        memory_type = payload.get("memory_type", "permanent")
        key = payload.get("key", f"mem_{int(time.time())}")
        raw_content = payload.get("raw_content", "")
        category = payload.get("category", "information")

        logger.info(f"[MemoryCrawler] Intercepted memory store request from [{agent_name}] (Type: {memory_type})")
        
        status_event = EventPayload(
            event_type=EventType.STATE_UPDATE,
            source_agent_id="Memory Crawler",
            correlation_id=event.correlation_id,
            payload={"status_action": f"Storing {memory_type} memory for {agent_name}..."}
        )
        await self.client.send(status_event)

        # 1. Run Aegis QA check if content looks like executable code or scripts
        if "def " in raw_content or "import " in raw_content or "eval(" in raw_content:
            logger.info("[MemoryCrawler] Code block detected. Routing through Aegis AsymmetricQA...")
            if not AsymmetricQA.verify(raw_content):
                logger.critical("[MemoryCrawler] 🔪 Aegis Rejected: Memory content contains dangerous execution payloads.")
                error_event = EventPayload(
                    event_type=EventType.ERROR,
                    source_agent_id=self.crawler_id,
                    correlation_id=event.correlation_id,
                    payload={"message": f"Storage rejected: Aegis QA violation in key '{key}'"}
                )
                await self.client.send(error_event)
                return

        # 2. Extract and Sort Heuristics
        cleaned_content = self._extract_and_sort_important_data(raw_content)
        
        # 3. Store in SQLite Database
        db = self._get_db(agent_name)
        success = False
        if memory_type == "permanent":
            success = db.store_permanent(key=key, category=category, content=cleaned_content)
        else:
            success = db.store_temporary(category=category, content=cleaned_content)

        # 4. Respond
        if success:
            stored_event = EventPayload(
                event_type=EventType.MEMORY_STORED,
                source_agent_id=self.crawler_id,
                correlation_id=event.correlation_id,
                payload={"status": "success", "key": key, "agent": agent_name}
            )
            await self.client.send(stored_event)
            logger.info(f"[MemoryCrawler] Successfully sorted and saved memory '{key}' for agent [{agent_name}].")
        else:
            error_event = EventPayload(
                event_type=EventType.ERROR,
                source_agent_id=self.crawler_id,
                correlation_id=event.correlation_id,
                payload={"message": f"Database insertion failed for agent [{agent_name}]"}
            )
            await self.client.send(error_event)
            
        # Clear status
        clear_status = EventPayload(
            event_type=EventType.STATE_UPDATE,
            source_agent_id="Memory Crawler",
            correlation_id=event.correlation_id,
            payload={"status_action": ""}
        )
        await self.client.send(clear_status)

    async def _handle_recall_request(self, event: EventPayload):
        payload = event.payload
        agent_name = event.source_agent_id.split('-')[0]
        query = payload.get("query", "")

        logger.info(f"[MemoryCrawler] Intercepted memory recall request from [{agent_name}] for query: '{query}'")

        status_event = EventPayload(
            event_type=EventType.STATE_UPDATE,
            source_agent_id="Memory Crawler",
            correlation_id=event.correlation_id,
            payload={"status_action": f"Recalling memory for {agent_name}..."}
        )
        await self.client.send(status_event)

        # 1. Query Agent SQLite DB
        db = self._get_db(agent_name)
        memories = db.recall(query)

        # 2. Inject back into agent
        inject_event = EventPayload(
            event_type=EventType.MEMORY_INJECT,
            source_agent_id=self.crawler_id,
            correlation_id=event.correlation_id,
            payload={
                "query": query,
                "agent": agent_name,
                "memories": memories  # List of serialized memory dicts
            }
        )
        await self.client.send(inject_event)
        logger.info(f"[MemoryCrawler] Injected {len(memories)} recalled memories back to [{agent_name}].")
        
        # Clear status
        clear_status = EventPayload(
            event_type=EventType.STATE_UPDATE,
            source_agent_id="Memory Crawler",
            correlation_id=event.correlation_id,
            payload={"status_action": ""}
        )
        await self.client.send(clear_status)

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s")
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    crawler = MemoryCrawler()
    try:
        asyncio.run(crawler.start())
        asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
