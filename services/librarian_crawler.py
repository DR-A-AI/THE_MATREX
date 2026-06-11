import os
import json
import asyncio
import logging
from pathlib import Path

logger = logging.getLogger("Matrix.LibrarianCrawler")

import uuid
from core.neural_bus import NeuralBusClient
from core.models import EventPayload, EventType

class LibrarianCrawler:
    """
    LibrarianCrawler - Skill Discovery.
    Scans the skills directory, extracts metadata from .md files, and generates a JSON schema.
    """
    def __init__(self, target_dir: str = "./skills", output_file: str = "./skills_schema.json", bus_client: NeuralBusClient = None):
        self.target_dir = Path(target_dir).resolve()
        self.output_file = Path(output_file).resolve()
        self.bus_client = bus_client
        
    async def scan_skills(self):
        logger.info(f"[LibrarianCrawler] Scanning for skills in {self.target_dir}")
        
        if self.bus_client:
            status_event = EventPayload(
                event_type=EventType.STATE_UPDATE,
                source_agent_id="Skills Crawler",
                correlation_id=uuid.uuid4().hex,
                payload={"status_action": "Scanning skills directory..."}
            )
            await self.bus_client.send(status_event)
        
        if not self.target_dir.exists():
            logger.warning(f"[LibrarianCrawler] Target directory {self.target_dir} does not exist. Creating it.")
            self.target_dir.mkdir(parents=True, exist_ok=True)
            
        skills_data = []
        
        # Non-blocking file I/O wrapper
        def extract_metadata(file_path: Path):
            # Security: Path Traversal Protection
            resolved_path = file_path.resolve()
            if not resolved_path.is_relative_to(self.target_dir):
                logger.warning(f"SECURITY: Path traversal blocked for {file_path}")
                return None
                
            try:
                with open(resolved_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                content = content.lstrip('\ufeff').strip()
                
                # Basic parsing for YAML frontmatter usually found in skill .md files
                name = resolved_path.stem
                description = "No description provided."
                
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = parts[1]
                        for line in frontmatter.split("\n"):
                            line = line.strip()
                            if line.startswith("name:"):
                                name = line[5:].strip()
                            elif line.startswith("description:"):
                                description = line[12:].strip()
                                
                return {
                    "name": name,
                    "description": description,
                    "path": str(resolved_path)
                }
            except Exception as e:
                logger.error(f"[LibrarianCrawler] Failed to read {file_path}: {e}")
                return None

        # Gather all .md files
        for root, _, files in os.walk(self.target_dir):
            for file in files:
                if file.endswith(".md"):
                    file_path = Path(root) / file
                    # Offload file reading to a thread to prevent blocking
                    data = await asyncio.to_thread(extract_metadata, file_path)
                    if data:
                        skills_data.append(data)
                        
        schema = {
            "version": "1.0",
            "skills_count": len(skills_data),
            "skills": skills_data
        }
        
        def save_schema():
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(schema, f, indent=4, ensure_ascii=False)
                
        await asyncio.to_thread(save_schema)
        logger.info(f"[LibrarianCrawler] Skill scan complete. Discovered {len(skills_data)} skills. Schema saved to {self.output_file}")
        
        if self.bus_client:
            clear_status = EventPayload(
                event_type=EventType.STATE_UPDATE,
                source_agent_id="Skills Crawler",
                correlation_id=uuid.uuid4().hex,
                payload={"status_action": ""}
            )
            await self.bus_client.send(clear_status)
            
        return schema

async def run_crawler_periodically():
    bus_client = NeuralBusClient(identity="LibrarianCrawler_Client", endpoint="tcp://127.0.0.1:5555")
    await bus_client.start()
    crawler = LibrarianCrawler(target_dir=r"J:\THE_MATRIX\skills", output_file=r"J:\THE_MATRIX\skills_schema.json", bus_client=bus_client)
    while True:
        await crawler.scan_skills()
        await asyncio.sleep(60) # Scan every 60 seconds

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_crawler_periodically())
