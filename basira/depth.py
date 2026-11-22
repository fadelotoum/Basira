"""Relative monocular depth estimation for Basira."""

import cv2
import numpy as np
import torch
from PIL import Image


class RelativeDepthEstimator:
    """Estimate relative depth from an RGB frame.

    This module intentionally produces relative proximity, not a claimed meter
    value. Physical distance requires calibration or an additional depth sensor.
    """

    def __init__(self) -> None:
        from transformers import AutoImageProcessor, AutoModelForDepthEstimation

        self._device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        model_name = "depth-anything/Depth-Anything-V2-Small-hf"
        self._processor = AutoImageProcessor.from_pretrained(model_name)
        self._model = AutoModelForDepthEstimation.from_pretrained(model_name).to(self._device)
        self._model.eval()

    def estimate(self, frame: np.ndarray) -> np.ndarray:
        """Return a depth map aligned with the supplied OpenCV frame."""
        height, width = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb_frame)
        inputs = self._processor(images=image, return_tensors="pt")
        inputs = {name: tensor.to(self._device) for name, tensor in inputs.items()}

        with torch.no_grad():
            outputs = self._model(**inputs)

        processed = self._processor.post_process_depth_estimation(
            outputs,
            target_sizes=[(height, width)],
        )
        return processed[0]["predicted_depth"].detach().float().cpu().numpy()
