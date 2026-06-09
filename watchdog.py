import zmq
import zmq.asyncio
import asyncio
import logging
from typing import Dict, Set
from datetime import datetime, timedelta

logger = logging.getLogger("Sovereign.Watchdog")

class WatchdogEngine:
    """Sovereign Process Monitor with Zero CPU-Spinning and Async-Native ZMQ."""
    
    def __init__(self, endpoint: str = "tcp://127.0.0.1:5556"):
        self.context = zmq.asyncio.Context.instance()
        self.router_socket = self.context.socket(zmq.ROUTER)
        self.router_socket.setsockopt(zmq.ROUTER_MANDATORY, 1) # Error if identity unknown
        self.router_socket.bind(endpoint)
        self.endpoint = endpoint
        
        self.alive_agents: Dict[str, datetime] = {}
        self.dead_agents: Set[str] = set()
        self.heartbeat_timeout = 5  # seconds
        self.heartbeat_interval = 2  # seconds
        self.is_running = False
        
        logger.info(f"Sovereign Watchdog strictly bound to {endpoint}")

    async def _ping_agents(self):
        """Send a strict heartbeat ping to all registered agents asynchronously."""
        ping_message = b"PING"
        for agent_id in list(self.alive_agents.keys()):
            try:
                await self.router_socket.send_multipart([agent_id.encode('utf-8'), ping_message])
            except zmq.ZMQError as e:
                # ROUTER_MANDATORY will raise EHOSTUNREACH if peer is gone
                logger.warning(f"ZMQ Error: Cannot reach {agent_id} - {e}")
            except Exception as e:
                logger.warning(f"Failed to ping {agent_id}: {e}")

    async def _listen_pongs(self):
        """True async listener for PONG responses without CPU spin loops."""
        while self.is_running:
            try:
                # Use native async await to prevent CPU spinning, no sleep loops needed
                parts = await self.router_socket.recv_multipart()
                if len(parts) >= 2:
                    agent_id = parts[0].decode('utf-8')
                    pong = parts[1]
                    
                    if pong in (b"PONG", b"REGISTER"):
                        self.alive_agents[agent_id] = datetime.utcnow()
                        if agent_id in self.dead_agents:
                            logger.info(f"Agent recovered: {agent_id}")
                            self.dead_agents.remove(agent_id)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Pong listener error: {e}")

    async def _detect_dead_agents(self):
        """Aggressively detect and restart dead agents (Zombie cure)."""
        now = datetime.utcnow()
        timeout = timedelta(seconds=self.heartbeat_timeout)
        
        for agent_id, last_seen in list(self.alive_agents.items()):
            if now - last_seen > timeout:
                logger.critical(f"ZOMBIE DETECTED: Agent {agent_id} timeout - PURGING.")
                self.dead_agents.add(agent_id)
                # Ensure it's removed so we don't keep pinging it
                del self.alive_agents[agent_id]

    async def run(self):
        """Main Sovereign Watchdog loop."""
        logger.info("Watchdog Engine Armed.")
        self.is_running = True
        
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
            self.router_socket.close(linger=0)

    def register_agent(self, agent_id: str):
        self.alive_agents[agent_id] = datetime.utcnow()
        if agent_id in self.dead_agents:
            self.dead_agents.remove(agent_id)
        logger.info(f"Agent {agent_id} registered into the Sovereign Watchdog matrix.")
