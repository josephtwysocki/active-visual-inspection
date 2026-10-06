# Week 4 — Monitoring-to-Inspection Dispatch

## Objective

Connect the passive monitoring pipeline built in Week 3 to the drone-control capability built in Week 2.

By the end of Week 4, the system should be able to take a `MonitoringEvent` representing suspected smoke, convert it into an `InspectionRequest`, determine a predefined inspection target associated with the monitoring region, and dispatch the simulated drone to that target.

The Week 4 milestone is:

> **A smoke detection can trigger a structured inspection request that causes the Project AirSim drone to fly to the correct inspection location.**

This week is about **dispatch**, not about completing the inspection.

---

## Where We Are Starting

### Week 2 — Simulation

The project can:

- connect to Project AirSim;
- initialize the simulated drone;
- take off;
- move to NED coordinates;
- read the drone's current position;
- capture RGB imagery;
- return home and land.

The simulator-specific behavior is isolated behind `ProjectAirSimAdapter`.

### Week 3 — Monitoring and Perception

The project can:

- run a pretrained Roboflow smoke model;
- accept both image files and simulator-shaped NumPy frames;
- normalize Roboflow output into project-owned detection structures;
- determine whether smoke is present;
- create a structured `MonitoringEvent`;
- save annotated evidence;
- successfully process actual Project AirSim RGB frames;
- successfully detect smoke in a positive 400×225 simulator-shaped frame.

We therefore have two functioning pieces:

```text
Monitoring / Perception

Image
  ↓
SmokeDetector
  ↓
DetectionResult
  ↓
MonitoringEvent
```

and:

```text
Simulation / Drone Control

Target NED coordinate
  ↓
ProjectAirSimAdapter
  ↓
Drone movement
  ↓
RGB capture
```

Week 4 connects them.

---

# Week 4 System Boundary

The Week 4 flow should be:

```text
MonitoringEvent
      ↓
InspectionRequest
      ↓
Resolve search region to inspection target
      ↓
Dispatch drone
      ↓
Fly to target
      ↓
Confirm arrival
```

For example:

```text
MonitoringEvent(
    camera_id="camera_1",
    event_type="suspected_smoke",
    search_region_id="sector_test",
    ...
)
```

becomes something conceptually similar to:

```text
InspectionRequest(
    request_id=...,
    source_event=...,
    target_region="sector_test",
    target_position=...,
    reason="suspected_smoke",
    ...
)
```

The drone can then be dispatched to the corresponding NED coordinate.

---

# Core Design Principle

The monitoring system should **request an inspection**.

It should **not control the drone directly**.

Avoid:

```text
SmokeDetector
    ↓
ProjectAirSimAdapter.move_to(...)
```

Prefer:

```text
SmokeDetector
    ↓
MonitoringEvent
    ↓
InspectionRequest
    ↓
Dispatch
    ↓
ProjectAirSimAdapter
```

This keeps perception, mission logic, and simulator control separated.

That separation will become important later when an agentic orchestration layer is introduced.

---

# Search Region → World Position

A major Week 4 requirement is bridging the difference between:

```text
search_region_id="sector_test"
```

and:

```text
north=...
east=...
down=...
```

For V1, do **not** attempt to infer a real-world 3D location from the smoke bounding box.

Instead, define a small static mapping between monitoring regions and known inspection coordinates.

Conceptually:

```python
SEARCH_REGIONS = {
    "sector_test": {
        "north": 5.0,
        "east": 10.0,
        "down": -5.0,
    },
}
```

The exact representation can be refined during implementation.

This deliberately simplifies localization.

The Week 4 problem is:

> "Given that smoke was detected in region X, dispatch the drone to the predefined inspection point for region X."

It is **not**:

> "Determine the exact 3D world coordinates of smoke from image pixels."

Exact localization can be added later if the project requires it.

---

# Week 4 Goals

## Goal 1 — Finalize `InspectionRequest`

