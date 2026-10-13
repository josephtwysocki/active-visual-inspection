"""Check live Project AirSim fresh-frame capture without issuing flight commands.

Run from the project root with Blocks already open:
    python -m scripts.test_fresh_rgb_capture
"""

import asyncio
from pathlib import Path

import cv2
import numpy as np

from src.simulation.projectairsim_adapter import ProjectAirSimAdapter


async def main() -> None:
    adapter = ProjectAirSimAdapter(scene_config="scene_basic_drone.jsonc")
    output_dir = Path("data/test_outputs/inspections")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        print("[CONNECT] Connecting and loading the scene...")
        adapter.connect()
        adapter.start_rgb_camera()

        for capture_number in (1, 2):
            print(f"[CAPTURE] Waiting for fresh frame {capture_number}...")
            frame = await adapter.capture_drone_rgb(timeout_sec=10.0)
            if (
                frame.ndim != 3
                or frame.shape[2] != 3
                or frame.size == 0
                or frame.dtype != np.uint8
            ):
                raise RuntimeError("Unexpected RGB frame shape or dtype.")

            evidence_path = output_dir / f"fresh_rgb_capture_{capture_number}.png"
            saved = cv2.imwrite(
                str(evidence_path), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            )
            if not saved:
                raise RuntimeError(f"Could not save evidence: {evidence_path}")

            print(f"[FRAME] shape={frame.shape}, dtype={frame.dtype}")
            print(f"[SAVED] {evidence_path}")

        print("[PASS] Two fresh-frame requests completed and saved evidence.")
    finally:
        adapter.disconnect()
        print("[CLEANUP] Disconnected.")


if __name__ == "__main__":
    asyncio.run(main())
