"""Virtual Agency Python runtime entrypoint (persistent working scaffold)."""

import json
import time
from pathlib import Path

from approval_service import ActionApprovalService
from agents import AgentRegistry
from agent_state import AgentStateManager
from api_snapshot import RuntimeSnapshotAPI
from config import RuntimeConfig
from coordination_service import CoordinationService
from db import Database
from event_stream import EventStreamService
from hiring_service import HiringService
from http_api import RuntimeApiServer
from intake_service import IntakeService
from llm_support import detect_execution_backend
from mission_lifecycle import MissionLifecycleService
from mission_service import MissionService
from mission_summary import MissionSummaryService
from notifications import NotificationService
from planner import Planner
from policies import PolicyEngine
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
    PolicyRepository,
    TaskRepository,
)
from runtime_state import RuntimeStateHydrator
from scheduler import Scheduler
from settings import ProgressSettings
from specialist_templates import SpecialistTemplateCatalog
from startup_recovery import StartupRecoveryService
from state_machine import StateHistory, StateReconciler, TransactionalStateUpdater
from status_report import StatusReportService
from storage import ensure_parent
from task_runner import TaskRunner
from templates import TemplateRegistry
from thought_log import ThoughtLogService
from websocket_server import WebSocketPublisher

# ── New intelligence modules (Puntos 2–6) ─────────────────────────────────────
from memory_distiller import MemoryDistiller
try:
    from stagnation_detector import StagnationDetector
except ImportError:
    StagnationDetector = None  # type: ignore[assignment,misc]
try:
    from intervention_policy import InterventionPolicy, get_default_policy
except ImportError:
    InterventionPolicy = None  # type: ignore[assignment,misc]
    get_default_policy = None  # type: ignore[assignment]


def bootstrap_agents(agent_repository: AgentRepository, registry: AgentRegistry) -> None:
    for record in registry.to_records():
        agent_repository.upsert_agent(record)


def export_snapshot(snapshot: dict) -> str:
    dashboard_dir = Path(__file__).resolve().parent.parent.parent / 'apps' / 'dashboard'
    output_paths = [
        dashboard_dir / 'public' / 'snapshot.json',
        dashboard_dir / 'dist' / 'snapshot.json',
    ]

    written_paths = []
    for output_path in output_paths:
        ensure_parent(str(output_path))
        output_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
        written_paths.append(str(output_path))

    return written_paths[0]


