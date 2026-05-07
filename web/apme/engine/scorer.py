"""
APME Scoring Engine

Scores attack paths based on:
- Vulnerability severity (0.30 weight)
- Exploitability / CVSS score (0.30 weight)
- Path length — shorter paths are higher risk (0.20 weight)
- Privilege gained (0.20 weight)

Outputs a normalised score in [0.0, 1.0] and a risk classification.
"""

import logging
from typing import Any, Dict, List

from apme.models.path import AttackPath, PathStep

logger = logging.getLogger(__name__)

# Severity map: reNgine integer severity -> normalised score
SEVERITY_MAP = {
    -1: 0.0,   # unknown
    0: 0.05,   # info
    1: 0.25,   # low
    2: 0.50,   # medium
    3: 0.75,   # high
    4: 1.0,    # critical
}

PRIVILEGE_MAP = {
    "none": 0.0,
    "user": 0.25,
    "admin": 0.75,
    "domain_admin": 1.0,
    "root": 1.0,
}


class Scorer:
    """Computes a risk score for a complete attack path."""

    WEIGHTS = {
        "severity": 0.30,
        "exploitability": 0.30,
        "path_length": 0.20,
        "privilege_gain": 0.20,
    }

    def score(self, path: AttackPath, path_metadata: Dict[str, Any]) -> float:
        """
        Compute and set the score on the given AttackPath.

        Args:
            path: The AttackPath to score.
            path_metadata: Dict with keys:
                - severity (int): highest severity encountered
                - cvss_score (float): highest CVSS score in path (0-10)
                - privilege_gained (str): final privilege level reached
                - validated_steps (int): number of ERL-validated steps

        Returns:
            Normalised score in [0.0, 1.0].
        """
        steps = path.steps
        if not steps:
            path.score = 0.0
            path.risk = "low"
            return 0.0

        severity_raw = path_metadata.get("severity", -1)
        severity_score = SEVERITY_MAP.get(severity_raw, 0.0)

        cvss = path_metadata.get("cvss_score", 0.0)
        exploitability = min(cvss / 10.0, 1.0) if cvss else severity_score * 0.8

        step_count = max(len(steps), 1)
        length_score = 1.0 / step_count

        privilege = path_metadata.get("privilege_gained", "none")
        privilege_score = PRIVILEGE_MAP.get(privilege, 0.0)

        score = (
            severity_score * self.WEIGHTS["severity"]
            + exploitability * self.WEIGHTS["exploitability"]
            + length_score * self.WEIGHTS["path_length"]
            + privilege_score * self.WEIGHTS["privilege_gain"]
        )

        # Boost score if ERL has validated steps
        validated = path_metadata.get("validated_steps", 0)
        if validated > 0:
            boost = min(validated * 0.05, 0.15)
            score = min(score + boost, 1.0)

        score = round(score, 4)
        path.score = score
        path.risk = self._classify(score)

        logger.debug(
            f"APME Scorer: path={path.id} score={score} risk={path.risk} "
            f"(severity={severity_score:.2f} exploit={exploitability:.2f} "
            f"length={length_score:.2f} priv={privilege_score:.2f})"
        )
        return score

    @staticmethod
    def _classify(score: float) -> str:
        if score > 0.85:
            return "critical"
        elif score > 0.70:
            return "high"
        elif score > 0.50:
            return "medium"
        return "low"

    def sort_paths(self, paths: List[AttackPath]) -> List[AttackPath]:
        """Sort paths descending by score."""
        return sorted(paths, key=lambda p: p.score, reverse=True)
