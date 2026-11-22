"""Live vision foundation for Basira."""

import cv2

from basira.camera import open_camera
from basira.config import CameraConfig
from basira.depth import RelativeDepthEstimator
from basira.detector import ObjectDetector
from basira.risk import assess_risk, relative_depth_score
from basira.stability import DetectionStabilizer, ProximityStabilizer


def draw_header(frame, camera_name: str) -> None:
    """Draw the application header over the live feed."""
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 96), (18, 24, 37), -1)
    cv2.putText(
        frame,
        "BASIRA | LIVE VISION INPUT",
        (20, 38),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.82,
        (255, 255, 255),
        2,
    )
    cv2.putText(
        frame,
        f"Camera: {camera_name} | AI detection: active",
        (20, 74),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.56,
        (135, 206, 235),
        1,
    )
    cv2.putText(
        frame,
        "Press q to stop",
        (20, frame.shape[0] - 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (255, 255, 255),
        1,
    )


def run() -> None:
    """Run the current Basira camera milestone."""
    config = CameraConfig()

    try:
        camera, camera_name = open_camera(config)
    except RuntimeError as error:
        print(error)
        return

    print("Loading Basira object-detection model...")
    detector = ObjectDetector()
    print("Loading Basira relative-depth model...")
    depth_estimator = RelativeDepthEstimator()
    stabilizer = DetectionStabilizer()
    proximity_stabilizer = ProximityStabilizer()
    depth_map = None
    frame_number = 0
    print(f"Basira started with {camera_name}. Press q to stop.")

    while True:
        ok, frame = camera.read()
        if not ok:
            print("Camera stream stopped.")
            break

        frame_number += 1
        # Depth inference is heavier than object detection, so refresh it every
        # sixth frame and reuse the latest map in between.
        depth_refreshed = frame_number % 6 == 0 or depth_map is None
        if depth_refreshed:
            depth_map = depth_estimator.estimate(frame)

        draw_header(frame, camera_name)

        stable_detections = stabilizer.update(detector.detect(frame))
        for detection in stable_detections:
            raw_depth_score = relative_depth_score(depth_map, detection)
            stable_depth_score = proximity_stabilizer.update(
                detection.label,
                raw_depth_score,
                depth_refreshed,
            )
            risk = assess_risk(
                detection,
                frame.shape[1],
                frame.shape[0],
                depth_map,
                stable_depth_score,
            )
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
                (detection.x1, max(detection.y1 - 10, 115)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.58,
                risk.color,
                2,
            )
        cv2.imshow(config.window_title, frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()
