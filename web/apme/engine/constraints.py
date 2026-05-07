"""
APME Constraint Engine

Validates whether a proposed attack path step is realistic.
Prevents fantasy exploit chains by enforcing:
- Authentication requirements
- Network segmentation boundaries
- Privilege level requirements

CRITICAL: A step that fails constraint validation MUST be dropped.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PathContext:
    """Tracks cumulative state along a path as steps are evaluated."""

    def __init__(self):
        self.has_auth: bool = False
        self.has_internal_access: bool = False
        self.privilege_level: str = "none"  # none | user | admin | domain_admin | root
        self.validated_step_count: int = 0

    def grant_auth(self) -> None:
        self.has_auth = True

    def grant_internal_access(self) -> None:
        self.has_internal_access = True

    def escalate_privilege(self, level: str) -> None:
        order = ["none", "user", "admin", "domain_admin", "root"]
        if order.index(level) > order.index(self.privilege_level):
            self.privilege_level = level


class ConstraintEngine:
    """
    Validates individual path steps against the current path context.
    Returns False for any step that violates a constraint.
    """

    def validate_step(
        self,
        step: Dict[str, Any],
        context: PathContext,
    ) -> bool:
        """
        Validate a single step in the context of the accumulated path state.

        Args:
            step: Dict with keys: requires_auth, requires_internal, requires_privilege, edge_type
            context: The accumulated PathContext up to this point

        Returns:
            True if the step is allowed, False if it must be dropped.
        """
        # Auth requirement check
        if step.get("requires_auth") and not context.has_auth:
            logger.debug(
                f"APME Constraint: Step '{step.get('action')}' requires auth "
                "but path has no authenticated access. Blocked."
            )
            return False

        # Network boundary check
        if step.get("requires_internal") and not context.has_internal_access:
            logger.debug(
                f"APME Constraint: Step '{step.get('action')}' requires internal "
                "network access but attacker has not pivoted. Blocked."
            )
            return False

        # Privilege level check
        required_priv = step.get("requires_privilege", "none")
        privilege_order = ["none", "user", "admin", "domain_admin", "root"]
        current_idx = privilege_order.index(context.privilege_level)
        required_idx = privilege_order.index(required_priv) if required_priv in privilege_order else 0

        if current_idx < required_idx:
            logger.debug(
                f"APME Constraint: Step '{step.get('action')}' requires privilege "
                f"'{required_priv}' but current level is '{context.privilege_level}'. Blocked."
            )
            return False

        return True

    def update_context(self, step: Dict[str, Any], context: PathContext) -> None:
        """Apply side-effects of a valid step to the path context."""
        if step.get("grants_auth"):
            context.grant_auth()
        if step.get("grants_internal"):
            context.grant_internal_access()
        if step.get("grants_privilege"):
            context.escalate_privilege(step["grants_privilege"])
        if step.get("validated"):
            context.validated_step_count += 1
