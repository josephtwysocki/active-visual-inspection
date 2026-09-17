## **Project Architecture**  

Here is an overview of the architecture of the visual inspection system:  

```
SIMULATED WORLD
      │
      ▼
3 FIXED RGB CAMERAS
      │
      ▼
MONITORING / SMOKE DETECTION
      │
      │ MonitoringEvent
      ▼
ORCHESTRATION
      │
      │ InspectionRequest
      ▼
DRONE INSPECTION
      │
      ├── navigate
      ├── reacquire
      ├── observe
      ├── reposition
      └── classify
      │
      │ InspectionResult
      ▼
ORCHESTRATION
    /    |     \
   /     |      \
TERMINATE LOG  ESCALATE
```

We start with a simulated world. Within that world, there are three fixed RGB cameras that are continuosly monitoring a property for smoke detection. This monitoring creats a `MonitoringEvent`.  
  
From there, we move into orchestration. This is where `InspectionRequests` are created.  
  
These requests then lead to drone inspections, which generate `InspectionResults`.  
  
Finally, we end up at a general orchestration layer that decides upon a final decision: terminate, log, or escalate.