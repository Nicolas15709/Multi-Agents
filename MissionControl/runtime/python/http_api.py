from __future__ import annotations

import contextlib
import json
import os
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse

try:
    from .approval_service import ActionApprovalService
    from .agent_state import AgentStateManager
    from .api_snapshot import RuntimeSnapshotAPI
    from .auth import create_jwt, verify_jwt, verify_password_plain
    from .config import RuntimeConfig
    from .coordination_service import CoordinationService
    from .db import Database
    from .event_stream import EventStreamService
    from .hiring_service import HiringService
    from .intake_service import IntakeService
    from .mission_service import MissionService
    from .mission_summary import MissionSummaryService
    from .notifications import NotificationService
    from .planner import Planner
    from .progress import ProgressNotifier
    from .progress_summary import ProgressSummaryService
    from .repository import (
        ActionApprovalRepository,
        AgentHireRequestRepository,
        AgentMessageRepository,
        AgentRepository,
        IntakeRequestRepository,
        MissionControlRepository,
        MissionMemoryRepository,
        MissionRepository,
        NotificationRepository,
        TaskRepository,
    )
    from .scheduler import Scheduler
    from .security import RateLimiter, validate_bool, validate_enum, validate_str
    from .settings import ProgressSettings
    from .specialist_templates import SpecialistTemplateCatalog
    from .templates import TemplateRegistry
except ImportError:  # pragma: no cover - runtime script compatibility
    from approval_service import ActionApprovalService
    from agent_state import AgentStateManager
    from api_snapshot import RuntimeSnapshotAPI
    from auth import create_jwt, verify_jwt, verify_password_plain
    from config import RuntimeConfig
    from coordination_service import CoordinationService
    from db import Database
    from event_stream import EventStreamService
    from hiring_service import HiringService
    from intake_service import IntakeService
    from mission_service import MissionService
    from mission_summary import MissionSummaryService
    from notifications import NotificationService
    from planner import Planner
    from progress import ProgressNotifier
    from progress_summary import ProgressSummaryService
    from repository import (
        ActionApprovalRepository,
        AgentHireRequestRepository,
        AgentMessageRepository,
        AgentRepository,
        IntakeRequestRepository,
        MissionControlRepository,
        MissionMemoryRepository,
        MissionRepository,
        NotificationRepository,
        TaskRepository,
    )
    from scheduler import Scheduler
    from security import RateLimiter, validate_bool, validate_enum, validate_str
    from settings import ProgressSettings
    from specialist_templates import SpecialistTemplateCatalog
    from templates import TemplateRegistry


# ─── Constants ────────────────────────────────────────────────────────────────

MAX_BODY_BYTES = 64 * 1024  # 64 KB — reject oversized payloads early

# General API: 120 requests / minute per IP
_API_LIMITER = RateLimiter(max_requests=120, window_seconds=60.0)

# Login endpoint: 5 attempts / minute per IP (brute-force protection)
_LOGIN_LIMITER = RateLimiter(max_requests=5, window_seconds=60.0)

# Public paths that bypass token auth (still subject to rate limiting)
_PUBLIC_PATHS = {"/health", "/api/health", "/api/auth/login"}

# Security response headers added to every response
_SECURITY_HEADERS = [
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("X-XSS-Protection", "1; mode=block"),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
]


# ─── Service factory ──────────────────────────────────────────────────────────

