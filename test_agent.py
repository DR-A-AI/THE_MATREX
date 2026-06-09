import asyncio
import logging
import uuid
import sys
from datetime import datetime

from core.neural_bus import NeuralBusClient
from core.models import EventPayload, EventType, AgentState

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestAgent")

async def main():
    agent_id = f"test_agent_{uuid.uuid4().hex[:8]}"
    client = NeuralBusClient(identity=agent_id, endpoint="tcp://127.0.0.1:5555")
    
    async def handle_response(event):
        logger.info(f"Received response: {event.payload}")
        
    client.register_handler("skill_inject", handle_response)
    
    await client.start()
    
    try:
        logger.info(f"Test Agent {agent_id} starting up...")
        
        for i in range(5):
            # Send heartbeat
            heartbeat = EventPayload(
                event_type=EventType.AGENT_HEARTBEAT,
                source_agent_id=agent_id,
                correlation_id=uuid.uuid4().hex,
                payload={"state": AgentState.ACTIVE.value}
            )
            await client.send(heartbeat)
            logger.info("Heartbeat sent.")
            
            if i == 1:
                # Send a skill request to test Librarian
                skill_req = EventPayload(
                    event_type="skill_request",
                    source_agent_id=agent_id,
                    correlation_id=uuid.uuid4().hex,
                    payload={"skill_name": "unknown_skill"}
                )
                await client.send(skill_req)
                logger.info("Skill request sent.")
                
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Error in test agent: {e}")
    finally:
        await client.stop()
        logger.info("Test Agent shutting down.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
