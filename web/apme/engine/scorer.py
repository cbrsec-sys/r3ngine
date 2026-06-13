"""
APME Scoring Engine

Scores attack paths. Additive factors (sum = 1.0):
- Vulnerability severity       (0.20 weight)
- Exploitability / CVSS        (0.20 weight)
- Path length — shorter=higher risk (0.15 weight)
- Privilege gained             (0.15 weight)
- Impact (blast radius + sensitivity) (0.15 weight)
- EPSS score                   (0.15 weight)

Post-sum modifiers (applied after additive sum):
- Path confidence product multiplier  ×[0.5, 1.0]
- CISA KEV flat boost                 +0.10
- ERL validated step boost            +0.05 per step, max +0.15

Risk classification:
  speculative : 0 validated steps AND score < 0.40
  low         : score <= 0.50
  medium      : score <= 0.70
  high        : score <= 0.85
  critical    : score  > 0.85
"""

import logging
from typing import Any, Dict, List

from apme.models.path import AttackPath, PathStep

logger = logging.getLogger(__name__)

SEVERITY_MAP = {-1: 0.0, 0: 0.05, 1: 0.25, 2: 0.50, 3: 0.75, 4: 1.0}
PRIVILEGE_MAP = {"none": 0.0, "user": 0.25, "admin": 0.75, "domain_admin": 1.0, "root": 1.0}


class Scorer:
    """Computes a risk score for a complete attack path."""

    WEIGHTS = {
        "severity":        0.20,
        "exploitability":  0.20,
        "path_length":     0.15,
        "privilege_gain":  0.15,
        "impact":          0.15,
        "epss":            0.15,
    }

    def __init__(self):
        self._blast_radius_cache: Dict[str, int] = {}

    def score(self, path: AttackPath, path_metadata: Dict[str, Any]) -> float:
        """Compute and set path.score and path.risk. Returns the final score."""
        steps = path.steps
        if not steps:
            path.score = 0.0
            path.risk = "low"
            return 0.0

        # 1. Severity
        severity_raw = path_metadata.get("severity", -1)
        severity_score = SEVERITY_MAP.get(severity_raw, 0.0)

        # 2. Exploitability
        cvss = path_metadata.get("cvss_score", 0.0)
        exploitability = min(cvss / 10.0, 1.0) if cvss else severity_score * 0.8

        # 3. Path length (shorter = higher risk)
        length_score = 1.0 / max(len(steps), 1)

        # 4. Privilege gained
        privilege = path_metadata.get("privilege_gained", "none")
        privilege_score = PRIVILEGE_MAP.get(privilege, 0.0)

        # 5. Impact (blast radius + target sensitivity)
        blast_radius = path_metadata.get("blast_radius", 1)
        blast_score = min(blast_radius / 50.0, 1.0)
        sensitivity_val = path_metadata.get("target_sensitivity", "low")
        sensitivity_score = {"high": 1.0, "medium": 0.6, "low": 0.2}.get(sensitivity_val, 0.2)
        impact_score = (blast_score * 0.4) + (sensitivity_score * 0.6)

        # 6. EPSS
        epss_percentile = path_metadata.get("epss_percentile", 0.0)
        epss_score = min(epss_percentile / 100.0, 1.0) if epss_percentile else 0.0

        # Additive sum (weights sum to 1.0)
        score = (
            severity_score    * self.WEIGHTS["severity"]
            + exploitability  * self.WEIGHTS["exploitability"]
            + length_score    * self.WEIGHTS["path_length"]
            + privilege_score * self.WEIGHTS["privilege_gain"]
            + impact_score    * self.WEIGHTS["impact"]
            + epss_score      * self.WEIGHTS["epss"]
        )

        # Path confidence product multiplier [0.5, 1.0]
        conf_product = path_metadata.get("path_confidence_product", 1.0)
        conf_multiplier = max(min(float(conf_product), 1.0), 0.5)
        score *= conf_multiplier

        # CISA KEV flat boost
        if path_metadata.get("has_cisa_kev"):
            score = min(score + 0.10, 1.0)

        # ERL validated step boost (+0.05 per validated step, max +0.15)
        validated = path_metadata.get("validated_steps", 0)
        if validated > 0:
            score = min(score + min(validated * 0.05, 0.15), 1.0)

        score = round(score, 4)
        path.score = score
        path.risk = self._classify(score, path)

        logger.debug(
            "APME Scorer: path=%s score=%.4f risk=%s "
            "(sev=%.2f expl=%.2f len=%.2f impact=%.2f epss=%.2f conf_mult=%.2f)",
            path.id, score, path.risk, severity_score, exploitability,
            length_score, impact_score, epss_score, conf_multiplier,
        )
        return score

    @staticmethod
    def _classify(score: float, path: AttackPath) -> str:
        validated_count = sum(1 for s in path.steps if s.validated)
        if validated_count == 0 and score < 0.40:
            return "speculative"
        if score > 0.85:
            return "critical"
        if score > 0.70:
            return "high"
        if score > 0.50:
            return "medium"
        return "low"

    def sort_paths(self, paths: List[AttackPath]) -> List[AttackPath]:
        """Sort descending by score; speculative paths always last."""
        def sort_key(p: AttackPath):
            return (1 if p.risk != "speculative" else 0, p.score)
        return sorted(paths, key=sort_key, reverse=True)

    def deduplicate(self, paths: List[AttackPath], overlap_threshold: float = 0.75) -> List[AttackPath]:
        """
        Remove paths sharing >overlap_threshold step-pairs with a higher-scored path.
        Also drops paths scoring below 0.15.
        Input must be sorted descending by score before calling.
        """
        kept = []
        for path in paths:
            if path.score < 0.15:
                continue
            step_pairs = {(s.from_id, s.to_id) for s in path.steps}
            dominated = False
            for kept_path in kept:
                kept_pairs = {(s.from_id, s.to_id) for s in kept_path.steps}
                if step_pairs and len(step_pairs & kept_pairs) / len(step_pairs) > overlap_threshold:
                    dominated = True
                    break
            if not dominated:
                kept.append(path)
        return kept
