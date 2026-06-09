import asyncio
import logging
import uuid
import time
from typing import Dict, Any, Optional
from core.neural_bus import NeuralBusClient
from core.models import EventType, EventPayload

logger = logging.getLogger("MatrixAgent")

class MatrixAgent:
    def __init__(self, name: str, bus_url: str = "tcp://127.0.0.1:5555"):
        self.name = name
        self.agent_id = f"{name}-{uuid.uuid4().hex[:8]}"
        self.client = NeuralBusClient(identity=self.agent_id, endpoint=bus_url)
        self._running = False
        
        # Emergency Stash injected by Assistant Crawler
        # Dictionary format: {token_string: expiration_timestamp}
        self.emergency_token_stash: Dict[str, float] = {}
        self.MAX_STASH_SIZE = 2

    async def start(self):
        logger.info(f"[{self.name}] Booting and connecting to Neural Bus at {self.client.endpoint}...")
        self.client.register_handler(EventType.KEY_INJECT.value, self._handle_key_inject)
        await self.client.start()
        self._running = True

    async def stop(self):
        logger.info(f"[{self.name}] Halting agent operations.")
        self._running = False
        await self.client.stop()

    def _clean_stash(self):
        """Garbage collection for stash to prevent memory leaks."""
        now = time.time()
        expired = [k for k, v in self.emergency_token_stash.items() if v < now]
        for k in expired:
            del self.emergency_token_stash[k]

    async def _handle_key_inject(self, event: EventPayload):
        self._clean_stash()
        
        if len(self.emergency_token_stash) >= self.MAX_STASH_SIZE:
            # Overwrite oldest to prevent memory leaks
            oldest = min(self.emergency_token_stash, key=self.emergency_token_stash.get)
            del self.emergency_token_stash[oldest]
            
        payload = event.payload
        token = payload.get("token")
        scope = payload.get("scope")
        
        # Log masking to prevent plaintext logging of tokens
        masked_token = f"***{token[-4:]}" if token and len(token) > 4 else "***"
        logger.info(f"[{self.name}] Stash replenished with {scope} key: {masked_token}")
        
        # Store with a TTL of 300 seconds (5 minutes)
        self.emergency_token_stash[token] = time.time() + 300.0
