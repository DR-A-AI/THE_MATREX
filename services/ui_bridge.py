import asyncio
import json
import logging
import time
import sys
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from core.neural_bus import NeuralBusClient
from core.models import EventPayload, EventType

logger = logging.getLogger("Sovereign.UI_Bridge")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Sovereign UI Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_connections = []
bus_client = NeuralBusClient(identity="UI_Bridge")

@app.on_event("startup")
async def startup_event():
    await bus_client.start()
    
    async def handle_agent_message(event: EventPayload):
        logger.info(f"Bridge received from ZMQ: {event.payload}")
        is_status = isinstance(event.payload, dict) and "status_action" in event.payload
        
        if is_status:
            text_content = event.payload.get("status_action")
        else:
            text_content = event.payload.get("message", str(event.payload)) if isinstance(event.payload, dict) else str(event.payload)
            
        msg_str = json.dumps({
            "sender": event.source_agent_id,
            "text": text_content,
            "type": "status" if is_status else "chat"
        })
        for conn in active_connections:
            try:
                await conn.send_text(msg_str)
            except Exception:
                pass
                
    bus_client.register_handler(EventType.STATE_UPDATE.value, handle_agent_message)
    bus_client.register_handler(EventType.TASK_COMPLETED.value, handle_agent_message)
    bus_client.register_handler(EventType.SOVEREIGN_OVERRIDE.value, handle_agent_message)
    bus_client.register_handler(EventType.AGENT_ALIVE.value, handle_agent_message)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    logger.info("New UI WebSocket Connection Established.")
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            target_agent = payload.get("agent", "neo")
            user_text = payload.get("text", "")
            
            logger.info(f"UI sent to {target_agent}: {user_text}")
            
            event = EventPayload(
                event_type=EventType.USER_COMMAND,
                source_agent_id="Commander_UI",
                correlation_id=str(int(time.time())),
                payload={"target_agent": target_agent, "message": user_text}
            )
            await bus_client.send(event)
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info("UI WebSocket Connection Closed.")

def run_bridge():
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    uvicorn.run("services.ui_bridge:app", host="127.0.0.1", port=8000, reload=False)

if __name__ == "__main__":
    run_bridge()
