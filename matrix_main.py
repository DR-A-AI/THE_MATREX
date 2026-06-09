import asyncio
import logging
import sys
import warnings

# Suppress Python 3.16 DeprecationWarning for WindowsSelectorEventLoopPolicy
warnings.filterwarnings("ignore", category=DeprecationWarning)

from core.neural_bus import NeuralBusRouter, NeuralBusClient
from core.auth_vault import AuthVault
from core.failsafe import FailsafeMonitor
from services.librarian import SecureLibrarian
from core.engine import SovereignEngineFSM

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s")
logger = logging.getLogger("Matrix.Boot")

async def boot_matrix():
    logger.info("=======================================")
    logger.info("BOOTING THE SOVEREIGN MATRIX ENGINE")
    logger.info("=======================================")
    
    # 1. Start the Neural Bus Router
    router = NeuralBusRouter(endpoint="tcp://127.0.0.1:5555")
    router_task = asyncio.create_task(router.start())
    
    # 2. Start the Failsafe Monitor
    failsafe_client = NeuralBusClient(identity="Failsafe_Client")
    await failsafe_client.start()
    failsafe = FailsafeMonitor(matrix_root=r"J:\THE_MATRIX")
    await failsafe.attach_to_bus(failsafe_client)
    
    # 3. Start the Librarian (Secure)
    bus_client = NeuralBusClient(identity="Librarian_Client")
    await bus_client.start()
    vault = AuthVault()
    librarian = SecureLibrarian(bus=bus_client, vault=vault)
    librarian_task = asyncio.create_task(librarian.run())
    
    # 4. Engine FSM Setup
    engine = SovereignEngineFSM()
    
    logger.info("ALL CORE SYSTEMS ONLINE. AWAITING COMMANDER.")
    
    # Keep the main loop alive
    await asyncio.gather(
        router_task,
        librarian_task
    )

if __name__ == "__main__":
    if sys.platform == 'win32':
        # Fix: ZMQ requires SelectorEventLoop on Windows, NOT Proactor!
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(boot_matrix())
    except KeyboardInterrupt:
        logger.info("Matrix Engine Terminated by Commander.")
