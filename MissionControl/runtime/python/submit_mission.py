import argparse
import json

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Submit a Virtual Agency mission")
    parser.add_argument("title", help="Mission title")
    parser.add_argument("goal", help="Mission goal")
    parser.add_argument("--mode", default="software_build", help="Mission template/mode")
    parser.add_argument("--priority", default="medium", choices=["low", "medium", "high", "critical"])
    parser.add_argument("--source", default="manual", choices=["manual", "scheduled", "system"])
    parser.add_argument("--allow-24x7", action="store_true", dest="allow_24x7")
    parser.add_argument("--schedule", default=None, help="Optional schedule descriptor (cron label, cadence, or timestamp)")
    return parser


def main() -> None:
    args = build_parser().parse_args()

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

    result = mission_service.submit_mission(
        title=args.title,
        goal=args.goal,
        mode=args.mode,
        priority=args.priority,
        source=args.source,
        allow_24x7=args.allow_24x7,
        schedule=args.schedule,
    )

    state_manager = AgentStateManager(repository=agent_repository)
    state_manager.set_state("agent-0", "planning", mission_id=result["mission_id"])

    print(json.dumps({
        "ok": True,
        "mission_id": result["mission_id"],
        "status": result["status"],
        "mode": args.mode,
        "priority": args.priority,
        "schedule": args.schedule,
    }, ensure_ascii=False))
    db.close()


if __name__ == "__main__":
    main()

