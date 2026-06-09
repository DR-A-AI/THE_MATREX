import asyncio
import json
import logging
import uuid
import zmq
import zmq.asyncio
import msgpack
from typing import Dict, Any, Optional
from core.neural_bus import NeuralBusClient
from core.models import EventPayload, EventType
from datetime import datetime

logger = logging.getLogger("MatrixAgent")

class MatrixAgent:
    """
    Lightweight Sovereign Agent connecting to the Neural Bus.
    - Dynamically loads skills via Tool Schema.
    - Uses non-blocking RPC ZMQ hooks to execute actions.
    - Zero-Trust validation on all inbound payloads.
    """
    def __init__(self, name: str, bus_url: str = "tcp://127.0.0.1:5555"):
        # Enforce localhost isolation
        if "127.0.0.1" not in bus_url and "localhost" not in bus_url:
            raise ValueError("Sovereign Razor Violation: Strict localhost isolation required.")
            
        self.name = name
        self.agent_id = str(uuid.uuid4())
        self.bus_url = bus_url
        
        # Security: Force NeuralBusClient instead of raw socket
        self.client = NeuralBusClient(identity=self.agent_id, endpoint=self.bus_url)
        
        # Sovereign DNA Constraint: Immutable Core Identity
        self._CORE_IDENTITY = {
            "identity": "Sovereign Agent",
            "commander": "الأب القائد",
            "directives": [
                "The Sovereign Rules",
                "Zero-Trust Protocol",
                "Absolute Truth Protocol"
            ]
        }
        
        self.tool_schema: Dict[str, Any] = {}
        self._running = False
        self._listen_task: Optional[asyncio.Task] = None

    async def start(self):
        """Connects to the Neural Bus and fetches initial schemas."""
        logger.info(f"[{self.name}] Booting and connecting to Neural Bus at {self.bus_url}...")
        
        # Register handlers
        self.client.register_handler(EventType.TASK_QUEUED.value, self._handle_event)
        self.client.register_handler(EventType.STATE_UPDATE.value, self._handle_event)
        
        await self.client.start()
        self._running = True
        
        # Fetch dynamic tool schemas
        await self.fetch_schemas()

    async def stop(self):
        """Halts the agent gracefully."""
        logger.info(f"[{self.name}] Halting agent operations.")
        self._running = False
        await self.client.stop()

    async def fetch_schemas(self):
        """Requests lightweight Tool Schemas from the Librarian Crawler."""
        logger.debug(f"[{self.name}] Requesting Tool Schema from Crawler via Neural Bus.")
        event = EventPayload(
            event_type=EventType.SKILL_REQUEST,
            source_agent_id=self.agent_id,
            correlation_id=str(uuid.uuid4()),
            payload={"action": "GET_TOOLS"}
        )
        await self.client.send(event)

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Sends a non-blocking RPC request via Neural Bus."""
        if not isinstance(tool_name, str) or not isinstance(arguments, dict):
            raise TypeError("Zero-Trust Violation: Invalid tool execution parameters.")
            
        req_id = str(uuid.uuid4())
        logger.info(f"[{self.name}] Dispatching RPC call to hooks worker: {tool_name} [{req_id}]")
        event = EventPayload(
            event_type=EventType.TASK_QUEUED,
            source_agent_id=self.agent_id,
            correlation_id=req_id,
            payload={
                "tool_name": tool_name,
                "arguments": arguments
            }
        )
        await self.client.send(event)
        return req_id

    async def _handle_event(self, event: EventPayload):
        """Processes and routes inbound payload definitions."""
        msg_type = event.event_type
        payload = event.payload
        
        if msg_type == EventType.SKILL_INJECT:
            schema = payload.get("schema")
            if isinstance(schema, dict):
                self.tool_schema = schema
                logger.info(f"[{self.name}] Tool Schema Loaded: {len(self.tool_schema)} available tools.")
            else:
                logger.error(f"[{self.name}] Invalid schema format received.")
                
        elif msg_type == EventType.TASK_COMPLETED:
            req_id = event.correlation_id
            status = payload.get("status", "unknown")
            logger.info(f"[{self.name}] Tool Call Result [{req_id}] -> Status: {status}")
            
        elif msg_type == EventType.AGENT_HEARTBEAT:
            pong_event = EventPayload(
                event_type=EventType.AGENT_ALIVE,
                source_agent_id=self.agent_id,
                correlation_id=event.correlation_id,
                payload={"status": "alive"}
            )
            await self.client.send(pong_event)
            
        else:
            logger.warning(f"[{self.name}] Unhandled or malicious message type blocked: {msg_type}")

