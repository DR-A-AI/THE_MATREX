import asyncio
import websockets
import json
import sys

# Fix encoding error for printing Arabic text in Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

async def test_frontend_backend_connection():
    uri = "ws://127.0.0.1:8000/ws"
    print(f"Connecting to UI Bridge at {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected successfully. Simulating human user typing...")
            
            # Send a message to Neo asking to list directory
            payload = {
                "agent": "neo",
                "text": "ما الساعه الان وتاريخ اليوم؟ وهل تستطيع استخدام المتصفح؟"
            }
            await websocket.send(json.dumps(payload))
            print(f"> Sent: {payload['text']}")
            
            print("\nWaiting for real-time responses (Status pulses and Chat answers)...\n")
            
            # Listen for 20 seconds
            for _ in range(15):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(response)
                    
                    if data.get("type") == "status":
                        print(f"[STATUS PULSE from {data['sender']}]: {data['text']}")
                    else:
                        print(f"\n[FINAL CHAT from {data['sender']}]: {data['text']}\n")
                        break
                        
                except asyncio.TimeoutError:
                    continue
                    
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_frontend_backend_connection())
