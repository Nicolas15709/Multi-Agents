from __future__ import annotations

import re
from typing import Dict, List, Optional

try:
    from .capability_router import infer_approval_policy, infer_external_action_kind, infer_tool_primitives
except ImportError:  # pragma: no cover - runtime script compatibility
    from capability_router import infer_approval_policy, infer_external_action_kind, infer_tool_primitives


TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#./-]*", re.IGNORECASE)


DOMAIN_KEYWORDS = {
    "engineering": {
        "api", "backend", "frontend", "database", "bug", "fix", "debug", "code",
        "deploy", "integration", "app", "website", "web", "automation", "script",
        "checkout", "login", "auth", "dashboard", "build", "ship",
    },
    "design": {
        "design", "ui", "ux", "brand", "landing", "prototype", "visual",
        "creative", "figma", "layout", "presentation", "experience",
    },
    "marketing": {
        "marketing", "campaign", "seo", "social", "growth", "content", "launch",
        "brand", "copy", "ads", "email", "instagram", "tiktok", "linkedin",
    },
    "sales": {
        "sales", "outreach", "lead", "prospect", "pipeline", "offer", "proposal",
        "deal", "close", "pitch", "contact", "client", "crm", "followup",
    },
    "legal": {
        "legal", "juridico", "juridica", "contract", "clause", "policy", "privacy",
        "terms", "compliance", "regulation", "regulatory", "agreement",
    },
    "operations": {
        "ops", "operations", "incident", "maintenance", "monitoring", "runbook",
        "process", "workflow", "system", "maintenance_cycle", "automation",
    },
    "support": {
        "support", "ticket", "customer", "reply", "respond", "helpdesk", "issue",
        "faq", "triage", "incident",
    },
    "research": {
        "research", "investigate", "analysis", "analyze", "audit", "compare",
        "study", "discovery", "benchmark", "market", "explore",
    },
    "product": {
        "product", "roadmap", "requirements", "scope", "spec", "feature",
        "prioritize", "prioritization", "feedback", "positioning",
    },
    "security": {
        "security", "vulnerability", "attack", "xss", "sql", "hardening",
        "threat", "breach", "auth", "permissions", "policy",
    },
}


INTENT_RULES = {
    "research": {"research", "investigate", "analyze", "audit", "compare", "study", "discover"},
    "plan": {"plan", "strategy", "roadmap", "scope", "prioritize", "offer", "proposal"},
    "design": {"design", "ui", "ux", "brand", "prototype", "layout", "experience"},
    "build": {"build", "create", "implement", "fix", "ship", "deploy", "automate", "integrate"},
    "report": {"report", "summary", "brief", "documentation", "docs", "readme", "deck"},
    "outreach": {"outreach", "contact", "email", "dm", "pitch", "followup", "proposal", "call"},
    "publish": {"publish", "post", "schedule", "campaign", "launch"},
    "review": {"review", "validate", "check", "qa", "harden", "approve"},
}


OUTCOME_RULES = {
    "working_solution": {"build", "create", "implement", "fix", "deploy", "automate", "integrate"},
    "strategy_pack": {"plan", "strategy", "roadmap", "offer", "proposal", "positioning"},
    "design_assets": {"design", "brand", "landing", "prototype", "presentation", "content"},
    "report_pack": {"report", "summary", "analysis", "audit", "documentation", "readme", "brief"},
    "outreach_assets": {"outreach", "contact", "email", "dm", "pitch", "followup"},
}


RISK_KEYWORDS = {
    "external_action": {"outreach", "contact", "email", "dm", "pitch", "publish", "post", "schedule"},
    "legal_sensitive": {"legal", "contract", "policy", "privacy", "terms", "compliance"},
    "security_sensitive": {"security", "auth", "xss", "sql", "breach", "hardening", "permissions"},
    "money_sensitive": {"payment", "invoice", "charge", "pricing", "close", "deal"},
}


DIVISIONS_BY_DOMAIN = {
    "engineering": ["engineering", "testing", "product"],
    "design": ["design", "product", "marketing"],
    "marketing": ["marketing", "paid-media", "design", "strategy"],
    "sales": ["sales", "strategy", "marketing"],
    "legal": ["support", "strategy", "project-management"],
    "operations": ["support", "project-management", "engineering"],
    "support": ["support", "project-management"],
    "research": ["strategy", "product", "support"],
    "product": ["product", "project-management", "design"],
    "security": ["engineering", "testing", "support"],
    "general": ["strategy", "project-management", "engineering", "support"],
}


