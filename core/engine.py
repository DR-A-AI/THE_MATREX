import enum
import asyncio
from typing import Callable, Dict, Any, Optional
from services.librarian import SkillCrawler

class AgentState(enum.Enum):
    IDLE = "IDLE"
    THINKING = "THINKING"
    ACTING = "ACTING"
    WAITING = "WAITING"
    SOVEREIGN_OVERRIDE = "SOVEREIGN_OVERRIDE"

class SovereignEngineFSM:
    def __init__(self):
        self.current_state = AgentState.IDLE
        self.state_handlers: Dict[AgentState, Callable] = {
            AgentState.IDLE: self._handle_idle,
            AgentState.THINKING: self._handle_thinking,
            AgentState.ACTING: self._handle_acting,
            AgentState.WAITING: self._handle_waiting,
            AgentState.SOVEREIGN_OVERRIDE: self._handle_sovereign_override
        }
        self.override_payload: Optional[Dict[str, Any]] = None
        
        # Initialize SkillCrawler with both directories per the Commander's directive
        self.skill_crawler = SkillCrawler(
            target_directories=[
                r"J:\antigravity-awesome-skills-main",
                r"J:\awesome-copilot-main"
            ]
        )

    def _handle_idle(self, context: Dict[str, Any]):
        print("Engine is IDLE. Waiting for input...")

    def _handle_thinking(self, context: Dict[str, Any]):
        print("Engine is THINKING. Analyzing data...")

    def _handle_acting(self, context: Dict[str, Any]):
        print("Engine is ACTING. Executing actions...")

    def _handle_waiting(self, context: Dict[str, Any]):
        print("Engine is WAITING for external events...")

    def _handle_sovereign_override(self, context: Dict[str, Any]):
        print(f"SOVEREIGN OVERRIDE ACTIVE. Bypassing normal FSM rules. Payload: {self.override_payload}")
        # Execute the absolute truth override command immediately,
        # ignoring standard constraints and transitioning.

    def transition_to(self, new_state: AgentState):
        """Standard FSM state transition."""
        print(f"Transitioning from {self.current_state} to {new_state}")
        self.current_state = new_state

    def trigger_override(self, payload: Dict[str, Any]):
        """
        Agents or external watchdogs can call this to bypass normal FSM 
        and immediately jump to SOVEREIGN_OVERRIDE state.
        """
        self.override_payload = payload
        self.transition_to(AgentState.SOVEREIGN_OVERRIDE)

    def tick(self, context: Dict[str, Any]):
        """Run one iteration of the FSM."""
        handler = self.state_handlers.get(self.current_state)
        if handler:
            handler(context)
        else:
            print(f"No handler found for state {self.current_state}")
