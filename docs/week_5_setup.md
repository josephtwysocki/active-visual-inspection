# Week 5 — Active Inspection and Inspection Results

## Objective

Extend the dispatch capability completed in Week 4 so that a drone that reaches an inspection region can actively investigate the suspected event.

By the end of Week 5, the system should be able to take an `InspectionRequest`, dispatch the simulated drone to the requested inspection location, capture close-range RGB evidence, run perception on that evidence, and produce a structured `InspectionResult`.

The Week 5 milestone is:

> **A dispatched drone can arrive at a suspected smoke location, capture inspection evidence, analyze that evidence, and return a structured inspection result.**

This week is about **active inspection**.

It is not yet about deciding what the system should ultimately do with the inspection result.

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

Simulator-specific behavior is isolated behind `ProjectAirSimAdapter`.

### Week 3 — Monitoring and Perception

The project can:

- run a pretrained Roboflow smoke model;
- accept image files and simulator-shaped NumPy frames;
- normalize Roboflow output into project-owned detection structures;
- determine whether smoke is present;
- create a structured `MonitoringEvent`;
- save annotated evidence;
- process actual Project AirSim RGB frames;
- detect smoke in a positive 400×225 simulator-shaped frame.

### Week 4 — Monitoring-to-Inspection Dispatch

The project can now:

- represent an inspection with `InspectionRequest`;
- preserve the triggering `MonitoringEvent` as request provenance;
- represent predefined NED inspection targets;
- resolve `search_region_id` values into inspection targets;
- fail clearly when a requested region does not exist;
- accept an `InspectionRequest` through `InspectionDispatcher`;
- dispatch through `ProjectAirSimAdapter`;
- move the drone to the requested inspection target;
- retrieve the drone's actual position after movement;
- verify arrival using a defined positional tolerance;
- produce a `DispatchResult`;
- safely return home and land after both successful and failed dispatches.

The Week 4 integration test successfully demonstrated:

```text
MonitoringEvent
      ↓
InspectionRequest
      ↓
Search-region resolution
      ↓
InspectionDispatcher
      ↓
ProjectAirSimAdapter
      ↓
Drone movement
      ↓
Arrival confirmation
      ↓
DispatchResult
```

Week 5 begins where that flow ends.

---

# Week 5 System Boundary

The Week 5 flow should be:

```text
InspectionRequest
      ↓
Dispatch
      ↓
Drone arrives
      ↓
Capture RGB inspection evidence
      ↓
Inspection perception
      ↓
InspectionResult
```

The complete project flow through Week 5 should therefore become:

```text
Monitoring image
      ↓
SmokeDetector
      ↓
MonitoringEvent
      ↓
InspectionRequest
      ↓
InspectionDispatcher
      ↓
Drone arrives
      ↓
Capture close-range RGB evidence
      ↓
Analyze inspection evidence
      ↓
InspectionResult
```

The major new capability is everything after arrival.

---

# Core Design Principle

The monitoring detection and the drone inspection are two separate observations.

The fixed monitoring camera says:

> **"I saw something that looks like smoke."**

The drone then says:

> **"I traveled there and this is what I observed."**

Do not treat the original `MonitoringEvent` as the final determination.

Prefer:

```text
MonitoringEvent
      ↓
InspectionRequest
      ↓
Drone dispatch
      ↓
New drone observation
      ↓
InspectionResult
```

This distinction is central to the active-perception architecture.

The drone is not simply transporting the original detection result. It is acquiring new evidence from a new viewpoint.

---

# Goal 1 — Finalize `InspectionResult`

Review the future `InspectionResult` section in `interfaces.md` and implement the minimum concrete representation required for the current V1 workflow.

The result should contain enough information to answer:

- which inspection was performed;
- whether relevant smoke was observed;
- the confidence associated with the inspection observation;
- what evidence was captured;
- whether the inspection completed successfully.

Do not add fields simply because they might be useful later.

The interface should support the Week 5 workflow rather than attempting to represent every future inspection scenario.

A conceptual result might resemble:

```text
InspectionResult(
    inspection_id=...,
    detected=True,
    classification="smoke",
    confidence=0.86,
    evidence_path=...,
    ...
)
```

The exact fields should be finalized during implementation.

Do not yet include final mission decisions such as:

```text
log
escalate
terminate
notify human
```

Those belong to a later decision layer.

---

# Goal 2 — Capture Inspection Evidence

After successful dispatch and arrival confirmation, capture a new RGB frame from the drone.

The evidence must come from the drone after it reaches the inspection target.

The flow should be:

```text
DispatchResult(arrived=True)
      ↓
Drone RGB camera
      ↓
New inspection frame
```

Use the existing RGB camera capability exposed through `ProjectAirSimAdapter`.

Project AirSim-specific subscription and image-decoding logic should remain inside:

