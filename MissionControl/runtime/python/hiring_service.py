from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

try:
    from .capability_router import capabilities_missing_from_agents, infer_approval_policy, infer_external_action_kind, infer_tool_primitives
    from .models import AgentHireRequestRecord, AgentRecord, Task
    from .repository import AgentHireRequestRepository, AgentRepository, MissionControlRepository, MissionRepository, TaskRepository
    from .specialist_templates import SpecialistTemplateCatalog
    from .templates import TemplateRegistry
    from .utils import new_id
except ImportError:  # pragma: no cover - runtime script compatibility
    from capability_router import capabilities_missing_from_agents, infer_approval_policy, infer_external_action_kind, infer_tool_primitives
    from models import AgentHireRequestRecord, AgentRecord, Task
    from repository import AgentHireRequestRepository, AgentRepository, MissionControlRepository, MissionRepository, TaskRepository
    from specialist_templates import SpecialistTemplateCatalog
    from templates import TemplateRegistry
    from utils import new_id


def _normalize_capabilities(value: Optional[List[str] | str]) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _normalize_words(value: str) -> str:
    return (value or "").strip().lower()


def _extract_search_tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9][a-z0-9+#./-]*", (value or "").lower()))


def _dedupe(values: List[str]) -> List[str]:
    seen = set()
    result = []
    for value in values:
        normalized = _normalize_words(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(value)
    return result


DEFAULT_HIRE_SUGGESTIONS = [
    {
        "display_name": "Frontend Specialist",
        "role": "frontend-specialist",
        "personality": "Sharp on UI polish, responsive fixes, and component architecture.",
        "capabilities": ["react", "ui", "responsive-design", "debugging"],
        "notes": "Take ownership of client-side fixes and polish.",
    },
    {
        "display_name": "Backend Specialist",
        "role": "backend-specialist",
        "personality": "Pragmatic on APIs, persistence, and reliability.",
        "capabilities": ["api", "database", "auth", "debugging", "tests"],
        "notes": "Own backend logic, data paths, and service correctness.",
    },
    {
        "display_name": "Docs Specialist",
        "role": "docs-specialist",
        "personality": "Systematic, concise, and strong at translating implementation into usable docs.",
        "capabilities": ["documentation", "readme", "guides"],
        "notes": "Document the new flow and operational decisions.",
    },
    {
        "display_name": "Security Specialist",
        "role": "security-specialist",
        "personality": "Suspicious, methodical, and focused on hardening risky paths.",
        "capabilities": ["security", "auth", "hardening", "review"],
        "notes": "Review security-sensitive paths and reduce obvious exploit risk.",
    },
]


DIVISION_HINTS_BY_CATEGORY = {
    "development": ["engineering", "testing", "design", "product", "project-management"],
    "security": ["engineering", "testing", "support"],
    "marketing": ["marketing", "paid-media", "design", "sales", "strategy"],
    "business": ["strategy", "sales", "project-management", "product", "marketing"],
    "research": ["strategy", "product", "academic", "support"],
    "operations": ["project-management", "support", "engineering", "testing"],
}

TEMPLATE_HINTS_BY_TOKEN = {
    "frontend": ["engineering-frontend-developer", "design-ui-designer"],
    "backend": ["engineering-backend-architect", "engineering-database-optimizer"],
    "api": ["engineering-backend-architect", "testing-api-tester"],
    "dashboard": ["engineering-frontend-developer", "design-ui-designer"],
    "bug": ["engineering-code-reviewer", "testing-reality-checker"],
    "auth": ["engineering-security-engineer", "engineering-backend-architect"],
    "security": ["engineering-security-engineer", "testing-reality-checker"],
    "docs": ["engineering-technical-writer"],
    "documentation": ["engineering-technical-writer"],
    "qa": ["testing-api-tester", "testing-reality-checker"],
    "test": ["testing-api-tester", "testing-performance-benchmarker"],
    "testing": ["testing-api-tester", "testing-reality-checker"],
    "marketing": ["marketing-growth-hacker", "marketing-social-media-strategist", "marketing-content-creator"],
    "campaign": ["marketing-growth-hacker", "marketing-social-media-strategist", "paid-media-ppc-strategist"],
    "content": ["marketing-content-creator", "marketing-linkedin-content-creator", "marketing-book-co-author"],
    "seo": ["marketing-seo-specialist", "marketing-ai-citation-strategist", "marketing-baidu-seo-specialist"],
    "social": ["marketing-social-media-strategist", "marketing-linkedin-content-creator", "marketing-twitter-engager"],
    "linkedin": ["marketing-linkedin-content-creator", "marketing-social-media-strategist"],
    "twitter": ["marketing-twitter-engager", "marketing-social-media-strategist"],
    "tiktok": ["marketing-tiktok-strategist", "marketing-carousel-growth-engine"],
    "instagram": ["marketing-instagram-curator", "marketing-carousel-growth-engine"],
    "brand": ["design-brand-guardian", "marketing-social-media-strategist"],
    "sales": ["sales-outbound-strategist", "sales-deal-strategist", "sales-proposal-strategist"],
    "pipeline": ["sales-pipeline-analyst", "sales-outbound-strategist"],
    "proposal": ["sales-proposal-strategist", "sales-deal-strategist"],
    "project": ["project-manager-senior", "project-management-project-shepherd"],
    "manager": ["project-manager-senior", "product-manager"],
    "product": ["product-manager", "product-sprint-prioritizer", "product-trend-researcher"],
    "feedback": ["product-feedback-synthesizer", "design-ux-researcher"],
    "support": ["support-support-responder", "support-infrastructure-maintainer"],
    "analytics": ["support-analytics-reporter", "sales-pipeline-analyst"],
    "data": ["engineering-data-engineer", "engineering-database-optimizer"],
    "mobile": ["engineering-mobile-app-builder"],
    "devops": ["engineering-devops-automator", "engineering-sre"],
    "sre": ["engineering-sre", "engineering-devops-automator"],
    "ai": ["engineering-ai-engineer", "engineering-autonomous-optimization-architect"],
    "design": ["design-ui-designer", "design-ux-researcher", "design-brand-guardian"],
    "ux": ["design-ux-researcher", "design-ux-architect"],
}


@dataclass
class HiringService:
    mission_repository: MissionRepository
    task_repository: TaskRepository
    agent_repository: AgentRepository
    hire_request_repository: AgentHireRequestRepository
    mission_control_repository: Optional[MissionControlRepository] = None
    approvals_enabled: bool = False
    template_registry: Optional[TemplateRegistry] = None
    specialist_template_catalog: Optional[SpecialistTemplateCatalog] = None

    def _mission_control(self, mission_id: str) -> Optional[Dict]:
        if not self.mission_control_repository:
            return None
        return self.mission_control_repository.get_control(mission_id)

    def list_available_templates(
        self,
        *,
        division: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 80,
    ) -> List[Dict]:
        if not self.specialist_template_catalog:
            return []
        return self.specialist_template_catalog.list_templates(division=division, query=query, limit=limit)

    def get_template(self, template_id: Optional[str]) -> Optional[Dict]:
        if not template_id or not self.specialist_template_catalog:
            return None
        return self.specialist_template_catalog.get_template(template_id)

    def _mission_template(self, mission: Dict) -> Dict:
        if not self.template_registry:
            return {}
        try:
            return self.template_registry.get_template(mission.get("mode") or "")
        except KeyError:
            return {}

    def _preferred_divisions_for_mission(self, mission: Dict) -> List[str]:
        template = self._mission_template(mission)
        hinted_divisions = list(template.get("preferredDivisions") or [])
        category = template.get("category")
        if category:
            hinted_divisions.extend(DIVISION_HINTS_BY_CATEGORY.get(category, []))

        text_tokens = _extract_search_tokens(f"{mission.get('title') or ''}\n{mission.get('goal') or ''}\n{mission.get('mode') or ''}")
        if text_tokens.intersection({"marketing", "campaign", "social", "seo", "brand", "content"}):
            hinted_divisions.extend(["marketing", "paid-media", "design"])
        if text_tokens.intersection({"sales", "pipeline", "proposal", "outbound"}):
            hinted_divisions.extend(["sales", "marketing", "strategy"])
        if text_tokens.intersection({"project", "timeline", "scope", "roadmap"}):
            hinted_divisions.extend(["project-management", "product"])
        if text_tokens.intersection({"support", "incident", "operations"}):
            hinted_divisions.extend(["support", "project-management", "engineering"])
        if text_tokens.intersection({"frontend", "backend", "api", "mobile", "auth", "bug", "ui"}):
            hinted_divisions.extend(["engineering", "testing", "design"])
        return _dedupe(hinted_divisions)

    def _preferred_template_ids_for_mission(self, mission: Dict) -> List[str]:
        template = self._mission_template(mission)
        hints = list(template.get("defaultSpecialistTemplates") or [])
        text_tokens = _extract_search_tokens(f"{mission.get('title') or ''}\n{mission.get('goal') or ''}\n{mission.get('mode') or ''}")
        for token, template_ids in TEMPLATE_HINTS_BY_TOKEN.items():
            if token in text_tokens:
                hints.extend(template_ids)
        return _dedupe(hints)

    def _fallback_suggestions_from_text(self, text: str) -> List[Dict]:
        suggestions: List[Dict] = []
        text_tokens = _extract_search_tokens(text)
        if text_tokens.intersection({"ui", "frontend", "dashboard", "responsive", "design"}):
            suggestions.append(DEFAULT_HIRE_SUGGESTIONS[0])
        if text_tokens.intersection({"api", "backend", "db", "database", "auth", "bug", "error", "integration"}):
            suggestions.append(DEFAULT_HIRE_SUGGESTIONS[1])
        if text_tokens.intersection({"docs", "documentation", "guide", "readme"}):
            suggestions.append(DEFAULT_HIRE_SUGGESTIONS[2])
        if text_tokens.intersection({"security", "hardening", "vulnerability", "auth"}):
            suggestions.append(DEFAULT_HIRE_SUGGESTIONS[3])
        return suggestions or DEFAULT_HIRE_SUGGESTIONS[:2]

    def _template_to_suggestion(self, template: Dict) -> Dict:
        return {
            "template_id": template["id"],
            "display_name": template["display_name"],
            "role": template["role"],
            "personality": template.get("personality") or template.get("description"),
            "capabilities": list(template.get("capabilities") or template.get("tools") or []),
            "notes": template.get("description") or template.get("vibe"),
            "division": template.get("division"),
            "division_label": template.get("division_label"),
            "description": template.get("description"),
            "emoji": template.get("emoji"),
            "color": template.get("color"),
            "vibe": template.get("vibe"),
            "source_path": template.get("source_path"),
        }

    def _task_plan_hints_for_mission(self, mission_id: str) -> Dict:
        preferred_divisions: List[str] = []
        preferred_template_ids: List[str] = []
        required_capabilities: List[str] = []
        workstreams: List[str] = []

        for task in self.task_repository.list_tasks_for_mission(mission_id):
            details = task.get("details") or {}
            preferred_divisions.extend(details.get("preferred_divisions") or [])
            preferred_template_ids.extend(details.get("specialist_template_hints") or [])
            required_capabilities.extend(details.get("required_capabilities") or [])
            workstream = details.get("workstream")
            if workstream:
                workstreams.append(workstream)

        return {
            "preferred_divisions": _dedupe(preferred_divisions),
            "preferred_template_ids": _dedupe(preferred_template_ids),
            "required_capabilities": _dedupe(required_capabilities),
            "workstreams": _dedupe(workstreams),
        }

    def _capability_gaps_for_mission(self, mission_id: str, required_capabilities: List[str]) -> List[str]:
        agents = self.agent_repository.list_agents()
        covered_capabilities: List[str] = []
        for agent in agents:
            if agent.get("mission_scope_id") not in {None, mission_id}:
                continue
            covered_capabilities.extend(agent.get("capabilities") or [])
        return capabilities_missing_from_agents(required_capabilities, covered_capabilities)

    def _templates_for_capability_gaps(
        self,
        mission: Dict,
        *,
        preferred_divisions: List[str],
        preferred_template_ids: List[str],
        missing_capabilities: List[str],
        limit: int = 6,
    ) -> List[Dict]:
        if not self.specialist_template_catalog or not self.specialist_template_catalog.templates:
            return []

        mission_blob = " ".join(
            [
                str(mission.get("title") or ""),
                str(mission.get("goal") or ""),
                str(mission.get("mode") or ""),
                " ".join(missing_capabilities),
            ]
        ).lower()
        mission_tokens = _extract_search_tokens(mission_blob)

        ranked: List[tuple[int, Dict]] = []
        for template in self.specialist_template_catalog.templates:
            overlap = mission_tokens.intersection(_extract_search_tokens(" ".join(template.get("capabilities") or [])))
            score = len(overlap) * 8
            if template.get("division") in preferred_divisions:
                score += 18
            if template.get("id") in preferred_template_ids:
                score += 24
            if score <= 0:
                continue
            ranked.append((score, template))

        ranked.sort(key=lambda item: (-item[0], item[1]["display_name"].lower()))
        return [dict(item[1]) for item in ranked[: max(1, limit)]]

    def suggest_subagents_for_mission(self, mission_id: str) -> List[Dict]:
        mission = self.mission_repository.get_mission(mission_id)
        if not mission:
            raise ValueError("mission not found")

        text = f"{mission.get('title') or ''}\n{mission.get('goal') or ''}\n{mission.get('mode') or ''}".lower()
        suggestions: List[Dict]
        task_hints = self._task_plan_hints_for_mission(mission_id)
        preferred_divisions = _dedupe(
            [
                *task_hints.get("preferred_divisions", []),
                *self._preferred_divisions_for_mission(mission),
            ]
        )
        preferred_template_ids = _dedupe(
            [
                *task_hints.get("preferred_template_ids", []),
                *self._preferred_template_ids_for_mission(mission),
            ]
        )
        missing_capabilities = self._capability_gaps_for_mission(
            mission_id,
            task_hints.get("required_capabilities", []),
        )

        if self.specialist_template_catalog and self.specialist_template_catalog.templates:
            templates = []
            if missing_capabilities:
                templates.extend(
                    self._templates_for_capability_gaps(
                        mission,
                        preferred_divisions=preferred_divisions,
                        preferred_template_ids=preferred_template_ids,
                        missing_capabilities=missing_capabilities,
                        limit=6,
                    )
                )
            templates.extend(
                self.specialist_template_catalog.suggest_for_mission(
                    mission,
                    preferred_divisions=preferred_divisions,
                    preferred_template_ids=preferred_template_ids,
                    limit=6,
                )
            )
            deduped_templates = []
            seen_template_ids = set()
            for item in templates:
                if item["id"] in seen_template_ids:
                    continue
                seen_template_ids.add(item["id"])
                deduped_templates.append(item)
            templates = deduped_templates[:6]
            suggestions = []
            for item in templates:
                suggestion = self._template_to_suggestion(item)
                suggestion["required_capabilities"] = task_hints.get("required_capabilities", [])
                suggestion_blob = " ".join(
                    [
                        suggestion.get("display_name") or "",
                        suggestion.get("role") or "",
                        suggestion.get("description") or "",
                        " ".join(suggestion.get("capabilities") or []),
                    ]
                )
                suggestion_tokens = _extract_search_tokens(suggestion_blob)
                suggestion["gap_capabilities"] = [
                    capability
                    for capability in missing_capabilities
                    if capability.lower() in suggestion_tokens
                    or any(token in suggestion_tokens for token in _extract_search_tokens(capability))
                ]
                suggestion["workstreams"] = task_hints.get("workstreams", [])
                if suggestion.get("workstreams"):
                    suggestion["notes"] = (
                        f"{suggestion.get('notes') or 'Support the mission'} "
                        f"Priority workstreams: {', '.join(suggestion['workstreams'][:3])}."
                    ).strip()
                if suggestion.get("gap_capabilities"):
                    suggestion["notes"] = (
                        f"{suggestion.get('notes') or 'Support the mission'} "
                        f"Close capability gaps: {', '.join(suggestion['gap_capabilities'][:4])}."
                    ).strip()
                suggestions.append(suggestion)
        else:
            suggestions = list(self._fallback_suggestions_from_text(text))

        existing = self.list_requests_for_mission(mission_id)
        existing_keys = {
            (_normalize_words(item.get("display_name") or ""), _normalize_words(item.get("role") or ""))
            for item in existing
        }
        return [
            suggestion
            for suggestion in suggestions
            if (_normalize_words(suggestion["display_name"]), _normalize_words(suggestion["role"])) not in existing_keys
        ]

    def list_requests_for_mission(self, mission_id: str) -> List[Dict]:
        return self.hire_request_repository.list_requests_for_mission(mission_id)

    def request_subagent(
        self,
        *,
        mission_id: str,
        display_name: str,
        role: str,
        personality: Optional[str] = None,
        capabilities: Optional[List[str] | str] = None,
        requested_by_agent_id: Optional[str] = "agent-0",
        reports_to: Optional[str] = "agent-0",
        budget_monthly_cents: int = 0,
        notes: Optional[str] = None,
        force_status: Optional[str] = None,
        template_id: Optional[str] = None,
        metadata_extra: Optional[Dict] = None,
    ) -> Dict:
        mission = self.mission_repository.get_mission(mission_id)
        if not mission:
            raise ValueError("mission not found")

        template = self.get_template(template_id)
        resolved_name = (display_name or "").strip() or (template.get("display_name") if template else "") or "Specialist"
        resolved_role = (role or "").strip() or (template.get("role") if template else "") or "specialist"
        duplicate = self.hire_request_repository.find_active_request_for_mission(
            mission_id,
            resolved_name,
            resolved_role,
        )
        if duplicate:
            return {
                "ok": True,
                "duplicate": True,
                "hire_request_id": duplicate["id"],
                "agent_id": duplicate.get("hired_agent_id"),
                "status": duplicate.get("status"),
                "template_id": duplicate.get("metadata", {}).get("template_id"),
            }

        capabilities_list = _normalize_capabilities(capabilities)
        if not capabilities_list and template:
            capabilities_list = list(template.get("capabilities") or [])
        resolved_personality = (personality or "").strip() or (template.get("personality") if template else None) or (template.get("description") if template else None)
        resolved_notes = (notes or "").strip() or (template.get("description") if template else None) or None
        metadata = {
            "template_id": template.get("id") if template else None,
            "template_division": template.get("division") if template else None,
            "template_division_label": template.get("division_label") if template else None,
            "template_source": template.get("source_repo") if template else None,
            "template_source_path": template.get("source_path") if template else None,
            "template_emoji": template.get("emoji") if template else None,
            "template_color": template.get("color") if template else None,
        }
        metadata = {key: value for key, value in metadata.items() if value}
        if metadata_extra:
            metadata.update({key: value for key, value in metadata_extra.items() if value is not None})

        status = force_status or ("pending" if self.approvals_enabled else "approved")
        hire_request = AgentHireRequestRecord(
            id=new_id("hire"),
            mission_id=mission_id,
            requested_by_agent_id=requested_by_agent_id,
            display_name=resolved_name,
            role=resolved_role,
            personality=resolved_personality,
            capabilities=capabilities_list,
            budget_monthly_cents=max(0, int(budget_monthly_cents or 0)),
            reports_to=reports_to,
            notes=resolved_notes,
            status=status,
            metadata=metadata,
        )
        self.hire_request_repository.create_request(hire_request)
        self.mission_repository.add_event(
            mission_id,
            "subagent_requested",
            requested_by_agent_id or "system",
            f"Subagent request created: {hire_request.display_name}",
            {
                "hire_request_id": hire_request.id,
                "role": hire_request.role,
                "reports_to": reports_to,
                "capabilities": capabilities_list,
                "status": status,
                "template_id": metadata.get("template_id"),
                "template_division": metadata.get("template_division"),
            },
        )
        return {
            "ok": True,
            "duplicate": False,
            "hire_request_id": hire_request.id,
            "status": status,
            "agent_id": None,
            "task_id": None,
            "template_id": metadata.get("template_id"),
        }

    def approve_hire_request(
        self,
        hire_request_id: str,
        *,
        create_task: bool = True,
        task_title: Optional[str] = None,
    ) -> Dict:
        hire_request = self.hire_request_repository.get_request(hire_request_id)
        if not hire_request:
            raise ValueError("hire request not found")
        if hire_request.get("status") == "hired":
            return {
                "ok": True,
                "hire_request_id": hire_request_id,
                "agent_id": hire_request.get("hired_agent_id"),
                "task_id": None,
                "template_id": hire_request.get("metadata", {}).get("template_id"),
            }
        if hire_request.get("status") not in {"pending", "approved"}:
            raise ValueError("hire request is not approvable")

        mission_id = hire_request["mission_id"]
        mission = self.mission_repository.get_mission(mission_id)
        if not mission:
            raise ValueError("mission not found")
        control = self._mission_control(mission_id)
        if control and int(control.get("dynamic_hires_used", 0) or 0) >= int(control.get("max_dynamic_hires", 0) or 0):
            raise ValueError("dynamic hire budget exhausted for mission")
        capabilities_list = _normalize_capabilities(hire_request.get("capabilities"))
        request_metadata = dict(hire_request.get("metadata") or {})

        agent_id = new_id("agent")
        agent = AgentRecord(
            agent_id=agent_id,
            display_name=hire_request["display_name"],
            role=hire_request["role"],
            personality=hire_request.get("personality"),
            reports_to=hire_request.get("reports_to"),
            capabilities=capabilities_list,
            budget_monthly_cents=max(0, int(hire_request.get("budget_monthly_cents") or 0)),
            origin="mission_hire",
            mission_scope_id=mission_id,
            metadata={
                **request_metadata,
                "hire_request_id": hire_request_id,
                "notes": hire_request.get("notes"),
                "hired_for_mission": mission_id,
            },
        )
        self.agent_repository.upsert_agent(agent)
        self.hire_request_repository.update_request(hire_request_id, status="hired", hired_agent_id=agent_id)
        if self.mission_control_repository:
            self.mission_control_repository.increment_usage(mission_id, dynamic_hires_used=1)

        created_task = None
        if create_task:
            created_task = self._attach_specialist_task(
                mission=mission,
                agent=agent,
                notes=hire_request.get("notes"),
                task_title=task_title,
            )

        self.mission_repository.add_event(
            mission_id,
            "subagent_hired",
            hire_request.get("requested_by_agent_id") or "system",
            f"Subagent hired for mission: {agent.display_name}",
            {
                "hire_request_id": hire_request_id,
                "agent_id": agent_id,
                "role": agent.role,
                "reports_to": hire_request.get("reports_to"),
                "capabilities": capabilities_list,
                "task_id": created_task["id"] if created_task else None,
                "template_id": request_metadata.get("template_id"),
                "template_division": request_metadata.get("template_division"),
            },
        )
        return {
            "ok": True,
            "hire_request_id": hire_request_id,
            "agent_id": agent_id,
            "task_id": created_task["id"] if created_task else None,
            "template_id": request_metadata.get("template_id"),
        }

    def hire_subagent(
        self,
        *,
        mission_id: str,
        display_name: str,
        role: str,
        personality: Optional[str] = None,
        capabilities: Optional[List[str] | str] = None,
        requested_by_agent_id: Optional[str] = "agent-0",
        reports_to: Optional[str] = "agent-0",
        budget_monthly_cents: int = 0,
        notes: Optional[str] = None,
        create_task: bool = True,
        task_title: Optional[str] = None,
        template_id: Optional[str] = None,
    ) -> Dict:
        request_result = self.request_subagent(
            mission_id=mission_id,
            display_name=display_name,
            role=role,
            personality=personality,
            capabilities=capabilities,
            requested_by_agent_id=requested_by_agent_id,
            reports_to=reports_to,
            budget_monthly_cents=budget_monthly_cents,
            notes=notes,
            template_id=template_id,
        )
        if request_result.get("duplicate"):
            return request_result
        if self.approvals_enabled:
            return request_result
        return self.approve_hire_request(
            request_result["hire_request_id"],
            create_task=create_task,
            task_title=task_title,
        )

    def seed_suggested_requests_for_mission(
        self,
        mission_id: str,
        *,
        requested_by_agent_id: Optional[str] = "agent-0",
        reports_to: Optional[str] = "agent-0",
        force_pending: bool = True,
    ) -> Dict:
        created_request_ids: List[str] = []
        duplicate_request_ids: List[str] = []
        suggestions = self.suggest_subagents_for_mission(mission_id)
        for suggestion in suggestions[:3]:
            result = self.request_subagent(
                mission_id=mission_id,
                display_name=suggestion["display_name"],
                role=suggestion["role"],
                personality=suggestion.get("personality"),
                capabilities=suggestion.get("capabilities"),
                requested_by_agent_id=requested_by_agent_id,
                reports_to=reports_to,
                notes=suggestion.get("notes"),
                force_status="pending" if force_pending else None,
                template_id=suggestion.get("template_id"),
                metadata_extra={
                    "workstreams": suggestion.get("workstreams"),
                    "required_capabilities": suggestion.get("required_capabilities"),
                    "gap_capabilities": suggestion.get("gap_capabilities"),
                    "task_title": (
                        f"Specialist execution: {suggestion['display_name']} for "
                        f"{', '.join((suggestion.get('workstreams') or ['mission support'])[:2])}"
                    ),
                },
            )
            if result.get("duplicate"):
                duplicate_request_ids.append(result["hire_request_id"])
            else:
                created_request_ids.append(result["hire_request_id"])
        return {
            "ok": True,
            "created": len(created_request_ids),
            "duplicates": len(duplicate_request_ids),
            "request_ids": created_request_ids,
            "duplicate_request_ids": duplicate_request_ids,
        }

    def _attach_specialist_task(self, *, mission: Dict, agent: AgentRecord, notes: Optional[str], task_title: Optional[str]) -> Optional[Dict]:
        tasks = self.task_repository.list_tasks_for_mission(mission["id"])
        kickoff = next((task for task in tasks if task.get("details", {}).get("phase_kind") == "lead_plan"), None)
        review = next((task for task in tasks if task.get("details", {}).get("phase_kind") == "review"), None)
        closeout = next((task for task in tasks if task.get("details", {}).get("phase_kind") == "lead_closeout"), None)
        task_metadata = dict(agent.metadata or {})

        depends_on = [kickoff["id"]] if kickoff else []
        specialist_task = Task(
            id=new_id("task"),
            mission_id=mission["id"],
            agent_id=agent.agent_id,
            title=task_title or task_metadata.get("task_title") or f"Specialist execution: {agent.display_name}",
            priority=mission["priority"],
            depends_on=depends_on,
            details={
                "mode": mission["mode"],
                "workflow_version": "open_capability_graph_v1+dynamic_hires+templates",
                "phase_kind": "specialist_hire",
                "phase_label": "Specialist Hire",
                "team_role": "specialist",
                "owner_agent_id": agent.agent_id,
                "specialist_display_name": agent.display_name,
                "template_id": agent.metadata.get("template_id"),
                "template_division": agent.metadata.get("template_division"),
                "workstream": ", ".join(task_metadata.get("workstreams") or []) or "specialist-delivery",
                "acceptance_criteria": [
                    "Subagent delivers specialist output for the mission scope",
                    "Output is usable by review and lead closeout",
                ],
                "guardrails": {
                    "max_retries": 1,
                    "escalate_on_failure": True,
                    "prevent_infinite_retry": True,
                },
                "hire_notes": notes,
                "capabilities": list(agent.capabilities or []),
                "required_capabilities": list(task_metadata.get("required_capabilities") or list(agent.capabilities or [])),
                "gap_capabilities": list(task_metadata.get("gap_capabilities") or []),
                "tool_primitives": infer_tool_primitives(
                    required_capabilities=task_metadata.get("required_capabilities") or list(agent.capabilities or []),
                    mission_profile={"domains": [mission.get("mode")], "risk_flags": []},
                    workstream=", ".join(task_metadata.get("workstreams") or []) or "specialist-delivery",
                ),
                "approval_policy": infer_approval_policy(
                    mission_profile={"domains": [mission.get("mode")], "risk_flags": []},
                    workstream=", ".join(task_metadata.get("workstreams") or []) or "specialist-delivery",
                    required_capabilities=task_metadata.get("required_capabilities") or list(agent.capabilities or []),
                ),
                "external_action_kind": infer_external_action_kind(
                    mission_profile={"domains": [mission.get("mode")], "risk_flags": []},
                    workstream=", ".join(task_metadata.get("workstreams") or []) or "specialist-delivery",
                    required_capabilities=task_metadata.get("required_capabilities") or list(agent.capabilities or []),
                ),
            },
        )
        self.task_repository.create_task(specialist_task)

        for dependent_task in [review, closeout]:
            if not dependent_task:
                continue
            deps = list(dependent_task.get("depends_on") or [])
            if specialist_task.id not in deps:
                deps.append(specialist_task.id)
                self.task_repository.update_task_dependencies(dependent_task["id"], deps)
                details = dict(dependent_task.get("details") or {})
                handoff = dict(details.get("handoff") or {})
                handoff["depends_on"] = deps
                details["handoff"] = handoff
                details["workflow_version"] = "open_capability_graph_v1+dynamic_hires+templates"
                self.task_repository.update_task_details(dependent_task["id"], details)

        return self.task_repository.get_task(specialist_task.id)
