"""Temporal smoothing for live visual detections."""

from dataclasses import dataclass
from time import monotonic

from basira.detector import Detection


@dataclass
class _CachedDetection:
    detection: Detection
    last_seen_at: float


class DetectionStabilizer:
    """Keep recent detections visible briefly when one frame misses them.

    Live models can miss an object for a frame because of motion blur or a
    changing angle. Holding it for a short duration makes feedback readable
    without hiding a real change in the scene.
    """

    def __init__(self, hold_seconds: float = 0.7) -> None:
        self._hold_seconds = hold_seconds
        self._cache: dict[str, _CachedDetection] = {}

    def update(self, detections: list[Detection]) -> list[Detection]:
        """Return current detections plus recently seen detections."""
        now = monotonic()

        for detection in detections:
            # A label is enough for V1. Object tracking is a later milestone.
            self._cache[detection.label] = _CachedDetection(detection, now)

        self._cache = {
            label: cached
            for label, cached in self._cache.items()
            if now - cached.last_seen_at <= self._hold_seconds
        }

        return [cached.detection for cached in self._cache.values()]


class ProximityStabilizer:
    """Smooth relative-depth values over successive depth refreshes."""

    def __init__(self, alpha: float = 0.18) -> None:
        self._alpha = alpha
        self._scores: dict[str, float] = {}

    def update(self, label: str, score: float | None, refresh: bool) -> float | None:
        """Return a stable proximity score for an object label."""
        if score is None:
            return self._scores.get(label)

        if label not in self._scores:
            self._scores[label] = score
        elif refresh:
            previous = self._scores[label]
            self._scores[label] = (1 - self._alpha) * previous + self._alpha * score

        return self._scores[label]
