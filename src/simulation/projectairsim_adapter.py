"""
Project AirSim adapter for the Active Visual Inspection project.

This module isolates Project AirSim-specific behavior from the rest of the
application.

The rest of the project should eventually interact with this adapter using
our own property coordinate system rather than dealing directly with
Project AirSim concepts such as:

    - ProjectAirSimClient
    - World
    - Drone
    - NED coordinates
    - simulator-specific sensor names

Keeping those details here will make it easier to change simulation
configuration later without changing the inspection/orchestration code.

Coordinate Systems
------------------

Active Visual Inspection property coordinates:

    x -> East
    y -> South
    altitude -> Up

Project AirSim uses NED (North-East-Down):

    north -> North
    east  -> East
    down  -> Down

For V1, we define the northwest corner of the property as:

    property (0, 0)

The exact transformation between property coordinates and Project AirSim
world coordinates will ultimately depend on where the property origin is
placed in the custom simulation environment.

For now, movement methods that explicitly use NED coordinates are kept
separate from the future property-coordinate interface.
"""

from __future__ import annotations
import asyncio
import copy
from typing import Any

import numpy as np

from projectairsim import Drone, ProjectAirSimClient, World


class ProjectAirSimAdapter:
    """
    Interface between Active Visual Inspection and Project AirSim.

    The adapter owns the Project AirSim client, simulated world, and drone.

    Parameters
    ----------
    scene_config : str
        Name/path of the Project AirSim scene configuration file.

    drone_name : str, optional
        Name of the drone actor defined in the scene configuration.
        Defaults to "Drone1".

    delay_after_load_sec : float, optional
        Number of seconds Project AirSim should wait after loading the
        scene before continuing. Defaults to 2 seconds.
    """

    def __init__(
        self,
        scene_config: str,
        sim_config_path: str = "config/projectairsim/",
        drone_name: str = "Drone1",
        delay_after_load_sec: int = 2,
    ) -> None:
        """
        Initialize the Project AirSim adapter.

        Parameters
        ----------
        scene_config : str
            Name of the Project AirSim scene configuration file.

            Example:
                "scene_basic_drone.jsonc"

        sim_config_path : str, optional
            Directory containing Project AirSim simulation configuration files.

            The default points to the configuration directory owned by this
            project:

                config/projectairsim/

            Keeping simulation configuration inside this repository makes the
            Active Visual Inspection project independent of the location of the
            separate Project AirSim source-code repository.

        drone_name : str, optional
            Name of the drone actor defined in the scene configuration.

        delay_after_load_sec : int, optional
            Number of seconds to wait after loading the scene before attempting
            to interact with its actors.
        """

        self.scene_config = scene_config
        self.sim_config_path = sim_config_path
        self.drone_name = drone_name
        self.delay_after_load_sec = delay_after_load_sec

        self.client: ProjectAirSimClient | None = None
        self.world: World | None = None
        self.drone: Drone | None = None

        self.home_position: dict[str, float] | None = None

        # ------------------------------------------------------------------
        # SENSOR STATE
        # ------------------------------------------------------------------

        # Project AirSim cameras publish images asynchronously. Rather than making
        # the rest of our application deal directly with subscriptions/callbacks,
        # the adapter stores the most recently received RGB frame here.
        self._latest_rgb_frame: np.ndarray | None = None

        # Keep the subscription object so the subscription remains active for the
        # lifetime of the adapter.
        self._rgb_subscription = None

    # ------------------------------------------------------------------
    # CONNECTION MANAGEMENT
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """
        Connect to Project AirSim and initialize the world and drone.

        Expected sequence:

            ProjectAirSimClient
                    ↓
                connect
                    ↓
                  World
                    ↓
                 Drone

        The Project AirSim host (for example Blocks.exe) must already be
        running before this method is called.
        """

        if self.client is not None:
            raise RuntimeError("Adapter is already connected.")

        self.client = ProjectAirSimClient()
        self.client.connect()

        self.world = World(
            self.client,
            self.scene_config,
            delay_after_load_sec=self.delay_after_load_sec,
            sim_config_path=self.sim_config_path,
        )

        self.drone = Drone(
            self.client,
            self.world,
            self.drone_name,
        )

        # Record the simulator-space position where the drone spawned.
        self.home_position = self.get_sim_position()

    def disconnect(self) -> None:
        """
        Disconnect cleanly from Project AirSim.

        Safe cleanup is important because a failed script should not leave
        the client connected to the simulation server.
        """

        if self.client is not None:
            self.client.disconnect()

        self.client = None
        self.world = None
        self.drone = None

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    def _require_drone(self) -> Drone:
        """
        Return the initialized Drone object.

        Raises
        ------
        RuntimeError
            If connect() has not yet been called.
        """

        if self.drone is None:
            raise RuntimeError(
                "Drone is not initialized. Call connect() first."
            )

        return self.drone

    # ------------------------------------------------------------------
    # DRONE STATE
    # ------------------------------------------------------------------

    def get_sim_pose(self) -> dict[str, Any]:
        """
        Return the drone's raw ground-truth Project AirSim pose.

        Project AirSim currently returns a structure similar to:

            {
                "frame_id": "DEFAULT_ID",
                "rotation": {
                    "w": ...,
                    "x": ...,
                    "y": ...,
                    "z": ...
                },
                "translation": {
                    "x": ...,
                    "y": ...,
                    "z": ...
                }
            }

        `translation` contains the drone position in simulator coordinates.
        `rotation` contains the drone orientation.
        """

        drone = self._require_drone()
        return drone.get_ground_truth_pose()

    def get_sim_position(self) -> dict[str, float]:
        """
        Return the drone position in Project AirSim simulator coordinates.

        Returns
        -------
        dict
            Dictionary containing:

                {
                    "x": float,
                    "y": float,
                    "z": float
                }

        Based on our initial Blocks experiment:

            +x -> North
            +y -> East
            +z -> Down

        Therefore higher altitude produces a more negative z value.
        """

        pose = self.get_sim_pose()
        translation = pose["translation"]

        return {
            "x": float(translation["x"]),
            "y": float(translation["y"]),
            "z": float(translation["z"]),
        }

    # ------------------------------------------------------------------
    # FLIGHT PREPARATION
    # ------------------------------------------------------------------

    def prepare_drone(self) -> None:
        """
        Give the Project AirSim API control of the drone and arm it.

        This must occur before issuing flight commands.
        """

        drone = self._require_drone()

        drone.enable_api_control()
        drone.arm()

    # ------------------------------------------------------------------
    # BASIC FLIGHT
    # ------------------------------------------------------------------

    async def takeoff(self) -> None:
        """
        Take off and wait until the takeoff operation completes.
        """

        drone = self._require_drone()

        task = await drone.takeoff_async()
        await task

    async def land(self) -> None:
        """
        Land the drone and wait until landing completes.
        """

        drone = self._require_drone()

        task = await drone.land_async()
        await task

    def shutdown_drone(self) -> None:
        """
        Disarm the drone and return control from the API.

        This should normally be called after landing.
        """

        drone = self._require_drone()

        drone.disarm()
        drone.disable_api_control()

    # ------------------------------------------------------------------
    # NED MOVEMENT
    # ------------------------------------------------------------------

    async def move_to_ned(
        self,
        north: float,
        east: float,
        down: float,
        velocity: float = 5.0,
    ) -> None:
        """
        Move the drone to an absolute position in NED coordinates.

        Parameters
        ----------
        north : float
            Target north coordinate in meters.

        east : float
            Target east coordinate in meters.

        down : float
            Target down coordinate in meters.

            Because Project AirSim uses NED coordinates:

                down = -40

            corresponds to approximately 40 meters above the NED origin.

        velocity : float, optional
            Travel velocity in meters per second.

        Notes
        -----
        This is intentionally a simulator-coordinate method.

        Application code should eventually use move_to_property(), which
        will accept our project's East/South/Altitude convention and perform
        the conversion internally.
        """

        drone = self._require_drone()

        task = await drone.move_to_position_async(
            north=north,
            east=east,
            down=down,
            velocity=velocity,
        )

        await task

    # ------------------------------------------------------------------
    # FUTURE PROPERTY COORDINATE INTERFACE
    # ------------------------------------------------------------------

    async def move_to_property(
        self,
        x: float,
        y: float,
        altitude: float,
        velocity: float = 5.0,
    ) -> None:
        """
        Move to a location using Active Visual Inspection property coordinates.

        Property convention:

            x        -> East
            y        -> South
            altitude -> Up

        This method is intentionally not implemented yet.

        Before implementing the transformation, we need to establish the
        relationship between the northwest property origin and the simulator
        world's NED origin in our eventual custom environment.

        Keeping this method here documents the interface that the rest of
        the application will eventually use.
        """

        raise NotImplementedError(
            "Property-to-simulator coordinate mapping has not been "
            "defined yet."
        )

    # ------------------------------------------------------------------
    # DRONE RGB CAMERA
    # ------------------------------------------------------------------

    def _on_rgb_frame(
        self,
        _,
        image: dict,
    ) -> None:
        """
        Receive and decode an RGB camera message from Project AirSim.

        Project AirSim publishes camera frames as dictionaries containing the
        raw pixel buffer plus image metadata. For an uncompressed RGB scene
        camera, the relevant fields are:

            image["data"]    -> raw uint8 pixel buffer
            image["height"]  -> image height in pixels
            image["width"]   -> image width in pixels

        The adapter converts that simulator-specific representation into a
        standard NumPy array with shape:

            (height, width, 3)

        This keeps Project AirSim message details inside the adapter. Downstream
        perception code can work directly with ordinary NumPy/OpenCV images.

        Parameters
        ----------
        _ :
            Project AirSim callback metadata. Currently unused.

        image : dict
            Project AirSim RGB camera message.
        """

        if image is None:
            return

        # Interpret Project AirSim's raw image bytes as unsigned 8-bit pixels.
        pixel_data = np.frombuffer(
            image["data"],
            dtype=np.uint8,
        )

        # Convert the flat pixel buffer into a conventional H x W x 3 image.
        rgb_frame = np.reshape(
            pixel_data,
            (
                image["height"],
                image["width"],
                3,
            ),
        )

        # Store the latest decoded frame for retrieval by application code.
        self._latest_rgb_frame = rgb_frame


    def start_rgb_camera(
        self,
        camera_name: str = "DownCamera",
    ) -> None:
        """
        Subscribe to the drone's RGB scene-camera topic.

        Project AirSim represents the entries in ``drone.sensors`` as topic
        identifiers. The ProjectAirSimClient owns the subscription mechanism.

        When a new RGB frame is published, ``_on_rgb_frame`` is invoked and
        the adapter stores the latest frame for use by the application.

        Parameters
        ----------
        camera_name : str, optional
            Name of the camera sensor defined in the drone configuration.
            The stock Blocks configuration uses ``DownCamera``.
        """

        drone = self._require_drone()

        if self.client is None:
            raise RuntimeError(
                "Project AirSim client is not initialized. Call connect() first."
            )

        # Ensure we cannot accidentally return a frame retained from an earlier
        # subscription.
        self._latest_rgb_frame = None

        # The value stored here is a Project AirSim topic identifier, not an
        # object with its own subscribe() method.
        rgb_topic = drone.sensors[camera_name]["scene_camera"]

        self._rgb_subscription = self.client.subscribe(
            rgb_topic,
            self._on_rgb_frame,
        )


    def get_drone_rgb(self) -> np.ndarray | None:
        """
        Return the most recently received drone RGB frame.

        Returns
        -------
        np.ndarray | None
            Copy of the latest RGB frame, or None if no frame has arrived yet.

        A copy is returned so downstream OpenCV processing cannot accidentally
        modify the frame stored internally by the adapter.
        """

        if self._latest_rgb_frame is None:
            return None

        return self._latest_rgb_frame.copy()

    # ------------------------------------------------------------------
    # RETURN HOME
    # ------------------------------------------------------------------
    

    async def return_home(
        self,
        altitude: float = 5.0,
        velocity: float = 5.0,
    ) -> None:
        """
        Return the drone above its recorded starting location.

        The drone first moves horizontally back to its original North/East
        coordinates while remaining at the requested altitude.

        This method does NOT land the drone. Landing is intentionally a
        separate operation.

        Parameters
        ----------
        altitude : float, optional
            Height above the recorded home position, in meters.

        velocity : float, optional
            Travel velocity in meters per second.

        Notes
        -----
        Project AirSim uses NED coordinates, so moving upward means decreasing
        the simulator Z/down coordinate.

        If the recorded home position has:

            z = -2.7

        and we request an altitude of 5 meters above home, the target down
        coordinate becomes approximately:

            -2.7 - 5.0 = -7.7
        """

        if self.home_position is None:
            raise RuntimeError(
                "Home position is unavailable. Call connect() first."
            )

        home_north = self.home_position["x"]
        home_east = self.home_position["y"]

        # NED uses positive-down coordinates, therefore altitude above home
        # is represented by subtracting from the home Z coordinate.
        home_down = self.home_position["z"] - altitude

        await self.move_to_ned(
            north=home_north,
            east=home_east,
            down=home_down,
            velocity=velocity,
        )