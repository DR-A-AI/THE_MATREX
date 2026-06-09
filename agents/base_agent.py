import asyncio
import os
from core.neural_bus import SovereignNeuralBus

class SecureMatrixAgent:
    """
    Sovereign Node. Zero-Trust compliant.
    Requests tokens via direct REQ socket, NEVER accepts blind injections.
    """
    def __init__(self, agent_id: str, bus: SovereignNeuralBus):
        self.agent_id = agent_id
        self.bus = bus
        
        self.context = self.bus.context
        self.req_socket = self.context.socket(import_zmq().REQ)
        self.req_socket.setsockopt_string(import_zmq().IDENTITY, self.agent_id)
        self.req_socket.connect("tcp://127.0.0.1:5556")
        
        # We DO NOT HAVE an `emergency_token_stash`. State is fetched JIT.
        self.active_token_id = None

    async def secure_task_execution(self, scope: str):
        """Perform a task that requires a secure token using JIT provisioning."""
        print(f"[{self.agent_id}] Need token for {scope}. Requesting securely via REQ/REP...")
        
        # 1. Request token JIT
        await self.req_socket.send_string(f"REQUEST_TOKEN:{scope}")
        response = await self.req_socket.recv_string()
        
        if response.startswith("TOKEN_GRANTED"):
            _, token_id = response.split(":")
            self.active_token_id = token_id
            print(f"[{self.agent_id}] JIT Token ID received: {token_id[:8]}...")
            
            # 2. Use token immediately and discard
            # In a real scenario, it sends the token_id to the service.
            self.active_token_id = None
            print(f"[{self.agent_id}] Token consumed and memory wiped.")
        else:
            print(f"[{self.agent_id}] Token request denied: {response}")

    async def run(self):
        print(f"[{self.agent_id}] Online. Compliant with Sovereign Razor Zero-Trust.")
        await asyncio.sleep(2)
        await self.secure_task_execution("core_access")
        
def import_zmq():
    import zmq
    return zmq

