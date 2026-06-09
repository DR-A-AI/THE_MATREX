import asyncio
import logging
import uuid
from typing import Dict, Any
from core.neural_bus import NeuralBusClient
from core.models import EventPayload, EventType

logger = logging.getLogger("Sovereign.AssistantCrawler")

class AssistantCrawler:
    """
    ASSISTANT CRAWLER: The Blind Distributor.
    Listens for TOKEN_EXTRACTED events from Neo/Trinity (Supreme Extractors).
    Hands keys over to the Main Crawler for archiving, and INJECTS them into the
    Emergency Stash of all agents (Smith, Morpheus, Oracle, etc.).
    """
    def __init__(self, bus_url: str = "tcp://127.0.0.1:5555"):
        self.crawler_id = f"assistant-crawler-{uuid.uuid4().hex[:8]}"
        self.client = NeuralBusClient(identity=self.crawler_id, endpoint=bus_url)
        self._running = False
        
    async def start(self):
        logger.info("[AssistantCrawler] Booting up to intercept Extractor payloads...")
        self.client.register_handler(EventType.TOKEN_EXTRACTED.value, self._handle_extracted_token)
        await self.client.start()
        self._running = True

    async def stop(self):
        logger.info("[AssistantCrawler] Shutting down.")
        self._running = False
        await self.client.stop()

    async def _handle_extracted_token(self, event: EventPayload):
        """
        Intercepts keys pulled from the outside world by Neo/Trinity.
        """
        payload = event.payload
        platform = payload.get("platform", "Unknown")
        token = payload.get("extracted_token")
        extractor = event.source_agent_id
        
        logger.info(f"[AssistantCrawler] 🚨 CRITICAL: Received extracted token for [{platform}] from Extractor: {extractor}")
        logger.info(f"[AssistantCrawler] Forwarding to Main Crawler for vault storage...")
        
        # Here we broadcast the KEY_INJECT back to the agents to fill their stashes
        logger.info(f"[AssistantCrawler] Injecting [{platform}] token into Sovereign Stashes...")
        inject_event = EventPayload(
            event_type=EventType.KEY_INJECT,
            source_agent_id=self.crawler_id,
            correlation_id=str(uuid.uuid4()),
            payload={
                "scope": platform,
                "token": token
            }
        )
        await self.client.send(inject_event)
        logger.info("[AssistantCrawler] Injection complete. Stashes replenished.")
