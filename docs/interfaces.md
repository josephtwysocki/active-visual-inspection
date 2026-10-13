# Major Interfaces

This document describes the project-owned payloads passed between the major subsystems of Active Visual Inspection.

**Current implementation: Week 6 mission handling implemented and checked with controlled fixtures on October 13, 2026.**

The implemented boundary includes monitoring, dispatch, active inspection, and deterministic mission decisions. Live inspection was validated in Week 5; the new outcome handling requires one live run for Week 6 closeout.

## Interface Overview

| Interface | Responsibility | Current implementation |
| --- | --- | --- |
| `DetectionResult` | Report normalized smoke-model output for an image | `src/perception/smoke_detector.py` |
| `MonitoringEvent` | Describe a monitoring observation that warrants investigation | `src/monitoring/monitoring_event.py` |
| `InspectionRequest` | Request investigation of a monitoring region | `src/dispatch/inspection_request.py` |
| `InspectionTarget` | Represent the predefined NED target for that region | `src/dispatch/search_regions.py` |
| `DispatchResult` | Report the target, actual position, and arrival status | `src/dispatch/dispatcher.py` |
| `InspectionResult` | Report execution status and the new drone observation | `src/inspection/inspection_result.py` |
| `MissionOutcome` | Describe the response chosen from an inspection result | `src/mission/mission_outcome.py` |

The same perception implementation supports both monitoring imagery and new drone inspection imagery. These are separate observations, even when they use the same detector.

---

## DetectionResult

**“This is what the smoke detector reported for this image.”**

`SmokeDetector.detect()` accepts an image file path or NumPy image and returns a normalized `DetectionResult`. Raw Roboflow response structures remain inside the perception implementation.

```python
DetectionResult(
    detected=True,
    detections=[
        SmokeDetection(
            confidence=0.70,
            label="smoke",
            bbox=(91, 0, 400, 180),
        )
    ],
    image_width=400,
    image_height=225,
)
```

| Field | Meaning |
| --- | --- |
| `detected` | Whether at least one qualifying smoke detection was retained |
| `detections` | List of normalized `SmokeDetection` objects |
| `image_width` | Source image width in pixels |
| `image_height` | Source image height in pixels |

Each `SmokeDetection` contains a model confidence, label, and bounding box in `(x1, y1, x2, y2)` pixel coordinates.

The current implementation retains smoke predictions meeting the configured confidence threshold. Its default threshold is `0.5`. Other model classes are filtered out.

`detected=False` means no qualifying smoke prediction was retained. It does not prove that no fire exists. Model confidence is a score associated with a prediction; this project has not established it as a calibrated probability of fire or danger.

These perception dataclasses do not currently define `to_dict()` methods. Their project-owned fields can be serialized with `dataclasses.asdict()` when needed.

---

## MonitoringEvent

**“The monitoring system saw something that warrants investigation.”**

A monitoring event preserves the triggering observation and its logical search region.

```python
MonitoringEvent(
    camera_id="camera_1",
    timestamp="2026-10-12T19:53:40+00:00",
    event_type="suspected_smoke",
    confidence=0.70,
    image_bbox=(91, 0, 400, 180),
    search_region_id="sector_test",
)
```

| Field | Meaning |
| --- | --- |
| `camera_id` | Monitoring camera identifier |
| `timestamp` | ISO-formatted event creation timestamp |
| `event_type` | Project-owned event description; currently `suspected_smoke` |
| `confidence` | Highest confidence among the qualifying smoke detections used to create the event |
| `image_bbox` | Bounding box of that primary detection in the monitoring image |
| `search_region_id` | Logical region associated with the monitoring observation |

`create_monitoring_event()` returns `None` for a negative `DetectionResult`. For a positive result, it uses the highest-confidence detection as the primary trigger.

`MonitoringEvent.to_dict()` returns a serializable dictionary. When encoded as JSON, the bounding-box tuple becomes an array.

Timestamps are ISO strings; the current interface does not require timezone awareness. New integration-test events use timezone-aware UTC timestamps. The event timestamp is not a simulator camera-exposure timestamp.

The bounding box preserves image provenance. It is not used to calculate world coordinates.

---

## InspectionRequest

