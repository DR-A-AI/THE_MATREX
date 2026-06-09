import json
import sys
sys.path.append(r"J:\THE_MATRIX")
from datetime import datetime, timezone
from core.models import EventPayload, EventType

def test_event_payload_serialization():
    # 1. Create a dummy payload
    payload = EventPayload(
        event_type=EventType.USER_COMMAND,
        timestamp=datetime.now(timezone.utc),
        source_agent_id="test-source",
        correlation_id="corr-123",
        payload={"message": "hello test", "target_agent": "neo"}
    )
    
    # 2. Serialize to dict and JSON
    serialized_dict = payload.model_dump(mode="json")
    serialized_json = json.dumps(serialized_dict)
    
    # 3. Deserialize back
    deserialized_dict = json.loads(serialized_json)
    deserialized_payload = EventPayload(**deserialized_dict)
    
    # 4. Assert correctness
    assert deserialized_payload.event_type == EventType.USER_COMMAND
    assert deserialized_payload.source_agent_id == "test-source"
    assert deserialized_payload.correlation_id == "corr-123"
    assert deserialized_payload.payload["message"] == "hello test"
    assert deserialized_payload.payload["target_agent"] == "neo"
    print("Serialization test PASSED successfully.")

if __name__ == "__main__":
    test_event_payload_serialization()
