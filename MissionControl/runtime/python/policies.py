from typing import Dict, List

try:
    from .repository import PolicyRepository
except ImportError:  # pragma: no cover - runtime script compatibility
    from repository import PolicyRepository


class PolicyEngine:
    def __init__(self, repository: PolicyRepository):
        self.repository = repository

    def summary(self) -> Dict:
        policies = self.repository.list_policies()
        return {
            "storage": "hybrid",
            "count": len(policies),
            "granularity": ["integration", "account_or_resource", "action"],
        }

    def is_action_allowed(self, integration: str, account_resource: str, action: str) -> Dict:
        for policy in self.repository.list_policies():
            if (
                policy["integration"] == integration
                and policy["account_resource"] == account_resource
                and policy["action"] == action
                and int(policy["enabled"]) == 1
            ):
                return {
                    "allowed": policy["mode"] in {"auto_allowed", "conditional"},
                    "mode": policy["mode"],
                }
        return {
            "allowed": False,
            "mode": "forbidden",
        }
