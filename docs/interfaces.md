## **Major Interfaces**  
  
This document describes the payloads passed between major subsytems:  
* monitoring -> orchestration
* orchestration -> drone inspeciton
* drone inspeciton -> orchestration
* orchestration -> human esclation / logging    
  
Below are example structures of how these payloads can be structured.
  
**MonitoringEvent**  
```
{
  "camera_id": "camera_2",
  "timestamp": "2026-09-17T14:30:00",
  "event_type": "suspected_smoke",
  "confidence": 0.67,
  "image_bbox": [812, 310, 895, 447],
  "search_region_id": "sector_b3"
}
```  
  
**InpsectionRequest**  
```
{
  "inspection_id": "inspection_0042",
  "classification": "campfire",
  "confidence": 0.94,
  "estimated_location": {
    "x": 724.1,
    "y": 398.7
  },
  "observations": 3,
  "decision": "log"
}
```  
  
**InspectionResult**  
```
{
  "inspection_id": "inspection_0042",
  "classification": "campfire",
  "confidence": 0.94,
  "estimated_location": {
    "x": 724.1,
    "y": 398.7
  },
  "observations": 3,
  "decision": "log"
}
```  
  
**MissionOutcome**  
```
{
  "mission_id": "inspection_0042",
  "decision": 3
}
```