def build_runtime_services(config: RuntimeConfig) -> Dict:
    db = Database(config.db_path)
    db.init()

    mission_repository = MissionRepository(db)
    task_repository = TaskRepository(db)
    agent_repository = AgentRepository(db)
    notification_repository = NotificationRepository(db)
    intake_repository = IntakeRequestRepository(db)
    hire_request_repository = AgentHireRequestRepository(db)
    mission_control_repository = MissionControlRepository(db)
    mission_memory_repository = MissionMemoryRepository(db)
    agent_message_repository = AgentMessageRepository(db)
    action_approval_repository = ActionApprovalRepository(db)

    notifications = NotificationService(config=config, repository=notification_repository)
    progress_settings = ProgressSettings.from_env()
    progress_notifier = ProgressNotifier(
        mission_repository=mission_repository,
        notifications=notifications,
        mode=progress_settings.telegram_progress_mode,
    )
    scheduler = Scheduler(mission_repository=mission_repository, task_repository=task_repository)
    template_registry = TemplateRegistry(config.templates_path)
    specialist_template_catalog = SpecialistTemplateCatalog(config.specialist_templates_root)
    planner = Planner(
        config=config,
        mission_repository=mission_repository,
        task_repository=task_repository,
        template_registry=template_registry,
    )
    mission_service = MissionService(
        planner=planner,
        mission_repository=mission_repository,
        scheduler=scheduler,
        notifications=notifications,
        progress_notifier=progress_notifier,
        auto_seed_hire_requests=config.auto_propose_hires_enabled,
        mission_control_repository=mission_control_repository,
        mission_control_defaults={
            "max_autonomous_steps": config.max_autonomous_steps,
            "max_estimated_tokens": config.max_estimated_tokens,
            "max_runtime_ticks": config.max_runtime_ticks,
            "max_dynamic_hires": config.max_dynamic_hires,
            "action_budgets": config.action_budgets,
        },
    )
    agent_state_manager = AgentStateManager(repository=agent_repository)
    intake_service = IntakeService(
        intake_repository=intake_repository,
        mission_repository=mission_repository,
        mission_service=mission_service,
        notifications=notifications,
        agent_state_manager=agent_state_manager,
    )
    hiring_service = HiringService(
        mission_repository=mission_repository,
        task_repository=task_repository,
        agent_repository=agent_repository,
        hire_request_repository=hire_request_repository,
        mission_control_repository=mission_control_repository,
        approvals_enabled=config.hire_approvals_enabled,
        template_registry=template_registry,
        specialist_template_catalog=specialist_template_catalog,
    )
    approval_service = ActionApprovalService(
        repository=action_approval_repository,
        mission_repository=mission_repository,
    )
    coordination_service = CoordinationService(
        task_repository=task_repository,
        memory_repository=mission_memory_repository,
        message_repository=agent_message_repository,
    )
    mission_service.hiring_service = hiring_service
    event_stream = EventStreamService(
        mission_repository=mission_repository,
        notification_repository=notification_repository,
    )
    snapshot_api = RuntimeSnapshotAPI(
        mission_repository=mission_repository,
        task_repository=task_repository,
        agent_repository=agent_repository,
        event_stream=event_stream,
        progress_summary=ProgressSummaryService(
            mission_repository=mission_repository,
            task_repository=task_repository,
            scheduler=scheduler,
        ),
        mission_summary=MissionSummaryService(
            mission_repository=mission_repository,
            task_repository=task_repository,
        ),
        scheduler=scheduler,
        intake_repository=intake_repository,
        hire_request_repository=hire_request_repository,
        mission_control_repository=mission_control_repository,
        mission_memory_repository=mission_memory_repository,
        agent_message_repository=agent_message_repository,
        action_approval_repository=action_approval_repository,
    )
    return {
        "db": db,
        "scheduler": scheduler,
        "snapshot_api": snapshot_api,
        "mission_service": mission_service,
        "intake_service": intake_service,
        "hiring_service": hiring_service,
        "approval_service": approval_service,
        "coordination_service": coordination_service,
    }


# ─── Request helpers ──────────────────────────────────────────────────────────

def _read_json_body(handler: BaseHTTPRequestHandler) -> Dict:
    content_length = int(handler.headers.get("Content-Length", "0") or 0)
    if content_length <= 0:
        return {}
    if content_length > MAX_BODY_BYTES:
        raise ValueError("request_body_too_large")
    raw = handler.rfile.read(content_length)
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _extract_bearer_token(handler: BaseHTTPRequestHandler) -> str:
    auth_header = handler.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[len("Bearer "):].strip()
    return (handler.headers.get("X-Mission-Control-Token") or "").strip()


