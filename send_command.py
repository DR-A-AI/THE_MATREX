import os

from dotenv import load_dotenv

load_dotenv()

import argparse
import asyncio
import sys
import uuid

from core.models import EventPayload, EventType
from core.neural_bus import NeuralBusClient


async def send_command(agent: str, message: str, timeout: int = 60):
    bus_url = os.getenv("ZMQ_BUS_URL", "tcp://127.0.0.1:5555")
    
    secret = os.getenv("SOVEREIGN_BUS_SECRET")
    if not secret:
        print("ERROR: SOVEREIGN_BUS_SECRET must be set in .env")
        sys.exit(1)

    # Use a unique identity for this CLI session
    session_id = str(uuid.uuid4())[:8]
    client_identity = f"CommanderCLI_{session_id}"
    
    client = NeuralBusClient(identity=client_identity, endpoint=bus_url)
    
    # We will use this event to wait for the response
    response_received = asyncio.Event()
    correlation_id = str(uuid.uuid4())
    final_response = None
    
    # Setup inbound handler
    async def on_response(event: EventPayload):
        nonlocal final_response
        # Check if this message is a response to our correlation_id
        if event.correlation_id == correlation_id:
            payload = event.payload or {}
            
            # Normalize event_type to string regardless of whether it's enum or str
            evt_type = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
            
            msg = payload.get("message", payload.get("status_action", ""))
            if msg and evt_type not in ("task_completed", "TASK_COMPLETED"):
                print(f"[{event.source_agent_id}]: {msg}")
                
            if evt_type in ("task_completed", "TASK_COMPLETED"):
                final_response = msg
                if msg:
                    print(f"[{event.source_agent_id}] (Final): {msg}")
                response_received.set()

    # Register handlers for both STATE_UPDATE and TASK_COMPLETED
    client.register_handler(EventType.STATE_UPDATE.value, on_response)
    client.register_handler(EventType.TASK_COMPLETED.value, on_response)
    
    await client.start()
    await asyncio.sleep(0.3)  # Allow ZMQ router dealer registration to settle
    
    payload = EventPayload(
        event_type=EventType.USER_COMMAND,
        source_agent_id="dr-anas-hilal",
        correlation_id=correlation_id,
        payload={
            "target_agent": agent,
            "message": message,
            "auth_token": os.getenv("COMMANDER_AUTH_TOKEN", "sovereign_commander_token_123"),
            # Include our reply_to identity so the agent knows who to send the response back to
            "reply_to": client_identity 
        }
    )
    
    print(f"📡 Sending authenticated command to '{agent}'...")
    await client.send(payload)
    print("✅ Command sent to Neural Bus. Waiting for response...\n")
    print("━" * 40)
    
    try:
        # Wait synchronously for the response (up to timeout)
        await asyncio.wait_for(response_received.wait(), timeout=timeout)
        if not final_response:
            print(f"\n[Agent {agent}]: Task completed successfully.")
    except asyncio.TimeoutError:
        print(f"\n❌ ERROR: Timed out after {timeout} seconds waiting for '{agent}' to respond.")
        print("The agent might be offline, processing a very long task, or the Router purged the queue.")
    
    print("━" * 40)
    
    # Graceful shutdown
    await client.stop()


if __name__ == "__main__":
    # Ensure Windows selector policy is set if on Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    parser = argparse.ArgumentParser(description="Send a command to a Matrix Agent synchronously")
    parser.add_argument("--agent", type=str, default="neo", help="Target agent name")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds to wait for a response")
    parser.add_argument("message", type=str, help="The command message to send")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(send_command(args.agent, args.message, args.timeout))
    except KeyboardInterrupt:
        print("\n⚠️ Command cancelled by user.")
        sys.exit(0)
