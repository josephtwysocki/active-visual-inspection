# Major Interfaces

This document describes the project-owned payloads passed between the major subsystems of Active Visual Inspection.

The interfaces define the boundaries between:

```text
perception
    ↓
monitoring
    ↓
dispatch
    ↓
simulation
    ↓
future inspection / decision logic
```

The goal is to keep responsibilities separated so that perception code does not directly control the drone and simulator-specific details do not leak into higher-level mission logic.

As the project develops, these interfaces should reflect capabilities that actually exist. Fields should not be added solely because they may be useful in a future version.

---

# MonitoringEvent

> **"The monitoring system saw something that warrants investigation."**

`MonitoringEvent` is produced by the passive monitoring pipeline when perception identifies an event that should trigger further investigation.

Current implementation:

```text
src/monitoring/monitoring_event.py
```

## Structure

```python
MonitoringEvent(
    camera_id="camera_1",
    timestamp="2026-10-06T10:30:00",
    event_type="suspected_smoke",
    confidence=0.70,
    image_bbox=(91, 0, 400, 180),
    search_region_id="sector_test",
)
```

Serialized representation:

```json
{
  "camera_id": "camera_1",
  "timestamp": "2026-10-06T10:30:00",
  "event_type": "suspected_smoke",
  "confidence": 0.70,
  "image_bbox": [91, 0, 400, 180],
  "search_region_id": "sector_test"
}
```

## Fields

### `camera_id`

Identifier for the monitoring camera that produced the observation.

### `timestamp`

ISO-formatted timestamp representing when the monitoring event was created.

### `event_type`

Project-owned description of the event detected by the monitoring system.

Current V1 value:

```text
suspected_smoke
```

### `confidence`

Confidence associated with the primary detection that triggered the event.

If multiple smoke detections are present, the highest-confidence detection is currently used as the primary trigger.

### `image_bbox`

Bounding box of the primary detection in the source image.

Format:

```text
(x1, y1, x2, y2)
```

The bounding box is retained as evidence/provenance. It is **not currently used to calculate the drone's world position**.

### `search_region_id`

Identifier for the predefined monitoring region associated with the event.

Example:

```text
sector_test
```

This provides the logical location that the dispatch system can later resolve into an inspection target.

---

# InspectionRequest

> **"Investigate the event detected in this monitoring region."**

`InspectionRequest` is the mission-level request created from a `MonitoringEvent`.

It represents the boundary between monitoring and drone dispatch.

Current implementation:

```text
src/dispatch/inspection_request.py
```

## Structure

```python
InspectionRequest(
    inspection_id="inspection_7cf06179",
    source_event=monitoring_event,
    reason="suspected_smoke",
    search_region_id="sector_test",
)
```

Conceptual serialized representation:

```json
{
  "inspection_id": "inspection_7cf06179",
  "source_event": {
    "camera_id": "camera_1",
    "timestamp": "2026-10-06T10:30:00",
    "event_type": "suspected_smoke",
    "confidence": 0.70,
    "image_bbox": [91, 0, 400, 180],
    "search_region_id": "sector_test"
  },
  "reason": "suspected_smoke",
  "search_region_id": "sector_test"
}
```

## Fields

### `inspection_id`

Unique identifier for the requested inspection.

Current V1 IDs use the form:

```text
inspection_<generated identifier>
```

### `source_event`

The complete `MonitoringEvent` that caused the inspection request.

Keeping the source event preserves provenance without duplicating monitoring-specific fields such as:

- camera ID;
- confidence;
- detection bounding box;
- monitoring timestamp.

For example:

```python
request.source_event.camera_id
request.source_event.confidence
request.source_event.image_bbox
```

remain available to downstream code.

### `reason`

Reason the inspection was requested.

For the current workflow this is derived from:

```python
MonitoringEvent.event_type
```

Current example:

```text
suspected_smoke
```

### `search_region_id`

Logical monitoring region that should be investigated.

Example:

```text
sector_test
```

The request deliberately contains a logical region rather than Project AirSim coordinates.

---

# InspectionTarget

> **"This is the predefined physical position associated with the requested monitoring region."**

`InspectionTarget` represents a known NED coordinate used for drone dispatch.

Current implementation:

```text
src/dispatch/search_regions.py
```

## Structure

```python
InspectionTarget(
    north=5.0,
    east=10.0,
    down=-5.0,
)
```

## Fields

### `north`

North coordinate in the current Project AirSim NED coordinate system.

### `east`

East coordinate in the current Project AirSim NED coordinate system.

### `down`

Vertical coordinate in the current Project AirSim NED coordinate system.

Because NED uses positive-down coordinates, increasingly negative values represent greater altitude above the origin.

## Region Resolution

The dispatch layer resolves:

```text
search_region_id
        ↓
InspectionTarget
```

For example:

