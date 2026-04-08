from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Dict, Iterable, List, Optional


DIVISION_LABELS = {
    "academic": "Academic",
    "design": "Design",
    "engineering": "Engineering",
    "game-development": "Game Development",
    "marketing": "Marketing",
    "paid-media": "Paid Media",
    "product": "Product",
    "project-management": "Project Management",
    "sales": "Sales",
    "spatial-computing": "Spatial Computing",
    "specialized": "Specialized",
    "strategy": "Strategy",
    "support": "Support",
    "testing": "Testing",
}

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "your",
    "into",
    "their",
    "through",
    "who",
    "why",
    "when",
    "where",
    "what",
    "how",
    "you",
    "they",
    "them",
    "are",
    "our",
    "its",
    "has",
    "have",
    "not",
    "all",
    "use",
    "using",
    "used",
    "agent",
    "specialist",
    "ready",
    "real",
    "build",
    "work",
    "workflow",
}

SECTION_HINTS = {
    "core capabilities",
    "specialized skills",
    "core responsibilities",
    "decision framework",
    "workflow integration",
    "platform strategy framework",
}

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#./-]*", re.IGNORECASE)
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def _clean_value(value: str) -> str:
    cleaned = (value or "").strip()
    if cleaned.startswith(("'", '"')) and cleaned.endswith(("'", '"')) and len(cleaned) >= 2:
        cleaned = cleaned[1:-1]
    return cleaned.strip()


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    tokens: List[str] = []
    for raw in TOKEN_RE.findall(text.lower()):
        raw = raw.strip(".-_/#")
        if not raw or raw in STOPWORDS or len(raw) < 3:
            continue
        tokens.append(raw)
        if "-" in raw:
            tokens.extend(part for part in raw.split("-") if part and part not in STOPWORDS and len(part) >= 3)
    seen = set()
    unique_tokens = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            unique_tokens.append(token)
    return unique_tokens


def _clean_markdown_line(line: str) -> str:
    cleaned = re.sub(r"^[-*]\s*", "", line.strip())
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"\[[^\]]+\]\([^)]+\)", "", cleaned)
    return cleaned.strip()


def _short_capability(line: str) -> str:
    cleaned = _clean_markdown_line(line)
    if ":" in cleaned:
        head, _tail = cleaned.split(":", 1)
        cleaned = head.strip()
    return cleaned[:90].strip()


def _parse_frontmatter(raw: str) -> Dict:
    if not raw:
        return {}
    data: Dict[str, object] = {}
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip().lower()
        cleaned = _clean_value(value)
        if key == "tools":
            data[key] = [item.strip() for item in cleaned.split(",") if item.strip()]
        else:
            data[key] = cleaned
    return data


def _split_frontmatter(content: str) -> tuple[Dict, str]:
    match = FRONTMATTER_RE.match(content)
    if not match:
        return {}, content
    return _parse_frontmatter(match.group(1)), content[match.end() :]


def _first_matching_line(body: str, needles: Iterable[str]) -> Optional[str]:
    normalized_needles = [needle.lower() for needle in needles]
    for line in body.splitlines():
        stripped = _clean_markdown_line(line)
        lowered = stripped.lower()
        if any(needle in lowered for needle in normalized_needles):
            if ":" in stripped:
                _, value = stripped.split(":", 1)
                return value.strip()
            return stripped
    return None


def _extract_capabilities(body: str, frontmatter: Dict) -> List[str]:
    capabilities: List[str] = []
    current_section = ""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            current_section = stripped[3:].strip().lower()
            continue
        if stripped.startswith("### "):
            current_section = stripped[4:].strip().lower()
            continue
        if not stripped.startswith(("-", "*")):
            continue
        if current_section not in SECTION_HINTS:
            continue
        capability = _short_capability(stripped)
        if capability:
            capabilities.append(capability)

    if not capabilities:
        tools = frontmatter.get("tools") or []
        capabilities.extend(str(item).strip() for item in tools if str(item).strip())

    seen = set()
    deduped = []
    for capability in capabilities:
        lowered = capability.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(capability)
    return deduped[:8]


