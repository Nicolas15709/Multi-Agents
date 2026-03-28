"""Mission Control Python runtime entrypoint (working scaffold)."""

from agents import AgentRegistry
from agent_state import AgentStateManager
from api_snapshot import RuntimeSnapshotAPI
from config import RuntimeConfig
from db import Database
from event_stream import EventStreamService
from notifications import NotificationService
from planner import Planner
from policies import PolicyEngine
from progress import ProgressNotifier
from repository import AgentRepository, MissionRepository, NotificationRepository, PolicyRepository, TaskRepository
from runtime_state import RuntimeStateHydrator
from scheduler import Scheduler
from mission_service import MissionService
from settings import ProgressSettings
from task_runner import TaskRunner
from templates import TemplateRegistry
from websocket_server import WebSocketPublisher


def bootstrap_agents(agent_repository: AgentRepository, registry: AgentRegistry) -> None:
    for record in registry.to_records():
        agent_repository.upsert_agent(record)


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
    bootstrap_agents(agent_repository, agent_registry)

    planner = Planner(config=config, mission_repository=mission_repository, task_repository=task_repository)
    notifications = NotificationService(config=config, repository=notification_repository)
    progress_notifier = ProgressNotifier(
        mission_repository=mission_repository,
        notifications=notifications,
        mode=progress_settings.telegram_progress_mode,
    )
    policy_engine = PolicyEngine(repository=policy_repository)
    scheduler = Scheduler(mission_repository=mission_repository, task_repository=task_repository)
    state_manager = AgentStateManager(repository=agent_repository)
    mission_service = MissionService(
        planner=planner,
        mission_repository=mission_repository,
        scheduler=scheduler,
        notifications=notifications,
        progress_notifier=progress_notifier,
    )
    event_stream = EventStreamService(mission_repository=mission_repository, notification_repository=notification_repository)
    publisher = WebSocketPublisher(config=config)
    hydrator = RuntimeStateHydrator(
        mission_repository=mission_repository,
        task_repository=task_repository,
        agent_state_manager=state_manager,
    )
    task_runner = TaskRunner(
        mission_repository=mission_repository,
        task_repository=task_repository,
        agent_state_manager=state_manager,
        progress_notifier=progress_notifier,
    )
    snapshot_api = RuntimeSnapshotAPI(
        mission_repository=mission_repository,
        task_repository=task_repository,
        agent_repository=agent_repository,
        event_stream=event_stream,
    )

    if not mission_repository.list_missions():
        result = mission_service.submit_mission(
            title="Mission Control bootstrap mission",
            goal="Initialize the orchestrator scaffold and validate core runtime pieces.",
            mode="software_build",
            priority="medium",
            source="system",
            allow_24x7=True,
        )
        state_manager.set_state("agent-0", "planning", mission_id=result["mission_id"])

    rehydration = hydrator.reconcile()
    top_mission = scheduler.highest_priority_mission()
    runner_result = None
    if top_mission:
        runner_result = task_runner.advance_next_task(top_mission["id"])

    snapshot = snapshot_api.snapshot()
    publisher.publish_snapshot(snapshot)

    print("Mission Control runtime")
    print({
        "environment": config.environment,
        "db_path": config.db_path,
        "websocket_enabled": config.websocket_enabled,
        "telegram_notifications": config.telegram_notifications_enabled,
        "agents": len(agent_repository.list_agents()),
        "missions": len(mission_repository.list_missions()),
        "templates": template_registry.summary(),
        "policies": policy_engine.summary(),
        "notifications": notifications.summary(),
        "progress": progress_notifier.summary(),
        "scheduler": scheduler.summary(),
        "agent_states": state_manager.summary(),
        "event_stream": event_stream.summary(),
        "publisher": publisher.summary(),
        "planner": planner.summary(),
        "rehydration": rehydration,
        "runner": runner_result,
        "snapshot_keys": list(snapshot.keys()),
    })

    db.close()


if __name__ == "__main__":
    main()
