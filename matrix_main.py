import os

from dotenv import load_dotenv

load_dotenv()
import asyncio
import logging
import sys
import warnings

# Suppress Python 3.16 DeprecationWarning for WindowsSelectorEventLoopPolicy
warnings.filterwarnings("ignore", category=DeprecationWarning)

from core.auth_vault import AuthVault
from core.engine import SovereignEngineFSM
from core.failsafe import FailsafeMonitor
from core.neural_bus import NeuralBusClient, NeuralBusRouter
from services.assistant_crawler import AssistantCrawler
from services.librarian import SecureLibrarian
from services.librarian_crawler import run_crawler_periodically
from services.memory_crawler import MemoryCrawler

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s"
)
logger = logging.getLogger("Matrix.Boot")


async def boot_matrix() -> None:
    logger.info("=======================================")
    logger.info("BOOTING THE SOVEREIGN MATRIX ENGINE")
    logger.info("=======================================")

    os.environ.pop("GOOGLE_API_KEY", None)
    os.environ.pop("GEMINI_API_KEY", None)

    # 1. Start the Neural Bus Router
    router = NeuralBusRouter(endpoint=os.getenv("ZMQ_ROUTER_URL", "tcp://0.0.0.0:5555"))
    router_task = asyncio.create_task(router.start())

    # 2. Start the Failsafe Monitor
    failsafe_client = NeuralBusClient(identity="Failsafe_Client")
    await failsafe_client.start()
    failsafe = FailsafeMonitor(
        matrix_root=os.getenv("MATRIX_ROOT", "/mnt/e/matrex-dev")
    )
    await failsafe.attach_to_bus(failsafe_client)

    # 3. Start the Librarian (Secure)
    bus_client = NeuralBusClient(identity="Librarian_Client")
    await bus_client.start()
    vault = AuthVault()
    librarian = SecureLibrarian(bus=bus_client, vault=vault)
    librarian_task = asyncio.create_task(librarian.run())

    # 4. Start the Memory Crawler
    bus_url = os.getenv("ZMQ_BUS_URL", "tcp://127.0.0.1:5555")
    memory_crawler = MemoryCrawler(bus_url=bus_url)
    memory_crawler_task = asyncio.create_task(memory_crawler.start())

    # 4b. Start the Assistant Crawler
    assistant_crawler = AssistantCrawler(bus_url=bus_url)
    assistant_crawler_task = asyncio.create_task(assistant_crawler.start())

    # 4c. Start the Librarian Crawler (Skills)
    skills_crawler_task = asyncio.create_task(run_crawler_periodically())

    # M2: Pre-warm Ollama model to eliminate cold start (~30s) delay
    # Sends a 1-token prompt before any agent is ready so the model is loaded
    try:
        from services.ollama_client import OllamaClient
        _ollama = OllamaClient()

        async def _prewarm() -> None:
            try:
                logger.info("🔥 [PreWarm] Sending Ollama pre-warm pulse...")
                await asyncio.to_thread(
                    _ollama.chat,
                    "llama3.2",
                    [{"role": "user", "content": "hi"}],
                )
                logger.info("✅ [PreWarm] Ollama model warm — first inference will be fast.")
            except Exception as _e:  # noqa: BLE001
                logger.warning(f"[PreWarm] Ollama pre-warm failed (non-fatal): {_e}")

        asyncio.create_task(_prewarm())
    except Exception as _prewarm_err:  # noqa: BLE001
        logger.warning(f"[PreWarm] Could not start pre-warm task: {_prewarm_err}")

    # 5. Start the Agents
    from agents.base_agent import MatrixAgent
    from agents.morpheus_agent import MorpheusAgent
    from agents.neo_agent import NeoAgent
    from agents.oracle_agent import OracleAgent
    from agents.smith_agent import SmithAgent
    from agents.trinity_agent import TrinityAgent

    neo = NeoAgent(name="neo", bus_url=bus_url)
    trinity = TrinityAgent(name="trinity", bus_url=bus_url)
    morpheus = MorpheusAgent(name="morpheus", bus_url=bus_url)
    smith = SmithAgent(name="smith", bus_url=bus_url)
    oracle = OracleAgent(name="oracle", bus_url=bus_url)
    base_agent = MatrixAgent(name="base", bus_url=bus_url)

    neo_task = asyncio.create_task(neo.start())
    trinity_task = asyncio.create_task(trinity.start())
    morpheus_task = asyncio.create_task(morpheus.start())
    smith_task = asyncio.create_task(smith.start())
    oracle_task = asyncio.create_task(oracle.start())
    base_task = asyncio.create_task(base_agent.start())

    # 6. Engine FSM Setup
    _engine = SovereignEngineFSM()

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
        base_task,
    )


if __name__ == "__main__":
    if sys.platform == "win32":
        # Fix: ZMQ requires SelectorEventLoop on Windows, NOT Proactor!
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(boot_matrix())
    except KeyboardInterrupt:
        logger.info("Matrix Engine Terminated by Commander.")