@dataclass
class SpecialistTemplateCatalog:
    root_path: str
    templates: List[Dict] = field(init=False, default_factory=list)
    templates_by_id: Dict[str, Dict] = field(init=False, default_factory=dict)

    _CACHE: ClassVar[Dict[str, List[Dict]]] = {}

    def __post_init__(self) -> None:
        self.root = Path(self.root_path)
        if not self.root.exists():
            self.templates = []
            self.templates_by_id = {}
            return
        cache_key = str(self.root.resolve())
        cached_templates = self._CACHE.get(cache_key)
        if cached_templates is None:
            cached_templates = self._load_templates()
            self._CACHE[cache_key] = cached_templates
        self.templates = [dict(item) for item in cached_templates]
        self.templates_by_id = {item["id"]: item for item in self.templates}

    def _load_templates(self) -> List[Dict]:
        templates: List[Dict] = []
        for path in sorted(self.root.rglob("*.md")):
            item = self._parse_template_file(path)
            if item:
                templates.append(item)
        return templates

    def _parse_template_file(self, path: Path) -> Optional[Dict]:
        content = path.read_text(encoding="utf-8")
        frontmatter, body = _split_frontmatter(content)
        if not frontmatter.get("name") or not frontmatter.get("description"):
            return None

        division = path.relative_to(self.root).parts[0]
        stem = path.stem
        role_slug = stem[len(f"{division}-") :] if stem.startswith(f"{division}-") else stem
        capabilities = _extract_capabilities(body, frontmatter)
        personality = _first_matching_line(body, ["personality"]) or str(frontmatter.get("vibe") or "").strip()
        keywords = _tokenize(
            " ".join(
                [
                    stem,
                    division,
                    str(frontmatter.get("name") or ""),
                    str(frontmatter.get("description") or ""),
                    str(frontmatter.get("vibe") or ""),
                    " ".join(capabilities),
                ]
            )
        )

        return {
            "id": stem,
            "role": role_slug,
            "display_name": str(frontmatter.get("name") or "").strip(),
            "description": str(frontmatter.get("description") or "").strip(),
            "division": division,
            "division_label": DIVISION_LABELS.get(division, division.replace("-", " ").title()),
            "emoji": str(frontmatter.get("emoji") or "").strip(),
            "color": str(frontmatter.get("color") or "").strip(),
            "vibe": str(frontmatter.get("vibe") or "").strip(),
            "personality": personality.strip() if personality else None,
            "capabilities": capabilities,
            "keywords": keywords,
            "tools": list(frontmatter.get("tools") or []),
            "source_path": str(path.relative_to(self.root)).replace("\\", "/"),
            "source_repo": "msitarzewski/agency-agents",
        }

    def list_templates(
        self,
        *,
        division: Optional[str] = None,
        query: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        items = list(self.templates)
        if division:
            normalized_division = division.strip().lower()
            items = [item for item in items if item["division"].lower() == normalized_division]
        if query:
            query_tokens = set(_tokenize(query))
            lowered_query = query.strip().lower()
            items = [
                item
                for item in items
                if lowered_query in item["display_name"].lower()
                or lowered_query in item["description"].lower()
                or lowered_query in item["role"].lower()
                or bool(query_tokens.intersection(item.get("keywords") or []))
            ]
        if limit and limit > 0:
            items = items[:limit]
        return [dict(item) for item in items]

    def get_template(self, template_id: str) -> Optional[Dict]:
        item = self.templates_by_id.get(template_id)
        return dict(item) if item else None

    def summary(self) -> Dict:
        divisions = sorted({item["division"] for item in self.templates})
        return {
            "count": len(self.templates),
            "divisions": divisions,
        }

    def suggest_for_mission(
        self,
        mission: Dict,
        *,
        preferred_divisions: Optional[List[str]] = None,
        preferred_template_ids: Optional[List[str]] = None,
        limit: int = 6,
    ) -> List[Dict]:
        if not self.templates:
            return []

        preferred_divisions = [item for item in (preferred_divisions or []) if item]
        preferred_template_ids = [item for item in (preferred_template_ids or []) if item]
        mission_blob = " ".join(
            [
                str(mission.get("title") or ""),
                str(mission.get("goal") or ""),
                str(mission.get("mode") or ""),
                str(mission.get("priority") or ""),
            ]
        )
        mission_tokens = set(_tokenize(mission_blob))

        ranked: List[tuple[int, Dict]] = []
        for template in self.templates:
            score = 0
            if template["id"] in preferred_template_ids:
                score += 60 - (preferred_template_ids.index(template["id"]) * 4)
            if template["division"] in preferred_divisions:
                score += 28 - (preferred_divisions.index(template["division"]) * 5)
            overlap = mission_tokens.intersection(template.get("keywords") or [])
            score += min(len(overlap), 8) * 4
            if mission.get("mode") and mission.get("mode") in template["id"]:
                score += 10
            if score <= 0:
                continue
            ranked.append((score, template))

        if not ranked and preferred_divisions:
            for template in self.templates:
                if template["division"] in preferred_divisions:
                    ranked.append((10, template))

        ranked.sort(
            key=lambda item: (
                -item[0],
                preferred_divisions.index(item[1]["division"]) if item[1]["division"] in preferred_divisions else 999,
                item[1]["display_name"].lower(),
            )
        )

        results: List[Dict] = []
        seen = set()
        for _score, template in ranked:
            if template["id"] in seen:
                continue
            seen.add(template["id"])
            results.append(dict(template))
            if len(results) >= max(1, limit):
                break
        return results
