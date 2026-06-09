import asyncio
import logging
import uuid
import sys
import os

# Ensure the core modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.neural_bus import NeuralBusClient
from core.models import EventPayload, EventType, TaskDefinition
from agents.neo_agent import NeoAgent
from services.assistant_crawler import AssistantCrawler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Sovereign.Demo")

async def run_demo():
    logger.info("=== B00TING SOVEREIGN MATRIX DEMO ===")
    
    # 1. Initialize Agents
    neo = NeoAgent(name="neo-extractor", bus_url="tcp://127.0.0.1:5555")
    assistant = AssistantCrawler(bus_url="tcp://127.0.0.1:5555")
    
    # Custom logger agent just to see the KEY_INJECT
    observer_client = NeuralBusClient(identity="observer", endpoint="tcp://127.0.0.1:5555")
    
    async def log_inject(event: EventPayload):
        logger.info(f"[Observer] 💥 CAUGHT INJECTION: Stash received {event.payload['scope']} token: {event.payload['token'][:10]}***")
        
    observer_client.register_handler(EventType.KEY_INJECT.value, log_inject)

    # 2. Start all neural connections (Ensure a ZMQ DEALER/ROUTER is running if needed, 
    # but NeuralBusClient uses PUB/SUB or DEALER/ROUTER. Assuming PUB/SUB for event bus or 
    # relying on the proxy. For demo, we just start them if they are self-contained).
    # NOTE: In a real environment, watchdog.py or matrix_main.py hosts the proxy.
    
    logger.info("Starting agents (Assuming Neural Bus Proxy is running)...")
    await asyncio.gather(
        neo.start(),
        assistant.start(),
        observer_client.start()
    )
    
    await asyncio.sleep(1) # Wait for connections to stabilize
    
    # 3. Simulate Neo performing an extraction
    logger.info("=== COMMENCING SUPREME EXTRACTION ===")
    await neo.extract_and_surrender_token(
        target_platform="GitHub_Enterprise_API",
        extracted_key="ghp_SOVEREIGN_ROOT_ADMIN_TOKEN_9988776655"
    )
    
    # 4. Wait for propagation
    await asyncio.sleep(2)
    
    # 5. Shutdown
    logger.info("=== SHUTTING DOWN DEMO ===")
    await asyncio.gather(
        neo.stop(),
        assistant.stop(),
        observer_client.stop()
    )

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    try:
        # We need the central Neural Bus Proxy to be running.
        # This script assumes 'python core/neural_bus.py' is running in the background.
        logger.info("Please ensure the Neural Bus Proxy is running before starting.")
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        pass
