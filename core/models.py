# ==============================================================================
# Pydantic Models for Message Types & State
# ==============================================================================

from pydantic import BaseModel, Field
from typing import Any, Optional, Dict, List
from enum import Enum
from datetime import datetime

class EventType(str, Enum):
    """Valid event types in the neural bus"""
    TASK_QUEUED = "task_queued"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    AGENT_HEARTBEAT = "agent_heartbeat"
    AGENT_ALIVE = "agent_alive"
    QA_SUBMISSION = "qa_submission"
    QA_VERDICT = "qa_verdict"
    STATE_UPDATE = "state_update"
    SKILL_INJECT = "skill_inject"
    SKILL_REQUEST = "skill_request"
    ERROR = "error"
    SOVEREIGN_OVERRIDE = "sovereign_override"

class AgentState(str, Enum):
    """FSM States for agents"""
    IDLE = "idle"
    ACTIVE = "active"
    BLOCKED = "blocked"
    ERROR = "error"
    SOVEREIGN_OVERRIDE = "sovereign_override"
    TERMINATED = "terminated"

class EventPayload(BaseModel):
    """Base event structure for ZMQ neural bus"""
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_agent_id: str
    correlation_id: str
    payload: Dict[str, Any]
    metadata: Optional[Dict[str, str]] = None
    
    class Config:
        use_enum_values = True

class TaskDefinition(BaseModel):
    """Task structure for agent execution"""
    task_id: str
    agent_type: str  # neo, morpheus, smith, trinity, oracle
    instructions: str
    input_data: Dict[str, Any]
    priority: int = 5
    timeout_seconds: int = 300
    retry_count: int = 3
    require_qc: bool = True

class QASubmission(BaseModel):
    """QA artifact for review"""
    submission_id: str
    artifact_type: str  # code, text, plan
    content: str
    source_agent_id: str
    submission_time: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any]

class QAVerdict(BaseModel):
    """QA decision on artifact"""
    submission_id: str
    passed_static: bool
    static_errors: List[str] = []
    passed_llm: bool
    llm_feedback: Optional[str] = None
    verdict: str  # APPROVED, REJECTED, NEEDS_REVISION
    confidence: float = Field(ge=0, le=1)

class AgentHealthReport(BaseModel):
    """Agent health status"""
    agent_id: str
    state: AgentState
    cpu_usage_percent: float
    memory_usage_mb: float
    tasks_completed: int
    last_heartbeat: datetime
    error_count: int = 0
    is_alive: bool = True

class SecretToken(BaseModel):
    """Auth vault token"""
    token_id: str
    scope: str
    created_at: datetime
    expires_at: datetime
    resource_path: str
    usage_count: int = 0
