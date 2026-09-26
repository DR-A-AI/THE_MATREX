# ==============================================================================
# Pydantic Models for Message Types & State
# ==============================================================================

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

SafeValue = str | int | float | bool | None | list | dict


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
    KEY_INJECT = "key_inject"
    TOKEN_EXTRACTED = "token_extracted"  # nosec: B105  # event-type enum value, not a credential
    ERROR = "error"
    SOVEREIGN_OVERRIDE = "sovereign_override"
    USER_COMMAND = "user_command"
    MEMORY_STORE_REQUEST = "memory_store_request"
    MEMORY_RECALL_REQUEST = "memory_recall_request"
    MEMORY_INJECT = "memory_inject"
    MEMORY_STORED = "memory_stored"
    SKILL_PROMOTED = "skill_promoted"
    SKILL_REVIEW_APPROVED = "skill_review_approved"
    DECISION_LOGGED = "decision_logged"
    INTENT_PARSED = "intent_parsed"


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
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_agent_id: str
    correlation_id: str
    payload: dict[str, SafeValue]
    metadata: dict[str, str] | None = None

    model_config = ConfigDict(use_enum_values=True)


class TaskDefinition(BaseModel):
    """Task structure for agent execution"""

    task_id: str
    agent_type: str  # neo, morpheus, smith, trinity, oracle
    instructions: str
    input_data: dict[str, SafeValue]
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
    metadata: dict[str, SafeValue]


class QAVerdict(BaseModel):
    """QA decision on artifact"""

    submission_id: str
    passed_static: bool
    static_errors: list[str] = []
    passed_llm: bool
    llm_feedback: str | None = None
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
