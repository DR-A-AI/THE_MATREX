import zmq
import zmq.asyncio
import msgpack
import logging
import asyncio
from typing import Dict, Any, Callable, Optional
import time

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

class NeuralBusPublisher:
    """High-performance ZMQ PUB socket using msgpack."""
    
    def __init__(self, endpoint: str = "tcp://127.0.0.1:5555"):
        self.context = zmq.asyncio.Context.instance()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.setsockopt(zmq.SNDHWM, 1000)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.endpoint = endpoint
        self.socket.bind(endpoint)
        self.circuit_breaker = CircuitBreaker()
        logger.info(f"Sovereign NeuralBus Publisher bound to {endpoint}")
    
    async def publish(self, topic: str, payload: Dict[str, Any], trace_id: str):
        if not self.circuit_breaker.can_execute():
            logger.error(f"Execution Halt: Cannot publish to {topic}, Circuit Breaker OPEN.")
            raise CircuitBreakerOpenException("Circuit breaker is open.")
            
        try:
            message = {
                "trace_id": trace_id,
                "timestamp": time.time(),
                "payload": payload
            }
            # MessagePack instead of slow JSON. NEVER use Pickle.
            await self.socket.send_multipart([
                topic.encode('utf-8'),
                msgpack.packb(message)
            ])
            self.circuit_breaker.record_success()
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(f"NeuralBus Publish Error: {e}")
            raise
    
    def close(self):
        self.socket.close(linger=0)

class NeuralBusSubscriber:
    """High-performance ZMQ SUB socket using msgpack."""
    
    def __init__(self, endpoint: str = "tcp://127.0.0.1:5555", topics: list = None):
        self.context = zmq.asyncio.Context.instance()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.setsockopt(zmq.RCVHWM, 1000)
        self.endpoint = endpoint
        self.socket.connect(endpoint)
        
        topics = topics or ["events"]
        for t in topics:
            self.socket.setsockopt_string(zmq.SUBSCRIBE, t)
            
        logger.info(f"Sovereign NeuralBus Subscriber connected to {endpoint} for topics: {topics}")
        self.is_running = False
        
    async def consume(self, callback: Callable):
        self.is_running = True
        while self.is_running:
            try:
                msg_parts = await self.socket.recv_multipart()
                if len(msg_parts) == 2:
                    topic = msg_parts[0].decode('utf-8')
                    # Secure msgpack decoding, explicitly disabling eval or arbitrary object execution
                    data = msgpack.unpackb(msg_parts[1])
                    # Ensure asynchronous callback execution to prevent event loop blocking
                    asyncio.create_task(callback(topic, data))
            except asyncio.CancelledError:
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"Subscriber consumption error: {e}")
                
    def close(self):
        self.is_running = False
        self.socket.close(linger=0)
