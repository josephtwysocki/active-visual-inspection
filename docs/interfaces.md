## **Major Interfaces**  
  
This document describes the payloads passed between major subsytems:  
* monitoring -> orchestration
* orchestration -> drone inspeciton
* drone inspeciton -> orchestration
* orchestration -> human esclation / logging    
  
Below are example structures of how these payloads can be structured.
  
**MonitoringEvent**  
*"I saw somthing happen"*  
What the fixed camera noticed.
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
  
**InspectionRequest**  
*"Drone, go investigate this."*  
What orchestration asks the drone to investigate.
```
{
  "inspection_id": "inspection_0042",
  "source_event_id": "monitoring_event_019",
  "suspected_event": "smoke",
  "search_region_id": "sector_b3",
  "initial_confidence": 0.67,
  "source_camera_id": "camera_2",
  "priority": "normal"
}
```  
  
**InspectionResult**  
*"Here's what I found."*  
What the drone learned while investigating.
```
{
  "inspection_id": "inspection_0042",
  "classification": "campfire",
  "confidence": 0.94,
  "estimated_location": {
    "x": 724.1,
    "y": 398.7
  },
  "observations": 3
}
```  
  
**MissionOutcome**  
"*"Based on that result, here's what we did."*  
What orchestration decided to do.
```
{
  "inspection_id": "inspection_0042",
  "decision": "log",
  "status": "completed"
}
```