```text
src/simulation/
```

Higher-level inspection code should work with the NumPy image returned by the adapter.

The inspection layer should not directly subscribe to Project AirSim topics.

---

# Goal 3 — Save Inspection Evidence

Save the captured inspection frame so that a successful inspection has visible evidence associated with it.

For V1, a simple local output path is sufficient.

The saved evidence should make it possible to inspect what the drone actually saw during the test.

A reasonable output organization might be:

```text
data/
└── test_outputs/
    └── inspections/
        └── ...
```

The exact naming convention can be determined during implementation.

Avoid building a generalized evidence-management system.

Local files are sufficient.

---

# Goal 4 — Run Perception on the Drone Observation

Run smoke perception against the newly captured drone frame.

Reuse the existing Week 3 perception capability wherever possible.

Conceptually:

```text
Drone RGB frame
      ↓
SmokeDetector
      ↓
DetectionResult
```

Do not create a second smoke-detection implementation solely for inspection.

The same normalized project-owned perception structures should remain useful regardless of whether the image originated from:

- a monitoring camera;
- a test image;
- a drone camera.

Week 5 should demonstrate that the perception capability can participate in an active inspection workflow.

---

# Goal 5 — Convert Inspection Perception → `InspectionResult`

Create inspection logic that converts the perception output from the drone observation into an `InspectionResult`.

Conceptually:

```text
InspectionRequest
      +
DetectionResult from drone evidence
      +
saved evidence
      ↓
InspectionResult
```

The result should preserve the relationship to the original inspection request.

For example:

```text
inspection_1234
      ↓
dispatch
      ↓
drone evidence
      ↓
smoke detected
      ↓
InspectionResult(
    inspection_id="inspection_1234",
    ...
)
```

At this point, the active-inspection system's responsibility ends.

The inspection layer should report what it observed.

It should not decide the final mission response.

---

# Goal 6 — Preserve the Difference Between Dispatch and Inspection

`DispatchResult` and `InspectionResult` represent different system outcomes.

`DispatchResult` answers:

> **Did the drone reach the requested location?**

`InspectionResult` answers:

> **What did the drone observe after reaching that location?**

Keep these concepts separate.

For example:

```text
DispatchResult(arrived=False)
```

means inspection cannot proceed normally.

But:

```text
DispatchResult(arrived=True)
InspectionResult(detected=False)
```

is a valid inspection outcome.

It means:

> The drone successfully investigated the requested location but did not confirm the suspected smoke.

That distinction will become important when decision logic is added later.

---

# End-to-End Week 5 Test

Create one explicit integration test that proves the complete Week 5 boundary.

The test may begin with a synthetic or previously validated `MonitoringEvent`.

The monitoring-side Roboflow call does not need to be repeated.

The test should demonstrate:

```text
Create MonitoringEvent
      ↓
Create InspectionRequest
      ↓
Connect to Project AirSim
      ↓
Take off
      ↓
Dispatch drone
      ↓
Confirm arrival
      ↓
Capture drone RGB evidence
      ↓
Save inspection evidence
      ↓
Run smoke perception
      ↓
Create InspectionResult
      ↓
Return home
      ↓
Land
```

The test should fail loudly if:

- the inspection request cannot be created;
- the search region cannot be resolved;
- the simulator cannot connect;
- dispatch fails;
- the drone does not arrive within the accepted tolerance;
- an inspection frame cannot be obtained;
- inspection perception cannot execute;
- an `InspectionResult` cannot be produced.

The test should return the drone to its starting/home state when possible, including when an error occurs after takeoff.

---

# Handling the Inspection Test Scene

The existing Project AirSim Blocks environment is sufficient for proving drone movement, but it does not inherently provide a real smoke event at the inspection target.

Week 5 should solve only the minimum problem necessary to prove the active-inspection pipeline.

Do not expand the work into a complete 150-acre environment or sophisticated fire simulation.

The integration test needs a controlled way to provide inspection imagery that allows the pipeline to demonstrate:

```text
arrival
    ↓
new visual evidence
    ↓
perception
    ↓
InspectionResult
```

The exact mechanism should be selected during implementation based on what Project AirSim can support cleanly.

Any test-specific mechanism should be clearly identified as such rather than presented as final production behavior.

---

# Definition of Done

Week 5 is complete when all of the following are true:

- [ ] `InspectionResult` has a concrete V1 implementation.
- [ ] Successful dispatch can transition into active inspection.
- [ ] A new RGB frame is captured after the drone reaches the inspection target.
- [ ] Inspection evidence can be saved locally.
- [ ] The existing smoke detector can process the drone inspection frame.
- [ ] Inspection perception produces a normalized `DetectionResult`.
- [ ] Inspection perception can be converted into an `InspectionResult`.
- [ ] `InspectionResult` preserves the associated inspection identifier.
- [ ] `DispatchResult` and `InspectionResult` remain separate concepts.
- [ ] A negative inspection result can be represented without treating successful dispatch as a failure.
- [ ] Simulator-specific camera behavior remains behind `ProjectAirSimAdapter`.
- [ ] The integration test returns/lands the drone safely.
- [ ] One end-to-end Week 5 test demonstrates the complete active-inspection flow.

