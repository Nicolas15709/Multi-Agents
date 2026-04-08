from __future__ import annotations

from typing import Dict, Iterable, List, Optional


CORE_AGENT_CAPABILITIES = {
    "agent-0": [
        "planning",
        "scoping",
        "delegation",
        "synthesis",
        "approval",
        "handoff",
    ],
    "agent-1": [
        "research",
        "analysis",
        "context-building",
        "discovery",
        "legal-review",
        "market-research",
    ],
    "agent-2": [
        "strategy",
        "design",
        "structure",
        "artifact-definition",
        "messaging",
        "positioning",
    ],
    "agent-3": [
        "engineering",
        "delivery",
        "build",
        "automation",
        "documentation",
        "communication",
        "outreach",
    ],
    "agent-4": [
        "review",
        "validation",
        "risk-checking",
        "qa",
        "security",
        "compliance",
    ],
}


CAPABILITY_TOOL_MAP = {
    "analysis": ["web-research", "docs-reader"],
    "api": ["api-client", "docs-reader"],
    "approval": ["approval-gate", "task-board"],
    "auth": ["api-client", "code-editor", "docs-reader"],
    "automation": ["workflow-runner", "shell"],
    "brand": ["design-editor", "asset-board"],
    "build": ["code-editor", "shell", "tests"],
    "campaign": ["crm", "email", "content-studio"],
    "communication": ["crm", "email", "chat"],
    "compliance": ["docs-reader", "approval-gate"],
    "context-building": ["web-research", "docs-reader"],
    "database": ["sql-client", "schema-browser"],
    "debugging": ["logs", "tests", "shell"],
    "delivery": ["code-editor", "shell", "tests"],
    "design": ["design-editor", "asset-board"],
    "documentation": ["docs-writer", "docs-reader"],
    "engineering": ["code-editor", "shell", "tests"],
    "external-action": ["crm", "email", "browser-automation"],
    "growth": ["analytics", "content-studio", "crm"],
    "handoff": ["shared-memory", "task-board"],
    "hardening": ["code-editor", "tests", "logs"],
    "legal-review": ["docs-reader", "approval-gate"],
    "market-research": ["web-research", "analytics"],
    "messaging": ["content-studio", "crm"],
    "outreach": ["crm", "email", "browser-automation"],
    "planning": ["task-board", "shared-memory"],
    "positioning": ["analytics", "content-studio", "docs-writer"],
    "qa": ["tests", "browser-automation", "logs"],
    "research": ["web-research", "docs-reader"],
    "review": ["tests", "docs-reader", "approval-gate"],
    "risk-checking": ["approval-gate", "docs-reader"],
    "scoping": ["task-board", "shared-memory"],
    "security": ["tests", "logs", "approval-gate"],
    "seo": ["web-research", "analytics", "content-studio"],
    "strategy": ["task-board", "analytics", "shared-memory"],
    "summary": ["docs-writer", "shared-memory"],
    "synthesis": ["docs-writer", "shared-memory"],
    "ux": ["design-editor", "browser-automation"],
    "validation": ["tests", "approval-gate"],
}


DOMAIN_TOOL_MAP = {
    "design": ["design-editor", "asset-board"],
    "engineering": ["code-editor", "shell", "tests"],
    "legal": ["docs-reader", "approval-gate"],
    "marketing": ["analytics", "content-studio", "crm"],
    "operations": ["workflow-runner", "logs", "task-board"],
    "product": ["analytics", "task-board", "shared-memory"],
    "research": ["web-research", "docs-reader"],
    "sales": ["crm", "email", "browser-automation"],
    "security": ["logs", "approval-gate", "tests"],
    "support": ["chat", "docs-reader", "task-board"],
}


RISK_TOOL_MAP = {
    "external_action": ["approval-gate", "crm", "email"],
    "legal_sensitive": ["approval-gate", "docs-reader"],
    "money_sensitive": ["approval-gate", "crm"],
    "security_sensitive": ["approval-gate", "logs", "tests"],
}


