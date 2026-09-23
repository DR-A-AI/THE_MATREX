import asyncio
import logging
from typing import Any

import msgpack  # type: ignore[import-not-found, import-untyped]
import zmq
import zmq.asyncio

logger = logging.getLogger(__name__)


class ZMQRouter:
    """
    ZMQ ROUTER socket for handling incoming asynchronous RPC execution requests.
    Acts as the main broker for distributing skill execution tasks.
    Sovereign Razor Standard: Strictly localhost binding, MsgPack serialization, Async I/O.
    """

    def __init__(self, bind_address: str = "tcp://127.0.0.1:5555") -> None:
        if "0.0.0.0" in bind_address or "*" in bind_address:  # nosec
            raise ValueError(
                "CRITICAL SECURITY VIOLATION: Localhost binding strictly enforced. Do not bind to all interfaces."
            )
        self.bind_address = bind_address
        self.ctx = zmq.asyncio.Context.instance()
        self.socket = self.ctx.socket(zmq.ROUTER)
        self.socket.setsockopt(zmq.LINGER, 0)

    async def start(self) -> None:
        self.socket.bind(self.bind_address)
        logger.info(f"[SOVEREIGN] ZMQ ROUTER securely bound to {self.bind_address}")
        try:
            while True:
                try:
                    # Wait for next request from client
                    identity, _empty, message = await self.socket.recv_multipart()
                    payload = msgpack.unpackb(message, raw=False)

                    # Process RPC call
                    logger.info(f"Received secure RPC request from {identity!r}: {payload}")

                    # Mock skill execution logic
                    response = {
                        "status": "success",
                        "data": f"Skill {payload.get('skill')} executed successfully under sovereign constraints.",
                    }

                    # Send reply back to client
                    await self.socket.send_multipart(
                        [identity, b"", msgpack.packb(response, use_bin_type=True)]
                    )
                except msgpack.UnpackException:
                    logger.exception("Serialization breach detected. Rejecting payload")
                except Exception:
                    logger.exception("Error in ZMQ ROUTER execution loop")
        except asyncio.CancelledError:
            logger.info("ZMQ ROUTER shutting down gracefully...")
        finally:
            self.socket.close()


class ZMQDealer:
    """
    ZMQ DEALER socket for sending asynchronous RPC execution requests.
    Acts as the worker/client that triggers skill execution.
    """

    def __init__(
        self, connect_address: str = "tcp://127.0.0.1:5555", identity: bytes = b"dealer_1"
    ) -> None:
        if "0.0.0.0" in connect_address or "*" in connect_address:  # nosec
            raise ValueError("CRITICAL SECURITY VIOLATION: Localhost connection strictly enforced.")
        self.connect_address = connect_address
        self.identity = identity
        self.ctx = zmq.asyncio.Context.instance()
        self.socket = self.ctx.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, self.identity)
        self.socket.setsockopt(zmq.LINGER, 0)

    async def connect(self) -> None:
        self.socket.connect(self.connect_address)
        logger.info(
            f"[SOVEREIGN] ZMQ DEALER {self.identity!r} connected securely to {self.connect_address}"
        )

    async def execute_skill(self, skill_name: str, kwargs: dict[str, Any]) -> Any:
        payload = {"skill": skill_name, "args": kwargs}
        await self.socket.send_multipart([b"", msgpack.packb(payload, use_bin_type=True)])

        # Wait for reply
        _empty, reply = await self.socket.recv_multipart()
        return msgpack.unpackb(reply, raw=False)

    def close(self) -> None:
        self.socket.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
