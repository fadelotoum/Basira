"""Real-time object detection for Basira."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Detection:
    """A single object found in a camera frame."""

    label: str
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def area(self) -> int:
        return max(self.x2 - self.x1, 0) * max(self.y2 - self.y1, 0)

    @property
    def center_x(self) -> int:
        return (self.x1 + self.x2) // 2


class ObjectDetector:
    """Wrap a pretrained YOLO model behind a small project-specific API."""

    def __init__(self, model_name: str = "yolo11n.pt", confidence: float = 0.45) -> None:
        from ultralytics import YOLO

        self._model = YOLO(self._resolve_model_path(model_name))
        self._confidence = confidence

    @staticmethod
    def _resolve_model_path(model_name: str) -> str:
        """Prefer a project copy, then a user-provided Desktop weight file."""
        requested = Path(model_name)
        project_model = Path(__file__).resolve().parents[1] / "models" / requested.name
        desktop_model = Path.home() / "Desktop" / requested.name

        for candidate in (requested, project_model, desktop_model):
            if candidate.is_file():
                return str(candidate)
        return model_name

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Return objects detected in one video frame."""
        result = self._model(frame, conf=self._confidence, verbose=False)[0]
        detections: list[Detection] = []

        for box in result.boxes:
            class_id = int(box.cls[0].item())
            x1, y1, x2, y2 = (int(value) for value in box.xyxy[0].tolist())
            detections.append(
                Detection(
                    label=result.names[class_id],
                    confidence=float(box.conf[0].item()),
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                )
            )

        return detections
