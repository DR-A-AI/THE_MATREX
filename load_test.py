import asyncio
import logging
import uuid
import sys
import time

from core.neural_bus import NeuralBusClient
from core.models import EventPayload, EventType, AgentState

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LoadTest")

async def test_agent(agent_index: int, iterations: int):
    agent_id = f"load_agent_{agent_index}"
    client = NeuralBusClient(identity=agent_id, endpoint="tcp://127.0.0.1:5555")
    await client.start()
    
    start_time = time.time()
    try:
        for i in range(iterations):
            heartbeat = EventPayload(
                event_type=EventType.AGENT_HEARTBEAT,
                source_agent_id=agent_id,
                correlation_id=uuid.uuid4().hex,
                payload={"state": AgentState.ACTIVE.value}
            )
            await client.send(heartbeat)
            if i % 1000 == 0:
                logger.info(f"{agent_id} sent {i} heartbeats")
                
    except Exception as e:
        logger.error(f"{agent_id} error: {e}")
    finally:
        await client.stop()
        
    duration = time.time() - start_time
    logger.info(f"{agent_id} finished {iterations} msgs in {duration:.2f} seconds ({iterations/duration:.2f} msg/s)")

async def main():
    logger.info("Starting load test...")
    tasks = []
    # 10 agents sending 5000 heartbeats each
    for i in range(10):
        tasks.append(test_agent(i, 5000))
        
    await asyncio.gather(*tasks)
    logger.info("Load test completed.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
