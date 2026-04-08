from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Dict, Optional

try:
    from .agent_state import AgentStateManager
    from .mission_blueprints import infer_mission_profile
    from .mission_service import MissionService
    from .models import IntakeRequestRecord
    from .notifications import NotificationService
    from .repository import IntakeRequestRepository, MissionRepository
    from .utils import new_id
except ImportError:  # pragma: no cover - runtime script compatibility
    from agent_state import AgentStateManager
    from mission_blueprints import infer_mission_profile
    from mission_service import MissionService
    from models import IntakeRequestRecord
    from notifications import NotificationService
    from repository import IntakeRequestRepository, MissionRepository
    from utils import new_id


MODE_HINTS = [
    ("security_review", ("security", "vulnerabilidad", "xss", "sql injection", "hardening", "auth bug")),
    ("bugfix_debug", ("bug", "error", "broken", "falla", "fix", "issue", "no funciona", "crash")),
    ("documentation_pack", ("docs", "document", "guide", "readme")),
    ("research_only", ("investiga", "research", "analiza", "comparar", "explorar")),
    ("business_audit_proposal", ("proposal", "offer", "outreach", "lead", "prospect", "pitch")),
    ("marketing_campaign", ("marketing", "campaign", "social", "seo", "brand", "content")),
    ("landing_launch", ("landing", "hero", "marketing page", "launch")),
    ("feature_extension", ("feature", "agrega", "anade", "nuevo flujo", "integracion")),
]

PRIORITY_HINTS = [
    ("critical", ("urgent", "critico", "critical", "down", "caido", "produccion", "payment", "security breach")),
    ("high", ("high", "importante", "asap", "bloquea", "broken login", "error 500")),
    ("medium", ("medium", "mejora", "polish", "optimize")),
]


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def infer_mode_from_problem(text: str) -> str:
    haystack = _normalize_text(text)
    for mode, hints in MODE_HINTS:
        if any(hint in haystack for hint in hints):
            return mode

    profile = infer_mission_profile({"title": "", "goal": text, "mode": ""})
    domains = set(profile.get("domains") or [])
    intents = set(profile.get("intent_tags") or [])
    outcomes = set(profile.get("outcome_tags") or [])
    risk_flags = set(profile.get("risk_flags") or [])

    if "security_sensitive" in risk_flags or "security" in domains:
        return "security_review"
    if "marketing" in domains and "sales" not in domains:
        return "marketing_campaign"
    if ("sales" in domains or "outreach" in intents) and any(
        token in haystack for token in ("outreach", "lead", "prospect", "pitch", "proposal", "offer", "sales")
    ):
        return "business_audit_proposal"
    software_tokens = ("feature", "api", "backend", "frontend", "bug", "fix", "integration", "auth", "database", "web", "website", "landing", "app", "ui", "ux")
    if {"strategy", "design", "build"} & intents and not any(token in haystack for token in software_tokens):
        return "general_operating_request"
    if intents == {"research"} or ("research" in intents and not intents.intersection({"build", "outreach", "publish"})):
        return "research_only"
    if "report_pack" in outcomes and "working_solution" not in outcomes:
        return "documentation_pack"
    if "design" in intents and any(token in haystack for token in ("landing", "website", "web", "ux", "ui")):
        return "landing_launch"
    if "build" in intents or "engineering" in domains or "product" in domains:
        return "feature_extension"
    return "general_operating_request"


def infer_priority_from_problem(text: str) -> str:
    haystack = _normalize_text(text)
    for priority, hints in PRIORITY_HINTS:
        if any(hint in haystack for hint in hints):
            return priority
    return "medium"


def build_request_title(title: Optional[str], description: str) -> str:
    candidate = (title or "").strip()
    if candidate:
        return candidate[:120]
    first_sentence = re.split(r"[.!?\n]", description.strip(), maxsplit=1)[0].strip()
    if first_sentence:
        return first_sentence[:120]
    return "Nueva solicitud operativa"


def fingerprint_problem(title: str, description: str) -> str:
    normalized = f"{_normalize_text(title)}::{_normalize_text(description)}"
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


