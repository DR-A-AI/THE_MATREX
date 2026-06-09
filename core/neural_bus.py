import zmq
import zmq.asyncio
import msgpack
import logging
import asyncio
from typing import Dict, Any, Callable, Optional
import time
from datetime import datetime

from core.models import EventPayload, EventType

logger = logging.getLogger("Sovereign.NeuralBus")

class CircuitBreakerOpenException(Exception):
    pass

class CircuitBreaker:
    """Strict Sovereign Circuit Breaker for DB/Network resilience."""
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 10):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"
    
    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.critical("Circuit breaker OPENED. Halting operations temporarily.")
    
    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"
    
    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return self.state == "HALF_OPEN"

class NeuralBusBroker:
    """ROUTER socket acting as the main neural bus."""
    def __init__(self, endpoint: str = "tcp://127.0.0.1:5555"):
        self.context = zmq.asyncio.Context.instance()
        self.socket = self.context.socket(zmq.ROUTER)
        self.socket.setsockopt(zmq.ROUTER_MANDATORY, 1)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.endpoint = endpoint
        self.socket.bind(endpoint)
        logger.info(f"Sovereign NeuralBus Broker (ROUTER) bound to {endpoint}")
        self._running = False
        self.handlers = {}
        self._task = None

    def register_handler(self, event_type: str, handler: Callable):
        self.handlers[event_type] = handler

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._routing_loop())
        logger.info("NeuralBus Broker routing loop active.")

    async def _routing_loop(self):
        while self._running:
            try:
                msg_parts = await self.socket.recv_multipart()
                if len(msg_parts) < 2:
                    continue
                
                identity = msg_parts[0]
                payload_bytes = msg_parts[-1]
                
                try:
                    data = msgpack.unpackb(payload_bytes)
                except Exception as e:
                    logger.error(f"Failed to unpack msgpack from {identity}: {e}")
                    continue
                
                try:
                    event = EventPayload(**data)
                except Exception as e:
                    logger.error(f"Invalid payload from {identity}: {e}")
                    continue
                
                handler = self.handlers.get(event.event_type)
                if handler:
                    asyncio.create_task(handler(identity, event))
                else:
                    logger.debug(f"No handler for event: {event.event_type}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Broker error: {e}")
                
    async def send(self, identity: bytes, event: EventPayload):
        try:
            # We explicitly handle event serialization. We use event.model_dump() instead of dict() for pydantic v2 if needed, 
            # but model.dict() works usually. EventPayload is inherited from BaseModel.
            payload_dict = event.dict()
            # msgpack requires datetime to be serialized properly. Let's convert timestamps to isoformat.
            payload_dict['timestamp'] = payload_dict['timestamp'].isoformat()
            
            payload_bytes = msgpack.packb(payload_dict)
            await self.socket.send_multipart([identity, payload_bytes])
        except Exception as e:
            logger.error(f"Broker failed to send to {identity}: {e}")
            
    async def broadcast(self, identities: list, event: EventPayload):
        """Send message to multiple identities."""
        for identity in identities:
            await self.send(identity, event)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        self.socket.close(linger=0)

class NeuralBusClient:
    """DEALER socket for agents to connect to the neural bus."""
    def __init__(self, identity: str, endpoint: str = "tcp://127.0.0.1:5555"):
        self.context = zmq.asyncio.Context.instance()
        self.socket = self.context.socket(zmq.DEALER)
        self.identity = identity.encode('utf-8')
        self.socket.setsockopt(zmq.IDENTITY, self.identity)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.endpoint = endpoint
        self.socket.connect(endpoint)
        self.circuit_breaker = CircuitBreaker()
        self._running = False
        self.handlers = {}
        self._task = None
        logger.info(f"Sovereign NeuralBus Client (DEALER) {identity} connected to {endpoint}")

    def register_handler(self, event_type: str, handler: Callable):
        self.handlers[event_type] = handler

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._client_loop())

    async def _client_loop(self):
        while self._running:
            try:
                msg_parts = await self.socket.recv_multipart()
                if not msg_parts:
                    continue
                    
                payload_bytes = msg_parts[-1]
                
                try:
                    data = msgpack.unpackb(payload_bytes)
                except Exception:
                    continue
                
                try:
                    event = EventPayload(**data)
                except Exception as e:
                    logger.error(f"Client {self.identity} received invalid payload: {e}")
                    continue
                    
                handler = self.handlers.get(event.event_type)
                if handler:
                    asyncio.create_task(handler(event))
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Client {self.identity} error: {e}")
                
    async def send(self, event: EventPayload):
        if not self.circuit_breaker.can_execute():
            raise CircuitBreakerOpenException("Circuit breaker is open.")
            
        try:
            payload_dict = event.dict()
            payload_dict['timestamp'] = payload_dict['timestamp'].isoformat()
            payload_bytes = msgpack.packb(payload_dict)
            await self.socket.send_multipart([payload_bytes])
            self.circuit_breaker.record_success()
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(f"Client {self.identity} failed to send: {e}")
            raise
            
    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        self.socket.close(linger=0)
