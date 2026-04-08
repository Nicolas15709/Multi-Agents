from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

try:
    from .models import ActionApprovalRecord
    from .repository import ActionApprovalRepository, MissionRepository
    from .utils import new_id
except ImportError:  # pragma: no cover - runtime script compatibility
    from models import ActionApprovalRecord
    from repository import ActionApprovalRepository, MissionRepository
    from utils import new_id


@dataclass
class ActionApprovalService:
    repository: ActionApprovalRepository
    mission_repository: MissionRepository

    def list_for_mission(self, mission_id: str):
        return self.repository.list_for_mission(mission_id)

    def ensure_request(
        self,
        *,
        mission_id: str,
        task_id: str,
        requested_by_agent_id: Optional[str],
        action_kind: str,
        policy_mode: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        existing = self.repository.find_for_task(task_id, action_kind)
        if existing:
            return existing
        approval = self.repository.create_request(
            ActionApprovalRecord(
                id=new_id("approval"),
                mission_id=mission_id,
                task_id=task_id,
                requested_by_agent_id=requested_by_agent_id,
                action_kind=action_kind,
                policy_mode=policy_mode,
                status="pending",
                reason=reason,
                metadata=metadata or {},
            )
        )
        self.mission_repository.add_event(
            mission_id,
            "action_approval_requested",
            requested_by_agent_id or "system",
            f"Approval requested for external action: {action_kind}",
            {
                "approval_id": approval["id"],
                "task_id": task_id,
                "action_kind": action_kind,
                "policy_mode": policy_mode,
            },
        )
        return approval

    def approve(self, approval_id: str, *, approved_by: str = "operator", decision_notes: Optional[str] = None) -> Dict:
        approval = self.repository.update_request(
            approval_id,
            status="approved",
            approved_by=approved_by,
            decision_notes=decision_notes,
        )
        self.mission_repository.add_event(
            approval["mission_id"],
            "action_approval_granted",
            approved_by,
            f"Approval granted for action: {approval['action_kind']}",
            {
                "approval_id": approval["id"],
                "task_id": approval["task_id"],
                "action_kind": approval["action_kind"],
            },
        )
        return approval

    def reject(self, approval_id: str, *, approved_by: str = "operator", decision_notes: Optional[str] = None) -> Dict:
        approval = self.repository.update_request(
            approval_id,
            status="rejected",
            approved_by=approved_by,
            decision_notes=decision_notes,
        )
        self.mission_repository.add_event(
            approval["mission_id"],
            "action_approval_rejected",
            approved_by,
            f"Approval rejected for action: {approval['action_kind']}",
            {
                "approval_id": approval["id"],
                "task_id": approval["task_id"],
                "action_kind": approval["action_kind"],
            },
        )
        return approval

    def is_authorized(self, task_id: str, action_kind: str) -> bool:
        approval = self.repository.find_for_task(task_id, action_kind)
        return bool(approval and approval.get("status") == "approved")
