import sys
import os
sys.path.append(r"J:\THE_MATRIX")

import pytest
from core.memory_manager import AgentMemoryDB

def test_agent_memory_db_lifecycle(tmp_path):
    # Use the tmp_path fixture provided by pytest to create an isolated database
    db = AgentMemoryDB(agent_name="test_agent", memory_root=str(tmp_path))
    
    # 1. Test store permanent
    success = db.store_permanent(key="my_key", category="credentials", content="secret_value")
    assert success is True
    
    # 2. Test store duplicate key (Upsert behavior)
    success = db.store_permanent(key="my_key", category="credentials", content="updated_secret")
    assert success is True
    
    # 3. Test store temporary
    success = db.store_temporary(category="session_info", content="session_token_123")
    assert success is True
    
    # 4. Test recall
    results = db.recall("secret")
    # Should find 1 permanent memory (updated_secret)
    permanent_results = [r for r in results if r["type"] == "permanent"]
    assert len(permanent_results) == 1
    assert permanent_results[0]["content"] == "updated_secret"
    
    # Recall session info
    results_temp = db.recall("session")
    temporary_results = [r for r in results_temp if r["type"] == "temporary"]
    assert len(temporary_results) == 1
    assert temporary_results[0]["content"] == "session_token_123"
    
    # 5. Test clear temporary
    db.clear_temporary()
    results_after_clear = db.recall("session")
    assert len([r for r in results_after_clear if r["type"] == "temporary"]) == 0
