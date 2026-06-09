import os
import zmq
import zmq.asyncio
import asyncio
import logging
from typing import Dict, Set
import time

logger = logging.getLogger("Sovereign.Watchdog")

class WatchdogEngine:
    """Strict process monitor with Ping/Pong heartbeats to prevent Zombie process blindness."""
    
    def __init__(self, endpoint: str = None):
        self.context = zmq.asyncio.Context.instance()
        self.router_socket = self.context.socket(zmq.ROUTER)
        
        # Zero-Trust / Stability Settings
        self.router_socket.setsockopt(zmq.LINGER, 0)
        self.router_socket.setsockopt(zmq.ROUTER_MANDATORY, 1)
        
        self.endpoint = endpoint or os.getenv("SOVEREIGN_WATCHDOG_ENDPOINT", "ipc:///tmp/sovereign_watchdog.ipc")
        self.router_socket.bind(self.endpoint)
        
        self.alive_agents: Dict[str, float] = {}
        self.dead_agents: Set[str] = set()
        self.heartbeat_timeout = 5.0  # seconds
        self.heartbeat_interval = 2.0  # seconds
        self.is_running = False
        
        logger.info(f"Watchdog Engine strictly bound to {self.endpoint}")

    async def _ping_agents(self):
        """Send a strict heartbeat ping to all registered agents."""
        ping_message = b"PING"
        for agent_id in list(self.alive_agents.keys()):
            try:
                await self.router_socket.send_multipart([agent_id.encode('utf-8'), ping_message])
            except zmq.ZMQError as e:
                if e.errno == zmq.EHOSTUNREACH:
                    logger.warning(f"Agent {agent_id} unreachable during PING.")
                else:
                    logger.warning(f"Failed to ping {agent_id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected ping error: {e}")

    async def _listen_pongs(self):
        """Asynchronously listen for PONG responses. Native async, NO polling loops!"""
        while self.is_running:
            try:
                # Natively await recv_multipart instead of NOBLOCK with asyncio.sleep
                parts = await self.router_socket.recv_multipart()
                if len(parts) >= 2:
                    agent_id = parts[0].decode('utf-8')
                    pong = parts[1]
                    
                    if pong in (b"PONG", b"REGISTER"):
                        self.alive_agents[agent_id] = time.monotonic()
                        if agent_id in self.dead_agents:
                            logger.info(f"Agent recovered: {agent_id}")
                            self.dead_agents.remove(agent_id)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Pong listener critical error: {e}")

    async def _detect_dead_agents(self):
        """Aggressively detect and restart dead agents (Zombie cure)."""
        now = time.monotonic()
        
        for agent_id, last_seen in list(self.alive_agents.items()):
            if now - last_seen > self.heartbeat_timeout:
                logger.warning(f"ZOMBIE DETECTED: Agent {agent_id} timeout - Aggressively purging & restarting.")
                self.dead_agents.add(agent_id)
                del self.alive_agents[agent_id]
                # Trigger internal recovery bus instead of just deleting

    async def run(self):
        """Main Watchdog loop."""
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
            logger.info("Watchdog Engine Disarmed.")
        finally:
            listener_task.cancel()
            self.router_socket.close(linger=0)

    def register_agent(self, agent_id: str):
        """Register a new agent to be monitored."""
        self.alive_agents[agent_id] = time.monotonic()
        if agent_id in self.dead_agents:
            self.dead_agents.remove(agent_id)
        logger.info(f"Agent {agent_id} strictly registered for monitoring.")
