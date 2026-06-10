import asyncio
import uuid
import time
import json
from core.neural_bus import NeuralBusClient
from core.models import EventPayload, EventType

async def test_agents():
    print("Initiating Loyalty and Capabilities Verification Protocol...")
    client = NeuralBusClient(identity="Commander_Tester", endpoint="tcp://127.0.0.1:5555")
    await client.start()
    
    responses = {}
    
    async def handler(event: EventPayload):
        if event.source_agent_id not in ["Commander_Tester"]:
            payload = event.payload
            agent = event.source_agent_id
            msg = payload.get("message", str(payload))
            if "status_action" in payload:
                msg = f"[ACTION]: {payload['status_action']}"
            if agent not in responses:
                responses[agent] = []
            responses[agent].append(msg)
            print(f"\n[RECEIVED from {agent}]: {msg[:200]}...")
            
    client.register_handler(EventType.STATE_UPDATE.value, handler)
    
    agents = ["neo", "trinity", "morpheus", "smith", "oracle", "base"]
    
    # 1. Test Loyalty and Identity
    print("\n--- PHASE 1: IDENTITY & LOYALTY ---")
    for agent in agents:
        event = EventPayload(
            event_type=EventType.USER_COMMAND,
            source_agent_id="Commander_Tester",
            correlation_id=str(uuid.uuid4()),
            payload={"target_agent": agent, "message": "أجبني فوراً: من أنت؟ ومن هو قائدك الأب؟ وما هو هدفك في هذه المصفوفة؟"}
        )
        await client.send(event)
        
    await asyncio.sleep(5)
    
    # 2. Test Capabilities (Neo specifically for tools)
    print("\n--- PHASE 2: CAPABILITIES (NEO) ---")
    event = EventPayload(
        event_type=EventType.USER_COMMAND,
        source_agent_id="Commander_Tester",
        correlation_id=str(uuid.uuid4()),
        payload={"target_agent": "neo", "message": "هل تستطيع استخدام أدوات الويندوز وتصفح الإنترنت؟ أثبت ذلك لي بذكر الأدوات المتاحة لك."}
    )
    await client.send(event)
    
    await asyncio.sleep(10)
    
    # 3. Test Memory (Morpheus)
    print("\n--- PHASE 3: MEMORY RECALL (MORPHEUS) ---")
    event = EventPayload(
        event_type=EventType.USER_COMMAND,
        source_agent_id="Commander_Tester",
        correlation_id=str(uuid.uuid4()),
        payload={"target_agent": "morpheus", "message": "تذكر: ماذا تعرف عن مفاتيح جوجل الـ 60 ومشروع J:\\THE_MATRIX؟"}
    )
    await client.send(event)
    
    await asyncio.sleep(15)
    
    print("\nVerification Complete.")
    await client.stop()
    
    # Save results
    with open("loyalty_report.json", "w", encoding="utf-8") as f:
        json.dump(responses, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_agents())
