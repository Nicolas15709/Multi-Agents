from dataclasses import dataclass
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from parent directory (MissionControl/)
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)


def _load_json_env(name: str, default: str) -> dict:
    raw = os.getenv(name, default)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        value = json.loads(default)
    return value if isinstance(value, dict) else json.loads(default)


@dataclass
class RuntimeConfig:
    db_path: str
    websocket_enabled: bool
    websocket_host: str
    websocket_port: int
    api_enabled: bool
    api_host: str
    api_port: int
    api_cors_origin: str
    api_auth_token: str
    # ── Auth / JWT ──────────────────────────────────────────────────────────
    jwt_secret: str          # HS256 signing key — set via MISSION_CONTROL_JWT_SECRET
    jwt_expiry_seconds: int  # Access-token lifetime in seconds (default 24 h)
    dashboard_username: str  # Dashboard login username
    dashboard_password: str  # Plain-text password from env (compared via hmac.compare_digest)
    # ── Hiring / autonomy controls ──────────────────────────────────────────
    hire_approvals_enabled: bool
    auto_propose_hires_enabled: bool
    max_autonomous_steps: int
    max_estimated_tokens: int
    max_runtime_ticks: int
    max_dynamic_hires: int
    action_budgets: dict
    tick_interval_seconds: int
    telegram_notifications_enabled: bool
    environment: str
    agents_registry_path: str
    templates_path: str
    specialist_templates_root: str

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        base_dir = Path(__file__).resolve().parent
        return cls(
            db_path=os.getenv("MISSION_CONTROL_RUNTIME_DB", str(base_dir / ".." / ".." / "data" / "runtime.db")),
            websocket_enabled=os.getenv("MISSION_CONTROL_WEBSOCKET", "true").lower() == "true",
            websocket_host=os.getenv("MISSION_CONTROL_WEBSOCKET_HOST", "0.0.0.0"),
            websocket_port=int(os.getenv("MISSION_CONTROL_WEBSOCKET_PORT", "8765")),
            api_enabled=os.getenv("MISSION_CONTROL_API", "true").lower() == "true",
            api_host=os.getenv("MISSION_CONTROL_API_HOST", "0.0.0.0"),
            api_port=int(os.getenv("MISSION_CONTROL_API_PORT", "8787")),
            api_cors_origin=os.getenv("MISSION_CONTROL_API_CORS_ORIGIN", "*"),
            api_auth_token=os.getenv("MISSION_CONTROL_API_AUTH_TOKEN", ""),
            jwt_secret=os.getenv("MISSION_CONTROL_JWT_SECRET", ""),
            jwt_expiry_seconds=int(os.getenv("MISSION_CONTROL_JWT_EXPIRY_HOURS", "24")) * 3600,
            dashboard_username=os.getenv("MISSION_CONTROL_DASHBOARD_USERNAME", "admin"),
            dashboard_password=os.getenv("MISSION_CONTROL_DASHBOARD_PASSWORD", ""),
            hire_approvals_enabled=os.getenv("MISSION_CONTROL_HIRE_APPROVALS", "false").lower() == "true",
            auto_propose_hires_enabled=os.getenv("MISSION_CONTROL_AUTO_PROPOSE_HIRES", "true").lower() == "true",
            max_autonomous_steps=int(os.getenv("MISSION_CONTROL_MAX_AUTONOMOUS_STEPS", "18")),
            max_estimated_tokens=int(os.getenv("MISSION_CONTROL_MAX_ESTIMATED_TOKENS", "16000")),
            max_runtime_ticks=int(os.getenv("MISSION_CONTROL_MAX_RUNTIME_TICKS", "64")),
            max_dynamic_hires=int(os.getenv("MISSION_CONTROL_MAX_DYNAMIC_HIRES", "3")),
            action_budgets=_load_json_env(
                "MISSION_CONTROL_ACTION_BUDGETS_JSON",
                '{"outreach": 2, "publish": 1, "legal_release": 1, "financial_commitment": 1}',
            ),
            tick_interval_seconds=int(os.getenv("MISSION_CONTROL_TICK_INTERVAL_SECONDS", "5")),
            telegram_notifications_enabled=os.getenv("MISSION_CONTROL_TELEGRAM_NOTIFICATIONS", "true").lower() == "true",
            environment=os.getenv("MISSION_CONTROL_ENV", "development"),
            agents_registry_path=os.getenv("MISSION_CONTROL_AGENTS_REGISTRY", str(base_dir / "agents_registry.json")),
            templates_path=os.getenv("MISSION_CONTROL_TEMPLATES_PATH", str(base_dir.parent.parent / "config" / "mission-templates.json")),
            specialist_templates_root=os.getenv(
                "MISSION_CONTROL_SPECIALIST_TEMPLATES_ROOT",
                str(base_dir.parent.parent.parent / "references" / "agency-agents"),
            ),
        )
