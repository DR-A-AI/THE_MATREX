import zmq
import zmq.asyncio
import json
import logging
import asyncio
from typing import Dict, Any, Callable, Optional
import time

logger = logging.getLogger("Sovereign.NeuralBus")

class CircuitBreakerOpenException(Exception):
    pass

class CircuitBreaker:
    """Implements Circuit Breaker to handle DB/Network faults resiliently."""
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 10):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
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
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        if self.state == "HALF_OPEN":
            return True
        return False

class NeuralBusPublisher:
    """ZMQ PUB socket for broadcasting microsecond-latency events."""
    
    def __init__(self, endpoint: str = "tcp://127.0.0.1:5555"):
        self.context = zmq.asyncio.Context.instance()
        self.socket = self.context.socket(zmq.PUB)
        # Security: ensure we drop messages immediately if no one is listening or buffers are full
        self.socket.setsockopt(zmq.SNDHWM, 1000)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.endpoint = endpoint
        self.socket.bind(endpoint)
        self.circuit_breaker = CircuitBreaker()
        logger.info(f"NeuralBus Publisher strictly bound to {endpoint}")
    
    async def publish(self, topic: str, payload: Dict[str, Any], trace_id: str):
        if not self.circuit_breaker.can_execute():
            logger.error(f"Cannot publish {topic}, Circuit Breaker is OPEN.")
            raise CircuitBreakerOpenException("Circuit breaker is open.")
            
        try:
            # Strict JSON validation to prevent malformed payload exploits
            payload_str = json.dumps(payload)
            message = {
                "trace_id": trace_id,
                "timestamp": time.time(),
                "payload": json.loads(payload_str) # ensure dictionary, catch serialization errors early
            }
            # Non-blocking send
            await self.socket.send_multipart([
                topic.encode('utf-8'),
                json.dumps(message).encode('utf-8')
            ], flags=zmq.NOBLOCK)
            self.circuit_breaker.record_success()
            logger.debug(f"Published to {topic} [Trace: {trace_id}]")
        except zmq.ZMQError as e:
            if e.errno == zmq.EAGAIN:
                logger.warning(f"ZMQ queue full for topic {topic}, message dropped to preserve non-blocking behavior.")
            else:
                self.circuit_breaker.record_failure()
                logger.error(f"NeuralBus Publish Error: {e}")
                raise
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(f"NeuralBus Publish Error: {e}")
            raise
    
    def close(self):
        self.socket.close()

class NeuralBusSubscriber:
    """ZMQ SUB socket for receiving microsecond-latency events."""
    
    def __init__(self, endpoint: str = "tcp://127.0.0.1:5555", topics: list = None):
        self.context = zmq.asyncio.Context.instance()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.setsockopt(zmq.RCVHWM, 1000)
        self.endpoint = endpoint
        self.socket.connect(endpoint)
        
        topics = topics or ["events"]
        for t in topics:
            self.socket.setsockopt_string(zmq.SUBSCRIBE, t)
            
        logger.info(f"NeuralBus Subscriber connected to {endpoint} listening to {topics}")
        self.is_running = False
        
    async def consume(self, callback: Callable):
        self.is_running = True
        while self.is_running:
            try:
                msg_parts = await self.socket.recv_multipart()
                if len(msg_parts) == 2:
                    topic = msg_parts[0].decode('utf-8')
                    try:
                        data = json.loads(msg_parts[1].decode('utf-8'))
                        await callback(topic, data)
                    except json.JSONDecodeError as e:
                        logger.error(f"Subscriber received malformed JSON on {topic}: {e}")
            except asyncio.CancelledError:
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"Subscriber error: {e}")
                
    def close(self):
        self.is_running = False
        self.socket.close()
