import sys
import os
import asyncio
sys.path.append(r"J:\THE_MATRIX")

import pytest
import zmq
import zmq.asyncio
from core.neural_bus import NeuralBusClient
from core.auth_vault import AuthVault
from services.librarian import SecureLibrarian

@pytest.mark.asyncio
async def test_librarian_jit_provisioning():
    # 1. Setup mock vault and ZMQ client
    vault = AuthVault()
    bus_client = NeuralBusClient(identity="Test_Librarian_Client", endpoint="tcp://127.0.0.1:5555")
    
    # 2. Instantiate Librarian on a separate test port (e.g. 5559) to prevent conflicts
    librarian = SecureLibrarian(bus=bus_client, vault=vault, port=5559)
    
    # Start Librarian task
    librarian_task = asyncio.create_task(librarian.run())
    await asyncio.sleep(0.5) # Wait for bind
    
    # 3. Create ZMQ Client (REQ)
    ctx = zmq.asyncio.Context.instance()
    client_socket = ctx.socket(zmq.REQ)
    client_socket.setsockopt(zmq.IDENTITY, b"Test_Agent_Identity")
    client_socket.setsockopt(zmq.LINGER, 0)
    client_socket.connect("tcp://127.0.0.1:5559")
    
    # 4. Request JIT Token
    print("Test agent requesting token...")
    payload = b"REQUEST_TOKEN:gemini"
    await client_socket.send_multipart([payload])
    
    parts = await client_socket.recv_multipart()
    assert len(parts) >= 1
    response = parts[0].decode('utf-8')
    print(f"Test agent received response: {response}")
    
    assert response.startswith("TOKEN_GRANTED:")
    token_id = response.split(":")[1]
    
    # 6. Verify token in Vault
    secret = vault.consume_token(token_id)
    assert secret == "EXTRACTED_SECRET_MOCK"
    
    # Clean up
    client_socket.close()
    librarian_task.cancel()
    try:
        await librarian_task
    except asyncio.CancelledError:
        pass
