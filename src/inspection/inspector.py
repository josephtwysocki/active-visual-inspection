"""Capture and analyze new drone evidence after confirmed dispatch arrival."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import cv2
import numpy as np

from src.inspection.inspection_result import InspectionResult
from src.dispatch.search_regions import resolve_search_region

if TYPE_CHECKING:
    from src.dispatch.dispatcher import DispatchResult
    from src.dispatch.inspection_request import InspectionRequest
    from src.perception.smoke_detector import SmokeDetector
    from src.simulation.projectairsim_adapter import ProjectAirSimAdapter


class Inspector:
    """Acquire inspection evidence and report observations without mission decisions.

    The caller owns takeoff, dispatch, return-home, landing, and connection
    cleanup. Start the adapter's RGB camera before calling ``inspect``.
    """

    def __init__(
        self,
        adapter: ProjectAirSimAdapter,
        detector: SmokeDetector,
        output_dir: str | Path = "data/test_outputs/inspections",
    ) -> None:
        self.adapter = adapter
        self.detector = detector
        self.output_dir = Path(output_dir)

    async def inspect(
        self,
        request: InspectionRequest,
        dispatch_result: DispatchResult,
        capture_timeout_sec: float = 10.0,
    ) -> InspectionResult:
        """Capture, save, and analyze evidence for an arrived inspection request.

        Operational failures produce ``completed=False`` with no detection
        outcome. Cancellation still propagates. Successful negative detection
        produces ``completed=True, detected=False``.
        """
        if not dispatch_result.arrived:
            return InspectionResult(
                inspection_id=request.inspection_id,
                completed=False,
                error="Inspection did not run: dispatch did not confirm arrival.",
            )

        saved_path: str | None = None
        stage = "request/dispatch validation"
        try:
            if dispatch_result.target != resolve_search_region(request.search_region_id):
                raise ValueError("Dispatch target does not match the requested region.")

            stage = "RGB capture"
            frame = await self.adapter.capture_drone_rgb(
                timeout_sec=capture_timeout_sec
            )
            if (
                not isinstance(frame, np.ndarray)
                or frame.ndim != 3
                or frame.shape[2] != 3
                or frame.size == 0
                or frame.dtype != np.uint8
            ):
                raise ValueError("Expected a nonempty H x W x 3 uint8 RGB frame.")

            stage = "evidence saving"
            self.output_dir.mkdir(parents=True, exist_ok=True)
            evidence_path = self.output_dir / f"inspection_{uuid4().hex}_rgb.png"
            saved = cv2.imwrite(
                str(evidence_path), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            )
            if not saved:
                raise OSError("OpenCV could not write the inspection image.")
            saved_path = str(evidence_path)

            stage = "smoke perception"
            # Analyze exactly the image saved as evidence. Using its file path
            # also avoids ambiguity about NumPy RGB/BGR conventions in the SDK.
            # The synchronous network call runs outside the async flight loop.
            observation = await asyncio.to_thread(self.detector.detect, saved_path)
            if observation.detected != bool(observation.detections):
                raise ValueError("Detector returned an inconsistent detection result.")
            confidence = (
                max(detection.confidence for detection in observation.detections)
                if observation.detected
                else None
            )

            stage = "inspection result construction"
            return InspectionResult(
                inspection_id=request.inspection_id,
                completed=True,
                detected=observation.detected,
                confidence=confidence,
                evidence_path=saved_path,
            )
        except Exception as exc:
            return InspectionResult(
                inspection_id=request.inspection_id,
                completed=False,
                evidence_path=saved_path,
                error=f"{stage} failed ({type(exc).__name__}): {exc}",
            )
