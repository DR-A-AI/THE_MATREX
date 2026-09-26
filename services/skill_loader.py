"""Declarative Skill Loader and Absorption Pipeline for Sovereign Matrix."""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import logging
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from agents.aegis_qa import AsymmetricQA
from core.models import EventPayload, EventType

logger = logging.getLogger("Matrix.SkillLoader")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SkillStage(str, Enum):
    DISCOVERED = "DISCOVERED"
    VALIDATED = "VALIDATED"
    PREPARED = "PREPARED"
    PROMOTED = "PROMOTED"
    INJECTED = "INJECTED"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"


# Invariant: Allowed tools closed allowlist
ALLOWED_SKILL_TOOLS: frozenset[str] = frozenset(
    {
        "docs.read",
        "memory.read",
        "memory.search",
        "planning.emit",
        "skills.discover",
        "skills.validate",
    }
)
ALLOWED_TOOL_IDS = ALLOWED_SKILL_TOOLS

# Offensive patterns strictly blocked from execution or absorption
BLOCKED_PATTERNS = (
    "active-directory-attack",
    "password-crack",
    "exploit-kit",
    "ransomware",
    "keylogger",
    "credential-dump",
    "bypass-auth",
)

SKILL_ID_PATTERN = re.compile(r"^sk_[0-9a-f]{12}$")
REQUIRED_CURATED_FIELDS = (
    "skill_id",
    "name",
    "version",
    "package_type",
    "risk",
    "capabilities",
    "allowed_tools",
    "boundaries",
    "system_instructions",
    "contract_version",
    "source_ref",
    "license",
    "reviewer",
)
SKILL_CONTRACT_VERSION = "1.0"


class SkillError(Exception):
    """Base exception for skill loader errors."""


class SkillApprovalError(SkillError, PermissionError):
    """Raised when required bus review or commander approval is missing."""


