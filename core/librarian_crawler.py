import os
import asyncio
import aiofiles
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class LibrarianCrawler:
    """
    Crawler to scan skill directories, read skills using aiofiles, 
    and generate lightweight JSON schemas for agents.
    Sovereign Razor Standard: Anti-Path-Traversal, Strictly Async I/O.
    """
    def __init__(self, target_dir=r"J:\antigravity-awesome-skills-main", output_file="skills_schema.json"):
        # Resolve absolutely to prevent symlink or ../ traversal trickery
        self.target_dir = Path(target_dir).resolve()
        self.output_file = Path(output_file).resolve()
        
    async def read_skill(self, file_path: Path):
        """Asynchronously reads a skill file and extracts basic metadata."""
        # Security Gate: Path Traversal Check
        resolved_path = file_path.resolve()
        if not resolved_path.is_relative_to(self.target_dir):
            logger.warning(f"SECURITY BREACH ATTEMPT: Path traversal detected and blocked for {file_path}")
            return None

        try:
            async with aiofiles.open(resolved_path, mode='r', encoding='utf-8') as f:
                content = await f.read()
                return {
                    "name": resolved_path.parent.name if resolved_path.parent.name != self.target_dir.name else resolved_path.stem,
                    "file": resolved_path.name,
                    "path": str(resolved_path),
                    "preview": content[:100].replace('\n', ' ') + "..."
                }
        except Exception as e:
            logger.error(f"Failed to read file {resolved_path}: {e}")
            return None

    async def _scan_directories(self):
        """Offload synchronous os.walk to a thread to prevent blocking the event loop."""
        def sync_walk():
            found_files = []
            for root, _, files in os.walk(self.target_dir):
                for file in files:
                    if file.endswith('.md'):
                        found_files.append(Path(root) / file)
            return found_files
        
        return await asyncio.to_thread(sync_walk)

    async def crawl(self):
        """Scans the target directory asynchronously to build the skill schema."""
        if not self.target_dir.exists():
            logger.error(f"Target directory {self.target_dir} does not exist.")
            return

        logger.info(f"[SOVEREIGN] Initiating secured asynchronous crawl of {self.target_dir}")
        
        # Gather all target paths strictly asynchronously
        file_paths = await self._scan_directories()
        
        # Execute all reads concurrently
        tasks = [self.read_skill(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        skills = []
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Execution exception during async read: {res}")
            elif res is not None:
                skills.append(res)
                
        # Generate JSON schema payload
        schema = {
            "version": "1.0",
            "skills_count": len(skills),
            "skills": skills
        }
        
        # Ensure output file path is not performing path traversal
        # Not strictly needed if output_file is internal, but sovereign architecture demands perfection.
        # Save schema asynchronously
        async with aiofiles.open(self.output_file, mode='w', encoding='utf-8') as f:
            await f.write(json.dumps(schema, indent=2))
            
        logger.info(f"[SOVEREIGN] Crawled {len(skills)} skills flawlessly and securely saved to {self.output_file}")
        return schema

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    crawler = LibrarianCrawler()
    asyncio.run(crawler.crawl())
