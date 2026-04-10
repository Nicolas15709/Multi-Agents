from datetime import datetime, timezone
from typing import Iterable, List
import json
import uuid


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def to_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def dedupe(values: Iterable[str]) -> List[str]:
    """Deduplicate a list of strings, normalizing to lowercase and stripping whitespace."""
    seen: set = set()
    result: List[str] = []
    for value in values:
        normalized = str(value or "").strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result
