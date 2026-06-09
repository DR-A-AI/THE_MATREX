import sys
import os
import asyncio
import time
import uuid
import tempfile
import json
from pathlib import Path

# Add project root to path
sys.path.append(r"J:\THE_MATRIX")

import pytest
from core.neural_bus import NeuralBusClient
from core.models import EventPayload, EventType
from core.memory_manager import AgentMemoryDB
from core.librarian_crawler import LibrarianCrawler
from services.assistant_crawler import AssistantCrawler
from services.memory_crawler import MemoryCrawler

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@pytest.mark.asyncio
async def test_real_world_librarian_crawler():
    """Tests the LibrarianCrawler scanning real skills in the workspace"""
    with tempfile.TemporaryDirectory() as tmpdir:
        schema_file = Path(tmpdir) / "skills_schema.json"
        
        # Instantiate crawler targeting the real J:\antigravity-awesome-skills-main folder
        crawler = LibrarianCrawler(
            target_dir=r"J:\antigravity-awesome-skills-main",
            output_file=str(schema_file)
        )
        
        # Run crawl
        schema = await crawler.crawl()
        
        assert schema is not None
        assert "skills" in schema
        assert schema["skills_count"] > 0
        assert schema_file.exists()
        print(f"Librarian Crawler successfully processed {schema['skills_count']} skills.")

@pytest.mark.asyncio
async def test_real_world_memory_crawler():
    """Tests storing and recalling memory using the active background MemoryCrawler on port 5555"""
    client = NeuralBusClient(identity="Real_World_Memory_Tester", endpoint="tcp://127.0.0.1:5555")
    await client.start()
    
    # Wait for dealer registration
    await asyncio.sleep(2)
    
    stored_received = asyncio.get_event_loop().create_future()
    inject_received = asyncio.get_event_loop().create_future()
    
    async def handle_stored(event: EventPayload):
        if event.payload.get("key") == "real_world_test_key":
            if not stored_received.done():
                stored_received.set_result(event.payload)
            
    async def handle_inject(event: EventPayload):
        if event.payload.get("query") == "real_world_test_key":
            if not inject_received.done():
                inject_received.set_result(event.payload.get("memories", []))
            
    client.register_handler(EventType.MEMORY_STORED.value, handle_stored)
    client.register_handler(EventType.MEMORY_INJECT.value, handle_inject)
    
    # 1. Send memory store request event
    store_event = EventPayload(
        event_type=EventType.MEMORY_STORE_REQUEST,
        source_agent_id="neo-tester",
        correlation_id=str(uuid.uuid4()),
        payload={
            "memory_type": "permanent",
            "key": "real_world_test_key",
            "raw_content": "The Architect created the first version of the Matrix",
            "category": "history"
        }
    )
    
    print("Sending store request for real_world_test_key...")
    await client.send(store_event)
    
    # Wait for stored confirmation
    try:
        stored_payload = await asyncio.wait_for(stored_received, timeout=15.0)
        print(f"Store confirmed: {stored_payload}")
    except asyncio.TimeoutError:
        print("Timeout waiting for MEMORY_STORED event!")
        await client.stop()
        assert False, "Memory storage failed"
        
    # 2. Send memory recall request event
    recall_event = EventPayload(
        event_type=EventType.MEMORY_RECALL_REQUEST,
        source_agent_id="neo-tester",
        correlation_id=str(uuid.uuid4()),
        payload={"query": "real_world_test_key"}
    )
    
    print("Sending recall request for real_world_test_key...")
    await client.send(recall_event)
    
    # Wait for injected context
    try:
        memories = await asyncio.wait_for(inject_received, timeout=15.0)
        print(f"Recall confirmed. Recovered memories: {memories}")
        assert len(memories) > 0
        assert any("Architect" in m.get("content", "") for m in memories)
    except asyncio.TimeoutError:
        print("Timeout waiting for MEMORY_INJECT event!")
        await client.stop()
        assert False, "Memory recall failed"
        
    await client.stop()
    print("Real-world Memory Crawler test PASSED.")

@pytest.mark.asyncio
async def test_real_world_assistant_crawler():
    """Tests token injection workflow by launching AssistantCrawler on port 5555"""
    crawler = AssistantCrawler(bus_url="tcp://127.0.0.1:5555")
    await crawler.start()
    
    client = NeuralBusClient(identity="Real_World_Assistant_Tester", endpoint="tcp://127.0.0.1:5555")
    await client.start()
    
    # Wait for registration
    await asyncio.sleep(2)
    
    inject_received = asyncio.get_event_loop().create_future()
    
    async def handle_key_inject(event: EventPayload):
        if event.payload.get("scope") == "real_world_github":
            if not inject_received.done():
                inject_received.set_result(event.payload.get("token"))
                
    client.register_handler(EventType.KEY_INJECT.value, handle_key_inject)
    
    # Send extracted token event
    token_event = EventPayload(
        event_type=EventType.TOKEN_EXTRACTED,
        source_agent_id="trinity-extractor",
        correlation_id=str(uuid.uuid4()),
        payload={
            "platform": "real_world_github",
            "extracted_token": "ghp_real_world_test_token_secret"
        }
    )
    
    print("Sending token extracted event...")
    await client.send(token_event)
    
    try:
        token = await asyncio.wait_for(inject_received, timeout=15.0)
        print(f"Token injection confirmed: {token[:6]}...")
        assert token == "ghp_real_world_test_token_secret"
    except asyncio.TimeoutError:
        print("Timeout waiting for KEY_INJECT event!")
        await client.stop()
        await crawler.stop()
        assert False, "Token injection workflow failed"
        
    await client.stop()
    await crawler.stop()
    print("Real-world Assistant Crawler test PASSED.")