Review the existing `InspectionRequest` definition in `interfaces.md` and implement the minimum concrete representation needed for V1.

The request should contain enough information for the dispatch layer to understand:

- why an inspection was requested;
- where the inspection should occur;
- which monitoring event caused it;
- any identifier needed to track the inspection.

Do not add fields simply because they might be useful someday.

The interface should support the current V1 workflow.

---

## Goal 2 — Define Search Regions

Create a simple project-owned representation of the monitored property.

For Week 4, this can be a small number of predefined regions with known NED inspection coordinates.

At minimum, support the test region already used during Week 3:

```text
sector_test
```

A lookup should be able to perform:

```text
search_region_id
        ↓
inspection target
        ↓
north / east / down
```

Unknown regions should fail clearly rather than silently selecting a default location.

---

## Goal 3 — Convert `MonitoringEvent` → `InspectionRequest`

Create a small piece of mission/dispatch logic that accepts a `MonitoringEvent` and produces an `InspectionRequest`.

The conversion should preserve the important provenance of the request.

For example:

```text
suspected_smoke detected
        ↓
MonitoringEvent
        ↓
InspectionRequest(reason="suspected_smoke")
```

At this point, the monitoring system's responsibility ends.

---

## Goal 4 — Implement Drone Dispatch

Create a dispatch component that accepts an `InspectionRequest` and uses `ProjectAirSimAdapter` to move the drone to the requested target.

Conceptually:

```python
dispatcher.dispatch(request)
```

should result in:

```text
InspectionRequest
      ↓
target coordinates
      ↓
ProjectAirSimAdapter
      ↓
takeoff
      ↓
move to target
```

The dispatcher should depend on the simulator adapter's public interface rather than Project AirSim APIs directly.

Project AirSim-specific code should remain inside:

```text
src/simulation/
```

---

## Goal 5 — Confirm Arrival

After movement completes, retrieve the drone's actual position.

Compare the actual position with the requested inspection target.

For V1, use a reasonable positional tolerance rather than requiring exact floating-point equality.

The result should make it obvious whether dispatch succeeded.

Example output:

```text
[DISPATCH] Inspection requested for sector_test
[DISPATCH] Target: north=5.0 east=10.0 down=-5.0

[DRONE] Taking off...
[DRONE] Moving to inspection target...

[ARRIVAL]
Requested: north=5.0 east=10.0 down=-5.0
Actual:    north=5.1 east=10.0 down=-4.9

[SUCCESS] Drone arrived at inspection region.
```

---

# End-to-End Week 4 Test

Create one explicit integration test that proves the complete Week 4 boundary.

The test should begin with a synthetic or previously validated positive monitoring event.

It does **not** need to call Roboflow.

Example:

```text
Create MonitoringEvent
        ↓
Convert to InspectionRequest
        ↓
Resolve sector_test
        ↓
Connect to Project AirSim
        ↓
Take off
        ↓
Dispatch drone
        ↓
Reach target
        ↓
Confirm position
        ↓
Return home / land
```

The test should fail loudly if:

- the region cannot be resolved;
- an `InspectionRequest` cannot be created;
- the simulator cannot connect;
- movement fails;
- the drone does not arrive within the accepted tolerance.

The test should return the drone to its starting/home state when possible, including when an error occurs after takeoff.

---

# Definition of Done

Week 4 is complete when all of the following are true:

- [ ] `InspectionRequest` has a concrete V1 implementation.
- [ ] A search-region representation exists.
- [ ] `sector_test` resolves to a known NED inspection coordinate.
- [ ] A `MonitoringEvent` can be converted into an `InspectionRequest`.
- [ ] Drone dispatch accepts an `InspectionRequest`.
- [ ] Dispatch uses `ProjectAirSimAdapter` rather than Project AirSim directly.
- [ ] The simulated drone takes off and flies to the requested inspection location.
- [ ] Actual drone position is checked against the requested target.
- [ ] Arrival succeeds within a defined positional tolerance.
- [ ] The integration test returns/lands the drone safely.
- [ ] One end-to-end Week 4 test demonstrates the complete dispatch flow.

