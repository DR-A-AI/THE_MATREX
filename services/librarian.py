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

    def _traverse_dir(self, directory: str):
        results = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.json') or file.endswith('.yaml') or file.endswith('SKILL.md'):
                    results.append((root, file))
        return results

    async def crawl_skills(self):
        logger.info(f"Librarian Crawler initializing index at: {self.target_dir}")
        if not await asyncio.to_thread(os.path.exists, self.target_dir):
            logger.error(f"Target directory {self.target_dir} does not exist.")
            return

        schema = {}
        file_paths = await asyncio.to_thread(self._traverse_dir, self.target_dir)
        
        for root, file in file_paths:
            skill_name = os.path.basename(root)
            if skill_name not in schema:
                schema[skill_name] = {
                    "name": skill_name,
                    "path": root,
                    "files": [],
                    "metadata": {}
                }
            schema[skill_name]["files"].append(file)
            
            # Use true asynchronous file I/O
            full_path = os.path.join(root, file)
            try:
                async with aiofiles.open(full_path, mode='r', encoding='utf-8') as f:
                    content = await f.read()
                    schema[skill_name]["metadata"][file] = f"Size: {len(content)} chars"
            except Exception as e:
                logger.error(f"Failed to read {full_path}: {e}")

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
