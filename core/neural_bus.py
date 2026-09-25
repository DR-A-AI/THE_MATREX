import asyncio
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from collections import deque
from collections.abc import Callable
from typing import Any

import zmq
import zmq.asyncio

from core.models import EventPayload

logger = logging.getLogger("Sovereign.NeuralBus")


# Router zero-trust gates (C6 hardening).
MAX_FRAME_BYTES = 1_048_576  # 1 MiB — oversized frames are dropped, never broadcast
FLOOD_MAX_MSGS = 300  # per-sender messages ...
FLOOD_WINDOW_SEC = 5.0
FLOOD_COOLDOWN_SEC = 10.0
FRAME_TTL_SEC = 60.0


# Pre-shared Sovereign Key - MUST be injected via environment
_secret = os.getenv("SOVEREIGN_BUS_SECRET")
if not _secret:
    logger.critical("SECURITY LEAK: SOVEREIGN_BUS_SECRET not set! Refusing to use static secret.")
    raise ValueError("SOVEREIGN_BUS_SECRET environment variable is REQUIRED.")
BUS_SECRET = _secret.encode("utf-8")


class NeuralBusClient:
    """Zero-Trust Neural Bus Client with HMAC-SHA256 and Anti-Replay"""

    def __init__(self, identity: str, endpoint: str | None = None):
        self.identity = identity
        self.endpoint: str = (
            endpoint or os.getenv("ZMQ_BUS_URL", "tcp://127.0.0.1:5555") or "tcp://127.0.0.1:5555"
        )
        self.context = zmq.asyncio.Context.instance()
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt_string(zmq.IDENTITY, self.identity)

        self.handlers: dict[str, Callable[..., Any]] = {}
        self.seen_nonces: dict[str, float] = {}
        self._listen_task: asyncio.Task[None] | None = None

    def _sign_payload(self, payload_bytes: bytes) -> str:
        return hmac.new(BUS_SECRET, payload_bytes, hashlib.sha256).hexdigest()

    def _verify_signature(self, payload_bytes: bytes, signature: str) -> bool:
        expected = self._sign_payload(payload_bytes)
        return hmac.compare_digest(expected, signature)

    def register_handler(self, event_type: str, handler: Callable[..., Any]) -> None:
        self.handlers[event_type] = handler

    async def start(self) -> None:
        self.socket.connect(self.endpoint)
        logger.info(
            f"Sovereign NeuralBus Client (DEALER) {self.identity} connected to {self.endpoint}"
        )
        self._listen_task = asyncio.create_task(self._listen_loop())
        # Register our dealer identity with the router
        await self.socket.send_multipart([b"REGISTER", b""])

    async def stop(self) -> None:
        if self._listen_task:
            self._listen_task.cancel()
        self.socket.close(linger=0)

    async def send(self, event: EventPayload) -> None:
        """Securely sign and send the EventPayload"""
        msg_dict = event.model_dump(mode="json")
        msg_dict["nonce"] = secrets.token_hex(16)
        msg_dict["timestamp"] = time.time()

        msg_bytes = json.dumps(msg_dict).encode("utf-8")
        signature = self._sign_payload(msg_bytes)

        # We send: [Signature, MsgBytes]
        await self.socket.send_multipart([signature.encode("utf-8"), msg_bytes])

    async def _listen_loop(self) -> None:
        while True:
            try:
                parts = await self.socket.recv_multipart()
                if len(parts) >= 2:
                    signature = parts[0].decode("utf-8")
                    msg_bytes = parts[1]

                    # 1. Verify HMAC Signature
                    if not self._verify_signature(msg_bytes, signature):
                        logger.critical(
                            f"[{self.identity}] ZMQ SPOOFING DETECTED! Invalid signature. Dropping message."
                        )
                        continue

                    msg_dict = json.loads(msg_bytes.decode("utf-8"))

                    # 2. Anti-Replay Check
                    nonce = msg_dict.get("nonce")
                    current_time = time.time()

                    # Purge old nonces (TTL 5 seconds)
                    self.seen_nonces = {
                        k: v for k, v in self.seen_nonces.items() if current_time - v <= 5.0
                    }

                    if nonce in self.seen_nonces:
                        logger.critical(
                            f"[{self.identity}] REPLAY ATTACK DETECTED! Nonce {nonce} already processed."
                        )
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
                    event_type_str = (
                        event.event_type.value
                        if hasattr(event.event_type, "value")
                        else event.event_type
                    )
                    handler = self.handlers.get(event_type_str)
                    if handler:
                        asyncio.create_task(handler(event))

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception(f"[{self.identity}] Error in listen loop")


