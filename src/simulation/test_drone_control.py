"""
Basic integration test for ProjectAirSimAdapter.

This script verifies that the Active Visual Inspection project can:

1. Connect to a running Project AirSim / Blocks simulation.
2. Access Drone1 through our ProjectAirSimAdapter.
3. Read the drone's simulator position.
4. Enable API control and arm the drone.
5. Take off.
6. Move the drone to a known NED coordinate.
7. Read the resulting position.
8. Land safely.
9. Release API control.
10. Disconnect cleanly.

This is intentionally NOT a unit test.

It is a small end-to-end integration test requiring the Project AirSim
Blocks environment to already be running.

Run this script from the root of the active-visual-inspection repository:

    python -m src.simulation.test_drone_control
"""

import asyncio
from pathlib import Path
import cv2

from src.simulation.projectairsim_adapter import ProjectAirSimAdapter


# ---------------------------------------------------------------------------
# TEST CONFIGURATION
# ---------------------------------------------------------------------------

# This is the same scene configuration used by Project AirSim's
# hello_drone.py example.
SCENE_CONFIG = "scene_basic_drone.jsonc"

# Project AirSim configuration used for this integration test.
#
# Unlike the original Project AirSim example scripts, our application owns
# the simulation configuration it needs. This keeps this repository from
# depending on the location of a separate Project AirSim source-code clone.
SCENE_CONFIG = "scene_basic_drone.jsonc"
SIM_CONFIG_PATH = "config/projectairsim/"

# Name of the drone actor in the scene.
DRONE_NAME = "Drone1"

# For this first adapter test, we work directly in Project AirSim's
# North-East-Down (NED) coordinate system.
#
# These coordinates are deliberately modest because we only need to prove
# that absolute-position movement works inside the Blocks environment.
TARGET_NORTH = 5.0
TARGET_EAST = 10.0
TARGET_DOWN = -5.0

# Speed used while traveling to the test coordinate.
VELOCITY = 2.0

# Save evidence from the fake inspection here.
OUTPUT_DIR = Path("data/test_outputs")
RGB_OUTPUT_PATH = OUTPUT_DIR / "fake_dispatch_rgb.png"

def print_position(label: str, position: dict[str, float]) -> None:
    """
    Print a simulator position in a consistent, readable format.

    Parameters
    ----------
    label : str
        Description of when the position was recorded.

    position : dict[str, float]
        Position dictionary returned by
        ProjectAirSimAdapter.get_sim_position().
    """

    print(
        f"{label}: "
        f"x={position['x']:.3f}, "
        f"y={position['y']:.3f}, "
        f"z={position['z']:.3f}"
    )


async def main() -> None:
    """
    Run the Project AirSim adapter integration test.

    Flight sequence
    ---------------

    connect
        ↓
    record home position
        ↓
    enable API control + arm
        ↓
    take off
        ↓
    record takeoff position
        ↓
    move to absolute NED target
        ↓
    record resulting position
        ↓
    land
        ↓
    disarm + release API control
        ↓
    disconnect

    Cleanup is handled in ``finally`` so that we attempt to disconnect
    even if an exception occurs during the test.
    """

    adapter = ProjectAirSimAdapter(
        scene_config=SCENE_CONFIG,
        sim_config_path=SIM_CONFIG_PATH,
        drone_name=DRONE_NAME,
    )

    # Track whether API control was enabled. This lets the cleanup block
    # avoid trying to shut down a drone that was never successfully prepared.
    drone_prepared = False

    try:
        # ------------------------------------------------------------------
        # CONNECT
        # ------------------------------------------------------------------

        print("\n[CONNECT] Connecting to Project AirSim...")

        adapter.connect()

        print("Connected successfully.")

        # The adapter records the initial simulator position during connect().
        if adapter.home_position is not None:
            print_position(
                "Initial / home position",
                adapter.home_position,
            )

        # ------------------------------------------------------------------
        # PREPARE DRONE
        # ------------------------------------------------------------------

        print("\n[PREPARE] Enabling API control and arming Drone1...")

        adapter.prepare_drone()
        drone_prepared = True

        print("Drone prepared successfully.")

        # ------------------------------------------------------------------
        # START DRONE RGB CAMERA
        # ------------------------------------------------------------------
        
        print("\nStarting drone RGB camera subscription...")

        adapter.start_rgb_camera()

        # Give the camera a moment to publish its first frame.
        await asyncio.sleep(1.0)

        # ------------------------------------------------------------------
        # TAKEOFF
        # ------------------------------------------------------------------

        print("\n[TAKEOFF] Taking off...")

        await adapter.takeoff()

        takeoff_position = adapter.get_sim_position()
        print_position("Position after takeoff", takeoff_position)

        # ------------------------------------------------------------------
        # ABSOLUTE NED MOVEMENT
        # ------------------------------------------------------------------

        print(
            "\n[DISPATCH] Moving to NED target "
            f"(north={TARGET_NORTH}, "
            f"east={TARGET_EAST}, "
            f"down={TARGET_DOWN})..."
        )

        await adapter.move_to_ned(
            north=TARGET_NORTH,
            east=TARGET_EAST,
            down=TARGET_DOWN,
            velocity=VELOCITY,
        )

        target_position = adapter.get_sim_position()
        print_position("Position after movement", target_position)

        # ------------------------------------------------------------------
        # CAPTURE INSPECTION IMAGE
        # ------------------------------------------------------------------
        
        print("\n[CAPTURE] Capturing RGB inspection frame...")

        # Give the camera a brief moment to publish a frame from the new location.
        await asyncio.sleep(1.0)

        rgb_frame = adapter.get_drone_rgb()

        if rgb_frame is None:
            raise RuntimeError(
                "No RGB frame was received from the drone camera."
            )

        print(
            "RGB frame received successfully: "
            f"shape={rgb_frame.shape}, dtype={rgb_frame.dtype}"
        )

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        image_saved = cv2.imwrite(
            str(RGB_OUTPUT_PATH),
            rgb_frame,
        )

        if not image_saved:
            raise RuntimeError(
                f"OpenCV failed to save RGB frame to {RGB_OUTPUT_PATH}"
            )

        print(f"Inspection image saved to: {RGB_OUTPUT_PATH}")


        # ------------------------------------------------------------------
        # RETURN HOME
        # ------------------------------------------------------------------

        print("\n[RETURN HOME] Returning to home location...")

        await adapter.return_home(
            altitude=5.0,
            velocity=VELOCITY,
        )

        return_position = adapter.get_sim_position()
        print_position("Position above home", return_position)


        # ------------------------------------------------------------------
        # LAND AT HOME
        # ------------------------------------------------------------------

        print("\nLanding at home...")

        await adapter.land()

        landed_position = adapter.get_sim_position()
        print_position("Position after landing", landed_position)

    except Exception as exc:
        print("\nTEST FAILED")
        print(f"{type(exc).__name__}: {exc}")

        # Re-raise so the process exits as a failure rather than making a
        # failed integration test look successful.
        raise

    finally:
        # ------------------------------------------------------------------
        # CLEANUP
        # ------------------------------------------------------------------

        print("\n[6/6] Cleaning up...")

        if drone_prepared:
            try:
                adapter.shutdown_drone()
                print("Drone disarmed and API control released.")
            except Exception as exc:
                # Cleanup errors should be visible, but should not prevent
                # us from attempting to disconnect the client.
                print(f"Warning during drone shutdown: {exc}")

        try:
            adapter.disconnect()
            print("Disconnected from Project AirSim.")
        except Exception as exc:
            print(f"Warning during disconnect: {exc}")


if __name__ == "__main__":
    asyncio.run(main())