def _dedupe(values: Iterable[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for value in values:
        normalized = str(value or "").strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def normalize_capabilities(values: Optional[Iterable[str]]) -> List[str]:
    return _dedupe(values or [])


def known_core_capabilities() -> List[str]:
    values: List[str] = []
    for capabilities in CORE_AGENT_CAPABILITIES.values():
        values.extend(capabilities)
    return _dedupe(values)


def capabilities_missing_from_core(required_capabilities: Optional[Iterable[str]]) -> List[str]:
    required = normalize_capabilities(required_capabilities)
    covered = set(known_core_capabilities())
    return [capability for capability in required if capability not in covered]


def capabilities_missing_from_agents(required_capabilities: Optional[Iterable[str]], agent_capabilities: Optional[Iterable[str]]) -> List[str]:
    required = normalize_capabilities(required_capabilities)
    covered = set(normalize_capabilities(agent_capabilities))
    return [capability for capability in required if capability not in covered]


def infer_tool_primitives(
    *,
    required_capabilities: Optional[Iterable[str]] = None,
    mission_profile: Optional[Dict] = None,
    workstream: Optional[str] = None,
) -> List[str]:
    mission_profile = mission_profile or {}
    tools: List[str] = ["shared-memory", "task-board"]

    for capability in normalize_capabilities(required_capabilities):
        tools.extend(CAPABILITY_TOOL_MAP.get(capability, []))

    for domain in normalize_capabilities(mission_profile.get("domains") or []):
        tools.extend(DOMAIN_TOOL_MAP.get(domain, []))

    for risk_flag in normalize_capabilities(mission_profile.get("risk_flags") or []):
        tools.extend(RISK_TOOL_MAP.get(risk_flag, []))

    normalized_workstream = str(workstream or "").strip().lower()
    if normalized_workstream in {"external-action", "outreach", "publish"}:
        tools.extend(["approval-gate", "crm", "email", "browser-automation"])
    elif normalized_workstream in {"documentation", "closeout"}:
        tools.extend(["docs-writer"])
    elif normalized_workstream in {"delivery", "engineering", "build"}:
        tools.extend(["code-editor", "tests", "shell"])

    return _dedupe(tools)


def infer_approval_policy(
    *,
    mission_profile: Optional[Dict] = None,
    workstream: Optional[str] = None,
    required_capabilities: Optional[Iterable[str]] = None,
) -> str:
    mission_profile = mission_profile or {}
    risk_flags = set(normalize_capabilities(mission_profile.get("risk_flags") or []))
    capabilities = set(normalize_capabilities(required_capabilities))
    normalized_workstream = str(workstream or "").strip().lower()

    if normalized_workstream in {"external-action", "outreach", "publish"} or "external-action" in capabilities:
        return "per_action_approval"
    if normalized_workstream in {"closeout", "documentation", "review"} and {"legal_sensitive", "money_sensitive"} & risk_flags:
        return "per_action_approval"
    if normalized_workstream in {"review", "delivery", "build"} and "security_sensitive" in risk_flags:
        return "conditional"
    return "auto_allowed"


def infer_external_action_kind(
    *,
    mission_profile: Optional[Dict] = None,
    workstream: Optional[str] = None,
    required_capabilities: Optional[Iterable[str]] = None,
) -> Optional[str]:
    mission_profile = mission_profile or {}
    risk_flags = set(normalize_capabilities(mission_profile.get("risk_flags") or []))
    capabilities = set(normalize_capabilities(required_capabilities))
    normalized_workstream = str(workstream or "").strip().lower()

    if normalized_workstream in {"external-action", "outreach"} or {"communication", "outreach", "external-action"} & capabilities:
        return "outreach"
    if normalized_workstream == "publish":
        return "publish"
    if normalized_workstream in {"closeout", "documentation", "review"} and "legal_sensitive" in risk_flags:
        return "legal_release"
    if normalized_workstream in {"closeout", "documentation", "review"} and "money_sensitive" in risk_flags:
        return "financial_commitment"
    return None
