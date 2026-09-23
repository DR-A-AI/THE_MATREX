import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("Sovereign.MemoryManager")


class AgentMemoryDB:
    """SQLite-based transactional memory store for a specific agent."""

    def __init__(self, agent_name: str, memory_root: str | None = None):
        self.agent_name = agent_name.lower().strip()
        _root = memory_root or os.getenv("MATRIX_MEMORY_ROOT", str(Path.cwd() / "memory"))
        self.memory_root = Path(_root).resolve()

        # Ensure memory root directory exists
        self.memory_root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.memory_root / f"{self.agent_name}_memory.db"

        self._init_db()

    def _init_db(self) -> None:
        """Initializes tables inside the agent's SQLite memory database."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            # 1. Permanent Memory Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS permanent_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE,
                    category TEXT,
                    content TEXT,
                    timestamp REAL
                )
            """)
            # 2. Temporary Memory Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS temporary_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    content TEXT,
                    timestamp REAL
                )
            """)
            conn.commit()
            logger.info(
                f"Initialized SQLite memory database for agent [{self.agent_name}] at {self.db_path}"
            )
        except Exception as e:
            logger.critical(
                f"Failed to initialize database for agent [{self.agent_name}]: {e}",
                exc_info=True,
            )
        finally:
            conn.close()

    def store_permanent(self, key: str, category: str, content: str) -> bool:
        """Stores or updates a permanent memory item atomically."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO permanent_memory (key, category, content, timestamp)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    category=excluded.category,
                    content=excluded.content,
                    timestamp=excluded.timestamp
            """,
                (key, category, content, time.time()),
            )
            conn.commit()
            logger.info(f"[{self.agent_name}] Permanent memory stored: Key={key}")
            return True
        except Exception:
            logger.exception(f"[{self.agent_name}] Failed to store permanent memory")
            return False
        finally:
            conn.close()

    def store_temporary(self, category: str, content: str) -> bool:
        """Appends a temporary/volatile memory item."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO temporary_memory (category, content, timestamp)
                VALUES (?, ?, ?)
            """,
                (category, content, time.time()),
            )
            conn.commit()
            logger.info(f"[{self.agent_name}] Temporary memory appended.")
            return True
        except Exception:
            logger.exception(f"[{self.agent_name}] Failed to store temporary memory")
            return False
        finally:
            conn.close()

    def recall(self, query: str) -> list[dict[str, Any]]:
        """Queries permanent and temporary tables using keyword matching."""
        conn = sqlite3.connect(self.db_path)
        results = []
        try:
            cursor = conn.cursor()
            search_pattern = f"%{query.lower().strip()}%"

            # Query Permanent
            cursor.execute(
                """
                SELECT key, category, content, timestamp FROM permanent_memory
                WHERE lower(key) LIKE ? OR lower(category) LIKE ? OR lower(content) LIKE ?
                ORDER BY timestamp DESC
            """,
                (search_pattern, search_pattern, search_pattern),
            )

            for row in cursor.fetchall():
                results.append(
                    {
                        "type": "permanent",
                        "key": row[0],
                        "category": row[1],
                        "content": row[2],
                        "timestamp": row[3],
                    }
                )

            # Query Temporary
            cursor.execute(
                """
                SELECT category, content, timestamp FROM temporary_memory
                WHERE lower(category) LIKE ? OR lower(content) LIKE ?
                ORDER BY timestamp DESC
            """,
                (search_pattern, search_pattern),
            )

            for row in cursor.fetchall():
                results.append(
                    {
                        "type": "temporary",
                        "key": None,
                        "category": row[0],
                        "content": row[1],
                        "timestamp": row[2],
                    }
                )
        except Exception:
            logger.exception(f"[{self.agent_name}] Failed to recall memories")
        finally:
            conn.close()
        return results

    def clear_temporary(self) -> None:
        """Purges the temporary memory table."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM temporary_memory")
            conn.commit()
            logger.info(f"[{self.agent_name}] Cleared temporary memory table.")
        except Exception:
            logger.exception(f"[{self.agent_name}] Failed to clear temporary memory")
        finally:
            conn.close()