@dataclass
class IntakeService:
    intake_repository: IntakeRequestRepository
    mission_repository: MissionRepository
    mission_service: MissionService
    notifications: NotificationService
    agent_state_manager: Optional[AgentStateManager] = None

    def list_requests(self, limit: int = 50):
        return self.intake_repository.list_requests(limit=limit)

    def submit_problem(
        self,
        *,
        description: str,
        title: Optional[str] = None,
        priority: Optional[str] = None,
        mode: Optional[str] = None,
        requested_by: Optional[str] = None,
        channel: str = "mobile",
        source: str = "mobile",
        auto_dispatch: bool = True,
        details: Optional[Dict] = None,
    ) -> Dict:
        description = (description or "").strip()
        if not description:
            raise ValueError("description is required")

        resolved_title = build_request_title(title, description)
        resolved_mode = mode or infer_mode_from_problem(f"{resolved_title}\n{description}")
        resolved_priority = priority or infer_priority_from_problem(f"{resolved_title}\n{description}")
        inferred_profile = infer_mission_profile({"title": resolved_title, "goal": description, "mode": resolved_mode})
        fingerprint = fingerprint_problem(resolved_title, description)
        duplicate = self.intake_repository.find_active_duplicate(fingerprint)

        if duplicate:
            duplicate_details = dict(duplicate.get("details") or {})
            duplicate_details["duplicate_seen_at"] = duplicate.get("updated_at")
            return {
                "ok": True,
                "duplicate": True,
                "request": duplicate,
                "mission_id": duplicate.get("mission_id"),
                "details": duplicate_details,
            }

        request = IntakeRequestRecord(
            id=new_id("request"),
            title=resolved_title,
            description=description,
            status="pending",
            priority=resolved_priority,
            requested_by=requested_by,
            channel=channel,
            source=source,
            mode=resolved_mode,
            fingerprint=fingerprint,
            details={
                "auto_dispatch": auto_dispatch,
                "submitted_via": channel,
                "inferred_profile": inferred_profile,
                **(details or {}),
            },
        )
        self.intake_repository.create_request(request)
        self.notifications.enqueue(
            kind="intake_received",
            summary=f"Nueva solicitud recibida: {resolved_title}",
            payload={
                "request_id": request.id,
                "priority": resolved_priority,
                "mode": resolved_mode,
                "source": source,
                "channel": channel,
                "domains": inferred_profile.get("domains"),
                "risk_level": inferred_profile.get("risk_level"),
            },
        )

        if auto_dispatch:
            return self.dispatch_request(request.id)

        return {
            "ok": True,
            "duplicate": False,
            "request": self.intake_repository.get_request(request.id),
            "mission_id": None,
        }

    def dispatch_request(self, request_id: str) -> Dict:
        request = self.intake_repository.get_request(request_id)
        if not request:
            raise ValueError("request not found")

        if request.get("mission_id"):
            return {
                "ok": True,
                "duplicate": False,
                "request": request,
                "mission_id": request.get("mission_id"),
            }

        mission_result = self.mission_service.submit_mission(
            title=request["title"],
            goal=request["description"],
            mode=request.get("mode") or "general_operating_request",
            priority=request.get("priority") or "medium",
            source=request.get("source") or "api",
            allow_24x7=True,
            schedule=f"intake:{request.get('channel') or 'api'}",
        )
        mission_id = mission_result["mission_id"]
        self.intake_repository.update_request_status(
            request_id,
            "dispatched",
            mission_id=mission_id,
            details={
                "dispatch_reason": "auto_dispatch",
                "dispatched_by": "intake_service",
            },
        )
        self.mission_repository.add_event(
            mission_id,
            "request_attached",
            request.get("source") or "api",
            f"Mission created from intake request: {request['title']}",
            {
                "request_id": request_id,
                "requested_by": request.get("requested_by"),
                "channel": request.get("channel"),
                "source": request.get("source"),
                "intake_profile": (request.get("details") or {}).get("inferred_profile"),
            },
        )
        if self.agent_state_manager:
            self.agent_state_manager.set_state("agent-0", "planning", mission_id=mission_id)
        self.notifications.enqueue(
            kind="intake_dispatched",
            summary=f"Solicitud enviada al equipo: {request['title']}",
            payload={
                "request_id": request_id,
                "mission_id": mission_id,
                "priority": request.get("priority"),
                "mode": request.get("mode"),
            },
        )
        return {
            "ok": True,
            "duplicate": False,
            "request": self.intake_repository.get_request(request_id),
            "mission_id": mission_id,
        }

    def dispatch_pending_requests(self, limit: int = 5) -> int:
        dispatched = 0
        pending = self.intake_repository.list_requests_by_status(["pending"], limit=limit)
        for request in pending:
            details = request.get("details") or {}
            if details.get("auto_dispatch", True):
                self.dispatch_request(request["id"])
                dispatched += 1
        return dispatched

    def reconcile_requests(self, limit: int = 20) -> int:
        updated = 0
        dispatched = self.intake_repository.list_requests_by_status(["dispatched"], limit=limit)
        for request in dispatched:
            mission_id = request.get("mission_id")
            if not mission_id:
                continue
            mission = self.mission_repository.get_mission(mission_id)
            if not mission:
                continue
            if mission.get("status") == "completed":
                self.intake_repository.update_request_status(
                    request["id"],
                    "resolved",
                    mission_id=mission_id,
                    details={
                        "resolved_by_mission_status": "completed",
                    },
                )
                updated += 1
        return updated