def _client_ip(handler: BaseHTTPRequestHandler) -> str:
    """Best-effort client IP (supports X-Forwarded-For for reverse-proxy setups)."""
    forwarded = handler.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return handler.client_address[0]


# ─── HTTP server ──────────────────────────────────────────────────────────────

@dataclass
class RuntimeApiServer:
    config: RuntimeConfig
    _server: Optional[ThreadingHTTPServer] = None
    _thread: Optional[threading.Thread] = None

    def _auth_enabled(self) -> bool:
        """Returns True when JWT or static-token auth is configured."""
        return bool(self.config.jwt_secret.strip() or self.config.api_auth_token.strip())

    def _verify_request_token(self, token: str) -> bool:
        """Verify an incoming Bearer token against JWT secret or static token."""
        jwt_secret = self.config.jwt_secret.strip()
        if jwt_secret:
            return verify_jwt(token, jwt_secret) is not None
        # Fallback: static bearer token (legacy mode)
        static = self.config.api_auth_token.strip()
        if static:
            import hmac as _hmac
            try:
                return _hmac.compare_digest(token.encode("utf-8"), static.encode("utf-8"))
            except Exception:
                return False
        return False

    def start(self) -> None:
        if not self.config.api_enabled or self._server is not None:
            return

        server_ref = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args) -> None:  # noqa: A003
                return  # Suppress default stdout logging

            # ── Response builder ──────────────────────────────────────────

            def _send_json(self, status: int, payload: Dict) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", server_ref.config.api_cors_origin)
                self.send_header(
                    "Access-Control-Allow-Headers",
                    "Content-Type, Authorization, X-Mission-Control-Token",
                )
                self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
                for name, value in _SECURITY_HEADERS:
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(body)

            # ── Auth guard ────────────────────────────────────────────────

            def _check_auth(self, path: str) -> bool:
                """Return True if the request is allowed to proceed."""
                if path in _PUBLIC_PATHS:
                    return True
                if not server_ref._auth_enabled():
                    return True  # Auth not configured — open (dev mode)
                token = _extract_bearer_token(self)
                return server_ref._verify_request_token(token)

            # ── Rate-limit guard ──────────────────────────────────────────

            def _check_rate_limit(self, path: str) -> bool:
                ip = _client_ip(self)
                if path in {"/api/auth/login"}:
                    return _LOGIN_LIMITER.is_allowed(ip)
                return _API_LIMITER.is_allowed(ip)

            # ── OPTIONS (CORS preflight) ───────────────────────────────────

            def do_OPTIONS(self) -> None:  # noqa: N802
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", server_ref.config.api_cors_origin)
                self.send_header(
                    "Access-Control-Allow-Headers",
                    "Content-Type, Authorization, X-Mission-Control-Token",
                )
                self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
                for name, value in _SECURITY_HEADERS:
                    self.send_header(name, value)
                self.end_headers()

            # ── GET ───────────────────────────────────────────────────────

            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                path = parsed.path.rstrip("/") or "/"

                if not self._check_rate_limit(path):
                    return self._send_json(429, {"ok": False, "error": "rate_limit_exceeded"})

                if not self._check_auth(path):
                    return self._send_json(401, {"ok": False, "error": "unauthorized"})

                services = build_runtime_services(server_ref.config)
                db = services["db"]
                try:
                    if path in {"/health", "/api/health"}:
                        db_status = "ok"
                        db_mode = "postgres" if os.getenv("DATABASE_URL") else "sqlite"
                        try:
                            db.fetchone("SELECT 1 AS ping")
                        except Exception:
                            db_status = "error"
                        return self._send_json(
                            200,
                            {
                                "ok": True,
                                "service": "mission-control-api",
                                "db": db_status,
                                "mode": db_mode,
                            },
                        )

                    if path == "/api/snapshot":
                        snapshot = services["snapshot_api"].snapshot()
                        return self._send_json(200, snapshot)

                    if path == "/api/intake/requests":
                        query = parse_qs(parsed.query)
                        raw_limit = (query.get("limit") or ["50"])[0]
                        limit = min(max(1, int(raw_limit)), 200)
                        requests = services["intake_service"].list_requests(limit=limit)
                        return self._send_json(200, {"ok": True, "requests": requests})

                    if path == "/api/agent-templates":
                        query = parse_qs(parsed.query)
                        division = (query.get("division") or [None])[0]
                        search = (query.get("q") or [None])[0]
                        raw_limit = (query.get("limit") or ["80"])[0]
                        limit = min(max(1, int(raw_limit)), 200)
                        templates = services["hiring_service"].list_available_templates(
                            division=division,
                            query=search,
                            limit=limit,
                        )
                        return self._send_json(200, {"ok": True, "templates": templates})

                    if path.startswith("/api/missions/") and path.endswith("/hire-requests"):
                        mission_id = path.split("/")[-2]
                        requests = services["hiring_service"].list_requests_for_mission(mission_id)
                        return self._send_json(200, {"ok": True, "requests": requests})

                    if path.startswith("/api/missions/") and path.endswith("/hire-suggestions"):
                        mission_id = path.split("/")[-2]
                        suggestions = services["hiring_service"].suggest_subagents_for_mission(mission_id)
                        return self._send_json(200, {"ok": True, "suggestions": suggestions})

                    if path.startswith("/api/missions/") and path.endswith("/approvals"):
                        mission_id = path.split("/")[-2]
                        approvals = services["approval_service"].list_for_mission(mission_id)
                        return self._send_json(200, {"ok": True, "approvals": approvals})

                    return self._send_json(404, {"ok": False, "error": "not_found"})
                finally:
                    db.close()

            # ── POST ──────────────────────────────────────────────────────

            def do_DELETE(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                path = parsed.path.rstrip("/") or "/"

                if not self._check_rate_limit(path):
                    return self._send_json(429, {"ok": False, "error": "rate_limit_exceeded"})
                if not self._check_auth(path):
                    return self._send_json(401, {"ok": False, "error": "unauthorized"})

                services = build_runtime_services(server_ref.config)
                db = services["db"]
                try:
                    # DELETE /api/agents/:agent_id
                    parts = path.strip("/").split("/")
                    if len(parts) == 3 and parts[0] == "api" and parts[1] == "agents":
                        agent_id = parts[2]
                        if agent_id == "agent-0":
                            return self._send_json(403, {"ok": False, "error": "cannot_delete_lead"})
                        agent_repo = AgentRepository(db)
                        agent_repo.delete_agent(agent_id)
                        return self._send_json(200, {"ok": True, "deleted": agent_id})
                    return self._send_json(404, {"ok": False, "error": "not_found"})
                finally:
                    db.close()

            def do_POST(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                path = parsed.path.rstrip("/") or "/"

                if not self._check_rate_limit(path):
                    return self._send_json(429, {"ok": False, "error": "rate_limit_exceeded"})

                try:
                    payload = _read_json_body(self)
                except (json.JSONDecodeError, ValueError) as exc:
                    return self._send_json(400, {"ok": False, "error": str(exc) or "invalid_json"})

                # ── /api/auth/login  (public — no auth check) ──────────────
                if path == "/api/auth/login":
                    return self._handle_login(payload)

                # ── All other POST routes require auth ─────────────────────
                if not self._check_auth(path):
                    return self._send_json(401, {"ok": False, "error": "unauthorized"})

                services = build_runtime_services(server_ref.config)
                db = services["db"]
                try:
                    if path in {"/api/missions", "/api/missions/create"}:
                        title = validate_str(payload.get("title"), field="title", required=True, max_len=200)
                        goal = validate_str(payload.get("goal"), field="goal", required=True, max_len=4000)
                        mode = validate_enum(
                            payload.get("mode"),
                            field="mode",
                            allowed=("general_operating_request", "deep_research", "creative", "analytical"),
                            default="general_operating_request",
                        )
                        priority = validate_enum(
                            payload.get("priority"),
                            field="priority",
                            allowed=("low", "medium", "high", "critical"),
                            default="medium",
                        )
                        result = services["mission_service"].submit_mission(
                            title=title,
                            goal=goal,
                            mode=mode,
                            priority=priority,
                            source=validate_str(payload.get("source"), field="source", max_len=64) or "api",
                            allow_24x7=validate_bool(payload.get("allow_24x7"), field="allow_24x7", default=True),
                            schedule=validate_str(payload.get("schedule"), field="schedule", max_len=128) or "api:manual",
                        )
                        return self._send_json(201, {"ok": True, **result})

                    if path.startswith("/api/missions/") and path.endswith("/pause"):
                        mission_id = path.split("/")[-2]
                        result = services["mission_service"].pause_mission(
                            mission_id,
                            actor=validate_str(payload.get("actor"), field="actor", max_len=64) or "api",
                        )
                        return self._send_json(200, result)

                    if path.startswith("/api/missions/") and path.endswith("/resume"):
                        mission_id = path.split("/")[-2]
                        result = services["mission_service"].resume_mission(
                            mission_id,
                            actor=validate_str(payload.get("actor"), field="actor", max_len=64) or "api",
                        )
                        return self._send_json(200, result)

                    if path in {"/api/intake/requests", "/api/openclaw/intake"}:
                        description = validate_str(
                            payload.get("description") or payload.get("problem") or payload.get("message"),
                            field="description",
                            max_len=8000,
                        )
                        result = services["intake_service"].submit_problem(
                            title=validate_str(payload.get("title"), field="title", max_len=200),
                            description=description,
                            priority=validate_enum(
                                payload.get("priority"),
                                field="priority",
                                allowed=("low", "medium", "high", "critical"),
                                default="medium",
                            ),
                            mode=validate_str(payload.get("mode"), field="mode", max_len=64) or None,
                            requested_by=validate_str(
                                payload.get("requested_by") or payload.get("sender"),
                                field="requested_by",
                                max_len=120,
                            ) or None,
                            channel=validate_str(
                                payload.get("channel"),
                                field="channel",
                                max_len=64,
                            ) or ("openclaw" if path.endswith("openclaw/intake") else "mobile"),
                            source=validate_str(
                                payload.get("source"),
                                field="source",
                                max_len=64,
                            ) or ("openclaw" if path.endswith("openclaw/intake") else "mobile"),
                            auto_dispatch=validate_bool(payload.get("auto_dispatch"), field="auto_dispatch", default=True),
                            details=payload.get("details") if isinstance(payload.get("details"), dict) else {},
                        )
                        return self._send_json(201, result)

                    if path.startswith("/api/missions/") and path.endswith("/hire-subagent"):
                        mission_id = path.split("/")[-2]
                        result = services["hiring_service"].hire_subagent(
                            mission_id=mission_id,
                            display_name=validate_str(
                                payload.get("display_name") or payload.get("name"),
                                field="display_name",
                                required=True,
                                max_len=100,
                            ),
                            role=validate_str(payload.get("role"), field="role", required=True, max_len=100),
                            personality=validate_str(payload.get("personality"), field="personality", max_len=500) or None,
                            capabilities=payload.get("capabilities"),
                            requested_by_agent_id=validate_str(
                                payload.get("requested_by_agent_id"),
                                field="requested_by_agent_id",
                                max_len=64,
                            ) or "agent-0",
                            reports_to=validate_str(payload.get("reports_to"), field="reports_to", max_len=64) or "agent-0",
                            budget_monthly_cents=int(payload.get("budget_monthly_cents") or 0),
                            notes=validate_str(payload.get("notes"), field="notes", max_len=1000) or None,
                            create_task=validate_bool(payload.get("create_task"), field="create_task", default=True),
                            task_title=validate_str(payload.get("task_title"), field="task_title", max_len=200) or None,
                            template_id=validate_str(payload.get("template_id"), field="template_id", max_len=64) or None,
                        )
                        return self._send_json(201, result)

                    if path.startswith("/api/hire-requests/") and path.endswith("/approve"):
                        hire_request_id = path.split("/")[-2]
                        result = services["hiring_service"].approve_hire_request(
                            hire_request_id,
                            create_task=validate_bool(payload.get("create_task"), field="create_task", default=True),
                            task_title=validate_str(payload.get("task_title"), field="task_title", max_len=200) or None,
                        )
                        return self._send_json(200, result)

                    if path.startswith("/api/action-approvals/") and path.endswith("/approve"):
                        approval_id = path.split("/")[-2]
                        result = services["approval_service"].approve(
                            approval_id,
                            approved_by=validate_str(payload.get("approved_by"), field="approved_by", max_len=64) or "api",
                            decision_notes=validate_str(payload.get("decision_notes"), field="decision_notes", max_len=1000) or None,
                        )
                        return self._send_json(200, {"ok": True, "approval": result})

                    if path.startswith("/api/action-approvals/") and path.endswith("/reject"):
                        approval_id = path.split("/")[-2]
                        result = services["approval_service"].reject(
                            approval_id,
                            approved_by=validate_str(payload.get("approved_by"), field="approved_by", max_len=64) or "api",
                            decision_notes=validate_str(payload.get("decision_notes"), field="decision_notes", max_len=1000) or None,
                        )
                        return self._send_json(200, {"ok": True, "approval": result})

                    if path.startswith("/api/intake/requests/") and path.endswith("/dispatch"):
                        request_id = path.split("/")[-2]
                        result = services["intake_service"].dispatch_request(request_id)
                        return self._send_json(200, result)

                    return self._send_json(404, {"ok": False, "error": "not_found"})
                except ValueError as error:
                    return self._send_json(400, {"ok": False, "error": str(error)})
                finally:
                    db.close()

            # ── Login handler ─────────────────────────────────────────────

            def _handle_login(self, payload: Dict) -> None:
                """
                POST /api/auth/login
                Body: { "username": str, "password": str }
                Returns: { "token": "<jwt>" } on success, 401 on failure.
                Uses constant-time comparison to resist timing attacks.
                """
                cfg = server_ref.config
                jwt_secret = cfg.jwt_secret.strip()
                stored_password = cfg.dashboard_password.strip()

                if not jwt_secret:
                    # JWT not configured — login endpoint unavailable
                    return self._send_json(503, {"ok": False, "error": "auth_not_configured"})

                if not stored_password:
                    return self._send_json(503, {"ok": False, "error": "auth_not_configured"})

                submitted_user = validate_str(payload.get("username"), field="username", max_len=128)
                submitted_pass = validate_str(payload.get("password"), field="password", max_len=256)

                user_ok = verify_password_plain(submitted_user, cfg.dashboard_username.strip())
                pass_ok = verify_password_plain(submitted_pass, stored_password)

                if not (user_ok and pass_ok):
                    return self._send_json(401, {"ok": False, "error": "invalid_credentials"})

                token = create_jwt(
                    {"sub": submitted_user, "role": "admin"},
                    jwt_secret,
                    expiry_seconds=cfg.jwt_expiry_seconds,
                )
                return self._send_json(200, {"ok": True, "token": token})

        self._server = ThreadingHTTPServer((self.config.api_host, self.config.api_port), Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="mission-control-api",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if self._server is None:
            return
        with contextlib.suppress(Exception):
            self._server.shutdown()
            self._server.server_close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._server = None
        self._thread = None

    def summary(self) -> Dict:
        return {
            "transport": "http",
            "status": "running" if self._server else "idle",
            "enabled": self.config.api_enabled,
            "host": self.config.api_host,
            "port": self.config.api_port,
            "cors_origin": self.config.api_cors_origin,
            "auth_enabled": self._auth_enabled(),
            "jwt_auth": bool(self.config.jwt_secret.strip()),
            "hire_approvals_enabled": bool(self.config.hire_approvals_enabled),
            "auto_propose_hires_enabled": bool(self.config.auto_propose_hires_enabled),
            "autonomy_budget_defaults": {
                "max_autonomous_steps": self.config.max_autonomous_steps,
                "max_estimated_tokens": self.config.max_estimated_tokens,
                "max_runtime_ticks": self.config.max_runtime_ticks,
                "max_dynamic_hires": self.config.max_dynamic_hires,
                "action_budgets": self.config.action_budgets,
            },
        }
