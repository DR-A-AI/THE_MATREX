import os
import uuid
import asyncio
import logging

logger = logging.getLogger("Matrix.Governance")

class SovereignGovernance:
    """
    Absolute HitL (Human-in-the-Loop) Governance Layer.
    Intercepts dangerous tool executions and mandates explicit Sovereign Commander approval.
    """
    GOVERNANCE_DIR = r"J:\THE_MATRIX\governance"

    @classmethod
    async def request_permission(cls, agent_name: str, tool_name: str, args: dict, client, correlation_id: str) -> bool:
        """
        Pauses execution and asks Commander for permission.
        Returns True if APPROVED, False if REJECTED or TIMEOUT.
        """
        # Safe tools that do not require approval
        SAFE_TOOLS = ["read_local_file", "list_local_dir", "search_local_code"]
        if tool_name in SAFE_TOOLS:
            return True

        os.makedirs(cls.GOVERNANCE_DIR, exist_ok=True)
        req_id = str(uuid.uuid4())[:8]
        
        req_file = os.path.join(cls.GOVERNANCE_DIR, f"PENDING_{req_id}.txt")
        approved_file = os.path.join(cls.GOVERNANCE_DIR, f"APPROVED_{req_id}.txt")
        rejected_file = os.path.join(cls.GOVERNANCE_DIR, f"REJECTED_{req_id}.txt")
        
        with open(req_file, "w", encoding="utf-8") as f:
            f.write(f"AGENT: {agent_name}\n")
            f.write(f"TOOL: {tool_name}\n")
            f.write(f"ARGS: {args}\n")

        # Notify the Commander
        from core.models import EventType, EventPayload
        reply = EventPayload(
            event_type=EventType.STATE_UPDATE,
            source_agent_id=agent_name,
            correlation_id=correlation_id,
            payload={"message": f"🚨 [GOVERNANCE LOCK] {agent_name} wants to use '{tool_name}'.\nAwaiting Commander approval (ID: {req_id}).\nCheck folder: {cls.GOVERNANCE_DIR}\nRename PENDING_{req_id}.txt to APPROVED_{req_id}.txt to allow, or REJECTED_{req_id}.txt to deny."}
        )
        if client:
            await client.send(reply)

        logger.warning(f"[{agent_name}] Execution PAUSED. Waiting for HITL approval on {req_id}...")

        # Wait loop (up to 10 minutes)
        for _ in range(600):
            if os.path.exists(approved_file):
                os.remove(approved_file)
                logger.info(f"[{agent_name}] Execution APPROVED by Commander (ID: {req_id}).")
                return True
            if os.path.exists(rejected_file):
                os.remove(rejected_file)
                logger.error(f"[{agent_name}] Execution DENIED by Commander (ID: {req_id}).")
                return False
            await asyncio.sleep(1)

        # Timeout
        if os.path.exists(req_file):
            os.remove(req_file)
        logger.error(f"[{agent_name}] Execution TIMED OUT waiting for approval (ID: {req_id}).")
        return False
