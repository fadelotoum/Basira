"""High-level analysis service shared by the live app and dashboard."""

import cv2
import numpy as np

from basira.depth import RelativeDepthEstimator
from basira.detector import Detection, ObjectDetector
from basira.risk import RiskAssessment, assess_risk


class BasiraAnalyzer:
    """Combine object detection and relative-depth analysis."""

    def __init__(self) -> None:
        self._detector = ObjectDetector()
        self._depth_estimator = RelativeDepthEstimator()

    def analyze(self, frame: np.ndarray) -> tuple[np.ndarray, list[tuple[Detection, RiskAssessment]]]:
        """Annotate a frame and return the detected objects with their risk."""
        depth_map = self._depth_estimator.estimate(frame)
        findings: list[tuple[Detection, RiskAssessment]] = []

        for detection in self._detector.detect(frame):
            risk = assess_risk(detection, frame.shape[1], frame.shape[0], depth_map)
            findings.append((detection, risk))

            cv2.rectangle(
                frame,
                (detection.x1, detection.y1),
                (detection.x2, detection.y2),
                risk.color,
                2,
            )
            text = f"{detection.label} | {risk.proximity} | {risk.level}"
            cv2.putText(
                frame,
                text,
                (detection.x1, max(detection.y1 - 10, 24)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.58,
                risk.color,
                2,
            )

        return frame, findings
