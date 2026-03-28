"""Mission Control Python runtime entrypoint (persistent working scaffold)."""

import json
import time
from pathlib import Path

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
from storage import ensure_parent
from task_runner import TaskRunner
from templates import TemplateRegistry
from websocket_server import WebSocketPublisher


def bootstrap_agents(agent_repository: AgentRepository, registry: AgentRegistry) -> None:
    for record in registry.to_records():
        agent_repository.upsert_agent(record)


def export_snapshot(snapshot: dict) -> str:
    output_path = Path(__file__).resolve().parent.parent.parent / 'apps' / 'dashboard' / 'public' / 'snapshot.json'
    ensure_parent(str(output_path))
    output_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
    return str(output_path)


def runtime_tick(
    mission_repository: MissionRepository,
    task_repository: TaskRepository,
    agent_repository: AgentRepository,
    scheduler: Scheduler,
    state_manager: AgentStateManager,
    mission_service: MissionService,
    hydrator: RuntimeStateHydrator,
    task_runner: TaskRunner,
    snapshot_api: RuntimeSnapshotAPI,
    publisher: WebSocketPublisher,
) -> dict:
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
    snapshot_path = export_snapshot(snapshot)
    publisher.publish_snapshot(snapshot)

    return {
        "rehydration": rehydration,
        "runner": runner_result,
        "snapshot_path": snapshot_path,
        "missions": len(mission_repository.list_missions()),
        "agents": len(agent_repository.list_agents()),
        "top_mission": top_mission["id"] if top_mission else None,
    }


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
    publisher.start()
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

    print("Mission Control runtime")
    print({
        "environment": config.environment,
        "db_path": config.db_path,
        "tick_interval_seconds": config.tick_interval_seconds,
        "websocket_enabled": config.websocket_enabled,
        "websocket_host": config.websocket_host,
        "websocket_port": config.websocket_port,
        "telegram_notifications": config.telegram_notifications_enabled,
        "templates": template_registry.summary(),
        "policies": policy_engine.summary(),
        "notifications": notifications.summary(),
        "progress": progress_notifier.summary(),
        "planner": planner.summary(),
    })

    try:
        while True:
            tick = runtime_tick(
                mission_repository=mission_repository,
                task_repository=task_repository,
                agent_repository=agent_repository,
                scheduler=scheduler,
                state_manager=state_manager,
                mission_service=mission_service,
                hydrator=hydrator,
                task_runner=task_runner,
                snapshot_api=snapshot_api,
                publisher=publisher,
            )
            print({
                "scheduler": scheduler.summary(),
                "agent_states": state_manager.summary(),
                "event_stream": event_stream.summary(),
                "publisher": publisher.summary(),
                "tick": tick,
            })
            time.sleep(config.tick_interval_seconds)
    except KeyboardInterrupt:
        print("Mission Control runtime stopped")
    finally:
        publisher.stop()
        db.close()


if __name__ == "__main__":
    main()
