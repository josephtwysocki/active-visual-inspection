## **Week 2 — Simulation Foundation**  
  
General Goal: Prove that we can create a simulated environment that Python can observe and control.  
  
#### **Week 2 Completion Checklist**  
1. **Select and Document the Simulator**  
Evaluate the realistic candidates against our needs—Python control, drone support, RGB cameras, environment creation, object placement, known world coordinates, and ideally reasonable smoke/fire support. Record the choice and reasoning in `docs/simulator_selection.md`.  
2. **Get the Simulator Running Locally**  
Establish a reproducible setup and document how to launch it. A fresh session should be able to get from repo → simulator running without rediscovering the setup process.  
3. **Create the V1 Property Environment**  
Build the approximate 1,000 m × 607 m property using our existing coordinate convention. It does not need to look beautiful. We need recognizable terrain, property boundaries, and the northwest base/house location.  
4. **Place the Monitoring Station**  
Put three fixed RGB cameras at the northwest base and give them collectively useful coverage of the property. For Week 2, we're only concerned that the cameras exist and produce imagery—not whether their eventual fire-detection coverage is perfect.  
5. **Retrieve all Three Fixed-Camera Feeds from Python**  
This is our first major integration test. Something in `src/simulation/` should be able to request an image from Camera 1, Camera 2, and Camera 3 and save/display the results.  
6. **Spawn and Control One Drone**  
Place the drone at the northwest base and demonstrate basic programmatic control from Python: take off, move to a requested world coordinate, hover/stop, and return toward the base. We don't need intelligent path planning.
7. **Retrieve the Drone's RGB Camera from Python**  
While the drone is at a known location, capture its camera image. At this point we should have four programmatically accessible visual sensors: three fixed + one mobile.  
8. **Verify the Coordinate Bridge**  
This is particularly important. Choose several known simulator locations and confirm that our project coordinate system maps to them predictably. We should be able to say something like `move_drone(x=700, y=400, altitude=50)` and know roughly where that means on our property.
9. **Run one Scripted End-to-End “Fake Dispatch.”**  
No CV whatsoever. Hard-code a suspected event at, say, `(720, 430)`. Start the drone at the house, command it toward that area, capture an image when it arrives, and return a simple success result. This proves the future `InspectionRequest` can physically cause something to happen in the simulator.
10. **Document the Simulation Interface**  
By the end of the week, we should know what our own code needs from the simulator. Ideally we expose a small conceptual surface such as get_fixed_camera_image`(camera_id)`, `get_drone_image()`, `get_drone_position()`, `takeoff()`, `move_to(x, y, z)`, and `return_home()`. We don't need the final abstraction yet, but we should avoid simulator-specific calls leaking everywhere.  
  
#### **Week 2 Acceptance Test**  
We can consider week 2 complete when one script can run the following process:
```
Launch simulated property

        ↓

Read Camera 1
Read Camera 2
Read Camera 3

        ↓

Create fake MonitoringEvent
"possible smoke in sector B3"

        ↓

Create fake InspectionRequest
target ≈ (720, 430)

        ↓

Drone takes off

        ↓

Drone flies toward target

        ↓

Capture drone RGB image

        ↓

Record drone position

        ↓

Return home

        ↓

SUCCESS
```  
  
#### **Explicit Week 2 Non-Goals** 
To protect the scope, do not spend Week 2 on smoke/fire detection, model training, realistic smoke physics, autonomous search, active viewpoint selection, campfire classification, orchestration agents/MCP, AWS, dashboards, sophisticated drone dynamics, or making the environment photorealistic.  
  
#### **Ongoing Week 2 Notes**  
* The prebuilt Blocks environment runs successfully on my local machine.  
* Python connect to the simulation and controls `Drone1`
* Takeoff, movement, landing, RGB imagery, and depth imagery all work
* Ground-truth position is available under `get_ground_truth_pose()["translation"]
* Testing confirmed the NED convention, with North increasing X, East increasing Y, and the altitude increasing as Z becomes more negative
* Project AirSim can remain separate from the main repo, which uses its own virtual environment and the installed `projectairsim` Python package to communciate with the external simulator 