def runtime_tick(
    mission_repository: MissionRepository,
    task_repository: TaskRepository,
    agent_repository: AgentRepository,
    mission_control_repository: MissionControlRepository,
    scheduler: Scheduler,
    state_manager: AgentStateManager,
    mission_service: MissionService,
    lifecycle: MissionLifecycleService,
    hydrator: RuntimeStateHydrator,
    task_runner: TaskRunner,
    intake_service: IntakeService,
    snapshot_api: RuntimeSnapshotAPI,
    publisher: WebSocketPublisher,
    distiller: MemoryDistiller,
    stagnation_detector=None,
    policy=None,
) -> dict:
    if not mission_repository.list_missions():
        result = mission_service.submit_mission(
            title="Virtual Agency bootstrap mission",
            goal="Initialize the orchestrator scaffold and validate core runtime pieces.",
            mode="software_build",
            priority="medium",
            source="system",
            allow_24x7=True,
        )
        state_manager.set_state("agent-0", "planning", mission_id=result["mission_id"])

    rehydration = hydrator.reconcile()
    reconciled_requests = intake_service.reconcile_requests(limit=10)
    dispatched_requests = intake_service.dispatch_pending_requests(limit=3)
    top_mission = scheduler.highest_priority_mission()
    runner_result = None
    stagnation_signal = None

    if top_mission:
        mission_id = top_mission["id"]
        lifecycle.activate(mission_id)

        # ── Punto 4: Stagnation detection (before advancing tasks) ────────────
        if stagnation_detector is not None:
            try:
                tasks_snapshot = task_repository.list_tasks_for_mission(mission_id)
                mc_record = None
                try:
                    mc_record = mission_control_repository.get_for_mission(mission_id)
                except Exception:
                    pass
                stagnation_signal = stagnation_detector.check(mission_id, tasks_snapshot, mc_record)
                if stagnation_signal and stagnation_signal.detected:
                    # ── Punto 6: Intervention policy decision ─────────────────
                    if policy is not None:
                        decision = policy.evaluate(
                            f"stagnation_{stagnation_signal.severity}",
                            {
                                "mission_id": mission_id,
                                "reason": stagnation_signal.reason,
                                "recommendation": stagnation_signal.recommendation,
                                "affected_task_id": stagnation_signal.affected_task_id,
                            },
                        )
                        if decision.action == "halt":
                            mission_repository.add_event(
                                mission_id, "mission_halted_stagnation", "stagnation_detector",
                                f"Mission halted: {stagnation_signal.reason}",
                                {"severity": stagnation_signal.severity, "signal": stagnation_signal.reason},
                            )
                            mission_repository.update_mission_status(mission_id, "needs_human")
                            runner_result = {
                                "status": "halted_stagnation",
                                "mission_id": mission_id,
                                "reason": stagnation_signal.reason,
                                "severity": stagnation_signal.severity,
                            }
                            # Skip task advancement this tick
                            lifecycle.mark_mission_done_if_ready(mission_id)
                            snapshot = snapshot_api.snapshot()
                            snapshot_path = export_snapshot(snapshot)
                            publisher.publish_snapshot(snapshot)
                            return {
                                "rehydration": rehydration,
                                "reconciled_requests": reconciled_requests,
                                "dispatched_requests": dispatched_requests,
                                "runner": runner_result,
                                "stagnation": stagnation_signal.reason,
                                "snapshot_path": snapshot_path,
                                "missions": len(mission_repository.list_missions()),
                                "agents": len(agent_repository.list_agents()),
                                "top_mission": mission_id,
                            }
            except Exception as exc:
                import logging
                logging.getLogger("main").error("Stagnation check failed: %s", exc)

        runner_result = task_runner.advance_next_task(mission_id)

        # ── Punto 6: Policy check on significant runner events ────────────────
        if policy is not None and runner_result:
            event_type = runner_result.get("status", "")
            if event_type in {"budget_exhausted", "needs_human"}:
                try:
                    policy.evaluate(event_type, {"mission_id": mission_id, **runner_result})
                except Exception:
                    pass

        lifecycle.mark_mission_done_if_ready(mission_id)

        # ── Punto 2: Memory distillation after mission completes ──────────────
        try:
            mission_now = mission_repository.get_mission(mission_id)
            if mission_now and mission_now.get("status") == "completed":
                distiller.distill_mission(mission_id, mission_repository, task_repository)
        except Exception as exc:
            import logging
            logging.getLogger("main").error("Memory distillation failed: %s", exc)

    snapshot = snapshot_api.snapshot()
    snapshot_path = export_snapshot(snapshot)
    publisher.publish_snapshot(snapshot)

    return {
        "rehydration": rehydration,
        "reconciled_requests": reconciled_requests,
        "dispatched_requests": dispatched_requests,
        "runner": runner_result,
        "stagnation": stagnation_signal.reason if stagnation_signal and stagnation_signal.detected else None,
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
    intake_repository = IntakeRequestRepository(db)
    hire_request_repository = AgentHireRequestRepository(db)
    mission_control_repository = MissionControlRepository(db)
    mission_memory_repository = MissionMemoryRepository(db)
    agent_message_repository = AgentMessageRepository(db)
    action_approval_repository = ActionApprovalRepository(db)

    agent_registry = AgentRegistry(config.agents_registry_path)
    template_registry = TemplateRegistry(config.templates_path)
    specialist_template_catalog = SpecialistTemplateCatalog(config.specialist_templates_root)
    bootstrap_agents(agent_repository, agent_registry)

    # Initialize state management infrastructure
    state_history = StateHistory()
    state_updater = TransactionalStateUpdater(
        mission_repository=mission_repository,
        task_repository=task_repository,
        state_history=state_history
    )
    state_reconciler = StateReconciler(
        mission_repository=mission_repository,
        task_repository=task_repository,
        state_updater=state_updater
    )

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
    scheduler = Scheduler(
        mission_repository=mission_repository,
        task_repository=task_repository,
        state_updater=state_updater
    )
    state_manager = AgentStateManager(repository=agent_repository, state_updater=state_updater)
    mission_service = MissionService(
        planner=planner,
        mission_repository=mission_repository,
        scheduler=scheduler,
        notifications=notifications,
        progress_notifier=progress_notifier,
        state_updater=state_updater,
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
    lifecycle = MissionLifecycleService(
        mission_repository=mission_repository,
        task_repository=task_repository,
        state_updater=state_updater
    )
    intake_service = IntakeService(
        intake_repository=intake_repository,
        mission_repository=mission_repository,
        mission_service=mission_service,
        notifications=notifications,
        agent_state_manager=state_manager,
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
    event_stream = EventStreamService(mission_repository=mission_repository, notification_repository=notification_repository)
    publisher = WebSocketPublisher(config=config)
    publisher.start()
    api_server = RuntimeApiServer(config=config)
    api_server.start()
    hydrator = RuntimeStateHydrator(
        mission_repository=mission_repository,
        task_repository=task_repository,
        agent_state_manager=state_manager,
        scheduler=scheduler,
    )
    task_runner = TaskRunner(
        mission_repository=mission_repository,
        task_repository=task_repository,
        mission_control_repository=mission_control_repository,
        agent_state_manager=state_manager,
        progress_notifier=progress_notifier,
        state_updater=state_updater,
        coordination_service=coordination_service,
        approval_service=approval_service,
    )
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
        intake_repository=intake_repository,
        hire_request_repository=hire_request_repository,
        mission_control_repository=mission_control_repository,
        mission_memory_repository=mission_memory_repository,
        agent_message_repository=agent_message_repository,
        action_approval_repository=action_approval_repository,
    )
    recovery = StartupRecoveryService(
        mission_repository=mission_repository,
        task_repository=task_repository,
        agent_state_manager=state_manager,
        scheduler=scheduler,
        state_updater=state_updater,
        state_reconciler=state_reconciler,
    )
    startup_recovery = recovery.recover()
    status_report = StatusReportService(snapshot_api=snapshot_api, lifecycle=lifecycle, recovery=recovery)

    # ── Intelligence modules (Puntos 2–6) ─────────────────────────────────────
    distiller = MemoryDistiller()
    stagnation_detector = StagnationDetector() if StagnationDetector is not None else None
    policy = get_default_policy() if get_default_policy is not None else None
    llm_backend = detect_execution_backend()

    print("Virtual Agency runtime")
    print({
        "environment": config.environment,
        "db_path": config.db_path,
        "tick_interval_seconds": config.tick_interval_seconds,
        "websocket_enabled": config.websocket_enabled,
        "websocket_host": config.websocket_host,
        "websocket_port": config.websocket_port,
        "api_enabled": config.api_enabled,
        "api_host": config.api_host,
        "api_port": config.api_port,
        "telegram_notifications": config.telegram_notifications_enabled,
        "templates": template_registry.summary(),
        "specialist_templates": specialist_template_catalog.summary(),
        "policies": policy_engine.summary(),
        "notifications": notifications.summary(),
        "progress": progress_notifier.summary(),
        "planner": planner.summary(),
        "api": api_server.summary(),
        "llm_execution": llm_backend,
        "auto_propose_hires_enabled": config.auto_propose_hires_enabled,
        "autonomy_budget_defaults": {
            "max_autonomous_steps": config.max_autonomous_steps,
            "max_estimated_tokens": config.max_estimated_tokens,
            "max_runtime_ticks": config.max_runtime_ticks,
            "max_dynamic_hires": config.max_dynamic_hires,
            "action_budgets": config.action_budgets,
        },
        "thought_log": thought_log.summary(),
        "startup_recovery": startup_recovery,
        "status": status_report.build(),
    })

    try:
        while True:
            tick = runtime_tick(
                mission_repository=mission_repository,
                task_repository=task_repository,
                agent_repository=agent_repository,
                mission_control_repository=mission_control_repository,
                scheduler=scheduler,
                state_manager=state_manager,
                mission_service=mission_service,
                lifecycle=lifecycle,
                hydrator=hydrator,
                task_runner=task_runner,
                intake_service=intake_service,
                snapshot_api=snapshot_api,
                publisher=publisher,
                distiller=distiller,
                stagnation_detector=stagnation_detector,
                policy=policy,
            )
            print({
                "scheduler": scheduler.summary(),
                "agent_states": state_manager.summary(),
                "event_stream": event_stream.summary(),
                "publisher": publisher.summary(),
                "api": api_server.summary(),
                "status": status_report.build(),
                "tick": tick,
            })
            time.sleep(config.tick_interval_seconds)
    except KeyboardInterrupt:
        print("Virtual Agency runtime stopped")
    finally:
        api_server.stop()
        publisher.stop()
        db.close()


if __name__ == "__main__":
    main()

