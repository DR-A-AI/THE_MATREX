import asyncio
import logging
import sys
import tempfile
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

# Add project root to path (portable repo root)
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from core.librarian_crawler import LibrarianCrawler
from core.memory_manager import AgentMemoryDB
from core.models import EventPayload, EventType
from core.neural_bus import NeuralBusClient, NeuralBusRouter
from services.assistant_crawler import AssistantCrawler
from services.memory_crawler import MemoryCrawler

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def _start_test_router(endpoint: str):
    """Start an isolated NeuralBusRouter for hermetic tests."""
    router = NeuralBusRouter(endpoint=endpoint)
    task = asyncio.create_task(router.start())
    await asyncio.sleep(0.5)  # Allow router to bind
    return router, task


async def _stop_test_router(router, task):
    """Cancel router task and free the bound port."""
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("Error stopping test router task")
    try:
        router.socket.close(linger=0)
    except Exception:
        logger.exception("Error closing test router socket")


@pytest.mark.asyncio
async def test_real_world_librarian_crawler():
    """Tests the LibrarianCrawler scanning skills in an isolated temp dir"""
    with tempfile.TemporaryDirectory() as tmpdir:
        schema_file = Path(tmpdir) / "skills_schema.json"
        skills_dir = Path(tmpdir) / "skills"
        skill_sub = skills_dir / "test_skill"
        skill_sub.mkdir(parents=True, exist_ok=True)
        (skill_sub / "skill.md").write_text(
            "# Test Skill\nThis is a portable test skill for agents.", encoding="utf-8"
        )

        # Portable target: temp skills dir
        crawler = LibrarianCrawler(target_dir=str(skills_dir), output_file=str(schema_file))

        # Run crawl
        schema = await crawler.crawl()

        assert schema is not None
        assert "skills" in schema
        assert schema["skills_count"] > 0
        assert schema_file.exists()
        print(f"Librarian Crawler successfully processed {schema['skills_count']} skills.")


@pytest.mark.asyncio
async def test_real_world_memory_crawler():
    """Tests storing and recalling memory via isolated router + MemoryCrawler"""
    bus = "tcp://127.0.0.1:5571"
    router, router_task = await _start_test_router(bus)
    # Isolate SQLite DBs in a temp dir to avoid memory junk + cross-run pollution
    tmp_mem = tempfile.TemporaryDirectory()
    crawler = MemoryCrawler(bus_url=bus)
    # Pre-populate the "neo" DB (source "neo-tester" -> base "neo") with isolated root
    crawler.memory_databases["neo"] = AgentMemoryDB(agent_name="neo", memory_root=tmp_mem.name)
    await crawler.start()

    client = NeuralBusClient(identity="Real_World_Memory_Tester", endpoint=bus)
    await client.start()

    try:
        # Wait for dealer registration
        await asyncio.sleep(0.5)

        loop = asyncio.get_running_loop()
        stored_received = loop.create_future()
        inject_received = loop.create_future()

        async def handle_stored(event: EventPayload):
            if event.payload.get("key") == "real_world_test_key" and not stored_received.done():
                stored_received.set_result(event.payload)

        async def handle_inject(event: EventPayload):
            if event.payload.get("query") == "real_world_test_key" and not inject_received.done():
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
                "category": "history",
            },
        )

        print("Sending store request for real_world_test_key...")
        await client.send(store_event)

        # Wait for stored confirmation
        try:
            stored_payload = await asyncio.wait_for(stored_received, timeout=10.0)
            print(f"Store confirmed: {stored_payload}")
        except asyncio.TimeoutError:
            print("Timeout waiting for MEMORY_STORED event!")
            assert False, "Memory storage failed"

        # 2. Send memory recall request event
        recall_event = EventPayload(
            event_type=EventType.MEMORY_RECALL_REQUEST,
            source_agent_id="neo-tester",
            correlation_id=str(uuid.uuid4()),
            payload={"query": "real_world_test_key"},
        )

        print("Sending recall request for real_world_test_key...")
        await client.send(recall_event)

        # Wait for injected context
        try:
            memories = await asyncio.wait_for(inject_received, timeout=10.0)
            print(f"Recall confirmed. Recovered memories: {memories}")
            assert len(memories) > 0
            assert any("Architect" in m.get("content", "") for m in memories)
        except asyncio.TimeoutError:
            print("Timeout waiting for MEMORY_INJECT event!")
            assert False, "Memory recall failed"

        print("Real-world Memory Crawler test PASSED.")
    finally:
        await client.stop()
        await crawler.stop()
        await _stop_test_router(router, router_task)
        tmp_mem.cleanup()


@pytest.mark.asyncio
async def test_real_world_assistant_crawler():
    """Tests token injection workflow via isolated router + AssistantCrawler"""
    bus = "tcp://127.0.0.1:5572"
    router, router_task = await _start_test_router(bus)
    crawler = AssistantCrawler(bus_url=bus)
    await crawler.start()

    client = NeuralBusClient(identity="Real_World_Assistant_Tester", endpoint=bus)
    await client.start()

    try:
        # Wait for registration
        await asyncio.sleep(0.5)

        loop = asyncio.get_running_loop()
        inject_received = loop.create_future()

        async def handle_key_inject(event: EventPayload):
            if event.payload.get("scope") == "real_world_github" and not inject_received.done():
                inject_received.set_result(event.payload.get("token"))

        client.register_handler(EventType.KEY_INJECT.value, handle_key_inject)

        # Send extracted token event
        token_event = EventPayload(
            event_type=EventType.TOKEN_EXTRACTED,
            source_agent_id="trinity-extractor",
            correlation_id=str(uuid.uuid4()),
            payload={
                "platform": "real_world_github",
                "extracted_token": "ghp_real_world_test_token_secret",
            },
        )

        print("Sending token extracted event...")
        await client.send(token_event)

        try:
            token = await asyncio.wait_for(inject_received, timeout=10.0)
            print(f"Token injection confirmed: {token[:6]}...")
            assert token == "ghp_real_world_test_token_secret"
        except asyncio.TimeoutError:
            print("Timeout waiting for KEY_INJECT event!")
            assert False, "Token injection workflow failed"

        print("Real-world Assistant Crawler test PASSED.")
    finally:
        await client.stop()
        await crawler.stop()
        await _stop_test_router(router, router_task)