class SkillLoader:
    workspace_root: Path
    curated_dir: Path
    quarantine_dir: Path

    def __init__(
        self,
        workspace_root: Path | str | None = None,
        bus_client: Any = None,
        memory_store: Any = None,
        sovereignty_gate: Any = None,
    ) -> None:
        if workspace_root:
            self.workspace_root = Path(workspace_root).resolve()
        else:
            self.workspace_root = (Path(os.getenv("MATRIX_ROOT", Path.cwd())) / "skills").resolve()

        self.curated_dir = self.workspace_root / "curated"
        self.quarantine_dir = self.workspace_root / "quarantine"
        # Backward-compatible aliases matching V2 loader
        self.curated = self.curated_dir
        self.quarantine = self.quarantine_dir
        self.root = self.workspace_root

        configured_source = os.getenv("MATRIX_SKILLS_SOURCE_DIR", "").strip()
        self.source = (
            Path(configured_source).resolve()
            if configured_source
            else self.workspace_root / "source" / "agentic-awesome-skills-clean"
        )

        self.curated_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        self.bus_client = bus_client
        self.memory = memory_store
        self.sovereignty = sovereignty_gate
        self.approved_skills: set[str] = set()

    def inventory_imported_source(self, limit: int = 5000) -> dict[str, Any]:
        """Inventory imported skill metadata without importing or executing code."""
        if not self.source.exists():
            return {"source": str(self.source), "skills": [], "count": 0}
        skills_root = self.source / "skills"
        if not skills_root.is_dir():
            return {"source": str(self.source), "skills": [], "count": 0}
        records: list[dict[str, Any]] = []
        for skill_file in sorted(skills_root.glob("*/SKILL.md")):
            if len(records) >= limit:
                break
            package = skill_file.parent.name
            try:
                first_line = next(
                    (
                        line.strip("# \t")
                        for line in skill_file.read_text(
                            encoding="utf-8", errors="replace"
                        ).splitlines()
                        if line.strip()
                    ),
                    package,
                )
            except OSError:
                first_line = package
            records.append(
                {
                    "name": package,
                    "path": str(skill_file.relative_to(self.workspace_root)),
                    "summary": first_line[:240],
                    "stage": SkillStage.DISCOVERED.value,
                    "executable": False,
                }
            )
        return {"source": str(self.source), "skills": records, "count": len(records)}

    # ---------- Discovery (Metadata-only — Never Executes) ----------

    def discover(self, manifest_path: Path | str) -> dict[str, Any]:
        """Reads metadata JSON without code import; assigns deterministic
        skill_id = f"sk_{hashlib.sha256(name.encode()).hexdigest()[:12]}".
        Returns record with stage=DISCOVERED.
        """
        path = Path(manifest_path).resolve()
        data = json.loads(path.read_text(encoding="utf-8"))
        name = str(data.get("name", path.stem))
        skill_id = self._skill_id(name)
        caps = list(data.get("capabilities", []))
        instructions = list(data.get("system_instructions", []))
        boundaries = list(data.get("boundaries", []))
        risk = self._assess_risk(
            name, caps, str(data.get("source_ref", "")), instructions + boundaries
        )

        record: dict[str, Any] = {
            "skill_id": skill_id,
            "name": name,
            "version": str(data.get("version", "0.1.0")),
            "capabilities": caps,
            "risk": risk,
            "allowed_tools": list(data.get("allowed_tools", [])),
            "boundaries": boundaries,
            "system_instructions": instructions,
            "contract_version": str(data.get("contract_version", SKILL_CONTRACT_VERSION)),
            "source_ref": str(data.get("source_ref", "")),
            "license": str(data.get("license", "unknown")),
            "stage": SkillStage.DISCOVERED.value,
            "discovered_at": _now(),
        }
        if self.memory and hasattr(self.memory, "register_skill"):
            self.memory.register_skill(
                skill_id,
                agent="oracle",
                name=name,
                stage=SkillStage.DISCOVERED.value,
                manifest_ref=str(path),
            )
        return record

    def _assess_risk(
        self,
        name: str,
        caps: list[str],
        source: str = "",
        instructions: list[str] | None = None,
    ) -> str:
        all_text = f"{name} {' '.join(caps)} {source} {' '.join(instructions or [])}".lower()
        if any(p in all_text for p in BLOCKED_PATTERNS):
            return "HIGH"
        if not caps:
            return "MEDIUM"  # Empty capabilities ghost
        return "LOW"

    # ---------- Validation ----------

    def validate(self, record: dict[str, Any], reviewer: str | list[str]) -> dict[str, Any]:
        """Enforces SKILL_CONTRACT v1.0. Checks reviewer presence,
        verifies license, checks allowed tools against ALLOWED_SKILL_TOOLS,
        blocks offensive patterns, and validates code safety via Aegis QA.
        Transitions stage to VALIDATED or REJECTED.
        """
        if not reviewer:
            return {
                **record,
                "stage": SkillStage.REJECTED.value,
                "reason": "no reviewer — promotion blocked",
            }

        reviewer_str = ", ".join(reviewer) if isinstance(reviewer, list) else str(reviewer)

        # High risk offensive check
        if record.get("risk") == "HIGH" or any(
            p in str(record.get("name", "")).lower() for p in BLOCKED_PATTERNS
        ):
            return {
                **record,
                "stage": SkillStage.REJECTED.value,
                "reason": f"blocked offensive skill (reviewer={reviewer_str})",
            }

        if not record.get("capabilities"):
            return {
                **record,
                "stage": SkillStage.REJECTED.value,
                "reason": f"empty capabilities ghost (reviewer={reviewer_str})",
            }

        license_str = str(record.get("license", "")).strip().lower()
        if license_str in ("", "unknown"):
            return {
                **record,
                "stage": SkillStage.REJECTED.value,
                "reason": f"unverified license (reviewer={reviewer_str})",
            }

        contract_error = self._contract_error(record)
        if contract_error:
            return {
                **record,
                "stage": SkillStage.REJECTED.value,
                "reason": f"invalid skill contract: {contract_error}",
            }

        # Aegis QA Gate: AsymmetricQA scan on skill content
        content_to_check = "\n".join(
            record.get("system_instructions", [])
            + record.get("boundaries", [])
            + record.get("capabilities", [])
        )
        if (
            "def " in content_to_check
            or "import " in content_to_check
            or "eval(" in content_to_check
            or "exec(" in content_to_check
        ) and not AsymmetricQA.verify(content_to_check):
            logger.critical("[SkillLoader] Aegis QA rejected dangerous execution payload in skill")
            return {
                **record,
                "stage": SkillStage.REJECTED.value,
                "reason": f"failed Aegis QA verification (reviewer={reviewer_str})",
            }

        validated_record = {
            **record,
            "stage": SkillStage.VALIDATED.value,
            "reviewer": reviewer_str,
            "validated_at": _now(),
        }
        if self.memory and hasattr(self.memory, "register_skill"):
            self.memory.register_skill(
                validated_record["skill_id"],
                agent="oracle",
                name=validated_record["name"],
                stage=SkillStage.VALIDATED.value,
            )
        return validated_record

    # ---------- Packaging & Preparation ----------

    def prepare(self, record: dict[str, Any]) -> dict[str, Any]:
        """Packages validated skill into curated/{skill_id} with package_manifest.json
        and source_manifest.json. Transitions stage to PREPARED.
        """
        if record.get("stage") != SkillStage.VALIDATED.value:
            raise ValueError("prepare requires VALIDATED stage")

        skill_id = str(record["skill_id"])
        pkg_dir = self.curated_dir / skill_id
        pkg_dir.mkdir(parents=True, exist_ok=True)

        package_manifest = {
            "allowed_tools": record["allowed_tools"],
            "boundaries": record["boundaries"],
            "capabilities": record["capabilities"],
            "contract_version": record["contract_version"],
            "license": record["license"],
            "name": record["name"],
            "package_type": "metadata_only",
            "reviewer": record["reviewer"],
            "risk": record["risk"],
            "skill_id": record["skill_id"],
            "source_ref": record["source_ref"],
            "system_instructions": record["system_instructions"],
            "version": record["version"],
        }
        (pkg_dir / "package_manifest.json").write_text(
            json.dumps(package_manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        source_manifest = {
            "allowed_tools": record["allowed_tools"],
            "boundaries": record["boundaries"],
            "capabilities": record["capabilities"],
            "contract_version": record["contract_version"],
            "license": record["license"],
            "name": record["name"],
            "source_ref": record["source_ref"],
            "system_instructions": record["system_instructions"],
            "version": record["version"],
        }
        (pkg_dir / "source_manifest.json").write_text(
            json.dumps(source_manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        prepared_record = {
            **record,
            "stage": SkillStage.PREPARED.value,
            "package": str(pkg_dir),
        }
        if self.memory and hasattr(self.memory, "register_skill"):
            self.memory.register_skill(
                prepared_record["skill_id"],
                agent="oracle",
                name=prepared_record["name"],
                stage=SkillStage.PREPARED.value,
            )
        return prepared_record

    # ---------- Curated Package Audit & Quarantine ----------

    def validate_curated(self) -> dict[str, list[Any]]:
        """Audits curated packages. Moves packages with missing manifests,
        symlinks, or tool violations into quarantine/.
        Returns {'valid': [...], 'quarantined': [...]}.
        """
        valid: list[str] = []
        quarantined: list[dict[str, Any]] = []

        if not self.curated_dir.exists():
            return {"valid": valid, "quarantined": quarantined}

        for pkg_dir in sorted(self.curated_dir.iterdir()):
            if not pkg_dir.is_dir():
                continue
            reason = self._curated_package_error(pkg_dir)
            if reason is None:
                valid.append(pkg_dir.name)
                continue

            destination = self.quarantine_dir / pkg_dir.name
            suffix = 1
            while destination.exists():
                destination = self.quarantine_dir / f"{pkg_dir.name}-{suffix}"
                suffix += 1

            shutil.move(str(pkg_dir), str(destination))
            quarantined.append(
                {
                    "package": pkg_dir.name,
                    "quarantine": str(destination),
                    "reason": reason,
                }
            )
        return {"valid": valid, "quarantined": quarantined}

    def _curated_package_error(self, pkg_dir: Path) -> str | None:
        if not SKILL_ID_PATTERN.fullmatch(pkg_dir.name):
            return "invalid package directory id"
        if pkg_dir.is_symlink():
            return "symlinked package directory"

        manifests: dict[str, Any] = {}
        for filename in ("package_manifest.json", "source_manifest.json", "bindings.json"):
            path = pkg_dir / filename
            if not path.is_file():
                return f"missing {filename}"
            if path.is_symlink():
                return f"symlinked {filename}"
            try:
                manifests[filename] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return f"invalid {filename}"

        package = manifests["package_manifest.json"]
        source = manifests["source_manifest.json"]
        if not isinstance(package, dict) or not isinstance(source, dict):
            return "manifest must be an object"

        missing = [field for field in REQUIRED_CURATED_FIELDS if field not in package]
        if missing:
            return f"missing package fields: {', '.join(missing)}"

        if package["skill_id"] != pkg_dir.name:
            return "package skill_id does not match directory"
        if package["skill_id"] != self._skill_id(package["name"]):
            return "package skill_id is not deterministic"
        if package["package_type"] != "metadata_only":
            return "unsupported package type"
        if not isinstance(package["capabilities"], list) or not package["capabilities"]:
            return "empty capabilities"

        for field in ("allowed_tools", "boundaries", "system_instructions"):
            val = package.get(field)
            if (
                not isinstance(val, list)
                or not val
                or any(not isinstance(item, str) or not item.strip() for item in val)
            ):
                return f"invalid {field}"

        if package["contract_version"] != SKILL_CONTRACT_VERSION:
            return "unsupported contract version"

        unknown_tools = set(package["allowed_tools"]) - ALLOWED_SKILL_TOOLS
        if unknown_tools:
            return f"unknown allowed tools: {', '.join(sorted(unknown_tools))}"

        if not package["source_ref"] or str(package["license"]).lower() in ("", "unknown"):
            return "incomplete source or license metadata"

        risk = self._assess_risk(
            str(package["name"]),
            package["capabilities"],
            str(package["source_ref"]),
            package.get("system_instructions", []),
        )
        if risk == "HIGH" or package.get("risk") != "LOW":
            return "unsafe metadata"

        # Aegis QA validation on package manifests
        content = "\n".join(
            package.get("system_instructions", [])
            + package.get("boundaries", [])
            + package.get("capabilities", [])
        )
        if (
            "def " in content or "import " in content or "eval(" in content or "exec(" in content
        ) and not AsymmetricQA.verify(content):
            return "Aegis QA violation in package content"

        for field in (
            "name",
            "version",
            "capabilities",
            "allowed_tools",
            "boundaries",
            "system_instructions",
            "contract_version",
            "source_ref",
            "license",
        ):
            if source.get(field) != package.get(field):
                return f"source manifest mismatch: {field}"

        bindings = manifests["bindings.json"]
        if not isinstance(bindings, list) or not bindings:
            return "empty bindings"
        for binding in bindings:
            if (
                not isinstance(binding, dict)
                or binding.get("skill_id") != package["skill_id"]
                or not binding.get("agent")
                or binding.get("status") != "BOUND"
            ):
                return "invalid bindings"

        return None

    @classmethod
    def _contract_error(cls, record: dict[str, Any]) -> str | None:
        missing = [
            field
            for field in (
                "allowed_tools",
                "boundaries",
                "system_instructions",
                "contract_version",
            )
            if field not in record
        ]
        if missing:
            return f"missing {', '.join(missing)}"
        if record.get("contract_version") != SKILL_CONTRACT_VERSION:
            return "unsupported contract version"
        for field in ("allowed_tools", "boundaries", "system_instructions"):
            value = record.get(field)
            if (
                not isinstance(value, list)
                or not value
                or any(not isinstance(item, str) or not item.strip() for item in value)
            ):
                return f"invalid {field}"
        unknown = set(record.get("allowed_tools", [])) - ALLOWED_SKILL_TOOLS
        return f"unknown allowed tools: {', '.join(sorted(unknown))}" if unknown else None

    def load_curated(self) -> list[dict[str, Any]]:
        """Return validated metadata only; never imports or executes a skill."""
        self.validate_curated()
        loaded = []
        curated_root = self.curated_dir.resolve()
        for package_id in sorted(self.curated_dir.iterdir()):
            if not package_id.is_dir():
                continue
            package_dir = package_id.resolve()
            if curated_root not in package_dir.parents:
                continue
            error = self._curated_package_error(package_dir)
            if error is not None:
                continue
            loaded.append(
                json.loads((package_dir / "package_manifest.json").read_text(encoding="utf-8"))
            )
        return loaded

    @staticmethod
    def _skill_id(name: Any) -> str:
        return f"sk_{hashlib.sha256(str(name).encode('utf-8')).hexdigest()[:12]}"

    # ---------- Promotion Gate ----------

    def promote(
        self,
        record: dict[str, Any],
        commander_approval: bool = False,
        bus_client: Any = None,
    ) -> dict[str, Any]:
        """Promotes prepared skill. Requires commander_approval=True.
        Transitions stage to PROMOTED. Emits SKILL_PROMOTED on bus.
        """
        if record.get("stage") != SkillStage.PREPARED.value:
            raise ValueError("promote requires PREPARED stage")
        if not commander_approval:
            raise SkillApprovalError("promotion requires Commander approval")

        promoted_at = _now()
        promoted_record = {
            **record,
            "stage": SkillStage.PROMOTED.value,
            "promoted_at": promoted_at,
        }

        # Construct and emit SKILL_PROMOTED event on the neural bus
        promoted_event = EventPayload(
            event_type=EventType.SKILL_PROMOTED,
            source_agent_id="oracle",
            correlation_id=uuid.uuid4().hex,
            payload={
                "skill_id": promoted_record["skill_id"],
                "skill_name": promoted_record["name"],
                "commander_approval": True,
                "allowed_tools": list(promoted_record.get("allowed_tools", [])),
                "timestamp": promoted_at,
            },
        )
        promoted_record["promoted_event"] = promoted_event.model_dump(mode="json")

        target_bus = bus_client or self.bus_client
        if target_bus and hasattr(target_bus, "send"):
            send_fn = target_bus.send
            if inspect.iscoroutinefunction(send_fn):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(send_fn(promoted_event))
                except RuntimeError:
                    asyncio.run(send_fn(promoted_event))
            else:
                send_fn(promoted_event)

        if self.memory and hasattr(self.memory, "register_skill"):
            self.memory.register_skill(
                promoted_record["skill_id"],
                agent="oracle",
                name=promoted_record["name"],
                stage=SkillStage.PROMOTED.value,
            )
            if hasattr(self.memory, "record_audit"):
                self.memory.record_audit(
                    "oracle",
                    "skill_promoted",
                    promoted_record["skill_id"],
                    risk_level="MEDIUM",
                    result="promoted",
                    approval_status="approved",
                )
        return promoted_record

    # ---------- Bus Review & Injection Gate ----------

    def create_review_approval_event(
        self,
        record: dict[str, Any],
        reviewers: list[str] | None = None,
        verdict: str = "APPROVED",
    ) -> EventPayload:
        """Create a validated SKILL_REVIEW_APPROVED EventPayload."""
        revs = reviewers or ["smith", "morpheus"]
        return EventPayload(
            event_type=EventType.SKILL_REVIEW_APPROVED,
            source_agent_id="oracle",
            correlation_id=uuid.uuid4().hex,
            payload={
                "skill_id": record["skill_id"],
                "skill_name": record["name"],
                "reviewers": revs,
                "contract_version": record.get("contract_version", SKILL_CONTRACT_VERSION),
                "verdict": verdict,
            },
        )

    def record_review_approval(self, event: EventPayload | dict[str, Any]) -> bool:
        """Validates and records a SKILL_REVIEW_APPROVED bus event.
        Requires dual-agent review (Smith + Morpheus) and APPROVED verdict.
        """
        event_type: Any
        if isinstance(event, EventPayload):
            event_type = event.event_type
            payload = event.payload
        elif isinstance(event, dict):
            event_type = event.get("event_type")
            payload = event.get("payload", {})
        else:
            return False

        if event_type not in (
            EventType.SKILL_REVIEW_APPROVED,
            EventType.SKILL_REVIEW_APPROVED.value,
        ):
            logger.warning("[SkillLoader] Rejected approval: wrong event type %s", event_type)
            return False

        verdict = str(payload.get("verdict", "")).strip().upper()
        if verdict != "APPROVED":
            logger.warning("[SkillLoader] Rejected approval: verdict is not APPROVED (%s)", verdict)
            return False

        reviewers = payload.get("reviewers", [])
        if not isinstance(reviewers, list):
            logger.warning("[SkillLoader] Rejected approval: reviewers is not a list")
            return False

        # Dual review check: Smith + Morpheus
        reviewer_set = {str(r).strip().lower() for r in reviewers}
        if not {"smith", "morpheus"}.issubset(reviewer_set):
            logger.warning(
                "[SkillLoader] Rejected approval: requires dual review (smith + morpheus), got %s",
                reviewers,
            )
            return False

        skill_id = str(payload.get("skill_id", "")).strip()
        if not skill_id or not SKILL_ID_PATTERN.fullmatch(skill_id):
            logger.warning("[SkillLoader] Rejected approval: invalid skill_id %s", skill_id)
            return False

        self.approved_skills.add(skill_id)
        logger.info("[SkillLoader] SKILL_REVIEW_APPROVED verified and registered for %s", skill_id)
        return True

    def inject(
        self,
        record: dict[str, Any],
        target_agents: list[str],
        has_bus_approval: bool = False,
        review_event: EventPayload | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Binds promoted skill to target agents.
        MANDATORY INVARIANT: Rejects injection unless has_bus_approval=True
        (verified SKILL_REVIEW_APPROVED event on bus).
        Writes curated/{skill_id}/bindings.json. Transitions stage to INJECTED.
        """
        if record.get("stage") != SkillStage.PROMOTED.value:
            raise ValueError("inject requires PROMOTED stage")

        skill_id = str(record.get("skill_id", ""))
        # Check review event if passed
        if review_event is not None and self.record_review_approval(review_event):
            has_bus_approval = True

        # Check recorded approved skills
        if skill_id in self.approved_skills:
            has_bus_approval = True

        if not has_bus_approval:
            raise SkillApprovalError(
                "injection rejected: verified SKILL_REVIEW_APPROVED bus event required"
            )

        bindings = [
            {"skill_id": skill_id, "agent": agent, "status": "BOUND"} for agent in target_agents
        ]
        pkg_dir = self.curated_dir / skill_id
        pkg_dir.mkdir(parents=True, exist_ok=True)
        bindings_file = pkg_dir / "bindings.json"
        bindings_file.write_text(json.dumps(bindings, indent=2) + "\n", encoding="utf-8")

        injected_record = {
            **record,
            "stage": SkillStage.INJECTED.value,
            "bindings": bindings,
            "injected_at": _now(),
        }
        if self.memory and hasattr(self.memory, "register_skill"):
            self.memory.register_skill(
                injected_record["skill_id"],
                agent="oracle",
                name=injected_record["name"],
                stage=SkillStage.INJECTED.value,
            )
        return injected_record
