import asyncio
import json
import logging
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from core.neural_bus import NeuralBusClient
from core.models import EventPayload, EventType

logger = logging.getLogger("Sovereign.UI_Bridge")
logging.basicConfig(level=logging.INFO)

# --- Clerk Validation Logic ---
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.critical("PyJWT not installed. Clerk validation will fail. Run: pip install PyJWT cryptography")

CLERK_PEM_PUBLIC_KEY = os.getenv("CLERK_PEM_PUBLIC_KEY", "")

def verify_clerk_token(token: str) -> bool:
    if not token:
        logger.critical("SECURITY LEAK: No Clerk token provided by frontend!")
        return False
        
    if not JWT_AVAILABLE:
        logger.critical("SECURITY LEAK: PyJWT not installed. Cannot verify token! Denying access.")
        return False
        
    if not CLERK_PEM_PUBLIC_KEY:
        logger.critical("SECURITY WARNING: CLERK_PEM_PUBLIC_KEY is missing! Enforcing strict deny.")
        return False
        
    try:
        decoded = jwt.decode(token, CLERK_PEM_PUBLIC_KEY, algorithms=["RS256"])
        logger.info(f"Clerk Token verified for user: {decoded.get('sub')}")
        return True
    except jwt.ExpiredSignatureError:
        logger.error("Clerk Token expired.")
        return False
    except Exception as e:
        logger.error(f"Clerk Token validation failed: {e}")
        return False

app = FastAPI(title="Sovereign UI Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_connections = []
bus_client = NeuralBusClient(identity="UI_Bridge")
send_lock = asyncio.Lock()

@app.on_event("startup")
async def startup_event():
    await bus_client.start()
    
    async def handle_agent_message(event: EventPayload):
        logger.info(f"Bridge received from ZMQ: {event.payload}")
        
        payload_data = event.payload
        if isinstance(payload_data, str):
            try:
                payload_data = json.loads(payload_data)
            except Exception:
                pass

        is_status = isinstance(payload_data, dict) and "status_action" in payload_data
        
        if is_status:
            text_content = payload_data.get("status_action")
        else:
            text_content = payload_data.get("message", str(payload_data)) if isinstance(payload_data, dict) else str(payload_data)
            
        msg_str = json.dumps({
            "sender": event.source_agent_id,
            "text": text_content,
            "type": "status" if is_status else "chat"
        })
        
        async with send_lock:
            for conn in list(active_connections):
                try:
                    await conn.send_text(msg_str)
                except Exception as e:
                    logger.error(f"WebSocket send failed: {e}")
                
    bus_client.register_handler(EventType.STATE_UPDATE.value, handle_agent_message)
    bus_client.register_handler(EventType.TASK_COMPLETED.value, handle_agent_message)
    bus_client.register_handler(EventType.SOVEREIGN_OVERRIDE.value, handle_agent_message)
    bus_client.register_handler(EventType.AGENT_ALIVE.value, handle_agent_message)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    logger.info("New UI WebSocket Connection Established.")
    
    authenticated = False
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            if not authenticated:
                token = payload.get("clerk_token")
                if verify_clerk_token(token):
                    authenticated = True
                    await websocket.send_text(json.dumps({"type": "auth", "status": "success"}))
                    continue
                else:
                    logger.critical("Unauthorized UI connection attempt closed.")
                    await websocket.send_text(json.dumps({"type": "auth", "status": "failed"}))
                    await websocket.close()
                    break

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
        logger.info("UI WebSocket Connection Closed.")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)

def run_bridge():
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    uvicorn.run("services.ui_bridge:app", host=os.getenv("UI_HOST", "0.0.0.0"), port=int(os.getenv("UI_PORT", 8000)), reload=False)

if __name__ == "__main__":
    run_bridge()
