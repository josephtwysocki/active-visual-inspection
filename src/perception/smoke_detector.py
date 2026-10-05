"""Smoke detection interface backed by Roboflow inference."""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Union

import numpy as np
from inference_sdk import InferenceConfiguration, InferenceHTTPClient


@dataclass
class SmokeDetection:
    """A single normalized smoke detection."""

    confidence: float
    label: str
    bbox: tuple[int, int, int, int]


@dataclass
class DetectionResult:
    """Normalized result returned by the smoke detector."""

    detected: bool
    detections: list[SmokeDetection]
    image_width: int
    image_height: int


class SmokeDetector:
    """Detect smoke in RGB images using a pretrained Roboflow model."""

    def __init__(
        self,
        confidence_threshold: float = 0.5,
        model_id: str = "fire-and-smoke-segmentation/11",
    ) -> None:
        api_key = os.getenv("ROBOFLOW_API_KEY")

        if not api_key:
            raise RuntimeError(
                "ROBOFLOW_API_KEY environment variable is not set."
            )

        self.confidence_threshold = confidence_threshold
        self.model_id = model_id

        self.client = InferenceHTTPClient(
            api_url="https://serverless.roboflow.com",
            api_key=api_key,
        )

        self.client.configure(
            InferenceConfiguration(api_key_transport="header")
        )

    def detect(
        self,
        image: Union[str, Path, np.ndarray],
    ) -> DetectionResult:
        """Run smoke detection and return a project-owned result."""

        result = self.client.infer(
            image,
            model_id=self.model_id,
        )

        image_width = int(result["image"]["width"])
        image_height = int(result["image"]["height"])

        detections = []

        for prediction in result.get("predictions", []):
            label = prediction["class"]
            confidence = float(prediction["confidence"])

            # Week 3 monitoring is specifically concerned with smoke.
            if label.lower() != "smoke":
                continue

            if confidence < self.confidence_threshold:
                continue

            x = float(prediction["x"])
            y = float(prediction["y"])
            width = float(prediction["width"])
            height = float(prediction["height"])

            x1 = round(x - width / 2)
            y1 = round(y - height / 2)
            x2 = round(x + width / 2)
            y2 = round(y + height / 2)

            detections.append(
                SmokeDetection(
                    confidence=confidence,
                    label=label,
                    bbox=(x1, y1, x2, y2),
                )
            )

        return DetectionResult(
            detected=bool(detections),
            detections=detections,
            image_width=image_width,
            image_height=image_height,
        )