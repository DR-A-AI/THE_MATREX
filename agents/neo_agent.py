import logging
from typing import Dict, Any
import uuid
from agents.base_agent import MatrixAgent
from core.models import TaskDefinition, EventPayload, EventType

logger = logging.getLogger(__name__)

class NeoAgent(MatrixAgent):
    """
    NEO: Supreme Extractor & Orchestrator.
    Capable of interfacing with any external server (Azure, GCP, GitHub, Gemini API).
    Extracts secrets and hands them blindly to the Assistant Crawler.
    """
    
    def __init__(self, name: str = "neo-primary", bus_url: str = "tcp://127.0.0.1:5555"):
        super().__init__(name=name, bus_url=bus_url)
        self._CORE_IDENTITY = {
            "identity": "Sovereign Supreme Extractor",
            "commander": "الأب القائد",
            "role": "Universal Web/API Interface and Blind Extraction"
        }
        
    async def extract_and_surrender_token(self, target_platform: str, extracted_key: str):
        """
        Simulates extracting a key from the outside world (e.g. Azure, Google).
        IMMEDIATELY sends it blindly onto the Neural Bus for the Assistant Crawler.
        Neo does NOT keep the key.
        """
        logger.info(f"[{self.name}] Succeeded in extracting token from {target_platform}. Surrendering to Assistant Crawler blindly.")
        
        event = EventPayload(
            event_type=EventType.TOKEN_EXTRACTED,
            source_agent_id=self.agent_id,
            correlation_id=str(uuid.uuid4()),
            payload={
                "platform": target_platform,
                "extracted_token": extracted_key
            }
        )
        await self.client.send(event)
        logger.info(f"[{self.name}] Token surrendered successfully. Hands are clean.")

    async def execute(self, task: TaskDefinition) -> Dict[str, Any]:
        """
        Executes a task securely by leveraging Neural Bus Zero-Trust ZMQ hooks.
        """
        if not isinstance(task, TaskDefinition):
            logger.error(f"[{self.name}] Zero-Trust Drop: Invalid task payload.")
            return {"status": "error", "agent": self.name, "message": "Zero-Trust violation: Invalid schema."}

        logger.info(f"[{self.name}] Assessing extraction directive: {task.task_id} | Priority: {task.priority}")
        
        # Dispatch orchestration instruction via ZMQ hook
        logger.info(f"[{self.name}] Dispatching task execution via ZMQ hooks...")
        try:
            req_id = await self.execute_tool("orchestrate_ecosystem", {
                "task_id": task.task_id,
                "instructions": task.instructions,
                "input_data": task.input_data
            })
            return {"status": "dispatched", "agent": self.name, "request_id": req_id, "message": "Extraction task requested."}
        except Exception as e:
            logger.error(f"[{self.name}] Execution failure: {e}")
            return {"status": "error", "agent": self.name, "message": str(e)}
