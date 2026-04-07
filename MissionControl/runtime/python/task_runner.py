"""Task execution runner with state machine validation."""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

try:
    from .agent_executor import TaskExecutionManager, get_execution_manager
    from .approval_service import ActionApprovalService
    from .agent_state import AgentStateManager
    from .coordination_service import CoordinationService
    from .progress import ProgressNotifier
    from .repository import MissionControlRepository, MissionRepository, TaskRepository
    from .state_machine import StateValidationError, TransactionalStateUpdater
except ImportError:  # pragma: no cover - runtime script compatibility
    from agent_executor import TaskExecutionManager, get_execution_manager
    from approval_service import ActionApprovalService
    from agent_state import AgentStateManager
    from coordination_service import CoordinationService
    from progress import ProgressNotifier
    from repository import MissionControlRepository, MissionRepository, TaskRepository
    from state_machine import StateValidationError, TransactionalStateUpdater

logger = logging.getLogger("task_runner")


STATE_BY_AGENT = {
    "agent-0": "planning",
    "agent-1": "researching",
    "agent-2": "designing",
    "agent-3": "building",
    "agent-4": "reviewing",
}

ESTIMATED_TOKENS_BY_PHASE = {
    "lead_plan": 900,
    "research": 1600,
    "strategy": 1300,
    "design": 1400,
    "build": 2200,
    "documentation": 1100,
    "outreach": 1500,
    "review": 1500,
    "lead_closeout": 900,
    "specialist_hire": 1800,
}


