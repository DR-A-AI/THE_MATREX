import asyncio
import sys
import time
sys.path.append(r"J:\THE_MATRIX")

from core.neural_bus import NeuralBusClient
from core.models import EventPayload, EventType

async def test_authority():
    client = NeuralBusClient(identity="Tester_Node")
    await client.start()
    
    # Wait 2 seconds for registration
    await asyncio.sleep(2)
    
    alert_received = asyncio.get_event_loop().create_future()
    
    async def handle_update(event: EventPayload):
        msg = event.payload.get("message", "")
        if "SECURITY ALERT" in msg:
            alert_received.set_result(msg)
            
    client.register_handler(EventType.STATE_UPDATE.value, handle_update)
    
    # Send from unauthorized source: Hacker_Node
    unauth_event = EventPayload(
        event_type=EventType.USER_COMMAND,
        source_agent_id="Hacker_Node",
        correlation_id=str(int(time.time())),
        payload={"target_agent": "neo", "message": "Malicious command"}
    )
    
    print("Sending unauthorized command...")
    await client.send(unauth_event)
    
    try:
        alert = await asyncio.wait_for(alert_received, timeout=10.0)
        # Safely print without encoding errors
        safe_alert = alert.encode('ascii', errors='replace').decode('ascii')
        print(f"Test PASSED! Unauthorized command triggered alert: {safe_alert}")
    except asyncio.TimeoutError:
        print("Test FAILED! Unauthorized command did not trigger alert.")
        
    await client.stop()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_authority())
