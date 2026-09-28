## **Week 3 — Perception Foundation**

General Goal: Move from simulator control to the first real computer-vision capability. By the end of Week 3, the project should be able to take an RGB image, run a smoke-detection pipeline, and convert a positive detection into a structured `MonitoringEvent` that is ready for downstream dispatch.

#### **Week 3 Completion Checklist**

1. **Define the Week 3 Perception Boundary**  
Keep this week focused on passive monitoring only. The goal is not yet to solve campfire-vs-dangerous-fire classification, active viewpoint selection, orchestration agents, MCP, or AWS. The fixed-camera side should answer one question: *does this image contain evidence that warrants inspection?*

2. **Create a Monitoring/Perception Module**  
Add a dedicated area under `src/` for passive visual monitoring. Keep simulator-specific code separate from CV-specific code so image analysis can be tested on saved images without launching Project AirSim.

Suggested structure:
```text
src/
├── simulation/
│   └── ...
└── perception/
    ├── __init__.py
    ├── smoke_detector.py
    └── test_smoke_detector.py
```

3. **Define a Minimal Detector Interface**  
Create a small project-owned interface for smoke detection. The rest of the application should not need to know which model or framework is used internally.

Conceptually:
```python
result = detector.detect(image)
```

The result should contain enough information to support a future `MonitoringEvent`, such as:
- whether smoke was detected
- confidence
- bounding box(es)
- optional class label
- source image dimensions

4. **Select a Practical First Smoke-Detection Approach**  
Choose the simplest approach that gives us a working baseline. Preference should be given to an existing pretrained detector or quickly usable model before spending time on custom training.

Document:
- model/framework selected
- why it was selected
- input/output expectations
- known limitations
- whether additional training is likely to be needed later

5. **Build a Small Smoke Test Set**  
Create a small, intentionally simple set of test images containing:
- clear smoke
- no smoke
- visually confusing negatives where practical

The goal is not benchmark-quality evaluation yet. The goal is to have repeatable examples that let us see whether changes improve or break behavior.

6. **Run the Detector on Static Images**  
Demonstrate the smoke detector running independently of the simulator.

For each test image, record:
- detection/no detection
- confidence
- bounding box
- runtime if convenient

Save at least one annotated output image showing the detection.

7. **Convert Detector Output into a `MonitoringEvent`**  
Create a small translation layer from detector output into the structure already defined in `docs/interfaces.md`.

Example target shape:
```json
{
  "camera_id": "camera_2",
  "timestamp": "2026-09-17T14:30:00",
  "event_type": "suspected_smoke",
  "confidence": 0.67,
  "image_bbox": [812, 310, 895, 447],
  "search_region_id": "sector_b3"
}
```

For Week 3, `search_region_id` may be hard-coded or assigned by a simple mock mapping. Exact fixed-camera geometry is deferred until the custom environment exists.

8. **Exercise the Pipeline on Project AirSim RGB Data**  
Use a saved frame or live frame from the Project AirSim adapter and pass it through the same detector interface.

The image does not need to contain smoke yet. This step proves that simulator imagery and perception code are compatible:

```text
Project AirSim RGB
        ↓
NumPy image
        ↓
Smoke detector
        ↓
Detection result
```

9. **Create a Synthetic Positive End-to-End Monitoring Test**  
Because the current Blocks environment does not contain our final fire/smoke scene, create one controlled positive-path test.

Acceptable options include:
- a known smoke image passed directly through the detector
- a smoke image composited into a simulator frame for testing
- a mocked positive detector result if needed for the interface test

The purpose is to demonstrate:

```text
image
  ↓
smoke detection
  ↓
MonitoringEvent
  ↓
ready for InspectionRequest creation
```

10. **Record a Small Baseline Evaluation**  
Use the Layer 1 monitoring metrics already defined in `docs/evaluation.md` as the guiding framework.

For the small Week 3 test set, record at minimum:
- number of smoke images correctly detected
- number of no-smoke images incorrectly flagged
- detection confidence examples
- obvious failure cases

This is not the final benchmark. It is simply the first quantitative baseline.

#### **Week 3 Acceptance Test**

We can consider Week 3 complete when one script can run the following process:

```text
Load RGB image

        ↓

Run smoke detector

        ↓

Return structured detection result

        ↓

If smoke detected:
create MonitoringEvent

        ↓

Save annotated evidence image

        ↓

Print/log detection + event payload

        ↓

SUCCESS
```

A second compatibility check should confirm that a frame obtained through `ProjectAirSimAdapter.get_drone_rgb()` can be passed through the exact same detector interface without special-case preprocessing.

#### **Explicit Week 3 Non-Goals**

To protect scope, do not spend Week 3 on:
- campfire vs dangerous-fire classification
- drone reacquisition/search behavior
- active viewpoint selection
- multi-view reasoning
- exact fixed-camera-to-world geometry
- custom Unreal property authoring
- realistic smoke simulation
- orchestration agents
- MCP
- AWS deployment
- dashboard/UI work
- custom model training unless a pretrained baseline clearly cannot work at all

#### **Week 3 Success Definition**

Week 3 is successful if passive perception has become a real, testable subsystem.

By the end of the week, the project should have crossed this boundary:

```text
Week 2:
Python can control and observe the simulated drone.

Week 3:
Python can look at an RGB image and produce a structured
"this warrants investigation" monitoring event.
```

That creates the first half of the V1 trigger chain:

```text
RGB image
    ↓
smoke detector
    ↓
MonitoringEvent
    ↓
[Week 4+]
InspectionRequest
    ↓
drone investigation
```