@dataclass
class TaskRunner:
    mission_repository: MissionRepository
    task_repository: TaskRepository
    mission_control_repository: Optional[MissionControlRepository]
    agent_state_manager: AgentStateManager
    progress_notifier: ProgressNotifier
    state_updater: Optional[TransactionalStateUpdater] = None
    coordination_service: Optional[CoordinationService] = None
    approval_service: Optional[ActionApprovalService] = None
    # LLM execution manager — None = simulation mode (backwards compatible)
    execution_manager: Optional[TaskExecutionManager] = field(
        default=None, repr=False
    )

    def __post_init__(self) -> None:
        # Auto-initialise if ANTHROPIC_API_KEY is present in env
        if self.execution_manager is None:
            import os
            if os.environ.get("ANTHROPIC_API_KEY"):
                self.execution_manager = get_execution_manager()
                logger.info("LLM execution enabled (ANTHROPIC_API_KEY found)")
            else:
                logger.warning(
                    "ANTHROPIC_API_KEY not set — running in simulation mode. "
                    "Tasks will be marked done without real LLM execution."
                )

    def _estimate_task_tokens(self, task: Dict) -> int:
        details = task.get("details") or {}
        return int(ESTIMATED_TOKENS_BY_PHASE.get(details.get("phase_kind") or "build", 1200))

    def _halt_for_budget(self, mission_id: str, mission: Dict, *, reason: str, payload: Dict) -> Dict:
        if self.mission_control_repository:
            self.mission_control_repository.update_status(mission_id, status="exhausted", notes=reason)
        if mission.get("status") != "needs_human":
            self._transition_mission_if_needed(
                mission_id,
                mission.get("status"),
                "needs_human",
                reason=reason,
                actor="task_runner",
            )
        self.mission_repository.add_event(
            mission_id,
            "mission_budget_exhausted",
            "task_runner",
            f"Mission autonomy budget exhausted: {reason}",
            payload,
        )
        self.progress_notifier.notify(
            mission_id,
            "blocked",
            "La mision se freno por presupuesto autonomo para evitar gasto o loops innecesarios.",
            payload,
        )
        return {
            "status": "budget_exhausted",
            "mission_id": mission_id,
            "reason": reason,
            **payload,
        }

    def _consume_tick_or_halt(self, mission_id: str, mission: Dict) -> Optional[Dict]:
        if not self.mission_control_repository:
            return None
        control = self.mission_control_repository.get_control(mission_id)
        if not control:
            return None
        used_ticks = int(control.get("runtime_ticks_used", 0) or 0)
        max_ticks = int(control.get("max_runtime_ticks", 0) or 0)
        if max_ticks > 0 and used_ticks >= max_ticks:
            return self._halt_for_budget(
                mission_id,
                mission,
                reason="runtime_tick_budget_exhausted",
                payload={
                    "runtime_ticks_used": used_ticks,
                    "max_runtime_ticks": max_ticks,
                },
            )
        self.mission_control_repository.increment_usage(mission_id, runtime_ticks_used=1)
        return None

    def _authorize_task_start(self, mission_id: str, mission: Dict, task: Dict) -> Optional[Dict]:
        if not self.mission_control_repository:
            return None
        control = self.mission_control_repository.get_control(mission_id)
        if not control:
            return None
        steps_used = int(control.get("autonomous_steps_used", 0) or 0)
        max_steps = int(control.get("max_autonomous_steps", 0) or 0)
        tokens_used = int(control.get("estimated_tokens_used", 0) or 0)
        max_tokens = int(control.get("max_estimated_tokens", 0) or 0)
        estimated_tokens = self._estimate_task_tokens(task)

        if max_steps > 0 and steps_used >= max_steps:
            return self._halt_for_budget(
                mission_id,
                mission,
                reason="autonomous_step_budget_exhausted",
                payload={
                    "autonomous_steps_used": steps_used,
                    "max_autonomous_steps": max_steps,
                },
            )
        if max_tokens > 0 and tokens_used + estimated_tokens > max_tokens:
            return self._halt_for_budget(
                mission_id,
                mission,
                reason="estimated_token_budget_exhausted",
                payload={
                    "estimated_tokens_used": tokens_used,
                    "incoming_estimated_tokens": estimated_tokens,
                    "max_estimated_tokens": max_tokens,
                    "task_id": task["id"],
                },
            )

        self.mission_control_repository.increment_usage(
            mission_id,
            autonomous_steps_used=1,
            estimated_tokens_used=estimated_tokens,
        )
        self.mission_control_repository.update_status(mission_id, status="active", notes=None)
        return None

    def _authorize_external_action(self, mission_id: str, mission: Dict, task: Dict) -> Optional[Dict]:
        details = task.get("details") or {}
        approval_policy = details.get("approval_policy") or "auto_allowed"
        action_kind = details.get("external_action_kind")
        if not action_kind:
            return None

        if self.mission_control_repository:
            budget_status = self.mission_control_repository.action_budget_status(mission_id, action_kind)
            if budget_status.get("exhausted"):
                return self._halt_for_budget(
                    mission_id,
                    mission,
                    reason=f"{action_kind}_budget_exhausted",
                    payload={
                        "task_id": task["id"],
                        "action_kind": action_kind,
                        "action_budget": budget_status,
                    },
                )

        if approval_policy in {"per_action_approval", "conditional"}:
            if not self.approval_service:
                self._transition_mission_if_needed(
                    mission_id,
                    mission.get("status"),
                    "needs_human",
                    reason="approval_service_missing",
                    actor="task_runner",
                )
                return {
                    "status": "awaiting_approval",
                    "mission_id": mission_id,
                    "task_id": task["id"],
                    "action_kind": action_kind,
                    "error": "approval_service_missing",
                }
            if not self.approval_service.is_authorized(task["id"], action_kind):
                approval = self.approval_service.ensure_request(
                    mission_id=mission_id,
                    task_id=task["id"],
                    requested_by_agent_id=task.get("agent_id"),
                    action_kind=action_kind,
                    policy_mode=approval_policy,
                    reason=f"Task {task['title']} wants to execute external action {action_kind}",
                    metadata={
                        "task_title": task.get("title"),
                        "workstream": details.get("workstream"),
                        "required_capabilities": details.get("required_capabilities") or [],
                        "tool_primitives": details.get("tool_primitives") or [],
                    },
                )
                self._transition_mission_if_needed(
                    mission_id,
                    mission.get("status"),
                    "needs_human",
                    reason="awaiting_action_approval",
                    actor="task_runner",
                )
                self.progress_notifier.notify(
                    mission_id,
                    "approval_required",
                    f"La mision requiere aprobacion para la accion {action_kind}: {task['title']}",
                    {
                        "approval_id": approval["id"],
                        "task_id": task["id"],
                        "action_kind": action_kind,
                    },
                )
                return {
                    "status": "awaiting_approval",
                    "mission_id": mission_id,
                    "task_id": task["id"],
                    "approval_id": approval["id"],
                    "action_kind": action_kind,
                }

        return None

    def _task_ready(self, task: Dict, tasks: List[Dict]) -> bool:
        deps = task.get("depends_on") or []
        if not deps:
            return True
        done_ids = {item["id"] for item in tasks if item["status"] in {"done", "completed"}}
        return all(dep in done_ids for dep in deps)

    def _failed_dependency_ids(self, task: Dict, tasks: List[Dict]) -> List[str]:
        deps = task.get("depends_on") or []
        if not deps:
            return []
        failed_ids = {item["id"] for item in tasks if item["status"] == "failed"}
        return [dep for dep in deps if dep in failed_ids]

    def _transition_task_with_validation(self, task_id: str, to_status: str, reason: Optional[str] = None, actor: Optional[str] = None) -> bool:
        if self.state_updater:
            try:
                self.state_updater.begin_transaction()
                self.state_updater.transition_task(task_id, to_status, reason=reason, actor=actor)
                self.state_updater.commit_transaction()
                return True
            except StateValidationError:
                self.state_updater.rollback_transaction()
                raise
        self.task_repository.update_task_status(task_id, to_status)
        return True

    def _transition_mission_if_needed(self, mission_id: str, current_status: Optional[str], to_status: str, reason: str, actor: str) -> None:
        if current_status == to_status:
            return
        if self.state_updater:
            try:
                self.state_updater.begin_transaction()
                self.state_updater.transition_mission(
                    mission_id,
                    to_status,
                    reason=reason,
                    actor=actor,
                )
                self.state_updater.commit_transaction()
                return
            except StateValidationError:
                self.state_updater.rollback_transaction()
                raise
        self.mission_repository.update_mission_status(mission_id, to_status)

    def _schedule_retry_if_allowed(self, mission_id: str, mission: Dict, task: Dict) -> Optional[Dict]:
        details = dict(task.get("details") or {})
        guardrails = details.get("guardrails") or {}
        max_retries = int(guardrails.get("max_retries", 0) or 0)
        retry_count = int(details.get("retry_count", 0) or 0)

        if retry_count >= max_retries:
            return None

        details["retry_count"] = retry_count + 1
        details["last_retry_reason"] = "auto_retry_after_failure"
        details["last_retry_actor"] = "task_runner"
        self.task_repository.update_task_details(task["id"], details)
        self._transition_task_with_validation(
            task["id"],
            "pending",
            reason="auto_retry_after_failure",
            actor="task_runner",
        )
        self.agent_state_manager.set_state(task["agent_id"], "idle")
        self._transition_mission_if_needed(
            mission_id,
            mission.get("status"),
            "queued",
            reason="retry_scheduled",
            actor="task_runner",
        )
        self.mission_repository.add_event(
            mission_id,
            "task_retry_scheduled",
            "task_runner",
            f"Retry scheduled for task: {task['title']}",
            {
                "task_id": task["id"],
                "agent_id": task["agent_id"],
                "retry_count": details["retry_count"],
                "max_retries": max_retries,
            },
        )
        self.progress_notifier.notify(
            mission_id,
            "task_retry_scheduled",
            f"Se reintentara {task['title']} ({details['retry_count']}/{max_retries}).",
            {
                "task_id": task["id"],
                "agent_id": task["agent_id"],
                "retry_count": details["retry_count"],
                "max_retries": max_retries,
            },
        )
        return {
            "status": "retry_scheduled",
            "mission_id": mission_id,
            "task_id": task["id"],
            "agent_id": task["agent_id"],
            "retry_count": details["retry_count"],
            "max_retries": max_retries,
        }

    def advance_next_task(self, mission_id: str) -> Dict:
        mission = self.mission_repository.get_mission(mission_id) or {"status": None}
        budget_tick_result = self._consume_tick_or_halt(mission_id, mission)
        if budget_tick_result:
            return budget_tick_result

        tasks = self.task_repository.list_tasks_for_mission(mission_id)
        failed_tasks = [task for task in tasks if task["status"] == "failed"]
        if failed_tasks:
            failed_task = failed_tasks[0]
            retry_result = self._schedule_retry_if_allowed(mission_id, mission, failed_task)
            if retry_result:
                return retry_result
            if mission.get("status") != "needs_human":
                self._transition_mission_if_needed(
                    mission_id,
                    mission.get("status"),
                    "needs_human",
                    reason="task_failed",
                    actor="task_runner",
                )
                self.mission_repository.add_event(
                    mission_id,
                    "mission_needs_human",
                    "system",
                    f"Mission requires human attention after task failure: {failed_task['title']}",
                    {
                        "failed_task_id": failed_task["id"],
                        "failed_task_title": failed_task["title"],
                        "failed_agent_id": failed_task["agent_id"],
                    },
                )
                self.progress_notifier.notify(
                    mission_id,
                    "blocked",
                    f"La mision requiere atencion humana por una tarea fallida: {failed_task['title']}",
                    {
                        "failed_task_id": failed_task["id"],
                        "failed_agent_id": failed_task["agent_id"],
                    },
                )
            self.agent_state_manager.set_state(
                failed_task["agent_id"],
                "blocked",
                mission_id=mission_id,
                task_id=failed_task["id"],
            )
            return {
                "status": "needs_human",
                "mission_id": mission_id,
                "failed_task_id": failed_task["id"],
            }

        running = [task for task in tasks if task["status"] == "running"]
        if running:
            mgr = self.execution_manager
            for task in running:
                task_id = task["id"]

                # ── Real LLM execution path ───────────────────────────────
                if mgr is not None:
                    exec_status = mgr.execution_status(task)

                    if exec_status is None:
                        # Not yet started — fire background thread and wait for next tick
                        mgr.start_execution(mission, task, self.task_repository)
                        logger.info("LLM execution started for task %s", task_id)
                        continue

                    if exec_status == "running":
                        # Still executing — skip this tick
                        logger.debug("Task %s still executing, skipping tick", task_id)
                        continue

                    if exec_status == "failed":
                        # LLM reported failure — transition task to failed for retry logic
                        result = mgr.get_result(task) or {}
                        logger.warning(
                            "Task %s LLM execution failed: %s", task_id, result.get("summary")
                        )
                        self._transition_task_with_validation(
                            task_id, "failed",
                            reason=result.get("error", "llm_execution_failed"),
                            actor="agent_executor",
                        )
                        self.agent_state_manager.set_state(task["agent_id"], "idle")
                        self.mission_repository.add_event(
                            mission_id, "task_failed", task["agent_id"],
                            f"LLM execution failed: {task['title']}",
                            {"task_id": task_id, "error": result.get("error")},
                        )
                        continue

                    # exec_status == "done" — fall through to complete below
                    result = mgr.get_result(task) or {}
                    logger.info(
                        "Task %s done (tokens=%s, iterations=%s)",
                        task_id, result.get("tokens_used", "?"), result.get("iterations", "?"),
                    )

                    # Re-fetch task with updated details to attach result to handoff
                    try:
                        fresh = self.task_repository.get_task(task_id)
                        task_for_handoff = fresh if fresh else task
                    except Exception:
                        task_for_handoff = task

                # ── Simulation path (no API key) ──────────────────────────
                else:
                    task_for_handoff = task

                # ── Mark task done (shared by both paths) ─────────────────
                self._transition_task_with_validation(
                    task_id, "done",
                    reason="task_completed",
                    actor="task_runner",
                )
                self.mission_repository.add_event(
                    mission_id, "task_completed", task["agent_id"],
                    f"Task completed: {task['title']}",
                    {"task_id": task_id, "task_title": task["title"]},
                )
                self.agent_state_manager.set_state(task["agent_id"], "idle")
                if self.coordination_service:
                    self.coordination_service.record_completion_handoffs(
                        mission_id, task_for_handoff, tasks
                    )
                self.progress_notifier.notify(
                    mission_id, "task_completed",
                    f"{task['agent_id']} completó: {task['title']}",
                    {"task_id": task_id, "agent_id": task["agent_id"]},
                )
            tasks = self.task_repository.list_tasks_for_mission(mission_id)

        actionable = [task for task in tasks if task["status"] in {"pending", "blocked"}]
        ready = [task for task in actionable if self._task_ready(task, tasks)]
        blocked = [task for task in actionable if task not in ready]

        for task in ready:
            if task["status"] == "blocked":
                self._transition_task_with_validation(
                    task["id"],
                    "pending",
                    reason="dependencies_met",
                    actor="task_runner"
                )
                self.mission_repository.add_event(
                    mission_id,
                    "task_unblocked",
                    task["agent_id"],
                    f"Task unblocked: {task['title']}",
                    {"task_id": task["id"], "depends_on": task.get("depends_on", [])},
                )

        for task in blocked:
            failed_dependency_ids = self._failed_dependency_ids(task, tasks)
            if failed_dependency_ids:
                if mission.get("status") != "needs_human":
                    self._transition_mission_if_needed(
                        mission_id,
                        mission.get("status"),
                        "needs_human",
                        reason="dependency_failed",
                        actor="task_runner",
                    )
                self.mission_repository.add_event(
                    mission_id,
                    "mission_needs_human",
                    "system",
                    f"Mission requires human attention because dependencies failed: {task['title']}",
                    {
                        "task_id": task["id"],
                        "failed_dependency_ids": failed_dependency_ids,
                    },
                )
                self.progress_notifier.notify(
                    mission_id,
                    "blocked",
                    f"La mision requiere atencion humana: {task['title']} depende de una tarea fallida.",
                    {"task_id": task["id"], "failed_dependency_ids": failed_dependency_ids},
                )
                return {
                    "status": "needs_human",
                    "mission_id": mission_id,
                    "task_id": task["id"],
                    "failed_dependency_ids": failed_dependency_ids,
                }
            if task["status"] != "blocked":
                self._transition_task_with_validation(
                    task["id"],
                    "blocked",
                    reason="waiting_dependencies",
                    actor="task_runner"
                )
                self.mission_repository.add_event(
                    mission_id,
                    "task_blocked",
                    task["agent_id"],
                    f"Task blocked waiting dependencies: {task['title']}",
                    {"task_id": task["id"], "depends_on": task.get("depends_on", [])},
                )
                self.progress_notifier.notify(
                    mission_id,
                    "blocked",
                    f"{task['agent_id']} esta bloqueada: {task['title']}",
                    {"task_id": task["id"], "agent_id": task["agent_id"]},
                )

        if ready:
            started_tasks: List[Dict] = []
            occupied_agents = set()
            for next_task in ready:
                agent_id = next_task["agent_id"]
                if agent_id in occupied_agents:
                    continue
                approval_result = self._authorize_external_action(mission_id, mission, next_task)
                if approval_result:
                    if started_tasks:
                        return {
                            "status": "started_partial",
                            "mission_id": mission_id,
                            "started_task_ids": [task["id"] for task in started_tasks],
                            "started_agent_ids": [task["agent_id"] for task in started_tasks],
                        }
                    return approval_result
                budget_start_result = self._authorize_task_start(mission_id, mission, next_task)
                if budget_start_result:
                    if started_tasks:
                        return {
                            "status": "started_partial",
                            "mission_id": mission_id,
                            "started_task_ids": [task["id"] for task in started_tasks],
                            "started_agent_ids": [task["agent_id"] for task in started_tasks],
                        }
                    return budget_start_result
                if self.coordination_service:
                    self.coordination_service.attach_context_to_task(mission_id, next_task)
                external_action_kind = (next_task.get("details") or {}).get("external_action_kind")
                if external_action_kind and self.mission_control_repository:
                    self.mission_control_repository.record_action_usage(mission_id, external_action_kind, 1)
                self._transition_task_with_validation(
                    next_task["id"],
                    "running",
                    reason="task_started",
                    actor="task_runner"
                )
                self.agent_state_manager.set_state(
                    agent_id,
                    STATE_BY_AGENT.get(agent_id, "idle"),
                    mission_id=mission_id,
                    task_id=next_task["id"],
                )
                occupied_agents.add(agent_id)
                started_tasks.append(next_task)
                self.mission_repository.add_event(
                    mission_id,
                    "task_started",
                    agent_id,
                    f"Task started: {next_task['title']}",
                    {"task_id": next_task["id"], "depends_on": next_task.get("depends_on", [])}
                )
                self.progress_notifier.notify(
                    mission_id,
                    "task_started",
                    f"{agent_id} inicio: {next_task['title']}",
                    {"task_id": next_task["id"], "agent_id": agent_id},
                )

            if started_tasks:
                self._transition_mission_if_needed(
                    mission_id,
                    mission.get("status"),
                    "running",
                    reason="task_started",
                    actor="task_runner",
                )
                if len(started_tasks) == 1:
                    return {"status": "started", "task_id": started_tasks[0]["id"], "agent_id": started_tasks[0]["agent_id"]}
                return {
                    "status": "started_parallel",
                    "mission_id": mission_id,
                    "started_task_ids": [task["id"] for task in started_tasks],
                    "started_agent_ids": [task["agent_id"] for task in started_tasks],
                }

        incomplete = [task for task in tasks if task["status"] in {"pending", "blocked", "running"}]
        if incomplete:
            desired_status = "blocked" if any(task["status"] == "blocked" for task in incomplete) else "queued"
            if mission.get("status") != desired_status:
                self._transition_mission_if_needed(
                    mission_id,
                    mission.get("status"),
                    desired_status,
                    reason="tasks_incomplete",
                    actor="task_runner",
                )
                self.mission_repository.add_event(
                    mission_id,
                    "mission_blocked" if desired_status == "blocked" else "mission_queued",
                    "system",
                    f"Mission {desired_status} waiting for dependencies",
                    {"blocked_task_ids": [task["id"] for task in incomplete if task["status"] == "blocked"]} if desired_status == "blocked" else {},
                )
            return {
                "status": desired_status,
                "mission_id": mission_id,
                "blocked_task_ids": [task["id"] for task in incomplete if task["status"] == "blocked"] if desired_status == "blocked" else [],
            }

        if mission.get("status") != "completed":
            self._transition_mission_if_needed(
                mission_id,
                mission.get("status"),
                "completed",
                reason="all_tasks_finished",
                actor="task_runner",
            )
            self.mission_repository.add_event(
                mission_id,
                "mission_completed",
                "system",
                "Mission completed successfully",
                {}
            )
            self.progress_notifier.notify(
                mission_id,
                "mission_completed",
                "La mision se completo correctamente.",
                {},
            )
        return {"status": "completed", "mission_id": mission_id}
