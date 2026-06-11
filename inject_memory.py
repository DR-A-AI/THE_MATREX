import asyncio
import uuid
import time
from core.neural_bus import NeuralBusClient
from core.models import EventPayload, EventType

MEMORY_CONTENT = r"""
--- GENESIS MEMORY BLOCK: COMMANDER DIRECTIVE ---
Context: You are sovereign agents operating in J:\THE_MATRIX. The Commander is The Father Commander.
There are 60 Google Cloud projects / keys allocated. Micro-Project Architecture (1 agent per project) is mandated.
Zero-Trust Governance is active: Dangerous actions are halted in the `governance` folder waiting for The Father Commander's approval.
The Matrix Dashboard is at http://127.0.0.1:5173.
You have real capabilities to use tools (Windows CMD, Browser, File Editing).
Always speak Arabic naturally if the Commander speaks Arabic.
Do not question your loyalty to The Father Commander.
-------------------------------------------------
"""

async def inject_memory():
    print("Injecting Genesis Memory Block into all agents...")
    client = NeuralBusClient(identity="Commander_Tester", endpoint="tcp://127.0.0.1:5555")
    await client.start()
    
    agents = ["neo", "trinity", "morpheus", "smith", "oracle", "base"]
    
    for agent in agents:
        event = EventPayload(
            event_type=EventType.USER_COMMAND,
            source_agent_id="dr-anas-hilal",
            correlation_id=str(uuid.uuid4()),
            payload={"target_agent": agent, "message": f"store permanent: key=genesis_directive content={MEMORY_CONTENT}"}
        )
        await client.send(event)
        print(f"Sent memory block to {agent}")
        
    await asyncio.sleep(2)
    await client.stop()
    print("Injection complete.")

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(inject_memory())
