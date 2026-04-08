import argparse
import json
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from api_snapshot import RuntimeSnapshotAPI
from config import RuntimeConfig
from db import Database
from event_stream import EventStreamService
from mission_lifecycle import MissionLifecycleService
from mission_summary import MissionSummaryService
from progress_summary import ProgressSummaryService
from repository import AgentHireRequestRepository, AgentRepository, IntakeRequestRepository, MissionControlRepository, MissionRepository, NotificationRepository, TaskRepository
from scheduler import Scheduler
from startup_recovery import StartupRecoveryService
from status_report import StatusReportService

SEVERITY_ORDER = {"critical": 3, "warning": 2, "info": 1}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Operational diagnostics for Virtual Agency runtime")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of a text report")
    parser.add_argument(
        "--snapshot-max-age-minutes",
        type=float,
        default=15.0,
        help="Warn when exported dashboard snapshots are older than this threshold",
    )
    parser.add_argument(
        "--systemd-unit",
        default="virtual-agency.service",
        help="systemd unit name to inspect when systemctl is available",
    )
    return parser.parse_args()


def parse_utc(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def minutes_since(dt: Optional[datetime]) -> Optional[float]:
    if not dt:
        return None
    return round((datetime.now(timezone.utc) - dt).total_seconds() / 60, 2)


def socket_is_open(host: str, port: int, timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def run_systemctl(*args: str) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            ["systemctl", *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return False, "systemctl unavailable"
    output = (result.stdout or result.stderr or "").strip()
    return result.returncode == 0, output


def add_check(checks: List[Dict], name: str, status: str, summary: str, details: Optional[Dict] = None) -> None:
    checks.append({
        "name": name,
        "status": status,
        "summary": summary,
        "details": details or {},
    })


def build_snapshot_api(config: RuntimeConfig, db: Database) -> Tuple[RuntimeSnapshotAPI, Scheduler, MissionRepository, TaskRepository, AgentRepository, NotificationRepository]:
    mission_repository = MissionRepository(db)
    task_repository = TaskRepository(db)
    agent_repository = AgentRepository(db)
    notification_repository = NotificationRepository(db)
    intake_repository = IntakeRequestRepository(db)
    hire_request_repository = AgentHireRequestRepository(db)
    mission_control_repository = MissionControlRepository(db)
    scheduler = Scheduler(mission_repository=mission_repository, task_repository=task_repository)
    snapshot_api = RuntimeSnapshotAPI(
        mission_repository=mission_repository,
        task_repository=task_repository,
        agent_repository=agent_repository,
        event_stream=EventStreamService(
            mission_repository=mission_repository,
            notification_repository=notification_repository,
        ),
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
    )
    return snapshot_api, scheduler, mission_repository, task_repository, agent_repository, notification_repository


def evaluate(config: RuntimeConfig, snapshot_max_age_minutes: float, systemd_unit: str) -> Dict:
    checks: List[Dict] = []
    db_path = Path(config.db_path).resolve()
    specialist_templates_root = Path(config.specialist_templates_root).resolve()
    dashboard_dir = Path(__file__).resolve().parent.parent.parent / "apps" / "dashboard"
    snapshot_paths = [dashboard_dir / "public" / "snapshot.json", dashboard_dir / "dist" / "snapshot.json"]

    db_exists = db_path.exists()
    add_check(
        checks,
        "database_file",
        "ok" if db_exists else "critical",
        f"Runtime database {'found' if db_exists else 'missing'} at {db_path}",
        {"path": str(db_path)},
    )

    if db_exists:
        writable = db_path.parent.exists() and db_path.parent.is_dir()
        add_check(
            checks,
            "database_directory",
            "ok" if writable else "critical",
            f"Database directory {'is present' if writable else 'is missing'}",
            {"path": str(db_path.parent)},
        )

    add_check(
        checks,
        "specialist_catalog",
        "ok" if specialist_templates_root.exists() else "warning",
        f"Specialist template catalog {'found' if specialist_templates_root.exists() else 'missing'} at {specialist_templates_root}",
        {"path": str(specialist_templates_root)},
    )

    db = Database(config.db_path)
    db.init()
    try:
        snapshot_api, scheduler, mission_repository, task_repository, agent_repository, _ = build_snapshot_api(config, db)
        lifecycle = MissionLifecycleService(mission_repository=mission_repository, task_repository=task_repository)
        recovery = StartupRecoveryService(
            mission_repository=mission_repository,
            task_repository=task_repository,
            agent_state_manager=None,
            scheduler=scheduler,
        )
        status = StatusReportService(snapshot_api=snapshot_api, lifecycle=lifecycle, recovery=recovery).build()

        mission = status.get("mission")
        mission_control = status.get("mission_control") or {}
        health = status.get("health", {})
        recovery_summary = status.get("runtime", {}).get("recovery", {})
        active_agents = status.get("runtime", {}).get("active_agents", [])
        progress = status.get("progress", {})

        if mission:
            add_check(
                checks,
                "focus_mission",
                "ok",
                f"Focus mission: {mission['title']} ({mission['status']}, {mission['priority']})",
                {"mission": mission, "progress": progress},
            )
        else:
            add_check(checks, "focus_mission", "warning", "No mission is currently queued or running")

        if health.get("blocked_tasks", 0) > 0 or health.get("blocked_mission_count", 0) > 0:
            add_check(
                checks,
                "blocked_work",
                "warning",
                "Runtime has blocked tasks or blocked missions that need operator review",
                {
                    "blocked_tasks": health.get("blocked_tasks", 0),
                    "blocked_missions": health.get("blocked_mission_count", 0),
                },
            )
        else:
            add_check(checks, "blocked_work", "ok", "No blocked tasks or missions detected")

        if mission and progress.get("running", 0) == 0 and mission.get("status") in {"queued", "running"}:
            add_check(
                checks,
                "execution_liveness",
                "warning",
                "Focus mission is active but no task is currently running",
                {"mission_id": mission.get("id"), "progress": progress, "active_agents": len(active_agents)},
            )
        else:
            add_check(
                checks,
                "execution_liveness",
                "ok",
                "Runtime has active execution flow or no active work is expected",
                {"active_agents": len(active_agents), "running_tasks": progress.get("running", 0)},
            )

        if mission_control:
            if mission_control.get("status") == "exhausted":
                add_check(
                    checks,
                    "autonomy_budget",
                    "warning",
                    "Active mission autonomy budget is exhausted; operator approval or budget increase is required",
                    mission_control,
                )
            else:
                add_check(
                    checks,
                    "autonomy_budget",
                    "ok",
                    "Active mission autonomy budget is available",
                    mission_control,
                )

        if recovery_summary.get("status") == "needs_recovery":
            add_check(
                checks,
                "startup_recovery",
                "warning",
                "Runtime state suggests stale tasks or mission status drift after restart",
                recovery_summary,
            )
        else:
            add_check(
                checks,
                "startup_recovery",
                "ok",
                f"Startup recovery state: {recovery_summary.get('status', 'unknown')}",
                recovery_summary,
            )

        add_check(
            checks,
            "mission_inventory",
            "ok",
            "Runtime inventory loaded",
            {
                "missions": len(mission_repository.list_missions()),
                "agents": len(agent_repository.list_agents()),
                "queued_missions": health.get("queued_mission_count", 0),
            },
        )
    finally:
        db.close()

    snapshot_details = []
    stale_snapshots = []
    missing_snapshots = []
    for path in snapshot_paths:
        if not path.exists():
            missing_snapshots.append(str(path))
            snapshot_details.append({"path": str(path), "exists": False})
            continue
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        age_minutes = minutes_since(modified_at)
        entry = {
            "path": str(path),
            "exists": True,
            "modified_at": modified_at.replace(microsecond=0).isoformat(),
            "age_minutes": age_minutes,
        }
        snapshot_details.append(entry)
        if age_minutes is not None and age_minutes > snapshot_max_age_minutes:
            stale_snapshots.append(entry)

    if missing_snapshots:
        add_check(
            checks,
            "dashboard_snapshots",
            "warning",
            "One or more exported dashboard snapshot files are missing",
            {"missing": missing_snapshots, "snapshots": snapshot_details},
        )
    elif stale_snapshots:
        add_check(
            checks,
            "dashboard_snapshots",
            "warning",
            "Dashboard snapshots are present but stale; runtime export may not be updating",
            {"stale": stale_snapshots, "snapshots": snapshot_details, "max_age_minutes": snapshot_max_age_minutes},
        )
    else:
        add_check(
            checks,
            "dashboard_snapshots",
            "ok",
            "Dashboard snapshots are present and fresh",
            {"snapshots": snapshot_details, "max_age_minutes": snapshot_max_age_minutes},
        )

    websocket_host = config.websocket_host
    reachable_host = "127.0.0.1" if websocket_host == "0.0.0.0" else websocket_host
    if config.websocket_enabled:
        socket_open = socket_is_open(reachable_host, config.websocket_port)
        add_check(
            checks,
            "websocket_listener",
            "ok" if socket_open else "warning",
            f"WebSocket listener {'is reachable' if socket_open else 'is not reachable'} on {reachable_host}:{config.websocket_port}",
            {
                "enabled": True,
                "configured_host": websocket_host,
                "reachable_host": reachable_host,
                "port": config.websocket_port,
            },
        )
    else:
        add_check(
            checks,
            "websocket_listener",
            "warning",
            "WebSocket publishing is disabled; dashboard live feed will rely on static snapshots",
            {"enabled": False},
        )

    systemctl_ok, is_active = run_systemctl("is-active", systemd_unit)
    if is_active == "systemctl unavailable":
        add_check(checks, "systemd_unit", "info", "systemctl is unavailable in this environment")
    else:
        unit_status = "ok" if systemctl_ok and is_active == "active" else "warning"
        add_check(
            checks,
            "systemd_unit",
            unit_status,
            f"systemd unit {systemd_unit}: {is_active or 'unknown'}",
            {"unit": systemd_unit},
        )

    overall_status = "ok"
    if any(check["status"] == "critical" for check in checks):
        overall_status = "critical"
    elif any(check["status"] == "warning" for check in checks):
        overall_status = "warning"

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "overall_status": overall_status,
        "config": {
            "environment": config.environment,
            "db_path": config.db_path,
            "websocket_enabled": config.websocket_enabled,
            "websocket_host": config.websocket_host,
            "websocket_port": config.websocket_port,
            "max_autonomous_steps": config.max_autonomous_steps,
            "max_estimated_tokens": config.max_estimated_tokens,
            "max_runtime_ticks": config.max_runtime_ticks,
            "max_dynamic_hires": config.max_dynamic_hires,
            "tick_interval_seconds": config.tick_interval_seconds,
            "agents_registry_path": config.agents_registry_path,
            "templates_path": config.templates_path,
            "specialist_templates_root": config.specialist_templates_root,
        },
        "checks": sorted(checks, key=lambda item: SEVERITY_ORDER.get(item["status"], 0), reverse=True),
    }


def render_text(report: Dict) -> str:
    lines = [
        f"Virtual Agency doctor: {report['overall_status'].upper()}",
        f"Generated at: {report['generated_at']}",
        "",
    ]
    for check in report["checks"]:
        lines.append(f"[{check['status'].upper()}] {check['name']}: {check['summary']}")
        details = check.get("details") or {}
        if details:
            details_text = json.dumps(details, ensure_ascii=False, sort_keys=True)
            lines.append(f"  details: {details_text}")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    config = RuntimeConfig.from_env()
    report = evaluate(
        config=config,
        snapshot_max_age_minutes=args.snapshot_max_age_minutes,
        systemd_unit=args.systemd_unit,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))


if __name__ == "__main__":
    main()


