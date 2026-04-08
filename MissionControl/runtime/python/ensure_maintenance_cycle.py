import argparse
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

from agent_state import AgentStateManager
from config import RuntimeConfig
from db import Database
from mission_service import MissionService
from notifications import NotificationService
from planner import Planner
from progress import ProgressNotifier
from repository import AgentRepository, MissionControlRepository, MissionRepository, NotificationRepository, TaskRepository
from scheduler import Scheduler
from settings import ProgressSettings
from templates import TemplateRegistry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ensure a scheduled maintenance_cycle mission exists when due"
    )
    parser.add_argument(
        "--title",
        default="Scheduled maintenance cycle",
        help="Mission title to use when a new maintenance cycle is created",
    )
    parser.add_argument(
        "--goal",
        default="Run a recurring maintenance pass, review runtime health, and surface follow-up work.",
        help="Mission goal to use when a new maintenance cycle is created",
    )
    parser.add_argument("--priority", default="medium", choices=["low", "medium", "high", "critical"])
    parser.add_argument(
        "--min-interval-hours",
        type=float,
        default=24.0,
        help="Minimum time between scheduled maintenance missions",
    )
    parser.add_argument(
        "--schedule-label",
        default="cron:daily",
        help="Schedule/cadence label stored with the mission for traceability",
    )
    parser.add_argument("--allow-24x7", action="store_true", dest="allow_24x7")
    parser.add_argument(
        "--activate-supervisor",
        action="store_true",
        help="Mark supervisor agent as planning on the created mission",
    )
    return parser.parse_args()


def parse_utc(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def due_reason(missions: List[Dict], min_interval_hours: float) -> Tuple[bool, str, Dict]:
    active = [
        mission for mission in missions
        if mission.get("mode") == "maintenance_cycle" and mission.get("status") in {"queued", "running", "blocked"}
    ]
    if active:
        current = sorted(active, key=lambda item: item["created_at"], reverse=True)[0]
        return False, "active_maintenance_exists", {
            "mission_id": current["id"],
            "status": current["status"],
            "created_at": current["created_at"],
        }

    historical = [mission for mission in missions if mission.get("mode") == "maintenance_cycle"]
    if not historical:
        return True, "no_previous_maintenance", {}

    latest = sorted(historical, key=lambda item: item["created_at"], reverse=True)[0]
    last_created_at = parse_utc(latest["created_at"])
    now = datetime.now(timezone.utc)
    elapsed = now - last_created_at
    min_interval = timedelta(hours=min_interval_hours)
    if elapsed >= min_interval:
        return True, "interval_elapsed", {
            "last_mission_id": latest["id"],
            "last_created_at": latest["created_at"],
            "elapsed_hours": round(elapsed.total_seconds() / 3600, 2),
        }

    next_due = last_created_at + min_interval
    return False, "interval_not_elapsed", {
        "last_mission_id": latest["id"],
        "last_created_at": latest["created_at"],
        "elapsed_hours": round(elapsed.total_seconds() / 3600, 2),
        "next_due_at": next_due.replace(microsecond=0).isoformat(),
    }


def main() -> None:
    args = parse_args()
    config = RuntimeConfig.from_env()
    progress_settings = ProgressSettings.from_env()
    db = Database(config.db_path)
    db.init()

    mission_repository = MissionRepository(db)
    task_repository = TaskRepository(db)
    agent_repository = AgentRepository(db)
    notification_repository = NotificationRepository(db)
    mission_control_repository = MissionControlRepository(db)

    planner = Planner(
        config=config,
        mission_repository=mission_repository,
        task_repository=task_repository,
        template_registry=TemplateRegistry(config.templates_path),
    )
    notifications = NotificationService(config=config, repository=notification_repository)
    progress_notifier = ProgressNotifier(
        mission_repository=mission_repository,
        notifications=notifications,
        mode=progress_settings.telegram_progress_mode,
    )
    scheduler = Scheduler(mission_repository=mission_repository, task_repository=task_repository)
    mission_service = MissionService(
        planner=planner,
        mission_repository=mission_repository,
        scheduler=scheduler,
        notifications=notifications,
        progress_notifier=progress_notifier,
        mission_control_repository=mission_control_repository,
        mission_control_defaults={
            "max_autonomous_steps": config.max_autonomous_steps,
            "max_estimated_tokens": config.max_estimated_tokens,
            "max_runtime_ticks": config.max_runtime_ticks,
            "max_dynamic_hires": config.max_dynamic_hires,
            "action_budgets": config.action_budgets,
        },
    )

    missions = mission_repository.list_missions()
    should_create, reason, context = due_reason(missions, args.min_interval_hours)
    response = {
        "ok": True,
        "action": "skipped",
        "reason": reason,
        "mode": "maintenance_cycle",
        "schedule": args.schedule_label,
        "context": context,
    }

    if should_create:
        result = mission_service.submit_mission(
            title=args.title,
            goal=args.goal,
            mode="maintenance_cycle",
            priority=args.priority,
            source="scheduled",
            allow_24x7=args.allow_24x7,
            schedule=args.schedule_label,
        )
        response.update({
            "action": "created",
            "reason": reason,
            "mission_id": result["mission_id"],
            "status": result["status"],
        })
        if args.activate_supervisor:
            state_manager = AgentStateManager(repository=agent_repository)
            state_manager.set_state("agent-0", "planning", mission_id=result["mission_id"])
            response["supervisor_state"] = "planning"

    print(json.dumps(response, ensure_ascii=False))
    db.close()


if __name__ == "__main__":
    main()
