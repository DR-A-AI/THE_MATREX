import os
import zmq
import zmq.asyncio
import orjson  # Faster, safer than standard json, no pickle!
import logging
import asyncio
from typing import Dict, Any, Callable, Optional
import time

logger = logging.getLogger("Sovereign.NeuralBus")

class CircuitBreakerOpenException(Exception):
    pass

class CircuitBreaker:
    """Implements Circuit Breaker to handle DB/Network faults resiliently without blocking async loops."""
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 10.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.monotonic()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning("Circuit breaker OPENED due to consecutive failures.")
    
    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"
    
    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.monotonic() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        if self.state == "HALF_OPEN":
            return True
        return False

class NeuralBusPublisher:
    """ZMQ PUB socket for broadcasting microsecond-latency events using IPC or configurable TCP."""
    
    def __init__(self, endpoint: Optional[str] = None):
        self.context = zmq.asyncio.Context.instance()
        self.socket = self.context.socket(zmq.PUB)
        # Prevent runaway processes / blocking
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.setsockopt(zmq.SNDHWM, 1000)
        
        self.endpoint = endpoint or os.getenv("SOVEREIGN_NEURAL_BUS_PUB", "ipc:///tmp/sovereign_neural_bus.ipc")
        self.socket.bind(self.endpoint)
        self.circuit_breaker = CircuitBreaker()
        logger.info(f"NeuralBus Publisher strictly bound to {self.endpoint}")
    
    async def publish(self, topic: str, payload: Dict[str, Any], trace_id: str):
        if not self.circuit_breaker.can_execute():
            logger.error(f"Cannot publish {topic}, Circuit Breaker is OPEN.")
            raise CircuitBreakerOpenException("Circuit breaker is open.")
            
        try:
            message = {
                "trace_id": trace_id,
                "timestamp": time.monotonic(),
                "payload": payload
            }
            # No pickle. Using orjson for speed and security.
            await self.socket.send_multipart([
                topic.encode('utf-8'),
                orjson.dumps(message)
            ])
            self.circuit_breaker.record_success()
            logger.debug(f"Published to {topic} [Trace: {trace_id}]")
        except zmq.ZMQError as e:
            self.circuit_breaker.record_failure()
            logger.error(f"NeuralBus Publish Error (ZMQ): {e}")
            raise
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.critical(f"NeuralBus Unhandled Publish Error: {e}")
            raise
    
    def close(self):
        self.socket.close(linger=0)

class NeuralBusSubscriber:
    """ZMQ SUB socket for receiving microsecond-latency events."""
    
    def __init__(self, endpoint: Optional[str] = None, topics: list = None):
        self.context = zmq.asyncio.Context.instance()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.setsockopt(zmq.RCVHWM, 1000)
        
        self.endpoint = endpoint or os.getenv("SOVEREIGN_NEURAL_BUS_PUB", "ipc:///tmp/sovereign_neural_bus.ipc")
        self.socket.connect(self.endpoint)
        
        topics = topics or ["events"]
        for t in topics:
            self.socket.setsockopt_string(zmq.SUBSCRIBE, t)
            
        logger.info(f"NeuralBus Subscriber connected to {self.endpoint} listening to {topics}")
        self.is_running = False
        
    async def consume(self, callback: Callable):
        self.is_running = True
        while self.is_running:
            try:
                # Proper native async receive, absolutely NO busy loop polling
                msg_parts = await self.socket.recv_multipart()
                if len(msg_parts) == 2:
                    topic = msg_parts[0].decode('utf-8')
                    data = orjson.loads(msg_parts[1])
                    asyncio.create_task(callback(topic, data))
            except asyncio.CancelledError:
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"Subscriber critical error: {e}")
                
    def close(self):
        self.is_running = False
        self.socket.close(linger=0)
