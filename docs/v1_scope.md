## **v1 Scope**

#### **V1 Mission**
The mission of this phase of the project is to monitor a simulated 150-acre property for possible fires used three fixed RGB cameras. When suspeced smoke is detected, the system will dispatch a drone to investigate. The drone actively gathers additional visual evidence until it can classify the event and either terminate the investigation, log a permitted campfire, or escalate a potentially dangerous fire to a human.

#### **General Info**

**Scenario Outcomes**
* No Threat
  * Action: Terminate investigation
* Campfire
  * Action: Log event (do not escalate)
* Dangerous Fire
  * Action: Log event and escalate to human  

#### **Things to Avoid in V1**

V1 **does not** include:  
- physical drones
- physical cameras
- multiple drones
- drone-to-drone coordination
- autonomous firefighting
- thermal cameras
- multispectral sensors
- PTZ cameras
- crop inspection
- real-world deployment
- sophisticated battery optimization
- ROS unless later proven necessary