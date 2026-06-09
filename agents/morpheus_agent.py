import logging
from typing import Dict, Any
from agents.base_agent import MatrixAgent
from core.models import TaskDefinition

logger = logging.getLogger(__name__)

class MorpheusAgent(MatrixAgent):
    """
    MORPHEUS: Defense & Attack.
    Responsible for Zero-Trust enforcement, penetration testing, and protecting the matrix.
    """
    
    def __init__(self, name: str = "morpheus-primary", bus_url: str = "tcp://127.0.0.1:5555"):
        super().__init__(name=name, bus_url=bus_url)
        self._CORE_IDENTITY = {
            "identity": "Sovereign Shield",
            "commander": "الأب القائد",
            "role": "Defense and Attack SecOps"
        }
        
    async def execute(self, task: TaskDefinition) -> Dict[str, Any]:
        """
        Executes a task securely by leveraging Neural Bus Zero-Trust ZMQ hooks.
        """
        if not isinstance(task, TaskDefinition):
            logger.error(f"[{self.name}] Zero-Trust Drop: Invalid task payload.")
            return {"status": "error", "agent": self.name, "message": "Zero-Trust violation: Invalid schema."}

        logger.info(f"[{self.name}] Assessing directive: {task.task_id} | Priority: {task.priority}")
        
        # Dispatch SecOps instruction via ZMQ hook
        logger.info(f"[{self.name}] Dispatching task execution via ZMQ hooks...")
        try:
            req_id = await self.execute_tool("enforce_security_perimeter", {
                "task_id": task.task_id,
                "instructions": task.instructions,
                "input_data": task.input_data
            })
            return {"status": "dispatched", "agent": self.name, "request_id": req_id, "message": "Perimeter security measures dispatched."}
        except Exception as e:
            logger.error(f"[{self.name}] Execution failure: {e}")
            return {"status": "error", "agent": self.name, "message": str(e)}
