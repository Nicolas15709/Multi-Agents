import json
from pathlib import Path

from api_snapshot import RuntimeSnapshotAPI
from config import RuntimeConfig
from db import Database
from event_stream import EventStreamService
from mission_summary import MissionSummaryService
from progress_summary import ProgressSummaryService
from repository import AgentHireRequestRepository, AgentRepository, IntakeRequestRepository, MissionControlRepository, MissionRepository, NotificationRepository, TaskRepository
from scheduler import Scheduler
from storage import ensure_parent


def main() -> None:
    config = RuntimeConfig.from_env()
    db = Database(config.db_path)
    db.init()

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

    snapshot = snapshot_api.snapshot()
    dashboard_dir = Path(__file__).resolve().parent.parent.parent / 'apps' / 'dashboard'
    output_paths = [
        dashboard_dir / 'public' / 'snapshot.json',
        dashboard_dir / 'dist' / 'snapshot.json',
    ]

    for output_path in output_paths:
        ensure_parent(str(output_path))
        output_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
        print(output_path)

    db.close()


if __name__ == '__main__':
    main()
