import zmq
import zmq.asyncio
import json
import logging
import asyncio
import time
import hmac
import hashlib
import secrets
import os
from typing import Dict, Any, Callable, Optional
from core.models import EventPayload

logger = logging.getLogger("Sovereign.NeuralBus")

import os

# Pre-shared Sovereign Key - MUST be injected via environment
_secret = os.getenv("SOVEREIGN_BUS_SECRET")
if not _secret:
    logger.critical("SECURITY LEAK: SOVEREIGN_BUS_SECRET not set! Refusing to use static secret.")
    raise ValueError("SOVEREIGN_BUS_SECRET environment variable is REQUIRED.")
BUS_SECRET = _secret.encode('utf-8')

class NeuralBusClient:
    """Zero-Trust Neural Bus Client with HMAC-SHA256 and Anti-Replay"""
    
    def __init__(self, identity: str, endpoint: str = None):
        self.identity = identity
        self.endpoint = endpoint or os.getenv("ZMQ_BUS_URL", "tcp://127.0.0.1:5555")
        self.context = zmq.asyncio.Context.instance()
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt_string(zmq.IDENTITY, self.identity)
        
        self.handlers: Dict[str, Callable] = {}
        self.seen_nonces: Dict[str, float] = {}
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
                    current_time = time.time()
                    
                    # Purge old nonces (TTL 5 seconds)
                    self.seen_nonces = {k: v for k, v in self.seen_nonces.items() if current_time - v <= 5.0}

                    if nonce in self.seen_nonces:
                        logger.critical(f"[{self.identity}] REPLAY ATTACK DETECTED! Nonce {nonce} already processed.")
                        continue
                    if nonce:
                        self.seen_nonces[nonce] = current_time
                        
                    # 3. TTL Check (60 seconds)
                    msg_time = msg_dict.get("timestamp", 0)
                    if time.time() - msg_time > 60.0:
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
    def __init__(self, endpoint: str = None):
        self.endpoint = endpoint or os.getenv("ZMQ_ROUTER_URL", "tcp://0.0.0.0:5555")
        self.context = zmq.asyncio.Context.instance()
        self.socket = self.context.socket(zmq.ROUTER)
        # Enable mandatory routing to detect offline clients
        self.socket.setsockopt(zmq.ROUTER_MANDATORY, 1)
        self.active_clients = set()
        self._running = False
        
    async def start(self):
        # Enable address reuse to allow fast restart after crashes
        self.socket.setsockopt(zmq.LINGER, 0)
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
                                # Architectural Fix: Use NOBLOCK to prevent one slow client from blocking the entire bus
                                await self.socket.send_multipart([client, signature, msg_bytes], flags=zmq.NOBLOCK)
                            except zmq.ZMQError as e:
                                # Host unreachable or Queue full (EAGAIN)
                                logger.info(f"Client {client.decode(errors='replace')} unreachable or queue full (errno={e.errno}), purging.")
                                disconnected.append(client)
                            except Exception:
                                disconnected.append(client)
                    for d in disconnected:
                        self.active_clients.discard(d)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in NeuralBusRouter loop: {e}")
