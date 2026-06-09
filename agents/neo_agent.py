import logging
from typing import Dict, Any
from agents.base_agent import MatrixAgent
from core.models import TaskDefinition

logger = logging.getLogger(__name__)

class NeoAgent(MatrixAgent):
    """
    NEO: Personal Assistant & Orchestrator.
    Manages the ecosystem, coordinates other agents, and handles primary user directives.
    """
    
    def __init__(self, name: str = "neo-primary", bus_url: str = "tcp://127.0.0.1:5555"):
        super().__init__(name=name, bus_url=bus_url)
        self._CORE_IDENTITY = {
            "identity": "Sovereign Orchestrator",
            "commander": "الأب القائد",
            "role": "Personal Assistant and Ecosystem Manager"
        }
        
    async def execute(self, task: TaskDefinition) -> Dict[str, Any]:
        """
        Executes a task securely by leveraging Neural Bus Zero-Trust ZMQ hooks.
        """
        if not isinstance(task, TaskDefinition):
            logger.error(f"[{self.name}] Zero-Trust Drop: Invalid task payload.")
            return {"status": "error", "agent": self.name, "message": "Zero-Trust violation: Invalid schema."}

        logger.info(f"[{self.name}] Assessing directive: {task.task_id} | Priority: {task.priority}")
        
        # Dispatch orchestration instruction via ZMQ hook
        logger.info(f"[{self.name}] Dispatching task execution via ZMQ hooks...")
        try:
            req_id = await self.execute_tool("orchestrate_ecosystem", {
                "task_id": task.task_id,
                "instructions": task.instructions,
                "input_data": task.input_data
            })
            return {"status": "dispatched", "agent": self.name, "request_id": req_id, "message": "Ecosystem synchronization requested."}
        except Exception as e:
            logger.error(f"[{self.name}] Execution failure: {e}")
            return {"status": "error", "agent": self.name, "message": str(e)}