TEMPLATES_BY_DOMAIN = {
    "engineering": [
        "engineering-frontend-developer",
        "engineering-backend-architect",
        "engineering-devops-automator",
    ],
    "design": [
        "design-ui-designer",
        "design-ux-researcher",
        "design-brand-guardian",
    ],
    "marketing": [
        "marketing-growth-hacker",
        "marketing-social-media-strategist",
        "marketing-content-creator",
    ],
    "sales": [
        "sales-outbound-strategist",
        "sales-proposal-strategist",
        "sales-deal-strategist",
    ],
    "legal": [
        "support-legal-compliance-checker",
        "support-executive-summary-generator",
    ],
    "operations": [
        "support-infrastructure-maintainer",
        "project-manager-senior",
        "engineering-sre",
    ],
    "support": [
        "support-support-responder",
        "support-executive-summary-generator",
    ],
    "research": [
        "product-trend-researcher",
        "support-analytics-reporter",
        "design-ux-researcher",
    ],
    "product": [
        "product-manager",
        "product-sprint-prioritizer",
    ],
    "security": [
        "engineering-security-engineer",
        "testing-reality-checker",
    ],
    "general": [
        "project-manager-senior",
        "testing-reality-checker",
    ],
}


TITLE_BY_DOMAIN = {
    "engineering": "Produce the working technical solution and implementation artifacts",
    "design": "Produce the design system, assets, and user-facing structure",
    "marketing": "Produce campaign, content, and growth-ready deliverables",
    "sales": "Produce outreach, offer, and closing-ready deliverables",
    "legal": "Draft the legal analysis pack and decision-ready materials",
    "operations": "Produce the operating workflow, automation, and process deliverables",
    "support": "Produce support materials, responses, and operational fixes",
    "research": "Package the findings and decision-ready research materials",
    "product": "Produce the product plan, prioritization, and decision artifacts",
    "security": "Produce hardening changes and security decision artifacts",
    "general": "Produce the requested deliverables and execution artifacts",
}


STRATEGY_TITLE_BY_DOMAIN = {
    "marketing": "Design the go-to-market and growth strategy",
    "sales": "Design the offer, positioning, and outreach strategy",
    "legal": "Define the legal review scope, constraints, and decision framework",
    "operations": "Design the operating model, sequencing, and constraints",
    "product": "Design the product strategy and execution blueprint",
    "general": "Design the execution strategy and delivery blueprint",
}


DESIGN_TITLE_BY_DOMAIN = {
    "design": "Design the user-facing structure, UX, and creative system",
    "marketing": "Design the messaging, content structure, and brand-facing assets",
    "sales": "Design the proposal structure and persuasion assets",
    "general": "Design the structure and artifacts needed for delivery",
}


TRACK_OWNER_BY_DOMAIN = {
    "design": "agent-2",
    "engineering": "agent-3",
    "legal": "agent-1",
    "marketing": "agent-2",
    "operations": "agent-3",
    "product": "agent-2",
    "research": "agent-1",
    "sales": "agent-3",
    "security": "agent-4",
    "support": "agent-3",
    "general": "agent-3",
}


TRACK_ROLE_BY_DOMAIN = {
    "design": "architect",
    "engineering": "executor",
    "legal": "analyst",
    "marketing": "strategist",
    "operations": "operator",
    "product": "architect",
    "research": "specialist",
    "sales": "executor",
    "security": "reviewer",
    "support": "operator",
    "general": "executor",
}


