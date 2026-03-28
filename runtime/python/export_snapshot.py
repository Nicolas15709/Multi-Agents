import json
from pathlib import Path

from agent_state import AgentStateManager
from api_snapshot import RuntimeSnapshotAPI
from agents import AgentRegistry
from config import RuntimeConfig
from db import Database
from event_stream import EventStreamService
from repository import AgentRepository, MissionRepository, NotificationRepository, TaskRepository
from storage import ensure_parent


def main() -> None:
    config = RuntimeConfig.from_env()
    db = Database(config.db_path)
    db.init()

    mission_repository = MissionRepository(db)
    task_repository = TaskRepository(db)
    agent_repository = AgentRepository(db)
    notification_repository = NotificationRepository(db)

    snapshot_api = RuntimeSnapshotAPI(
        mission_repository=mission_repository,
        task_repository=task_repository,
        agent_repository=agent_repository,
        event_stream=EventStreamService(
            mission_repository=mission_repository,
            notification_repository=notification_repository,
        ),
    )

    snapshot = snapshot_api.snapshot()
    output_path = Path(__file__).resolve().parent.parent.parent / 'apps' / 'dashboard' / 'public' / 'snapshot.json'
    ensure_parent(str(output_path))
    output_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
    print(output_path)
    db.close()


if __name__ == '__main__':
    main()
