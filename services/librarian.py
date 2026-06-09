import os
import asyncio
import aiofiles
import json
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

class SkillCrawler:
    """
    Crawler to scan multiple skill directories concurrently, read skills using aiofiles, 
    and generate lightweight JSON schemas for agents. 
    Refactored for Sovereign Architecture to avoid blocking the event loop.
    """
    def __init__(self, target_directories: List[str] = None, output_file="skills_schema.json"):
        if target_directories is None:
            target_directories = [r"J:\antigravity-awesome-skills-main"]
        # Enforce strict path resolution for Zero-Trust
        self.target_directories = [Path(d).resolve() for d in target_directories]
        self.output_file = Path(output_file).resolve()
        
    async def read_skill(self, file_path: Path):
        """Asynchronously reads a skill file and extracts basic metadata."""
        try:
            async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
                content = await f.read()
                return {
                    "name": file_path.stem,
                    "file": file_path.name,
                    "path": str(file_path),
                    "preview": content[:100].replace('\n', ' ') + "..."
                }
        except Exception as e:
            logger.error(f"Failed to read skill {file_path}: {e}")
            return None

    def _get_md_files(self, target_dir: Path) -> List[Path]:
        """Blocking directory walk function to be run in a separate thread."""
        md_files = []
        try:
            for root, _, files in os.walk(target_dir):
                for file in files:
                    if file.endswith('.md'):
                        md_files.append(Path(root) / file)
        except Exception as e:
            logger.error(f"Error walking directory {target_dir}: {e}")
        return md_files

    async def crawl(self):
        """Scans the target directories concurrently to build the skill schema."""
        skills = []
        tasks = []
        
        for target_dir in self.target_directories:
            if not target_dir.exists() or not target_dir.is_dir():
                logger.error(f"Target directory {target_dir} does not exist or is not a directory.")
                continue

            # Run blocking os.walk in a separate thread to prevent event loop blocking
            files_to_read = await asyncio.to_thread(self._get_md_files, target_dir)
            
            for file_path in files_to_read:
                tasks.append(self.read_skill(file_path))
                    
        if tasks:
            # Execute all reads concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for res in results:
                if isinstance(res, Exception):
                    logger.error(f"Exception during skill reading: {res}")
                elif res is not None:
                    skills.append(res)
                
        # Generate JSON schema payload
        schema = {
            "version": "1.0",
            "skills_count": len(skills),
            "skills": skills
        }
        
        # Save schema asynchronously
        try:
            async with aiofiles.open(self.output_file, mode='w', encoding='utf-8') as f:
                await f.write(json.dumps(schema, indent=2))
            logger.info(f"Crawled {len(skills)} skills and saved to {self.output_file}")
        except Exception as e:
            logger.error(f"Failed to save schema to {self.output_file}: {e}")
            
        return schema

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    directories = [r"J:\antigravity-awesome-skills-main", r"J:\awesome-copilot-main"]
    crawler = SkillCrawler(target_directories=directories)
    asyncio.run(crawler.crawl())