def _tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    for match in TOKEN_RE.findall((text or "").lower()):
        token = match.strip(".-_/#")
        if not token:
            continue
        tokens.append(token)
        if "-" in token:
            tokens.extend(part for part in token.split("-") if part)
    deduped: List[str] = []
    seen = set()
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def _dedupe(values: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        normalized = (value or "").strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(value)
    return result


def format_tag(value: str) -> str:
    return str(value or "").replace("_", " ").replace("-", " ").strip().title()


def infer_mission_profile(mission: Dict, template: Optional[Dict] = None) -> Dict:
    blob = " ".join(
        [
            str(mission.get("title") or ""),
            str(mission.get("goal") or ""),
            str(mission.get("mode") or ""),
            str(mission.get("priority") or ""),
        ]
    )
    tokens = _tokenize(blob)
    token_set = set(tokens)

    domain_scores = {key: 0 for key in DOMAIN_KEYWORDS}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        domain_scores[domain] += len(token_set.intersection(keywords))

    if template:
        category = str(template.get("category") or "").strip().lower()
        if category and category in domain_scores:
            domain_scores[category] += 4
        for division in template.get("preferredDivisions") or []:
            if division in domain_scores:
                domain_scores[division] += 2

    ranked_domains = [
        domain
        for domain, score in sorted(domain_scores.items(), key=lambda item: (-item[1], item[0]))
        if score > 0
    ]
    if not ranked_domains:
        ranked_domains = ["general"]

    intent_tags = [
        intent
        for intent, keywords in INTENT_RULES.items()
        if token_set.intersection(keywords)
    ]
    if "research" not in intent_tags:
        intent_tags.insert(0, "research")
    intent_tags = _dedupe(intent_tags)

    outcome_tags = [
        outcome
        for outcome, keywords in OUTCOME_RULES.items()
        if token_set.intersection(keywords)
    ]
    if not outcome_tags and ranked_domains != ["general"]:
        outcome_tags = ["working_solution"]

    risk_flags = [
        risk
        for risk, keywords in RISK_KEYWORDS.items()
        if token_set.intersection(keywords)
    ]
    risk_level = "low"
    if any(risk in risk_flags for risk in ("legal_sensitive", "security_sensitive", "money_sensitive")):
        risk_level = "high"
    elif risk_flags or mission.get("priority") in {"high", "critical"}:
        risk_level = "medium"

    preferred_divisions: List[str] = []
    preferred_template_ids: List[str] = []
    for domain in ranked_domains[:3]:
        preferred_divisions.extend(DIVISIONS_BY_DOMAIN.get(domain, []))
        preferred_template_ids.extend(TEMPLATES_BY_DOMAIN.get(domain, []))

    if template:
        preferred_divisions.extend(template.get("preferredDivisions") or [])
        preferred_template_ids.extend(template.get("defaultSpecialistTemplates") or [])

    return {
        "domains": ranked_domains,
        "primary_domain": ranked_domains[0],
        "intent_tags": intent_tags,
        "outcome_tags": outcome_tags,
        "risk_flags": _dedupe(risk_flags),
        "risk_level": risk_level,
        "requires_human_approval": "external_action" in risk_flags or "legal_sensitive" in risk_flags or "money_sensitive" in risk_flags,
        "preferred_divisions": _dedupe(preferred_divisions),
        "preferred_template_ids": _dedupe(preferred_template_ids),
        "tokens": tokens,
    }


def _stage(
    stage_id: str,
    *,
    phase_kind: str,
    phase_label: str,
    title: str,
    owner_agent_id: str,
    team_role: str,
    depends_on_stage_ids: Optional[List[str]] = None,
    acceptance_criteria: Optional[List[str]] = None,
    max_retries: int = 1,
    required_capabilities: Optional[List[str]] = None,
    preferred_divisions: Optional[List[str]] = None,
    specialist_template_hints: Optional[List[str]] = None,
    workstream: Optional[str] = None,
    tool_primitives: Optional[List[str]] = None,
    approval_policy: Optional[str] = None,
    external_action_kind: Optional[str] = None,
) -> Dict:
    return {
        "id": stage_id,
        "phase_kind": phase_kind,
        "phase_label": phase_label,
        "title": title,
        "owner_agent_id": owner_agent_id,
        "team_role": team_role,
        "depends_on_stage_ids": list(depends_on_stage_ids or []),
        "acceptance_criteria": list(acceptance_criteria or []),
        "max_retries": max(0, int(max_retries)),
        "required_capabilities": list(required_capabilities or []),
        "preferred_divisions": list(preferred_divisions or []),
        "specialist_template_hints": list(specialist_template_hints or []),
        "workstream": workstream or phase_kind,
        "tool_primitives": list(tool_primitives or []),
        "approval_policy": approval_policy or "auto_allowed",
        "external_action_kind": external_action_kind,
    }


def build_mission_blueprint(mission: Dict, template: Optional[Dict] = None) -> Dict:
    profile = infer_mission_profile(mission, template=template)
    primary_domain = profile["primary_domain"]
    domains = profile["domains"]
    intent_tags = set(profile["intent_tags"])
    outcome_tags = set(profile["outcome_tags"])
    risk_flags = set(profile["risk_flags"])

    strategy_needed = bool(
        intent_tags.intersection({"plan", "publish", "outreach"})
        or primary_domain in {"marketing", "sales", "legal", "operations", "product"}
    )
    design_needed = bool(
        primary_domain in {"design", "marketing"}
        or intent_tags.intersection({"design"})
        or outcome_tags.intersection({"design_assets"})
    )
    outreach_needed = bool(
        intent_tags.intersection({"outreach", "publish"})
        or primary_domain in {"sales"}
        or outcome_tags.intersection({"outreach_assets"})
    )
    documentation_needed = bool(
        intent_tags.intersection({"report"})
        or outcome_tags.intersection({"report_pack", "strategy_pack"})
        or primary_domain in {"legal", "research", "product"}
    )
    execution_needed = bool(
        intent_tags.intersection({"build", "publish", "outreach"})
        or outcome_tags.intersection({"working_solution", "design_assets"})
        or primary_domain in {"engineering", "marketing", "sales", "operations", "support", "security"}
    )

    stages: List[Dict] = []

    def build_stage(
        stage_id: str,
        *,
        phase_kind: str,
        phase_label: str,
        title: str,
        owner_agent_id: str,
        team_role: str,
        depends_on_stage_ids: Optional[List[str]] = None,
        acceptance_criteria: Optional[List[str]] = None,
        max_retries: int = 1,
        required_capabilities: Optional[List[str]] = None,
        preferred_divisions: Optional[List[str]] = None,
        specialist_template_hints: Optional[List[str]] = None,
        workstream: Optional[str] = None,
    ) -> Dict:
        capabilities = _dedupe(required_capabilities or [])
        normalized_workstream = workstream or phase_kind
        return _stage(
            stage_id,
            phase_kind=phase_kind,
            phase_label=phase_label,
            title=title,
            owner_agent_id=owner_agent_id,
            team_role=team_role,
            depends_on_stage_ids=depends_on_stage_ids,
            acceptance_criteria=acceptance_criteria,
            max_retries=max_retries,
            required_capabilities=capabilities,
            preferred_divisions=preferred_divisions,
            specialist_template_hints=specialist_template_hints,
            workstream=normalized_workstream,
            tool_primitives=infer_tool_primitives(
                required_capabilities=capabilities,
                mission_profile=profile,
                workstream=normalized_workstream,
            ),
            approval_policy=infer_approval_policy(
                mission_profile=profile,
                workstream=normalized_workstream,
                required_capabilities=capabilities,
            ),
            external_action_kind=infer_external_action_kind(
                mission_profile=profile,
                workstream=normalized_workstream,
                required_capabilities=capabilities,
            ),
        )

    stages.append(
        build_stage(
            "lead_plan",
            phase_kind="lead_plan",
            phase_label="Lead Plan",
            title="Triage the mission, define the operating workstreams, and set approval gates",
            owner_agent_id="agent-0",
            team_role="team_lead",
            max_retries=0,
            required_capabilities=["planning", "scoping", "delegation"],
            preferred_divisions=profile["preferred_divisions"],
            specialist_template_hints=profile["preferred_template_ids"][:4],
            workstream="mission-control",
            acceptance_criteria=[
                "The mission is decomposed into workstreams instead of a single vague task",
                "Risks, approvals, and external-action boundaries are explicit",
                "The team knows what good completion looks like",
            ],
        )
    )

    stages.append(
        build_stage(
            "research",
            phase_kind="research",
            phase_label="Discovery Research",
            title="Gather context, constraints, sources, and operating assumptions",
            owner_agent_id="agent-1",
            team_role="specialist",
            depends_on_stage_ids=["lead_plan"],
            required_capabilities=["research", "analysis", "context-building"],
            preferred_divisions=_dedupe(["strategy", "product", "support", *profile["preferred_divisions"][:2]]),
            specialist_template_hints=_dedupe(profile["preferred_template_ids"][:3]),
            workstream="discovery",
            acceptance_criteria=[
                "Important unknowns and constraints are documented",
                "Research reduces guesswork for downstream workstreams",
                "The mission has enough context to avoid blind execution",
            ],
        )
    )

    last_planning_stage_ids = ["research"]

    if strategy_needed:
        stages.append(
            build_stage(
                "strategy",
                phase_kind="strategy",
                phase_label="Strategy Blueprint",
                title=STRATEGY_TITLE_BY_DOMAIN.get(primary_domain, STRATEGY_TITLE_BY_DOMAIN["general"]),
                owner_agent_id="agent-2",
                team_role="architect",
                depends_on_stage_ids=["research"],
                required_capabilities=["strategy", "sequencing", "decision-framework"],
                preferred_divisions=_dedupe(
                    [
                        *DIVISIONS_BY_DOMAIN.get(primary_domain, []),
                        "project-management",
                        "strategy",
                    ]
                ),
                specialist_template_hints=_dedupe(profile["preferred_template_ids"][:4]),
                workstream="strategy",
                acceptance_criteria=[
                    "The mission has a clear approach, not just a list of wishes",
                    "Tradeoffs and execution order are explicit",
                    "The next builder can execute without inventing the plan",
                ],
            )
        )
        last_planning_stage_ids = ["strategy"]

    if design_needed:
        stages.append(
            build_stage(
                "design",
                phase_kind="design",
                phase_label="Design System",
                title=DESIGN_TITLE_BY_DOMAIN.get(primary_domain, DESIGN_TITLE_BY_DOMAIN["general"]),
                owner_agent_id="agent-2",
                team_role="architect",
                depends_on_stage_ids=list(last_planning_stage_ids),
                required_capabilities=["design", "structure", "artifact-definition"],
                preferred_divisions=_dedupe(["design", "product", *DIVISIONS_BY_DOMAIN.get(primary_domain, [])]),
                specialist_template_hints=_dedupe(
                    [
                        *TEMPLATES_BY_DOMAIN.get("design", []),
                        *profile["preferred_template_ids"][:2],
                    ]
                ),
                workstream="design",
                acceptance_criteria=[
                    "Deliverables have a defined shape and structure",
                    "Brand, UX, or narrative requirements are made concrete",
                    "Execution has a tangible design target",
                ],
            )
        )
        last_planning_stage_ids = ["design"]

    execution_stage_ids: List[str] = []
    if execution_needed:
        execution_deps = ["research"]
        if strategy_needed:
            execution_deps.append("strategy")
        if design_needed:
            execution_deps.append("design")
        candidate_domains = _dedupe(
            [
                primary_domain,
                *[domain for domain in domains[:3] if domain not in {"research"}],
            ]
        )
        track_domains = [domain for domain in candidate_domains if domain not in {"general"}]
        if not track_domains:
            track_domains = [primary_domain]

        for index, domain in enumerate(track_domains):
            stage_id = "delivery" if index == 0 else f"track_{domain}"
            phase_label = "Execution" if index == 0 else f"{format_tag(domain)} Track"
            stage_title = TITLE_BY_DOMAIN.get(domain, TITLE_BY_DOMAIN["general"])
            if index > 0:
                stage_title = f"Own the {format_tag(domain)} workstream and deliver its mission-specific outputs"
            stages.append(
                build_stage(
                    stage_id,
                    phase_kind="build",
                    phase_label=phase_label,
                    title=stage_title,
                    owner_agent_id=TRACK_OWNER_BY_DOMAIN.get(domain, "agent-3"),
                    team_role=TRACK_ROLE_BY_DOMAIN.get(domain, "executor"),
                    depends_on_stage_ids=_dedupe(execution_deps),
                    required_capabilities=_dedupe([domain, *profile["intent_tags"], "delivery"]),
                    preferred_divisions=_dedupe(DIVISIONS_BY_DOMAIN.get(domain, DIVISIONS_BY_DOMAIN["general"])),
                    specialist_template_hints=_dedupe(
                        [
                            *TEMPLATES_BY_DOMAIN.get(domain, []),
                            *profile["preferred_template_ids"][:4],
                        ]
                    ),
                    workstream=domain if domain not in {"general"} else "delivery",
                    acceptance_criteria=[
                        "The requested output exists in a usable form",
                        "Delivery matches the upstream strategy and design constraints",
                        "Known limits are surfaced instead of hidden",
                    ],
                )
            )
            execution_stage_ids.append(stage_id)

    if documentation_needed:
        documentation_deps = execution_stage_ids if execution_stage_ids else (["design"] if design_needed else ["research"])
        stages.append(
            build_stage(
                "documentation",
                phase_kind="documentation",
                phase_label="Documentation Pack",
                title="Package the mission outputs into documentation, summaries, or decision assets",
                owner_agent_id="agent-3",
                team_role="executor",
                depends_on_stage_ids=documentation_deps,
                required_capabilities=["documentation", "summary", "handoff"],
                preferred_divisions=_dedupe(["support", "project-management", *profile["preferred_divisions"][:2]]),
                specialist_template_hints=_dedupe(
                    [
                        "engineering-technical-writer",
                        "support-executive-summary-generator",
                        *profile["preferred_template_ids"][:2],
                    ]
                ),
                workstream="documentation",
                acceptance_criteria=[
                    "The work is handed off in a readable, reusable format",
                    "The output can be consumed by humans or downstream agents",
                    "Important decisions and caveats are preserved",
                ],
            )
        )

    if outreach_needed:
        outreach_deps: List[str] = []
        if strategy_needed:
            outreach_deps.append("strategy")
        if design_needed:
            outreach_deps.append("design")
        if documentation_needed:
            outreach_deps.append("documentation")
        elif execution_stage_ids:
            outreach_deps.extend(execution_stage_ids)
        if not outreach_deps:
            outreach_deps.append("research")
        stages.append(
            build_stage(
                "outreach",
                phase_kind="outreach",
                phase_label="External Action Pack",
                title="Prepare outreach, communication, or publication-ready assets",
                owner_agent_id="agent-3",
                team_role="executor",
                depends_on_stage_ids=_dedupe(outreach_deps),
                required_capabilities=["communication", "outreach", "external-action"],
                preferred_divisions=_dedupe(["sales", "marketing", "strategy"]),
                specialist_template_hints=_dedupe(
                    [
                        "sales-outbound-strategist",
                        "sales-proposal-strategist",
                        "marketing-social-media-strategist",
                        *profile["preferred_template_ids"][:2],
                    ]
                ),
                workstream="external-action",
                acceptance_criteria=[
                    "External-facing material is ready for approval",
                    "The messaging aligns with the mission strategy",
                    "No external action is assumed without explicit approval",
                ],
            )
        )

    review_inputs = [
        stage["id"]
        for stage in stages
        if stage["id"] not in {"lead_plan"} and stage["phase_kind"] != "lead_closeout"
    ]
    review_title = "Validate outputs, harden weak spots, and enforce approval gates"
    if not risk_flags:
        review_title = "Validate outputs, quality, and mission readiness"
    stages.append(
        build_stage(
            "review",
            phase_kind="review",
            phase_label="Review",
            title=review_title,
            owner_agent_id="agent-4",
            team_role="reviewer",
            depends_on_stage_ids=review_inputs,
            required_capabilities=["review", "validation", "risk-checking"],
            preferred_divisions=_dedupe(["testing", "support", *profile["preferred_divisions"][:2]]),
            specialist_template_hints=_dedupe(
                [
                    "testing-reality-checker",
                    "engineering-code-reviewer",
                    *profile["preferred_template_ids"][:2],
                ]
            ),
            workstream="review",
            acceptance_criteria=[
                "Weak assumptions, regressions, and missing approvals are called out",
                "The mission is either approved or returned with precise fixes",
                "High-risk work is clearly marked before closeout",
            ],
        )
    )

    stages.append(
        build_stage(
            "lead_closeout",
            phase_kind="lead_closeout",
            phase_label="Lead Closeout",
            title="Consolidate the outputs, decide next action, and close the mission",
            owner_agent_id="agent-0",
            team_role="team_lead",
            depends_on_stage_ids=["review"],
            max_retries=0,
            required_capabilities=["synthesis", "approval", "handoff"],
            preferred_divisions=profile["preferred_divisions"],
            specialist_template_hints=profile["preferred_template_ids"][:3],
            workstream="closeout",
            acceptance_criteria=[
                "Outputs are synthesized into one coherent closeout",
                "Approval-sensitive work is flagged clearly",
                "The mission can finish or escalate without ambiguity",
            ],
        )
    )

    profile["workflow_version"] = "open_capability_graph_v1"
    profile["recommended_parallel_tracks"] = [
        stage["workstream"]
        for stage in stages
        if stage["phase_kind"] in {"strategy", "design", "build", "documentation", "outreach"}
    ]

    return {
        "profile": profile,
        "stages": stages,
    }
