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
from services.memory_crawler import MemoryCrawler
from services.assistant_crawler import AssistantCrawler
from services.librarian_crawler import run_crawler_periodically

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s")
logger = logging.getLogger("Matrix.Boot")

async def boot_matrix():
    logger.info("=======================================")
    logger.info("BOOTING THE SOVEREIGN MATRIX ENGINE")
    logger.info("=======================================")
    import os
    os.environ.pop("GOOGLE_API_KEY", None)
    os.environ.pop("GEMINI_API_KEY", None)
    
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

    # 4. Start the Memory Crawler
    memory_crawler = MemoryCrawler(bus_url="tcp://127.0.0.1:5555")
    memory_crawler_task = asyncio.create_task(memory_crawler.start())
    
    # 4b. Start the Assistant Crawler
    assistant_crawler = AssistantCrawler(bus_url="tcp://127.0.0.1:5555")
    assistant_crawler_task = asyncio.create_task(assistant_crawler.start())
    
    # 4c. Start the Librarian Crawler (Skills)
    skills_crawler_task = asyncio.create_task(run_crawler_periodically())
    
    # 5. Start the Agents
    from agents.neo_agent import NeoAgent
    from agents.trinity_agent import TrinityAgent
    from agents.morpheus_agent import MorpheusAgent
    from agents.smith_agent import SmithAgent
    from agents.oracle_agent import OracleAgent
    from agents.base_agent import MatrixAgent
    
    neo = NeoAgent(name="neo", bus_url="tcp://127.0.0.1:5555")
    trinity = TrinityAgent(name="trinity", bus_url="tcp://127.0.0.1:5555")
    morpheus = MorpheusAgent(name="morpheus", bus_url="tcp://127.0.0.1:5555")
    smith = SmithAgent(name="smith", bus_url="tcp://127.0.0.1:5555")
    oracle = OracleAgent(name="oracle", bus_url="tcp://127.0.0.1:5555")
    base_agent = MatrixAgent(name="base", bus_url="tcp://127.0.0.1:5555")
    
    neo_task = asyncio.create_task(neo.start())
    trinity_task = asyncio.create_task(trinity.start())
    morpheus_task = asyncio.create_task(morpheus.start())
    smith_task = asyncio.create_task(smith.start())
    oracle_task = asyncio.create_task(oracle.start())
    base_task = asyncio.create_task(base_agent.start())
    
    # 6. Engine FSM Setup
    engine = SovereignEngineFSM()
    
    logger.info("ALL CORE SYSTEMS ONLINE. AWAITING COMMANDER.")
    
    # Keep the main loop alive
    await asyncio.gather(
        router_task,
        librarian_task,
        memory_crawler_task,
        assistant_crawler_task,
        skills_crawler_task,
        neo_task,
        trinity_task,
        morpheus_task,
        smith_task,
        oracle_task,
        base_task
    )

if __name__ == "__main__":
    if sys.platform == 'win32':
        # Fix: ZMQ requires SelectorEventLoop on Windows, NOT Proactor!
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(boot_matrix())
    except KeyboardInterrupt:
        logger.info("Matrix Engine Terminated by Commander.")
