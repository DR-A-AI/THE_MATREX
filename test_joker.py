import asyncio
import logging
import sys

# Ensure logs show up in the terminal
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")

# Import the Neo Agent
from agents.neo_agent import NeoAgent

async def run_joker_test():
    print("==================================================")
    print("🛡️ INITIATING NEO JOKER PROTOCOL (INTERACTIVE MODE) 🛡️")
    print("==================================================")
    
    # Initialize Neo
    neo = NeoAgent(bus_client=None)
    
    # Target URL (The Dashboard)
    target_url = "http://localhost:5173"
    
    print(f"\n[COMMAND] Ordering Neo to open {target_url} in the LIGHT...\n")
    
    # Execute the light protocol
    await neo.operate_browser(target_url, show_ui=True)
    
    print("\n[SUCCESS] If Neo's code is correct, the browser should have popped up instantly on your screen.")
    print("==================================================")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run_joker_test())
