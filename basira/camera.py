"""Camera acquisition for Basira."""

import cv2

from basira.config import CameraConfig


def open_camera(config: CameraConfig) -> tuple[cv2.VideoCapture, str]:
    """Open the preferred iPhone source, otherwise use the Mac camera."""
    camera = cv2.VideoCapture(config.preferred_source)
    if camera.isOpened():
        return camera, "iPhone camera"

    camera.release()
    camera = cv2.VideoCapture(config.fallback_source)
    if camera.isOpened():
        return camera, "Mac camera (development mode)"

    raise RuntimeError("No camera is available. Check camera permissions and retry.")
