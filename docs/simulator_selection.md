# Simulator Selection

## Selected Simulator

Project AirSim

## Rationale

Project AirSim was selected because the project requires:

- Python-based simulation control
- autonomous drone support
- RGB camera access
- world-coordinate navigation
- custom environments
- integration with OpenCV
- support for headless/cloud execution

## Local Feasibility Test

A Project AirSim prebuilt Blocks environment was tested on Windows 11
using the Project AirSim Python client.

The `hello_drone.py` example successfully:

- connected to the simulation server
- spawned a drone
- commanded the drone to take off
- hovered/moved the drone
- landed the drone
- retrieved RGB camera imagery
- retrieved depth imagery
- displayed sensor imagery through OpenCV
- disconnected cleanly

Project AirSim is therefore selected as the V1 simulation platform.