**“Investigate the event detected in this monitoring region.”**

```python
InspectionRequest(
    inspection_id="inspection_988cb783",
    source_event=monitoring_event,
    reason="suspected_smoke",
    search_region_id="sector_test",
)
```

| Field | Meaning |
| --- | --- |
| `inspection_id` | Identifier for this inspection, currently generated as `inspection_<8 hex characters>` |
| `source_event` | Complete `MonitoringEvent` that triggered the request |
| `reason` | Request reason, derived from `source_event.event_type` |
| `search_region_id` | Logical monitoring region to investigate |

`create_inspection_request(event)` generates the identifier and copies the event type and logical region into the request.

Keeping `source_event` preserves the monitoring camera, timestamp, confidence, and bounding box without duplicating those fields. `InspectionRequest.to_dict()` serializes the nested event.

The request contains a logical region. It does not contain simulator coordinates or a final mission decision.

---

## InspectionTarget

**“This is the predefined physical position associated with the requested region.”**

```python
InspectionTarget(north=5.0, east=10.0, down=-5.0)
```

| Field | Meaning |
| --- | --- |
| `north` | North coordinate in meters |
| `east` | East coordinate in meters |
| `down` | Down coordinate in meters |

These coordinates use Project AirSim's NED convention. More negative `down` values represent higher positions relative to the simulator origin.

`resolve_search_region("sector_test")` currently returns the target above. Unknown regions raise `ValueError`; there is no fallback target.

V1 uses predefined region-to-target mappings. Bounding-box localization, ray casting, triangulation, and a full property-coordinate transformation remain outside the implemented workflow.

---

## DispatchResult

**“Did the drone reach the requested inspection location?”**

```python
DispatchResult(
    target=inspection_target,
    actual_north=5.00,
    actual_east=9.98,
    actual_down=-5.54,
    arrived=True,
)
```

| Field | Meaning |
| --- | --- |
| `target` | Requested `InspectionTarget` |
| `actual_north` | Actual north position after movement |
| `actual_east` | Actual east position after movement |
| `actual_down` | Actual down position after movement |
| `arrived` | Whether all three coordinate errors meet the configured tolerance |

The dispatcher and Week 5 integration test currently use a default arrival tolerance of **1.0 meter per axis**. This is an axis-wise check, not a spherical distance threshold.

`DispatchResult` is a dataclass without a custom `to_dict()` method. The integration trace serializes it with `dataclasses.asdict()`.

Dispatch success does not establish that inspection completed or that smoke exists. Return-home and landing are caller-owned cleanup operations rather than fields on `DispatchResult`.

---

## Drone RGB Capture Boundary

Simulator subscriptions and image decoding remain inside `ProjectAirSimAdapter`.

| Adapter method | Behavior |
| --- | --- |
| `start_rgb_camera(camera_name="DownCamera")` | Start the RGB subscription once per connection |
| `get_drone_rgb()` | Return a copy of the latest cached frame, or `None` |
| `await capture_drone_rgb(timeout_sec=5.0)` | Wait for a newly processed camera callback after the capture request starts; return an independent NumPy image copy |

Frames have shape `(height, width, 3)` and dtype `uint8`, using the adapter's RGB convention. The live scene produced `(225, 400, 3)` frames.

`capture_drone_rgb()` rejects nonpositive or nonfinite timeouts, requires a connected drone and started camera, and raises `TimeoutError` when no new frame becomes available. It also detects camera disconnection during the wait.

Freshness uses callback processing order. It does not verify a simulator exposure timestamp or eliminate all possible transport buffering. The caller requests capture immediately after confirmed arrival. A frame already cached when the request begins cannot satisfy it.

The inspection layer does not subscribe directly to Project AirSim topics.

---

## InspectionResult

**“This describes whether inspection completed and what the drone observation reported.”**

`InspectionResult` is now implemented as a frozen dataclass with validated field combinations.

The live Week 5 run produced:

```json
{
  "inspection_id": "inspection_988cb783",
  "completed": true,
  "detected": true,
  "confidence": 0.6585273146629333,
  "evidence_path": "data/test_outputs/inspections/inspection_308c2b0ffd074cd39611dd71be46adea_rgb.png",
  "error": null
}
```

