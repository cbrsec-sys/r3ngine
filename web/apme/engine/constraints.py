"""
APME Constraint Engine

Validates whether a proposed attack path step is realistic.
Prevents fantasy exploit chains by enforcing:
1. Authentication requirements (original)
2. Network segmentation boundaries (original)
3. Privilege level requirements (original)
4. Step confidence threshold — Phase 1
5. Cycle detection — Phase 1
6. Victim interaction gate — Phase 1
7. PHP technology gate — Phase 1
8. Java technology gate — Phase 1
9. WordPress technology gate — Phase 1
10. Authenticated endpoint boundary — Phase 1
11. Minimum path confidence product — Phase 1
12-23. Technology gates for .NET, Kubernetes, Docker, Ruby, Node.js,
       Active Directory, MSSQL, Oracle, Redis, Drupal, Joomla, Magento — Phase 2
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

_PRIVILEGE_ORDER = ["none", "user", "admin", "domain_admin", "root"]

# Steps with confidence below this threshold are always blocked.
MIN_STEP_CONFIDENCE = 0.15

# If the cumulative product of step confidences drops below this, block the path.
MIN_PATH_CONFIDENCE_PRODUCT = 0.05


class PathContext:
    """Tracks cumulative state along a path as steps are evaluated."""

    def __init__(self):
        self.has_auth: bool = False
        self.has_internal_access: bool = False
        self.privilege_level: str = "none"
        self.validated_step_count: int = 0
        # Phase 1 additions
        self.has_victim_interaction: bool = False
        self.has_php_tech: bool = False
        self.has_java_tech: bool = False
        self.has_python_tech: bool = False
        self.has_wordpress_tech: bool = False
        self.has_dotnet_tech: bool = False
        self.has_kubernetes_tech: bool = False
        self.has_docker_tech: bool = False
        self.has_ruby_tech: bool = False
        self.has_nodejs_tech: bool = False
        self.has_active_directory_tech: bool = False
        self.has_mssql_tech: bool = False
        self.has_oracle_tech: bool = False
        self.has_redis_tech: bool = False
        self.has_drupal_tech: bool = False
        self.has_joomla_tech: bool = False
        self.has_magento_tech: bool = False
        self.visited_node_ids: set = None
        self.path_confidence_product: float = 1.0

    def __post_init_visited(self):
        if self.visited_node_ids is None:
            self.visited_node_ids = set()

    def grant_auth(self) -> None:
        self.has_auth = True

    def grant_internal_access(self) -> None:
        self.has_internal_access = True

    def escalate_privilege(self, level: str) -> None:
        if level in _PRIVILEGE_ORDER:
            if _PRIVILEGE_ORDER.index(level) > _PRIVILEGE_ORDER.index(self.privilege_level):
                self.privilege_level = level

    def visit_node(self, node_id: str) -> None:
        if self.visited_node_ids is None:
            self.visited_node_ids = set()
        self.visited_node_ids.add(node_id)

    def update_confidence_product(self, step_confidence: float) -> None:
        self.path_confidence_product *= step_confidence


class ConstraintEngine:
    """
    Validates individual path steps against the current path context.
    Returns False for any step that violates a constraint.
    """

    def validate_step(self, step: Dict[str, Any], context: PathContext) -> bool:
        """
        Validate a single step in the context of the accumulated path state.
        All 11 constraints are checked in order; first failure short-circuits.
        """
        # 1. Min step confidence
        if step.get("confidence", 1.0) < MIN_STEP_CONFIDENCE:
            logger.debug(
                "APME Constraint [confidence]: Step '%s' confidence %.2f below threshold %.2f. Blocked.",
                step.get("action"), step.get("confidence"), MIN_STEP_CONFIDENCE,
            )
            return False

        # 2. Cycle detection
        visited = context.visited_node_ids or set()
        to_id = step.get("to_id", "")
        if to_id and to_id in visited:
            logger.debug("APME Constraint [cycle]: Node '%s' already visited. Blocked.", to_id)
            return False

        # 3. Auth requirement (original)
        if step.get("requires_auth") and not context.has_auth:
            logger.debug(
                "APME Constraint [auth]: Step '%s' requires auth but none granted. Blocked.",
                step.get("action"),
            )
            return False

        # 4. Internal network requirement (original)
        if step.get("requires_internal") and not context.has_internal_access:
            logger.debug(
                "APME Constraint [internal]: Step '%s' requires internal access. Blocked.",
                step.get("action"),
            )
            return False

        # 5. Privilege level (original)
        required_priv = step.get("requires_privilege", "none")
        if required_priv in _PRIVILEGE_ORDER:
            current_idx = _PRIVILEGE_ORDER.index(context.privilege_level)
            required_idx = _PRIVILEGE_ORDER.index(required_priv)
            if current_idx < required_idx:
                logger.debug(
                    "APME Constraint [privilege]: Step requires '%s' but level is '%s'. Blocked.",
                    required_priv, context.privilege_level,
                )
                return False

        # 6. Victim interaction gate
        if step.get("requires_victim") and not context.has_victim_interaction:
            logger.debug(
                "APME Constraint [victim]: Step '%s' requires victim interaction. Blocked.",
                step.get("action"),
            )
            return False

        # 7. PHP gate
        if step.get("requires_php") and not context.has_php_tech:
            logger.debug("APME Constraint [php]: PHP required but not detected. Blocked.")
            return False

        # 8. Java gate
        if step.get("requires_java") and not context.has_java_tech:
            logger.debug("APME Constraint [java]: Java required but not detected. Blocked.")
            return False

        # 9. WordPress gate
        if step.get("requires_wordpress") and not context.has_wordpress_tech:
            logger.debug("APME Constraint [wordpress]: WordPress required but not detected. Blocked.")
            return False

        # 10. Authenticated endpoint boundary
        if step.get("endpoint_requires_auth") and not context.has_auth:
            logger.debug("APME Constraint [endpoint_auth]: Endpoint requires auth. Blocked.")
            return False

        # 11. Minimum path confidence product
        projected = context.path_confidence_product * step.get("confidence", 1.0)
        if projected < MIN_PATH_CONFIDENCE_PRODUCT:
            logger.debug(
                "APME Constraint [path_confidence]: Projected product %.4f below %.4f. Blocked.",
                projected, MIN_PATH_CONFIDENCE_PRODUCT,
            )
            return False

        # 12. .NET gate
        if step.get("requires_dotnet") and not context.has_dotnet_tech:
            logger.debug("APME Constraint [dotnet]: .NET required but not detected. Blocked.")
            return False

        # 13. Kubernetes gate
        if step.get("requires_kubernetes") and not context.has_kubernetes_tech:
            logger.debug("APME Constraint [kubernetes]: Kubernetes required but not detected. Blocked.")
            return False

        # 14. Docker gate
        if step.get("requires_docker") and not context.has_docker_tech:
            logger.debug("APME Constraint [docker]: Docker required but not detected. Blocked.")
            return False

        # 15. Ruby gate
        if step.get("requires_ruby") and not context.has_ruby_tech:
            logger.debug("APME Constraint [ruby]: Ruby required but not detected. Blocked.")
            return False

        # 16. Node.js gate
        if step.get("requires_nodejs") and not context.has_nodejs_tech:
            logger.debug("APME Constraint [nodejs]: Node.js required but not detected. Blocked.")
            return False

        # 17. Active Directory gate
        if step.get("requires_active_directory") and not context.has_active_directory_tech:
            logger.debug("APME Constraint [active_directory]: Active Directory required but not detected. Blocked.")
            return False

        # 18. MSSQL gate
        if step.get("requires_mssql") and not context.has_mssql_tech:
            logger.debug("APME Constraint [mssql]: MSSQL required but not detected. Blocked.")
            return False

        # 19. Oracle gate
        if step.get("requires_oracle") and not context.has_oracle_tech:
            logger.debug("APME Constraint [oracle]: Oracle required but not detected. Blocked.")
            return False

        # 20. Redis gate
        if step.get("requires_redis") and not context.has_redis_tech:
            logger.debug("APME Constraint [redis]: Redis required but not detected. Blocked.")
            return False

        # 21. Drupal gate
        if step.get("requires_drupal") and not context.has_drupal_tech:
            logger.debug("APME Constraint [drupal]: Drupal required but not detected. Blocked.")
            return False

        # 22. Joomla gate
        if step.get("requires_joomla") and not context.has_joomla_tech:
            logger.debug("APME Constraint [joomla]: Joomla required but not detected. Blocked.")
            return False

        # 23. Magento gate
        if step.get("requires_magento") and not context.has_magento_tech:
            logger.debug("APME Constraint [magento]: Magento required but not detected. Blocked.")
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
        # Technology context propagation via to_subtype
        to_subtype = step.get("to_subtype", "")
        if to_subtype == "php":
            context.has_php_tech = True
        elif to_subtype in ("java", "spring", "jenkins"):
            context.has_java_tech = True
        elif to_subtype == "python":
            context.has_python_tech = True
        elif to_subtype == "wordpress":
            context.has_wordpress_tech = True
        elif to_subtype in ("dotnet", "csharp", "aspnet"):
            context.has_dotnet_tech = True
        elif to_subtype in ("kubernetes", "k8s"):
            context.has_kubernetes_tech = True
        elif to_subtype in ("docker", "container"):
            context.has_docker_tech = True
        elif to_subtype in ("ruby", "rails"):
            context.has_ruby_tech = True
        elif to_subtype in ("nodejs", "node", "express"):
            context.has_nodejs_tech = True
        elif to_subtype in ("active_directory", "ldap", "exchange"):
            context.has_active_directory_tech = True
        elif to_subtype in ("mssql", "sqlserver"):
            context.has_mssql_tech = True
        elif to_subtype == "oracle":
            context.has_oracle_tech = True
        elif to_subtype == "redis":
            context.has_redis_tech = True
        elif to_subtype == "drupal":
            context.has_drupal_tech = True
        elif to_subtype == "joomla":
            context.has_joomla_tech = True
        elif to_subtype == "magento":
            context.has_magento_tech = True
        # Track visited nodes and update confidence product
        if to_id := step.get("to_id", ""):
            context.visit_node(to_id)
        context.update_confidence_product(step.get("confidence", 1.0))