class NeuralBusRouter:
    """The central router that binds to port 5555 and broadcasts/routes."""

    def __init__(self, endpoint: str | None = None):
        self.endpoint: str = (
            endpoint or os.getenv("ZMQ_ROUTER_URL", "tcp://0.0.0.0:5555") or "tcp://0.0.0.0:5555"
        )
        self.context = zmq.asyncio.Context.instance()
        self.socket = self.context.socket(zmq.ROUTER)
        # Enable mandatory routing to detect offline clients
        self.socket.setsockopt(zmq.ROUTER_MANDATORY, 1)
        self.active_clients: set[bytes] = set()
        self._running = False
        self._sender_hits: dict[bytes, deque[float]] = {}
        self._sender_muted_until: dict[bytes, float] = {}

    def _valid_signature(self, signature: bytes, msg_bytes: bytes) -> bool:
        """HMAC-SHA256 gate: True only for frames signed with BUS_SECRET."""
        try:
            signature_str = signature.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            return False
        if not signature_str:
            return False
        expected = hmac.new(BUS_SECRET, msg_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_str)

    def _acceptable_size(self, msg_bytes: bytes) -> bool:
        return len(msg_bytes) <= MAX_FRAME_BYTES

    def _fresh_enough(self, msg_bytes: bytes) -> bool:
        """TTL gate: sender timestamp must be within FRAME_TTL_SEC."""
        try:
            ts = float(json.loads(msg_bytes.decode("utf-8")).get("timestamp", 0))
        except (ValueError, AttributeError, UnicodeDecodeError):
            return False
        return 0 <= time.time() - ts <= FRAME_TTL_SEC

    def _flood_ok(self, sender: bytes) -> bool:
        """Sliding-window flood guard with cooldown mute."""
        now = time.time()
        if now < self._sender_muted_until.get(sender, 0.0):
            return False
        hits = self._sender_hits.setdefault(sender, deque())
        while hits and now - hits[0] > FLOOD_WINDOW_SEC:
            hits.popleft()
        hits.append(now)
        if len(hits) > FLOOD_MAX_MSGS:
            self._sender_muted_until[sender] = now + FLOOD_COOLDOWN_SEC
            logger.warning(
                "NeuralBus Router flood-muted %s for %.0fs.",
                sender.decode(errors="replace"),
                FLOOD_COOLDOWN_SEC,
            )
            return False
        return True

    async def start(self) -> None:
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

                    # Zero-trust gates: HMAC, then size, TTL, flood. A frame
                    # failing any gate is dropped — never broadcast — so one
                    # bad sender can neither storm agents nor replay stale
                    # traffic. Defense in depth: clients re-verify on receipt.
                    if not self._valid_signature(signature, msg_bytes):
                        logger.warning(
                            "NeuralBus Router dropped unsigned/invalid frame "
                            "from %s (not broadcast).",
                            sender.decode(errors="replace"),
                        )
                        continue
                    if not self._acceptable_size(msg_bytes):
                        logger.warning(
                            "NeuralBus Router dropped oversized frame (%d bytes) "
                            "from %s (not broadcast).",
                            len(msg_bytes),
                            sender.decode(errors="replace"),
                        )
                        continue
                    if not self._fresh_enough(msg_bytes):
                        logger.warning(
                            "NeuralBus Router dropped stale frame from %s "
                            "(TTL expired, not broadcast).",
                            sender.decode(errors="replace"),
                        )
                        continue
                    if not self._flood_ok(sender):
                        continue

                    # Broadcast to all other active clients
                    disconnected = []
                    for client in list(self.active_clients):
                        if client != sender:
                            try:
                                # Architectural Fix: Use NOBLOCK to prevent one slow client from blocking the entire bus
                                await self.socket.send_multipart(
                                    [client, signature, msg_bytes], flags=zmq.NOBLOCK
                                )
                            except zmq.ZMQError as e:
                                # Host unreachable or Queue full (EAGAIN)
                                logger.info(
                                    f"Client {client.decode(errors='replace')} unreachable or queue full (errno={e.errno}), purging."
                                )
                                disconnected.append(client)
                            except Exception:
                                logger.exception("Broadcast to client failed")
                                disconnected.append(client)
                    for d in disconnected:
                        self.active_clients.discard(d)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in NeuralBusRouter loop")
