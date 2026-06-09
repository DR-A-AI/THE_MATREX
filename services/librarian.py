import os
import asyncio
import aiofiles
import json
import logging
import shutil
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

class SkillCrawler:
    """
    Crawler to scan multiple vault directories concurrently, validate skills, 
    and securely copy valid ones to the active runtime directory. 
    Refactored for Dual-Stage Skill Sandboxing in the Sovereign Architecture.
    """
    def __init__(self, vault_directories: List[str] = None, active_directory: str = r"J:\THE_MATRIX\skills\active", output_file: str = "skills_schema.json"):
        if vault_directories is None:
            vault_directories = [r"J:\THE_MATRIX\skills\vault"]
        
        # Enforce strict path resolution for Zero-Trust
        self.vault_directories = [Path(d).resolve() for d in vault_directories]
        self.active_directory = Path(active_directory).resolve()
        self.output_file = Path(output_file).resolve()
        
        # Ensure Dual-Stage directories exist
        for vault_dir in self.vault_directories:
            os.makedirs(vault_dir, exist_ok=True)
        os.makedirs(self.active_directory, exist_ok=True)

    def _validate_and_copy_skill(self, src_file: Path, dest_dir: Path) -> Path:
        """
        Synchronous function to validate a skill and copy it securely.
        Runs in a separate thread.
        """
        try:
            # Zero-Trust Validation: Only markdown files allowed. Further regex or checksums go here.
            if src_file.suffix != '.md':
                return None
                
            dest_file = dest_dir / src_file.name
            
            # Use shutil.copy for secure file transfer into Hot Runtime
            shutil.copy(src_file, dest_file)
            return dest_file
        except Exception as e:
            logger.error(f"Failed to copy/validate skill {src_file}: {e}")
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

    async def read_skill(self, file_path: Path):
        """Asynchronously reads a skill file from the active directory and extracts basic metadata."""
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

    async def crawl(self):
        """
        Scans vault directories, validates and copies skills to the active directory, 
        and indexes ONLY from the active directory.
        """
        skills = []
        copy_tasks = []
        
        # Phase 1: Scan and Copy from Vault to Active
        for vault_dir in self.vault_directories:
            if not vault_dir.exists() or not vault_dir.is_dir():
                logger.error(f"Vault directory {vault_dir} does not exist or is not a directory.")
                continue

            # Run blocking os.walk in a separate thread to prevent event loop blocking
            files_to_read = await asyncio.to_thread(self._get_md_files, vault_dir)
            
            for file_path in files_to_read:
                # Dispatch copy task in thread
                copy_tasks.append(
                    asyncio.to_thread(self._validate_and_copy_skill, file_path, self.active_directory)
                )
        
        # Wait for all copying to finish
        if copy_tasks:
            await asyncio.gather(*copy_tasks, return_exceptions=True)

        # Phase 2: Index from Active Directory ONLY
        active_files = await asyncio.to_thread(self._get_md_files, self.active_directory)
        
        read_tasks = [self.read_skill(f) for f in active_files]
        if read_tasks:
            results = await asyncio.gather(*read_tasks, return_exceptions=True)
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
            logger.info(f"Crawled {len(skills)} active skills and saved to {self.output_file}")
        except Exception as e:
            logger.error(f"Failed to save schema to {self.output_file}: {e}")
            
        return schema

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    vault_dirs = [r"J:\THE_MATRIX\skills\vault", r"J:\antigravity-awesome-skills-main", r"J:\awesome-copilot-main"]
    crawler = SkillCrawler(vault_directories=vault_dirs, active_directory=r"J:\THE_MATRIX\skills\active")
    asyncio.run(crawler.crawl())
