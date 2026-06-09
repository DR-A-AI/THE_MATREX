import zmq
import zmq.asyncio
import asyncio
import logging
from typing import Dict, Set
from datetime import datetime, timedelta

logger = logging.getLogger("Sovereign.Watchdog")

class WatchdogEngine:
    """Strict process monitor with Ping/Pong heartbeats to prevent Zombie process blindness."""
    
    def __init__(self, endpoint: str = "tcp://127.0.0.1:5556"):
        self.context = zmq.asyncio.Context.instance()
        self.router_socket = self.context.socket(zmq.ROUTER)
        self.router_socket.setsockopt(zmq.SNDHWM, 1000)
        self.router_socket.setsockopt(zmq.RCVHWM, 1000)
        self.router_socket.setsockopt(zmq.LINGER, 0)
        self.router_socket.bind(endpoint)
        self.endpoint = endpoint
        
        self.alive_agents: Dict[str, datetime] = {}
        self.dead_agents: Set[str] = set()
        self.heartbeat_timeout = 5  # seconds
        self.heartbeat_interval = 2  # seconds
        self.is_running = False
        
        logger.info(f"Watchdog Engine strictly bound to {endpoint}")

    async def _ping_agents(self):
        """Send a strict heartbeat ping to all registered agents."""
        ping_message = b"PING"
        for agent_id in list(self.alive_agents.keys()):
            try:
                await self.router_socket.send_multipart([agent_id.encode('utf-8'), ping_message], flags=zmq.NOBLOCK)
            except zmq.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                     logger.warning(f"Failed to ping {agent_id}: ZMQ queue full (EAGAIN)")
                else:
                     logger.warning(f"Failed to ping {agent_id}: {e}")
            except Exception as e:
                logger.warning(f"Failed to ping {agent_id}: {e}")

    async def _listen_pongs(self):
        """Asynchronously listen for PONG responses from agents."""
        while self.is_running:
            try:
                parts = await self.router_socket.recv_multipart(flags=zmq.NOBLOCK)
                if len(parts) >= 2:
                    agent_id = parts[0].decode('utf-8')
                    pong = parts[1]
                    
                    if pong == b"PONG" or pong == b"REGISTER":
                        self.alive_agents[agent_id] = datetime.utcnow()
                        if agent_id in self.dead_agents:
                            logger.info(f"Agent recovered: {agent_id}")
                            self.dead_agents.remove(agent_id)
            except zmq.ZMQError as e:
                if e.errno == zmq.EAGAIN:
                    await asyncio.sleep(0.01)
                else:
                    logger.error(f"ZMQ Error in pong listener: {e}")
            except Exception as e:
                logger.error(f"Pong listener error: {e}")
                await asyncio.sleep(0.1)

    async def _detect_dead_agents(self):
        """Aggressively detect and restart dead agents (Zombie cure)."""
        now = datetime.utcnow()
        timeout = timedelta(seconds=self.heartbeat_timeout)
        
        for agent_id, last_seen in list(self.alive_agents.items()):
            if now - last_seen > timeout:
                logger.warning(f"ZOMBIE DETECTED: Agent {agent_id} timeout - Aggressively purging & restarting.")
                self.dead_agents.add(agent_id)
                # Future implementation: Trigger OS-level hard kill and container/agent restart via System API
                del self.alive_agents[agent_id]

    async def run(self):
        """Main Watchdog loop."""
        logger.info("Watchdog Engine Armed.")
        self.is_running = True
        
        # Start the listener in the background
        listener_task = asyncio.create_task(self._listen_pongs())
        
        try:
            while self.is_running:
                await self._ping_agents()
                await asyncio.sleep(self.heartbeat_interval)
                await self._detect_dead_agents()
        except asyncio.CancelledError:
            self.is_running = False
        finally:
            listener_task.cancel()
            self.router_socket.close()

    def register_agent(self, agent_id: str):
        """Register a new agent to be monitored."""
        self.alive_agents[agent_id] = datetime.utcnow()
        if agent_id in self.dead_agents:
            self.dead_agents.remove(agent_id)
        logger.info(f"Agent {agent_id} strictly registered for monitoring.")