The final successful flow should be:

```text
MonitoringEvent
      ↓
InspectionRequest
      ↓
Search-region resolution
      ↓
Drone dispatch
      ↓
Project AirSim movement
      ↓
Arrival confirmation
```

---

# Explicit Non-Goals

To prevent feature drift, the following are **not Week 4 work**.

## No New CV Models

Do not:

- train another smoke model;
- tune the Roboflow model;
- build fire classification;
- classify campfires;
- add object tracking;
- add temporal smoke detection.

Week 3 perception is sufficient for the current milestone.

---

## No Exact Smoke Localization

Do not attempt to derive NED coordinates from:

- bounding-box coordinates;
- segmentation polygons;
- camera intrinsics;
- depth imagery;
- ray casting;
- triangulation.

Use predefined search-region inspection points.

---

## No Autonomous Search Pattern

The drone does not need to:

- sweep an area;
- circle a target;
- choose viewpoints;
- dynamically replan;
- explore autonomously.

It only needs to travel to the requested inspection point.

---

## No Close-Range Inspection Yet

Reaching the target completes the Week 4 mission.

Do not yet:

- capture inspection evidence;
- rerun smoke detection from the drone;
- classify fire vs. campfire;
- determine whether the situation is dangerous;
- produce `InspectionResult`.

Those belong to the next stage of the project.

---

## No Agent or MCP Layer Yet

Do not add:

- LLM decision making;
- MCP servers;
- MCP tools;
- agent frameworks;
- autonomous planning;
- natural-language mission control.

The underlying deterministic tools and interfaces should work first.

The future agent should orchestrate reliable capabilities rather than compensate for capabilities that have not been built.

---

## No Full 150-Acre Simulation Yet

The final project scenario includes three fixed cameras monitoring a 150-acre property.

Week 4 does not require modeling that entire environment.

A single test region and inspection target are enough to prove the architecture.

Expand the simulated property only when the system behavior requires it.

---

## No Production Infrastructure

Do not add:

- databases;
- message queues;
- cloud deployment;
- AWS infrastructure;
- persistent event stores;
- REST APIs;
- dashboards;
- authentication systems.

In-memory Python objects and simple configuration are sufficient.

---

# Expected Source Organization

Use the existing separation of responsibilities.

A likely organization is:

```text
src/
├── monitoring/
│   └── monitoring_event.py
│
├── perception/
│   ├── smoke_detector.py
│   └── annotation.py
│
├── simulation/
│   └── projectairsim_adapter.py
│
├── dispatch/
│   ├── inspection_request.py
│   ├── search_regions.py
│   └── dispatcher.py
│
└── ...
```

The exact filenames can change if implementation reveals a cleaner structure.

The important architectural boundaries are:

```text
perception
    ↓
monitoring
    ↓
dispatch
    ↓
simulation
```

No layer should reach around another layer merely because doing so is convenient.

---

# What Comes After Week 4

Do not implement these items during Week 4, but keep the direction visible.

Once the drone can reliably respond to an `InspectionRequest`, the next system capability should be **active inspection**:

```text
MonitoringEvent
      ↓
InspectionRequest
      ↓
Dispatch
      ↓
Drone arrives
      ↓
Capture close-range evidence
      ↓
Inspection perception
      ↓
InspectionResult
```

That is where the system begins transitioning from passive monitoring into true active perception.

Later stages can then introduce decision logic:

```text
InspectionResult
      ↓
benign campfire → log / terminate
      OR
dangerous fire → escalate to human
```

Only after these deterministic capabilities exist should the project add the agentic/MCP orchestration layer that ties them together.

---

# Week 4 Guiding Question

When deciding whether to add something this week, ask:

> **Is this required to turn a `MonitoringEvent` into a drone that arrives at the requested inspection region?**

If the answer is **no**, it belongs in a later week.
