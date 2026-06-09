import asyncio
import json
import logging
import uuid
import zmq
import zmq.asyncio
from typing import Dict, Any, Optional

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
        self.ctx = zmq.asyncio.Context.instance()
        self.socket = self.ctx.socket(zmq.DEALER)
        self.socket.identity = self.agent_id.encode('utf-8')
        
        # Security: set timeout/linger to prevent infinite hanging
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.setsockopt(zmq.RCVTIMEO, 5000)
        
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
        self.socket.connect(self.bus_url)
        self._running = True
        
        # Start background listener for responses and async tool hooks
        self._listen_task = asyncio.create_task(self._listen_loop())
        
        # Fetch dynamic tool schemas
        await self.fetch_schemas()

    async def stop(self):
        """Halts the agent gracefully."""
        logger.info(f"[{self.name}] Halting agent operations.")
        self._running = False
        if self._listen_task:
            self._listen_task.cancel()
        self.socket.close(linger=0)

    async def fetch_schemas(self):
        """Requests lightweight Tool Schemas from the Librarian Crawler."""
        logger.debug(f"[{self.name}] Requesting Tool Schema from Crawler via Neural Bus.")
        request = {
            "type": "GET_TOOLS",
            "sender": self.agent_id
        }
        await self._send_request(request)

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Sends a non-blocking RPC request to the ZMQ hooks worker."""
        if not isinstance(tool_name, str) or not isinstance(arguments, dict):
            raise TypeError("Zero-Trust Violation: Invalid tool execution parameters.")
            
        req_id = str(uuid.uuid4())
        logger.info(f"[{self.name}] Dispatching RPC call to hooks worker: {tool_name} [{req_id}]")
        request = {
            "type": "CALL_TOOL",
            "tool_name": tool_name,
            "arguments": arguments,
            "sender": self.agent_id,
            "request_id": req_id
        }
        await self._send_request(request)
        return req_id

    async def _send_request(self, payload: Dict[str, Any]):
        """Encodes and dispatches payload via Zero-Trust parameters."""
        try:
            payload_bytes = json.dumps(payload).encode('utf-8')
            # Sending DEALER -> ROUTER requires empty frame delimiter for proper REQ/REP wrapping
            await self.socket.send_multipart([b"", payload_bytes])
        except (TypeError, ValueError) as e:
            logger.error(f"[{self.name}] Serialization failure. Zero-trust drop: {e}")

    async def _listen_loop(self):
        """Background loop to receive schemas, RPC results, and Watchdog pings."""
        while self._running:
            try:
                # Non-blocking receive via zmq.asyncio
                message = await self.socket.recv_multipart()
                
                if len(message) < 2:
                    logger.warning(f"[{self.name}] Dropping malformed multipart message.")
                    continue
                    
                payload_data = message[-1].decode('utf-8')
                
                try:
                    payload = json.loads(payload_data)
                    if not isinstance(payload, dict):
                        raise ValueError("Payload must be a JSON object.")
                    await self._handle_message(payload)
                except json.JSONDecodeError:
                    logger.error(f"[{self.name}] Zero-trust violation: Invalid JSON payload received.")
                    
            except zmq.error.Again:
                # Timeout reached, continue loop
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{self.name}] Critical fault in listen loop: {e}")
                await asyncio.sleep(0.5)

    async def _handle_message(self, payload: Dict[str, Any]):
        """Processes and routes inbound payload definitions."""
        msg_type = payload.get("type")
        
        if msg_type == "TOOL_SCHEMA_RESPONSE":
            schema = payload.get("schema")
            if isinstance(schema, dict):
                self.tool_schema = schema
                logger.info(f"[{self.name}] Tool Schema Loaded: {len(self.tool_schema)} available tools.")
            else:
                logger.error(f"[{self.name}] Invalid schema format received.")
                
        elif msg_type == "TOOL_CALL_RESULT":
            req_id = payload.get("request_id")
            status = payload.get("status", "unknown")
            logger.info(f"[{self.name}] Tool Call Result [{req_id}] -> Status: {status}")
            
        elif msg_type == "WATCHDOG_PING":
            pong = {"type": "WATCHDOG_PONG", "sender": self.agent_id}
            await self._send_request(pong)
            
        else:
            logger.warning(f"[{self.name}] Unhandled or malicious message type blocked: {msg_type}")
