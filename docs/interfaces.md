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
  
**InpsectionResult**  
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