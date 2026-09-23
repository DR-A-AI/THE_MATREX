import asyncio
import contextlib
import os
import sys
import time
from collections.abc import AsyncIterator

# Set loop policy BEFORE anything else to fix ZMQ on Windows
if sys.platform == "win32":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    import warnings

    warnings.filterwarnings("ignore", category=DeprecationWarning)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from core.models import EventPayload, EventType
from core.neural_bus import NeuralBusClient

logger = logging.getLogger("Sovereign.UI_Bridge")
logging.basicConfig(level=logging.INFO)

# --- Clerk Validation Logic ---
try:
    import jwt

    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.critical(
        "PyJWT not installed. Clerk validation will fail. Run: pip install PyJWT cryptography"
    )

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
    except Exception:
        logger.exception("Clerk Token validation failed")
        return False


active_connections: list[WebSocket] = []
send_lock: asyncio.Lock | None = None
bus_client: NeuralBusClient | None = None


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global send_lock
    send_lock = asyncio.Lock()
    global bus_client
    bus_client = NeuralBusClient(identity="UI_Bridge")

    async def handle_agent_message(event: EventPayload) -> None:
        logger.info(f"Bridge received from ZMQ: {event.payload}")

        payload_data = event.payload
        if isinstance(payload_data, str):
            try:
                payload_data = json.loads(payload_data)
            except Exception:
                logger.debug("Bridge payload is not JSON, keeping as string", exc_info=True)

        is_status = isinstance(payload_data, dict) and "status_action" in payload_data

        if is_status:
            text_content = payload_data.get("status_action")
        else:
            text_content = (
                payload_data.get("message", str(payload_data))
                if isinstance(payload_data, dict)
                else str(payload_data)
            )

        msg_str = json.dumps(
            {
                "sender": event.source_agent_id,
                "text": text_content,
                "type": "status" if is_status else "chat",
            }
        )

        if send_lock:
            async with send_lock:
                for conn in list(active_connections):  # noqa: PERF101
                    try:
                        await conn.send_text(msg_str)
                    except Exception:
                        logger.exception("WebSocket send failed")

    bus_client.register_handler(EventType.STATE_UPDATE.value, handle_agent_message)
    bus_client.register_handler(EventType.TASK_COMPLETED.value, handle_agent_message)
    bus_client.register_handler(EventType.SOVEREIGN_OVERRIDE.value, handle_agent_message)
    bus_client.register_handler(EventType.AGENT_ALIVE.value, handle_agent_message)

    asyncio.create_task(bus_client.start())
    try:
        yield
    finally:
        if bus_client is not None:
            await bus_client.stop()


app = FastAPI(title="Sovereign UI Bridge", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(
        ","
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
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
                payload={"target_agent": target_agent, "message": user_text},
            )
            if bus_client is not None:
                await bus_client.send(event)
            else:
                logger.error("Cannot forward user command: bus_client is not initialized")

    except WebSocketDisconnect:
        logger.info("UI WebSocket Connection Closed.")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)


def run_bridge() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    uvicorn.run(
        "services.ui_bridge:app",
        # Localhost default; set UI_HOST or HOST to 0.0.0.0 to opt into all interfaces.
        host=os.getenv("UI_HOST", os.getenv("HOST", "127.0.0.1")),
        port=int(os.getenv("UI_PORT", "8000")),
        reload=False,
        loop="asyncio",
    )


if __name__ == "__main__":
    try:
        run_bridge()
    except Exception:
        import traceback

        with open("crash.log", "w") as f:
            f.write(traceback.format_exc())
        raise