Path separators in serialized results follow the host operating system. The example above uses forward slashes for readability.

### Fields and Valid States

| Field | Meaning |
| --- | --- |
| `inspection_id` | Identifier preserved from the associated request |
| `completed` | Whether evidence capture, saving, perception, and result construction completed |
| `detected` | `True` for smoke reported, `False` for no qualifying smoke detection, or `None` for failed inspection |
| `confidence` | Highest qualifying smoke confidence; `None` for negative or failed inspection |
| `evidence_path` | Path to the saved new drone image; may remain available after a later failure |
| `error` | Failure description; `None` for completed inspection |

| Outcome | `completed` | `detected` | `confidence` | `evidence_path` | `error` |
| --- | --- | --- | --- | --- | --- |
| Smoke reported | `True` | `True` | Score in `[0, 1]` | Required | `None` |
| No smoke reported | `True` | `False` | `None` | Required | `None` |
| Inspection failed | `False` | `None` | `None` | Optional | Required |

An empty inspection identifier is invalid. Completed inspections require a nonempty evidence path. The result constructor records the path; it does not itself check file existence. The inspector writes the image, and the live integration script verifies that the file exists.

Negative inspection has no confidence-of-absence score because the current detector does not provide one. Inspection failure has no detection outcome because the observation was not successfully established.

`completed` does not describe flight cleanup, final mission status, human review, or detector correctness. A completed inspection can contain a false positive or false negative.

`InspectionResult.to_dict()` returns a JSON-serializable dictionary. Python `None` becomes JSON `null`.

### Inspector Contract

```python
inspector = Inspector(adapter, detector)
result = await inspector.inspect(request, dispatch_result)
```

`Inspector` is implemented in `src/inspection/inspector.py` and:

1. Rejects an unconfirmed arrival without capturing evidence.
2. Checks that the dispatch target matches the request's resolved region.
3. Requests a fresh RGB frame from the adapter.
4. Saves the frame as a uniquely named PNG under the configured output directory.
5. Reuses `SmokeDetector.detect()` on the exact saved image.
6. Converts the normalized perception output into `InspectionResult`.

The inspector's capture timeout defaults to `10.0` seconds. Saved RGB imagery is converted to OpenCV's BGR write convention before PNG encoding. File-based inference avoids ambiguity about the SDK's NumPy color convention.

Operational exceptions become failed inspection results with a stage-specific error description. Cancellation propagates. If saving succeeded before perception failed, `evidence_path` is retained.

The caller owns connection, camera startup, takeoff, dispatch, return-home, landing, and shutdown. The inspector does not choose mission responses or operate flight cleanup.

---

## Current Execution and Evidence Trace

The existing live entry point now includes Week 6 outcome handling:

```powershell
python -m scripts.test_active_inspection
```

It starts with a synthetic `MonitoringEvent` and uses actual Project AirSim drone imagery for inspection. Monitoring inference is not rerun in this test.

After inspection, the script calls `evaluate_inspection(result)`, saves the outcome, and reports its reason. For review branches, terminal output identifies the inspection, reason, evidence path (or its absence), and trace path. The trace itself is the local review record; no separate notification service or approval state is implemented.

The trace has these top-level keys:

```json
{
  "synthetic_monitoring_trigger": true,
  "inspection_evidence_source": "Project AirSim DownCamera",
  "request": {},
  "dispatch": {},
  "inspection": {},
  "outcome": {},
  "execution_error": null,
  "cleanup": {
    "completed": true,
    "errors": []
  }
}
```

The empty objects show the envelope only. Actual traces contain the full serialized payloads, including the event nested inside `request.source_event`. The request, inspection, and outcome identifiers must agree.

PNG evidence and `<inspection_id>_trace.json` remain under `data/test_outputs/inspections/`. Image filenames use a separate generated identifier; `InspectionResult.evidence_path` links the image to the request.

The trace is saved immediately after evaluation, before an incomplete inspection raises. Cleanup is initially pending (`completed=null`); the trace is rewritten after cleanup with its status and errors. Setup or dispatch exceptions produce a partial trace when writing is possible, with unavailable sections set to `null`, an `execution_error`, and no invented inspection or mission outcome. Invalid detector/region configuration fails before flight begins.

