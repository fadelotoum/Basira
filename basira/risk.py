"""Transparent risk scoring for Basira's first prototype."""

from dataclasses import dataclass

from basira.detector import Detection


@dataclass(frozen=True)
class RiskAssessment:
    """Human-readable risk output for one detected object."""

    level: str
    proximity: str
    depth_score: float | None
    message: str
    color: tuple[int, int, int]


def relative_depth_score(depth_map, detection: Detection) -> float | None:
    """Return a normalized relative-depth score for a detected object."""
    if depth_map is None:
        return None

    # Ignore the bounding-box edges, which commonly contain background pixels.
    inset_x = max((detection.x2 - detection.x1) // 8, 1)
    inset_y = max((detection.y2 - detection.y1) // 8, 1)
    region = depth_map[
        detection.y1 + inset_y : detection.y2 - inset_y,
        detection.x1 + inset_x : detection.x2 - inset_x,
    ]
    if region.size == 0:
        return None

    low, high = float(depth_map.min()), float(depth_map.max())
    if high - low < 1e-6:
        return None

    return (float(region.mean()) - low) / (high - low)


def proximity_label(score: float | None) -> str:
    """Translate a relative-depth score into a readable zone."""
    if score is None:
        return "UNKNOWN"
    if score >= 0.72:
        return "VERY NEAR"
    if score >= 0.54:
        return "NEAR"
    if score >= 0.34:
        return "MEDIUM"
    return "FAR"


def assess_risk(
    detection: Detection,
    frame_width: int,
    frame_height: int,
    depth_map=None,
    depth_score: float | None = None,
) -> RiskAssessment:
    """Estimate visual risk from relative depth and position.

    This is an approximate relative proximity score. It is not a physical meter
    measurement and must not be presented as a navigation guarantee.
    """
    centered = frame_width * 0.25 <= detection.center_x <= frame_width * 0.75
    if depth_score is None:
        depth_score = relative_depth_score(depth_map, detection)
    proximity = proximity_label(depth_score)

    if centered and proximity in {"VERY NEAR", "NEAR"}:
        return RiskAssessment("HIGH", proximity, depth_score, "Obstacle ahead: close", (0, 0, 255))
    if centered and proximity == "MEDIUM":
        return RiskAssessment("MEDIUM", proximity, depth_score, "Obstacle ahead", (0, 165, 255))
    return RiskAssessment("LOW", proximity, depth_score, "Object detected", (0, 255, 0))