```text
sector_test
        ↓
north=5.0
east=10.0
down=-5.0
```

Unknown search regions must fail explicitly rather than silently falling back to another target.

For V1, inspection targets are predefined.

The system does **not** currently calculate world coordinates from:

- detection bounding boxes;
- camera intrinsics;
- depth imagery;
- ray casting;
- triangulation;
- other localization methods.

---

# DispatchResult

> **"The drone was sent to the requested target; this describes whether it arrived."**

`DispatchResult` represents the outcome of the drone-dispatch operation.

It should not be confused with `InspectionResult`.

A `DispatchResult` answers:

> **Did the drone reach the requested inspection location?**

An eventual `InspectionResult` will answer:

> **What did the drone discover after arriving?**

Current implementation:

```text
src/dispatch/dispatcher.py
```

## Structure

Conceptually:

```python
DispatchResult(
    target=inspection_target,
    actual_north=5.00,
    actual_east=9.98,
    actual_down=-5.53,
    arrived=True,
)
```

## Fields

### `target`

The `InspectionTarget` requested for the dispatch.

### `actual_north`

Drone's actual north coordinate after movement completes.

### `actual_east`

Drone's actual east coordinate after movement completes.

### `actual_down`

Drone's actual down coordinate after movement completes.

### `arrived`

Boolean indicating whether the actual drone position falls within the accepted arrival tolerance.

The current Week 4 integration flow uses a tolerance of:

```text
±1.0 meter per axis
```

Exact floating-point equality is not required.

---

# Current End-to-End Interface Flow

As of the completion of Week 4, the implemented system boundary is:

```text
SmokeDetector
      ↓
DetectionResult
      ↓
MonitoringEvent
      ↓
InspectionRequest
      ↓
search_region_id
      ↓
InspectionTarget
      ↓
InspectionDispatcher
      ↓
ProjectAirSimAdapter
      ↓
Drone movement
      ↓
DispatchResult
```

The important separation of responsibilities is:

```text
Perception
    │
    │ reports what was detected
    ▼
Monitoring
    │
    │ creates a structured event
    ▼
Dispatch
    │
    │ requests and coordinates movement
    ▼
Simulation
    │
    │ executes simulator-specific commands
    ▼
Project AirSim
```

Perception code does not directly control the drone.

Monitoring code does not directly call Project AirSim.

Dispatch code interacts with Project AirSim through `ProjectAirSimAdapter` rather than directly using simulator APIs.

---

# Future Interface — InspectionResult

> **"The drone arrived and investigated the event. This is what it found."**

`InspectionResult` is the next major project interface, but it is **not yet finalized or implemented**.

It will eventually represent the result of active inspection after the drone reaches its requested inspection region.

The expected future flow is:

```text
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

Potential information may include concepts such as:

```text
inspection_id
classification
confidence
inspection evidence
observations
```

The exact structure should be defined when the active-inspection capability is implemented.

Do not treat these potential fields as part of the current interface contract.

---

# Future Interface — MissionOutcome

> **"Given the inspection result, this is what the system decided to do."**

`MissionOutcome` is also a future interface and is **not yet finalized or implemented**.

Eventually, an `InspectionResult` may lead to outcomes such as:

```text
benign campfire
      ↓
log / terminate mission
```

or:

```text
dangerous fire
      ↓
escalate to human
```

A future representation may contain concepts such as:

```text
inspection_id
decision
status
```

The exact structure should be defined only when decision and escalation behavior is implemented.

---

# Interface Design Principles

## Preserve subsystem boundaries

Higher-level application code should communicate through project-owned interfaces rather than reaching directly into another subsystem's implementation.

Prefer:

```text
MonitoringEvent
      ↓
InspectionRequest
      ↓
InspectionDispatcher
      ↓
ProjectAirSimAdapter
```

Avoid:

```text
SmokeDetector
      ↓
ProjectAirSimAdapter.move_to_ned(...)
```

---

## Preserve provenance

An inspection should retain enough information to determine what caused it.

For the current implementation, `InspectionRequest.source_event` preserves the complete triggering `MonitoringEvent`.

---

## Avoid duplicated state

Information that already exists on `MonitoringEvent` should generally remain accessible through `InspectionRequest.source_event` rather than being copied into additional fields.

---

## Keep logical and simulator coordinates separate

Monitoring produces a logical location:

```text
search_region_id="sector_test"
```

Dispatch resolves that location into a simulator target:

```text
north=5.0
east=10.0
down=-5.0
```

The monitoring pipeline should not need to understand Project AirSim's NED coordinate system.

---

## Add interfaces when capabilities exist

Interfaces should describe real system boundaries rather than speculative future architecture.

As new capabilities are implemented, this document should be updated to reflect the concrete structures used by the project.

The immediate next interface to finalize will be `InspectionResult` when active inspection is implemented.