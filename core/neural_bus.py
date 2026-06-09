import zmq
import zmq.asyncio
import json
import logging
import asyncio
import time
import hmac
import hashlib
import secrets
from typing import Dict, Any, Callable, Optional
from core.models import EventPayload

logger = logging.getLogger("Sovereign.NeuralBus")

# Pre-shared Sovereign Key
BUS_SECRET = b"SOVEREIGN_RAZOR_STATIC_SECRET_DO_NOT_USE_IN_PROD"

class NeuralBusClient:
    """Zero-Trust Neural Bus Client with HMAC-SHA256 and Anti-Replay"""
    
    def __init__(self, identity: str, endpoint: str = "tcp://127.0.0.1:5555"):
        self.identity = identity
        self.endpoint = endpoint
        self.context = zmq.asyncio.Context.instance()
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt_string(zmq.IDENTITY, self.identity)
        
        self.handlers: Dict[str, Callable] = {}
        self.seen_nonces = set()
        self._listen_task: Optional[asyncio.Task] = None

    def _sign_payload(self, payload_bytes: bytes) -> str:
        return hmac.new(BUS_SECRET, payload_bytes, hashlib.sha256).hexdigest()

    def _verify_signature(self, payload_bytes: bytes, signature: str) -> bool:
        expected = self._sign_payload(payload_bytes)
        return hmac.compare_digest(expected, signature)

    def register_handler(self, event_type: str, handler: Callable):
        self.handlers[event_type] = handler

    async def start(self):
        self.socket.connect(self.endpoint)
        logger.info(f"Sovereign NeuralBus Client (DEALER) {self.identity} connected to {self.endpoint}")
        self._listen_task = asyncio.create_task(self._listen_loop())
        # Register our dealer identity with the router
        await self.socket.send_multipart([b"REGISTER", b""])

    async def stop(self):
        if self._listen_task:
            self._listen_task.cancel()
        self.socket.close(linger=0)

    async def send(self, event: EventPayload):
        """Securely sign and send the EventPayload"""
        msg_dict = event.model_dump(mode="json")
        msg_dict["nonce"] = secrets.token_hex(16)
        msg_dict["timestamp"] = time.time()
        
        msg_bytes = json.dumps(msg_dict).encode("utf-8")
        signature = self._sign_payload(msg_bytes)
        
        # We send: [Signature, MsgBytes]
        await self.socket.send_multipart([
            signature.encode("utf-8"),
            msg_bytes
        ])

    async def _listen_loop(self):
        while True:
            try:
                parts = await self.socket.recv_multipart()
                if len(parts) >= 2:
                    signature = parts[0].decode("utf-8")
                    msg_bytes = parts[1]
                    
                    # 1. Verify HMAC Signature
                    if not self._verify_signature(msg_bytes, signature):
                        logger.critical(f"[{self.identity}] ZMQ SPOOFING DETECTED! Invalid signature. Dropping message.")
                        continue
                        
                    msg_dict = json.loads(msg_bytes.decode("utf-8"))
                    
                    # 2. Anti-Replay Check
                    nonce = msg_dict.get("nonce")
                    if nonce in self.seen_nonces:
                        logger.critical(f"[{self.identity}] REPLAY ATTACK DETECTED! Nonce {nonce} already processed.")
                        continue
                    if nonce:
                        self.seen_nonces.add(nonce)
                        
                    # 3. TTL Check (5 seconds)
                    msg_time = msg_dict.get("timestamp", 0)
                    if time.time() - msg_time > 5.0:
                        logger.warning(f"[{self.identity}] Message TTL expired. Dropping message.")
                        continue
                    
                    # 4. Dispatch Event
                    event = EventPayload(**msg_dict)
                    event_type_str = event.event_type.value if hasattr(event.event_type, 'value') else event.event_type
                    handler = self.handlers.get(event_type_str)
                    if handler:
                        asyncio.create_task(handler(event))
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{self.identity}] Error in listen loop: {e}")

class NeuralBusRouter:
    """The central router that binds to port 5555 and broadcasts/routes."""
    def __init__(self, endpoint: str = "tcp://127.0.0.1:5555"):
        self.endpoint = endpoint
        self.context = zmq.asyncio.Context.instance()
        self.socket = self.context.socket(zmq.ROUTER)
        # Enable mandatory routing to detect offline clients
        self.socket.setsockopt(zmq.ROUTER_MANDATORY, 1)
        self.active_clients = set()
        self._running = False
        
    async def start(self):
        self.socket.bind(self.endpoint)
        self._running = True
        logger.info(f"Sovereign NeuralBus Router started at {self.endpoint}")
        while self._running:
            try:
                parts = await self.socket.recv_multipart()
                if len(parts) >= 3:
                    sender = parts[0]
                    self.active_clients.add(sender)
                    
                    signature = parts[1]
                    msg_bytes = parts[2]
                    
                    # If it's a registration frame, do not broadcast
                    if signature == b"REGISTER":
                        continue
                    
                    # Broadcast to all other active clients
                    disconnected = []
                    for client in list(self.active_clients):
                        if client != sender:
                            try:
                                await self.socket.send_multipart([client, signature, msg_bytes])
                            except zmq.ZMQError as e:
                                # Host unreachable (EHOSTUNREACH)
                                logger.info(f"Client {client.decode(errors='replace')} unreachable, purging.")
                                disconnected.append(client)
                            except Exception:
                                disconnected.append(client)
                    for d in disconnected:
                        self.active_clients.discard(d)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in NeuralBusRouter loop: {e}")
