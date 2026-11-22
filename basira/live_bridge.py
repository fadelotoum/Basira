"""Local WebSocket bridge between Basira Camera and the Mac AI model.

The bridge remains on the local Wi-Fi network. The iPhone sends a compressed
camera frame; the Mac returns object labels and normalized bounding boxes.
LiDAR distance remains on the iPhone and is fused in the next milestone.
"""

from __future__ import annotations

import asyncio
import base64
import json
import socket
from functools import lru_cache
from contextlib import contextmanager
from typing import Any

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from zeroconf import ServiceInfo, Zeroconf

from basira.detector import ObjectDetector

app = FastAPI(title="Basira Local Live Bridge", version="0.1.0")
SERVICE_TYPE = "_basira._tcp.local."
SERVICE_NAME = "Basira Mac._basira._tcp.local."


def local_ipv4_address() -> str:
    """Return the active LAN address without depending on a fixed Wi-Fi name."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(("10.255.255.255", 1))
            return str(probe.getsockname()[0])
        except OSError:
            return "127.0.0.1"


@contextmanager
def advertise_on_local_network(port: int = 8000):
    """Make Basira Mac discoverable by the iPhone through Bonjour."""
    address = local_ipv4_address()
    service = ServiceInfo(
        type_=SERVICE_TYPE,
        name=SERVICE_NAME,
        addresses=[socket.inet_aton(address)],
        port=port,
        properties={"path": "/ws/frames", "service": "Basira Mac"},
        server=f"{socket.gethostname()}.local.",
    )
    zeroconf = Zeroconf()
    zeroconf.register_service(service)
    try:
        yield address
    finally:
        zeroconf.unregister_service(service)
        zeroconf.close()


@lru_cache(maxsize=1)
def detector() -> ObjectDetector:
    """Load the model once, rather than once per iPhone frame."""
    return ObjectDetector()


def decode_frame(payload: dict[str, Any]) -> np.ndarray:
    """Decode a base64 JPEG frame received from Basira Camera."""
    encoded = payload.get("jpeg_base64")
    if not isinstance(encoded, str):
        raise ValueError("Missing jpeg_base64")

    image_bytes = base64.b64decode(encoded, validate=True)
    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("The received image could not be decoded")
    return image


def detect_frame(frame: np.ndarray) -> list[dict[str, Any]]:
    """Return JSON-safe, normalized detections for one iPhone camera frame."""
    height, width = frame.shape[:2]
    results: list[dict[str, Any]] = []

    for item in detector().detect(frame):
        results.append(
            {
                "label": item.label,
                "confidence": round(item.confidence, 3),
                "bbox": {
                    "x": round(item.x1 / width, 4),
                    "y": round(item.y1 / height, 4),
                    "width": round((item.x2 - item.x1) / width, 4),
                    "height": round((item.y2 - item.y1) / height, 4),
                },
            }
        )
    return results


@app.get("/health")
def health() -> dict[str, str]:
    """A simple local check that the bridge is running."""
    return {"status": "ready", "service": "Basira Local Live Bridge"}


@app.websocket("/ws/frames")
async def analyse_live_frame(websocket: WebSocket) -> None:
    """Analyse incoming camera frames and return object detections live."""
    await websocket.accept()
    frame_count = 0
    try:
        while True:
            payload = json.loads(await websocket.receive_text())
            frame_id = payload.get("frame_id")
            try:
                frame = decode_frame(payload)
                objects = await asyncio.to_thread(detect_frame, frame)
                frame_count += 1
                if frame_count == 1 or frame_count % 10 == 0:
                    print(
                        f"Basira live frame {frame_id}: {len(objects)} objects detected",
                        flush=True,
                    )
                await websocket.send_json(
                    {"type": "analysis", "frame_id": frame_id, "objects": objects}
                )
            except Exception as error:
                print(f"Basira live analysis error: {error}", flush=True)
                await websocket.send_json(
                    {"type": "error", "frame_id": frame_id, "message": str(error)}
                )
    except WebSocketDisconnect:
        return
