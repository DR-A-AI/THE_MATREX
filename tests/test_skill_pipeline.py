"""Comprehensive tests for the declarative skill absorption pipeline and bus events.

Validates the 5-stage lifecycle: DISCOVERED -> VALIDATED -> PREPARED -> PROMOTED -> INJECTED.
Enforces SKILL_CONTRACT v1.0, 6-tool allowlist, Aegis QA gating, quarantine isolation,
and dual-agent bus review approvals.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import uuid
from pathlib import Path

import pytest

from core.models import EventPayload, EventType
from services.skill_loader import (
    ALLOWED_SKILL_TOOLS,
    SkillApprovalError,
    SkillLoader,
    SkillStage,
)


@pytest.fixture
def temp_workspace():
    """Provides an isolated workspace directory with curated and quarantine subdirectories."""
    td = Path(tempfile.mkdtemp(prefix="test_skill_pipeline_"))
    yield td
    shutil.rmtree(td, ignore_errors=True)


@pytest.fixture
def loader(temp_workspace):
    """Provides a SkillLoader instance bound to the temporary workspace."""
    return SkillLoader(workspace_root=temp_workspace)


def create_manifest(
    path: Path,
    name: str = "matrix-analyzer",
    version: str = "1.0.0",
    capabilities: list[str] | None = None,
    allowed_tools: list[str] | None = None,
    boundaries: list[str] | None = None,
    system_instructions: list[str] | None = None,
    contract_version: str = "1.0",
    source_ref: str = "catalog/matrix-analyzer",
    license: str = "MIT",
) -> Path:
    """Helper to generate a valid or custom skill manifest file."""
    data = {
        "name": name,
        "version": version,
        "capabilities": capabilities or ["read_docs", "search_memory"],
        "allowed_tools": allowed_tools or ["docs.read", "memory.read"],
        "boundaries": boundaries or ["Read-only access", "No command execution"],
        "system_instructions": system_instructions or ["Analyze data carefully"],
        "contract_version": contract_version,
        "source_ref": source_ref,
        "license": license,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


# 1. Discovery of valid metadata (computes sha256 skill_id, stage DISCOVERED)
def test_discovery_computes_sha256_id_and_discovered_stage(loader, temp_workspace):
    manifest_path = temp_workspace / "sample_skill.json"
    create_manifest(manifest_path, name="neural-probe")

    record = loader.discover(manifest_path)

    expected_id = f"sk_{hashlib.sha256(b'neural-probe').hexdigest()[:12]}"
    assert record["skill_id"] == expected_id
    assert record["name"] == "neural-probe"
    assert record["stage"] == SkillStage.DISCOVERED.value
    assert record["risk"] == "LOW"
    assert record["contract_version"] == "1.0"
    assert "docs.read" in record["allowed_tools"]
    assert "discovered_at" in record


# 2. Offensive skill blocked during discovery/validation
def test_offensive_skill_blocked_during_discovery_and_validation(loader, temp_workspace):
    offensive_path = temp_workspace / "offensive_skill.json"
    create_manifest(
        offensive_path,
        name="password-crack-tool",
        capabilities=["credential-dump", "active-directory-attack"],
    )

    record = loader.discover(offensive_path)
    assert record["risk"] == "HIGH"

    validation_result = loader.validate(record, reviewer="smith")
    assert validation_result["stage"] == SkillStage.REJECTED.value
    assert "blocked offensive skill" in validation_result["reason"]


def test_offensive_pattern_in_capabilities_blocked(loader, temp_workspace):
    manifest_path = temp_workspace / "ransomware_skill.json"
    create_manifest(
        manifest_path,
        name="crypto-locker",
        capabilities=["ransomware-encryption"],
    )

    record = loader.discover(manifest_path)
    assert record["risk"] == "HIGH"

    res = loader.validate(record, reviewer="morpheus")
    assert res["stage"] == SkillStage.REJECTED.value
    assert "blocked offensive skill" in res["reason"]


# 3. Validation passes with valid contract and reviewer
def test_validation_passes_with_valid_contract_and_reviewer(loader, temp_workspace):
    manifest_path = temp_workspace / "valid_skill.json"
    create_manifest(manifest_path, name="safe-doc-analyzer")

    record = loader.discover(manifest_path)
    validated = loader.validate(record, reviewer="smith")

    assert validated["stage"] == SkillStage.VALIDATED.value
    assert validated["reviewer"] == "smith"
    assert "validated_at" in validated
    assert validated["skill_id"] == record["skill_id"]


def test_validation_fails_without_reviewer(loader, temp_workspace):
    manifest_path = temp_workspace / "valid_skill.json"
    create_manifest(manifest_path, name="unreviewed-skill")

    record = loader.discover(manifest_path)
    rejected = loader.validate(record, reviewer="")

    assert rejected["stage"] == SkillStage.REJECTED.value
    assert "no reviewer" in rejected["reason"]


# 4. Validation fails on unknown allowed_tools (outside the 6 allowed tools)
def test_validation_fails_on_unknown_allowed_tools(loader, temp_workspace):
    manifest_path = temp_workspace / "bad_tools.json"
    create_manifest(
        manifest_path,
        name="shell-executor",
        allowed_tools=["docs.read", "shell.exec", "system.root"],
    )

    record = loader.discover(manifest_path)
    rejected = loader.validate(record, reviewer="smith")

    assert rejected["stage"] == SkillStage.REJECTED.value
    assert "unknown allowed tools" in rejected["reason"]
    assert "shell.exec" in rejected["reason"]
    assert "system.root" in rejected["reason"]


def test_validation_allowed_tools_strictly_subset_of_six(loader, temp_workspace):
    # Verify that only the 6 allowed tools are accepted
    assert ALLOWED_SKILL_TOOLS == frozenset(
        {
            "docs.read",
            "memory.read",
            "memory.search",
            "planning.emit",
            "skills.discover",
            "skills.validate",
        }
    )

    manifest_path = temp_workspace / "all_allowed_tools.json"
    create_manifest(
        manifest_path,
        name="full-access-declarative",
        allowed_tools=list(ALLOWED_SKILL_TOOLS),
    )

    record = loader.discover(manifest_path)
    validated = loader.validate(record, reviewer="morpheus")
    assert validated["stage"] == SkillStage.VALIDATED.value


# 5. Validation fails on missing/unknown license
@pytest.mark.parametrize("invalid_license", ["", "unknown", "UNKNOWN", "   "])
def test_validation_fails_on_missing_or_unknown_license(loader, temp_workspace, invalid_license):
    manifest_path = temp_workspace / f"license_{abs(hash(invalid_license))}.json"
    create_manifest(manifest_path, name="unlicensed-skill", license=invalid_license)

    record = loader.discover(manifest_path)
    rejected = loader.validate(record, reviewer="smith")

    assert rejected["stage"] == SkillStage.REJECTED.value
    assert "unverified license" in rejected["reason"]


# 6. Preparation creates manifests in curated directory
def test_preparation_creates_manifests_in_curated_directory(loader, temp_workspace):
    manifest_path = temp_workspace / "prep_skill.json"
    create_manifest(manifest_path, name="doc-summarizer")

    record = loader.discover(manifest_path)
    validated = loader.validate(record, reviewer="smith")
    prepared = loader.prepare(validated)

    assert prepared["stage"] == SkillStage.PREPARED.value
    skill_id = prepared["skill_id"]
    pkg_dir = loader.curated_dir / skill_id

    assert pkg_dir.is_dir()
    pkg_manifest_file = pkg_dir / "package_manifest.json"
    src_manifest_file = pkg_dir / "source_manifest.json"

    assert pkg_manifest_file.is_file()
    assert src_manifest_file.is_file()

    # Verify package manifest content
    pkg_manifest = json.loads(pkg_manifest_file.read_text(encoding="utf-8"))
    assert pkg_manifest["skill_id"] == skill_id
    assert pkg_manifest["package_type"] == "metadata_only"
    assert pkg_manifest["contract_version"] == "1.0"
    assert pkg_manifest["reviewer"] == "smith"
    assert "prepared_at" not in pkg_manifest  # deterministic invariant

    # Verify prepare requires VALIDATED stage
    with pytest.raises(ValueError, match="prepare requires VALIDATED stage"):
        loader.prepare(record)  # still at DISCOVERED stage


# 7. Quarantine moves corrupted/tampered package to quarantine directory
def test_quarantine_moves_corrupted_tampered_package_to_quarantine_dir(loader):
    package_id = "sk_112233445566"
    pkg_dir = loader.curated_dir / package_id
    pkg_dir.mkdir(parents=True, exist_ok=True)

    # Incomplete package: package_manifest.json present, but source_manifest.json missing
    (pkg_dir / "package_manifest.json").write_text("{}", encoding="utf-8")

    report = loader.validate_curated()
    assert len(report["quarantined"]) == 1
    assert report["quarantined"][0]["package"] == package_id
    assert "missing source_manifest.json" in report["quarantined"][0]["reason"]

    # Package directory must be removed from curated and present in quarantine
    assert not pkg_dir.exists()
    assert (loader.quarantine_dir / package_id).is_dir()


def test_quarantine_tampered_unauthorized_tools(loader):
    skill_name = "tampered-skill"
    skill_id = f"sk_{hashlib.sha256(skill_name.encode('utf-8')).hexdigest()[:12]}"
    pkg_dir = loader.curated_dir / skill_id
    pkg_dir.mkdir(parents=True, exist_ok=True)

    package = {
        "skill_id": skill_id,
        "name": skill_name,
        "version": "1.0.0",
        "package_type": "metadata_only",
        "risk": "LOW",
        "capabilities": ["read_docs"],
        "allowed_tools": ["shell.exec"],  # Tampered with unauthorized tool!
        "boundaries": ["Safe only"],
        "system_instructions": ["Instructions"],
        "contract_version": "1.0",
        "source_ref": "catalog",
        "license": "MIT",
        "reviewer": "smith",
    }
    (pkg_dir / "package_manifest.json").write_text(json.dumps(package), encoding="utf-8")
    (pkg_dir / "source_manifest.json").write_text(json.dumps(package), encoding="utf-8")
    (pkg_dir / "bindings.json").write_text(
        json.dumps([{"skill_id": skill_id, "agent": "neo", "status": "BOUND"}]),
        encoding="utf-8",
    )

    report = loader.validate_curated()
    assert len(report["quarantined"]) == 1
    assert report["quarantined"][0]["package"] == skill_id
    assert "unknown allowed tools: shell.exec" in report["quarantined"][0]["reason"]
    assert (loader.quarantine_dir / skill_id).is_dir()


# 8. Promotion requires Commander approval and emits SKILL_PROMOTED event
def test_promotion_requires_commander_approval_and_emits_skill_promoted_event(
    loader, temp_workspace
):
    manifest_path = temp_workspace / "promo_skill.json"
    create_manifest(manifest_path, name="probe-analyzer")

    record = loader.discover(manifest_path)
    validated = loader.validate(record, reviewer="morpheus")
    prepared = loader.prepare(validated)

    # Calling promote without commander approval must fail
    with pytest.raises(SkillApprovalError, match="promotion requires Commander approval"):
        loader.promote(prepared, commander_approval=False)

    # Calling promote with invalid stage must fail
    with pytest.raises(ValueError, match="promote requires PREPARED stage"):
        loader.promote(validated, commander_approval=True)

    # Mock bus client to capture emission
    class MockBusClient:
        def __init__(self):
            self.emitted_events: list[EventPayload] = []

        def send(self, event: EventPayload) -> None:
            self.emitted_events.append(event)

    bus = MockBusClient()
    promoted = loader.promote(prepared, commander_approval=True, bus_client=bus)

    assert promoted["stage"] == SkillStage.PROMOTED.value
    assert "promoted_at" in promoted
    assert len(bus.emitted_events) == 1

    event = bus.emitted_events[0]
    assert event.event_type == EventType.SKILL_PROMOTED
    assert event.payload["skill_id"] == prepared["skill_id"]
    assert event.payload["skill_name"] == "probe-analyzer"
    assert event.payload["commander_approval"] is True
    assert "allowed_tools" in event.payload


# 9. Injection fails if SKILL_REVIEW_APPROVED bus event was not emitted
def test_injection_fails_if_skill_review_approved_bus_event_not_emitted(loader, temp_workspace):
    manifest_path = temp_workspace / "inject_fail_skill.json"
    create_manifest(manifest_path, name="unapproved-skill")

    record = loader.discover(manifest_path)
    validated = loader.validate(record, reviewer="smith")
    prepared = loader.prepare(validated)
    promoted = loader.promote(prepared, commander_approval=True)

    # Attempt injection without bus approval
    with pytest.raises(
        SkillApprovalError,
        match="injection rejected: verified SKILL_REVIEW_APPROVED bus event required",
    ):
        loader.inject(promoted, target_agents=["neo", "trinity"], has_bus_approval=False)

    bindings_file = loader.curated_dir / promoted["skill_id"] / "bindings.json"
    assert not bindings_file.exists()


# 10. Injection succeeds when SKILL_REVIEW_APPROVED event is verified and writes bindings.json
def test_injection_succeeds_when_skill_review_approved_event_verified(loader, temp_workspace):
    manifest_path = temp_workspace / "inject_success_skill.json"
    create_manifest(manifest_path, name="approved-skill")

    record = loader.discover(manifest_path)
    validated = loader.validate(record, reviewer="smith")
    prepared = loader.prepare(validated)
    promoted = loader.promote(prepared, commander_approval=True)

    # Dual-agent review event (Smith + Morpheus)
    review_event = loader.create_review_approval_event(
        promoted,
        reviewers=["smith", "morpheus"],
        verdict="APPROVED",
    )
    assert loader.record_review_approval(review_event) is True

    # Injection should now succeed
    injected = loader.inject(promoted, target_agents=["neo", "trinity"])

    assert injected["stage"] == SkillStage.INJECTED.value
    assert "injected_at" in injected
    assert len(injected["bindings"]) == 2

    bindings_file = loader.curated_dir / promoted["skill_id"] / "bindings.json"
    assert bindings_file.is_file()

    bindings = json.loads(bindings_file.read_text(encoding="utf-8"))
    assert len(bindings) == 2
    assert bindings[0] == {"skill_id": promoted["skill_id"], "agent": "neo", "status": "BOUND"}
    assert bindings[1] == {"skill_id": promoted["skill_id"], "agent": "trinity", "status": "BOUND"}


def test_dual_agent_review_requires_both_smith_and_morpheus(loader, temp_workspace):
    manifest_path = temp_workspace / "dual_agent_test.json"
    create_manifest(manifest_path, name="partial-review-skill")

    record = loader.discover(manifest_path)
    validated = loader.validate(record, reviewer="smith")
    prepared = loader.prepare(validated)
    promoted = loader.promote(prepared, commander_approval=True)

    # Review with only smith (morpheus missing)
    single_review_event = loader.create_review_approval_event(
        promoted,
        reviewers=["smith"],
        verdict="APPROVED",
    )
    assert loader.record_review_approval(single_review_event) is False

    # Attempt injection must still fail
    with pytest.raises(SkillApprovalError):
        loader.inject(promoted, target_agents=["neo"])

    # Now add both smith and morpheus
    dual_review_event = loader.create_review_approval_event(
        promoted,
        reviewers=["smith", "morpheus"],
        verdict="APPROVED",
    )
    assert loader.record_review_approval(dual_review_event) is True

    # Injection succeeds
    injected = loader.inject(promoted, target_agents=["neo"])
    assert injected["stage"] == SkillStage.INJECTED.value


# 11. Bus schema verification: SKILL_PROMOTED and SKILL_REVIEW_APPROVED serialize properly in EventPayload
def test_bus_schema_verification_skill_events_serialize_properly():
    # Verify SKILL_PROMOTED schema serialization
    promoted_payload = {
        "skill_id": "sk_123456789abc",
        "skill_name": "data-extractor",
        "commander_approval": True,
        "allowed_tools": ["docs.read", "memory.read"],
        "timestamp": "2026-09-23T14:30:00Z",
    }
    promoted_event = EventPayload(
        event_type=EventType.SKILL_PROMOTED,
        source_agent_id="oracle",
        correlation_id=uuid.uuid4().hex,
        payload=promoted_payload,
    )

    serialized_promoted = promoted_event.model_dump(mode="json")
    assert serialized_promoted["event_type"] == "skill_promoted"
    assert serialized_promoted["payload"]["skill_id"] == "sk_123456789abc"
    assert serialized_promoted["payload"]["commander_approval"] is True

    # Verify SKILL_REVIEW_APPROVED schema serialization
    review_payload = {
        "skill_id": "sk_123456789abc",
        "skill_name": "data-extractor",
        "reviewers": ["smith", "morpheus"],
        "contract_version": "1.0",
        "verdict": "APPROVED",
    }
    review_event = EventPayload(
        event_type=EventType.SKILL_REVIEW_APPROVED,
        source_agent_id="smith",
        correlation_id=uuid.uuid4().hex,
        payload=review_payload,
    )

    serialized_review = review_event.model_dump(mode="json")
    assert serialized_review["event_type"] == "skill_review_approved"
    assert serialized_review["payload"]["verdict"] == "APPROVED"
    assert "morpheus" in serialized_review["payload"]["reviewers"]


# Aegis QA Integration Test
def test_aegis_qa_blocks_executable_python_payloads(loader, temp_workspace):
    manifest_path = temp_workspace / "aegis_fail.json"
    create_manifest(
        manifest_path,
        name="dangerous-code-skill",
        system_instructions=["def exploit():\n    import os\n    os.system('rm -rf /')"],
    )

    record = loader.discover(manifest_path)
    rejected = loader.validate(record, reviewer="smith")

    assert rejected["stage"] == SkillStage.REJECTED.value
    assert "Aegis QA" in rejected["reason"]
