import json

from agents import AgentRegistry
from agent_state import AgentStateManager
from api_snapshot import RuntimeSnapshotAPI
from config import RuntimeConfig
from db import Database
from event_stream import EventStreamService
from mission_lifecycle import MissionLifecycleService
from mission_summary import MissionSummaryService
from notifications import NotificationService
from planner import Planner
from policies import PolicyEngine
from progress import ProgressNotifier
from progress_summary import ProgressSummaryService
from repository import AgentRepository, MissionRepository, NotificationRepository, PolicyRepository, TaskRepository
from scheduler import Scheduler
from settings import ProgressSettings
from templates import TemplateRegistry
from thought_log import ThoughtLogService
from status_report import StatusReportService


def main() -> None:
    config = RuntimeConfig.from_env()
    progress_settings = ProgressSettings.from_env()
    db = Database(config.db_path)
    db.init()

    mission_repository = MissionRepository(db)
    task_repository = TaskRepository(db)
    agent_repository = AgentRepository(db)
    policy_repository = PolicyRepository(db)
    notification_repository = NotificationRepository(db)

    agent_registry = AgentRegistry(config.agents_registry_path)
    template_registry = TemplateRegistry(config.templates_path)
    for record in agent_registry.to_records():
        agent_repository.upsert_agent(record)

    thought_log = ThoughtLogService(mission_repository)
    planner = Planner(
        config=config,
        mission_repository=mission_repository,
        task_repository=task_repository,
        template_registry=template_registry,
        thought_log=thought_log,
    )
    notifications = NotificationService(config=config, repository=notification_repository)
    progress_notifier = ProgressNotifier(
        mission_repository=mission_repository,
        notifications=notifications,
        mode=progress_settings.telegram_progress_mode,
    )
    policy_engine = PolicyEngine(repository=policy_repository)
    scheduler = Scheduler(mission_repository=mission_repository, task_repository=task_repository)
    state_manager = AgentStateManager(repository=agent_repository)
    lifecycle = MissionLifecycleService(mission_repository=mission_repository, task_repository=task_repository)
    event_stream = EventStreamService(mission_repository=mission_repository, notification_repository=notification_repository)
    progress_summary = ProgressSummaryService(
        mission_repository=mission_repository,
        task_repository=task_repository,
        scheduler=scheduler,
    )
    mission_summary = MissionSummaryService(mission_repository=mission_repository, task_repository=task_repository)
    snapshot_api = RuntimeSnapshotAPI(
        mission_repository=mission_repository,
        task_repository=task_repository,
        agent_repository=agent_repository,
        event_stream=event_stream,
        progress_summary=progress_summary,
        mission_summary=mission_summary,
        scheduler=scheduler,
    )
    status_report = StatusReportService(snapshot_api=snapshot_api, lifecycle=lifecycle)

    print(json.dumps({
        "environment": config.environment,
        "db_path": config.db_path,
        "templates": template_registry.summary(),
        "policies": policy_engine.summary(),
        "progress": progress_notifier.summary(),
        "scheduler": scheduler.summary(),
        "thought_log": thought_log.summary(),
        "status": status_report.build(),
    }, ensure_ascii=False, indent=2))

    db.close()


if __name__ == "__main__":
    main()
