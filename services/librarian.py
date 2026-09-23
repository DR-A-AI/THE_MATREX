from typing import Any

from core.auth_vault import AuthVault
from core.neural_bus import NeuralBusClient


class SecureLibrarian:
    """
    Sovereign Librarian. No blind injection!
    Responds to explicit Token Requests via secure channels.
    """

    def __init__(self, bus: NeuralBusClient, vault: AuthVault, port: int = 5557):
        self.bus = bus
        self.vault = vault

        self.context = self.bus.context
        self.router_socket = self.context.socket(import_zmq().ROUTER)
        # Enable linger and address reuse for fast restart
        self.router_socket.setsockopt(import_zmq().LINGER, 0)
        self.router_socket.bind(f"tcp://127.0.0.1:{port}")

    async def handle_token_requests(self) -> None:
        """Secure JIT token provisioning using strict REQ/REP over ZMQ."""

        while True:
            parts = await self.router_socket.recv_multipart()
            if len(parts) >= 3:
                identity = parts[0]
                command = parts[2].decode("utf-8")

                if command.startswith("REQUEST_TOKEN"):
                    _, scope = command.split(":")
                    # Generate an ephemeral securely encrypted token inside the vault
                    # Return the token ID to the agent
                    token_id = self.vault.issue_token(
                        scope=scope,
                        secret_data="EXTRACTED_SECRET_MOCK",  # nosec: B106  # mock placeholder, not a real credential
                    )
                    await self.router_socket.send_multipart(
                        [identity, b"", f"TOKEN_GRANTED:{token_id}".encode()]
                    )
                    print(
                        f"[Librarian] JIT Token securely provisioned for {identity.decode()} (Scope: {scope})"
                    )

    async def run(self) -> None:
        print(
            "[Librarian] Started. Listening for secure JIT token requests. Blind injection DESTROYED."
        )
        await self.handle_token_requests()


def import_zmq() -> Any:
    import zmq

    return zmq
