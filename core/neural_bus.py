import zmq
import zmq.asyncio
import json
import logging
import asyncio
import time
import hmac
import hashlib
import secrets
from typing import Dict, Any, Callable

logger = logging.getLogger("Sovereign.NeuralBus")

class CircuitBreakerOpenException(Exception): pass

# Secret key injected dynamically via secure vault in a real system.
# Using a static placeholder for the Sovereign Matrix.
BUS_SECRET = b"SOVEREIGN_RAZOR_STATIC_SECRET_DO_NOT_USE_IN_PROD"

class SovereignNeuralBus:
    """Zero-Trust Neural Bus with HMCA-SHA256 Signatures and Anti-Replay."""
    
    def __init__(self, endpoint_pub: str = "tcp://127.0.0.1:5555", endpoint_sub: str = "tcp://127.0.0.1:5555"):
        self.context = zmq.asyncio.Context.instance()
        self.pub_endpoint = endpoint_pub
        self.sub_endpoint = endpoint_sub
        self.seen_nonces = set()
        
    def _sign_payload(self, payload_bytes: bytes) -> str:
        return hmac.new(BUS_SECRET, payload_bytes, hashlib.sha256).hexdigest()

    def _verify_signature(self, payload_bytes: bytes, signature: str) -> bool:
        expected = self._sign_payload(payload_bytes)
        return hmac.compare_digest(expected, signature)

    async def publish(self, socket, topic: str, payload: Dict[str, Any], trace_id: str):
        message = {
            "trace_id": trace_id,
            "nonce": secrets.token_hex(16),
            "timestamp": time.time(),
            "payload": payload
        }
        msg_bytes = json.dumps(message).encode("utf-8")
        signature = self._sign_payload(msg_bytes)
        
        await socket.send_multipart([
            topic.encode("utf-8"),
            signature.encode("utf-8"),
            msg_bytes
        ])
        logger.debug(f"Securely published to {topic}")

    async def consume(self, socket, callback: Callable):
        while True:
            parts = await socket.recv_multipart()
            if len(parts) == 3:
                topic = parts[0].decode("utf-8")
                signature = parts[1].decode("utf-8")
                msg_bytes = parts[2]
                
                # 1. Signature Verification
                if not self._verify_signature(msg_bytes, signature):
                    logger.critical(f"SPOOFING DETECTED on {topic}. Invalid signature.")
                    continue
                
                msg = json.loads(msg_bytes.decode("utf-8"))
                
                # 2. Replay Attack Prevention
                nonce = msg.get("nonce")
                if nonce in self.seen_nonces:
                    logger.critical(f"REPLAY ATTACK DETECTED on {topic}.")
                    continue
                self.seen_nonces.add(nonce)
                
                # 3. TTL / Expiration Check
                if time.time() - msg.get("timestamp", 0) > 5.0:
                    logger.warning(f"Message TTL expired for {topic}.")
                    continue
                    
                await callback(topic, msg["payload"])