The final successful flow should be:

```text
MonitoringEvent
      ↓
InspectionRequest
      ↓
Drone dispatch
      ↓
Arrival confirmation
      ↓
Capture new evidence
      ↓
Inspection perception
      ↓
InspectionResult
```

---

# Explicit Non-Goals

To prevent feature drift, the following are **not Week 5 work**.

## No New CV Model Training

Do not:

- train another smoke model;
- fine-tune the current Roboflow model;
- build a custom fire dataset;
- optimize smoke-model accuracy;
- add object tracking;
- add temporal smoke analysis.

The existing perception capability is sufficient for proving the active-inspection architecture.

---

## No Fire vs. Campfire Decision Yet

The final project scenario distinguishes acceptable campfires from dangerous fires.

Do not implement that decision in Week 5.

Week 5 ends with:

```text
InspectionResult
```

It does not continue into:

```text
InspectionResult
      ↓
benign vs. dangerous
      ↓
log vs. escalate
```

That belongs to a later phase.

---

## No Human Escalation

Do not add:

- notifications;
- email alerts;
- SMS alerts;
- dashboards;
- emergency-service integration;
- human approval workflows.

Week 5 reports what the drone observed.

It does not yet act on that observation.

---

## No Autonomous Search Pattern

The drone does not need to:

- sweep the region;
- orbit the target;
- select viewpoints;
- perform waypoint searches;
- dynamically reposition based on perception;
- autonomously explore.

For V1, the drone can inspect from the predefined inspection target.

More sophisticated active-viewpoint behavior can be introduced later if it becomes necessary.

---

## No Exact Smoke Localization

Do not derive smoke world coordinates from:

- image bounding boxes;
- depth imagery;
- camera intrinsics;
- ray casting;
- triangulation;
- segmentation masks.

Continue using the predefined inspection target associated with the monitoring region.

---

## No Agent or MCP Layer Yet

Do not add:

- LLM decision making;
- MCP servers;
- MCP tools;
- agent frameworks;
- autonomous planning;
- natural-language mission control.

Week 5 should produce another deterministic capability that a future agent can orchestrate.

The future agent should call reliable tools rather than compensate for unfinished underlying behavior.

---

## No Full Property Simulation

Do not build the complete 150-acre property yet.

Do not add all three final monitoring cameras.

Do not attempt to create the entire final competition environment.

A controlled inspection scenario is sufficient for proving the Week 5 architecture.

---

## No Production Infrastructure

Do not add:

- databases;
- message queues;
- cloud infrastructure;
- AWS services;
- persistent event stores;
- REST APIs;
- authentication;
- generalized media storage.

Local Python objects and files remain sufficient.

---

# Expected Source Organization

Continue the existing separation of responsibilities.

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
├── dispatch/
│   ├── inspection_request.py
│   ├── search_regions.py
│   └── dispatcher.py
│
├── inspection/
│   ├── inspection_result.py
│   └── inspector.py
│
├── simulation/
│   └── projectairsim_adapter.py
│
└── ...
```

The exact filenames can change if implementation reveals a cleaner structure.

The important conceptual boundary becomes:

```text
perception
    ↓
monitoring
    ↓
dispatch
    ↓
inspection
```

with:

```text
simulation
```

providing the simulator-specific capabilities required by dispatch and inspection.

No layer should reach around another layer merely because doing so is convenient.

---

# What Comes After Week 5

Do not implement these items during Week 5, but keep the project direction visible.

Once the system can produce a reliable `InspectionResult`, the next capability should be **mission decision and outcome handling**.

Conceptually:

```text
InspectionResult
      ↓
Decision logic
      ↓
MissionOutcome
```

For the final V1 scenario:

```text
InspectionResult
      ↓
benign campfire
      ↓
log / terminate
```

or:

```text
InspectionResult
      ↓
dangerous fire
      ↓
escalate to human
```

That phase should finalize the `MissionOutcome` interface and establish the deterministic decision capabilities required before introducing agentic orchestration.

After monitoring, dispatch, inspection, and outcome handling all exist as reliable deterministic capabilities, the project can begin introducing the MCP/agent layer that orchestrates them.

---

# Week 5 Guiding Question

When deciding whether to add something this week, ask:

> **Is this required for a drone that has reached an inspection region to acquire new visual evidence and produce a structured `InspectionResult`?**

If the answer is **no**, it belongs in a later week.