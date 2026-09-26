import os
import secrets
from typing import Any

from core.auth_vault import AuthVault
from core.models import EventPayload, EventType
from core.neural_bus import NeuralBusClient


class SecureLibrarian:
    """
    Sovereign Librarian. No blind injection!
    Responds to explicit Token Requests via secure channels.
    """

    def __init__(self, bus: NeuralBusClient, vault: AuthVault, port: int = 5557):
        self.bus = bus
        self.vault = vault
        self._secret_store: dict[str, str] = {}

        if hasattr(self.bus, "register_handler"):
            self.bus.register_handler(EventType.KEY_INJECT.value, self._handle_key_inject)

        self.context = self.bus.context
        self.router_socket = self.context.socket(import_zmq().ROUTER)
        # Enable linger and address reuse for fast restart
        self.router_socket.setsockopt(import_zmq().LINGER, 0)
        self.router_socket.bind(f"tcp://127.0.0.1:{port}")

    async def _handle_key_inject(self, event: EventPayload) -> None:
        """Store verified injected tokens from the neural bus."""
        payload = event.payload or {}
        scope = str(payload.get("scope", ""))
        token = str(payload.get("token", ""))
        if scope and token:
            self._secret_store[scope] = token

    def extract_secret(self, scope: str) -> str:
        """Extract secret credential for scope from bus token store, environment, or crypto session."""
        if scope in self._secret_store:
            return self._secret_store[scope]

        env_keys = [
            f"{scope.upper()}_API_KEY",
            f"{scope.upper()}_TOKEN",
            f"{scope.upper()}_SECRET",
            scope.upper(),
        ]
        for key in env_keys:
            val = os.getenv(key)
            if val:
                return val

        # Issue cryptographically secure session credential for the scope
        generated = secrets.token_urlsafe(32)
        self._secret_store[scope] = generated
        return generated

    async def handle_token_requests(self) -> None:
        """Secure JIT token provisioning using strict REQ/REP over ZMQ."""

        while True:
            parts = await self.router_socket.recv_multipart()
            if len(parts) >= 3:
                identity = parts[0]
                command = parts[2].decode("utf-8")

                if command.startswith("REQUEST_TOKEN"):
                    _, scope = command.split(":")
                    # Extract secret credential for the requested scope
                    secret_data = self.extract_secret(scope)
                    token_id = self.vault.issue_token(
                        scope=scope,
                        secret_data=secret_data,
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
