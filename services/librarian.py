import asyncio
import time
from core.neural_bus import NeuralBusClient
from core.auth_vault import AuthVault

class SecureLibrarian:
    """
    Sovereign Librarian. No blind injection!
    Responds to explicit Token Requests via secure channels.
    """
    def __init__(self, bus: NeuralBusClient, vault: AuthVault):
        self.bus = bus
        self.vault = vault
        
        self.context = self.bus.context
        self.router_socket = self.context.socket(import_zmq().ROUTER)
        self.router_socket.bind("tcp://127.0.0.1:5557")

    async def handle_token_requests(self):
        """Secure JIT token provisioning using strict REQ/REP over ZMQ."""
        import zmq
        while True:
            parts = await self.router_socket.recv_multipart()
            if len(parts) >= 3:
                identity = parts[0]
                command = parts[2].decode("utf-8")
                
                if command.startswith("REQUEST_TOKEN"):
                    _, scope = command.split(":")
                    # Generate an ephemeral securely encrypted token inside the vault
                    # Return the token ID to the agent
                    token_id = self.vault.issue_token(scope=scope, secret_data="EXTRACTED_SECRET_MOCK")
                    await self.router_socket.send_multipart([
                        identity,
                        b"",
                        f"TOKEN_GRANTED:{token_id}".encode("utf-8")
                    ])
                    print(f"[Librarian] JIT Token securely provisioned for {identity.decode()} (Scope: {scope})")

    async def run(self):
        print("[Librarian] Started. Listening for secure JIT token requests. Blind injection DESTROYED.")
        await self.handle_token_requests()

def import_zmq():
    import zmq
    return zmq

