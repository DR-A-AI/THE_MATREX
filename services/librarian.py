import os
import json
import logging
import asyncio
from typing import Dict, Any
import aiofiles

from core.neural_bus import NeuralBusBroker
from core.models import EventPayload, EventType

logger = logging.getLogger("Sovereign.Librarian")

class SkillCrawler:
    def __init__(self, target_directory: str, bus: NeuralBusBroker):
        self.target_dir = os.path.abspath(target_directory)
        self.bus = bus
        self.indexed_schema = {}
        self._running = False

    async def crawl_skills(self):
        logger.info(f"Librarian Crawler initializing index at: {self.target_dir}")
        if not os.path.exists(self.target_dir):
            logger.error(f"Target directory {self.target_dir} does not exist.")
            return

        schema = {}
        for root, _, files in os.walk(self.target_dir):
            for file in files:
                if file.endswith('.json') or file.endswith('.yaml') or file.endswith('SKILL.md'):
                    # Read the schema or basic details. We'll simplify and just record path and name for the truth.
                    # This simulates actual parsing.
                    skill_name = os.path.basename(root)
                    if skill_name not in schema:
                        schema[skill_name] = {
                            "name": skill_name,
                            "path": root,
                            "files": []
                        }
                    schema[skill_name]["files"].append(file)
                    
                    # We can use aiofiles if we were actually reading content heavily.
                    # For a basic metadata scan, os.walk is fine, but we'll yield control just in case.
                    await asyncio.sleep(0)

        self.indexed_schema = schema
        logger.info(f"Librarian Crawler finished indexing. Secured {len(self.indexed_schema)} skills.")

    async def inject_skills(self, target_identity: bytes):
        """Broadcasts or sends SKILL_INJECT to a specific agent."""
        payload = EventPayload(
            event_type=EventType.SKILL_INJECT,
            source_agent_id="librarian",
            correlation_id="librarian_inject",
            payload={"schema": self.indexed_schema}
        )
        logger.info(f"Injecting skills to {target_identity}")
        await self.bus.send(target_identity, payload)

    async def handle_skill_request(self, identity: bytes, event: EventPayload):
        """Handler for when an agent asks for skills."""
        logger.info(f"Received skill request from {event.source_agent_id}")
        await self.inject_skills(identity)

    def register_hooks(self):
        # We assume the event type for requesting skills is STATE_UPDATE or a specific request.
        # But we'll just bind a generic "request_skills" logic if needed.
        pass