Return-home and landing remain caller-owned and are attempted after takeoff, including after inspection failure. Landing is attempted even if return-home fails. Shutdown is skipped following a failed landing. Disconnect is attempted separately. A primary inspection or execution error is preserved even if cleanup or final trace saving also fails. Cleanup errors are recorded independently and prevent `PASS`.

Controlled checks run without AirSim, Roboflow, or image-analysis dependencies:

```powershell
python -m scripts.test_mission_outcome
```

These checks use explicit positive, negative, capture-failure, and perception-failure `InspectionResult` fixtures. They verify serialization, provenance, deterministic policy, malformed-input rejection, trace recording, and cleanup/error behavior. Temporary fixture traces identify their evidence as synthetic. They do not measure detector accuracy. Fifteen controlled tests passed on October 13, 2026; a Week 6 live run was also completed on this day.

### Week 5 Validation and Known Limitation

On October 12, 2026, inspection `inspection_988cb783` reached the target with approximate axis errors of `0.00`, `0.02`, and `0.54` meters. It captured and saved drone evidence, produced the result above, and returned home and landed.

The Blocks scene was known to contain no intended smoke event. The detector nevertheless reported smoke at approximately `0.659` confidence. Record this as a known false positive, preserving the image and trace as evaluation evidence.

This run validates the live inspection pipeline. It does not validate smoke-model accuracy or demonstrate correct identification of a real fire. Positive, negative, and failed result states were also checked locally with controlled dependencies; a live negative inspection was not established by this particular run.

---

## MissionOutcome

**“Given the inspection result, this is the response the system chose.”**

`MissionOutcome` is implemented as a frozen dataclass in `src/mission/mission_outcome.py`.

```python
MissionOutcome(
    inspection_id="inspection_988cb783",
    decision="request_human_review",
    reason="smoke_observed",
)
```

| Field | Meaning |
| --- | --- |
| `inspection_id` | Nonempty string linking the response to its inspection and trace |
| `decision` | `terminate` or `request_human_review` |
| `reason` | Stable observation-specific explanation from the policy below |

The constructor validates values and decision/reason combinations. `to_dict()` returns a JSON-serializable dictionary. Evidence, confidence, and failure details remain on the linked `InspectionResult`.

### Deterministic Policy

```python
from src.mission.decision_policy import evaluate_inspection

outcome = evaluate_inspection(result)
```

| Inspection state | Decision | Reason |
| --- | --- | --- |
| `completed=True, detected=False` | `terminate` | `no_smoke_observed` |
| `completed=True, detected=True` | `request_human_review` | `smoke_observed` |
| `completed=False, detected=None` | `request_human_review` | `inspection_failed` |

The policy requires an `InspectionResult`, verifies a boolean completion flag, and revalidates result field combinations. Unsupported or malformed inputs raise rather than defaulting to termination. It makes no flight, simulator, detector, file, or network calls and introduces no second confidence threshold.

A negative result reports no qualifying prediction; it does not establish safety. A smoke result does not classify a dangerous fire or acceptable campfire. Failed inspection retains uncertainty. The known Week 5 false positive follows the same smoke-review branch as any positive observation.

A review decision means a request was recorded locally. It does not mean notification was delivered or a person approved an action. Both decisions still require return-home, landing, and disconnect. An `inspection_failed` outcome is saved before the live script raises for the underlying inspection error.

---

## Interface Design Principles

- **Preserve observations separately.** The monitoring event triggers inspection; the new drone observation determines the inspection result.
- **Preserve provenance.** Keep the source event in the request, preserve `inspection_id`, and link saved evidence through the result and trace.
- **Preserve execution distinctions.** Arrival, inspection completion, model output, cleanup success, and mission response describe separate outcomes.
- **Preserve uncertainty.** Failed observation uses `detected=None`; a negative model result does not assert safety.
- **Preserve subsystem boundaries.** Perception reports observations; dispatch coordinates movement; the adapter owns simulator behavior; inspection acquires and interprets evidence.
- **Keep coordinates explicit.** Logical monitoring regions resolve to predefined NED targets in the dispatch layer.
- **Document implemented contracts.** Mission response is implemented; Week 6 live verification remains a separate closeout requirement.
