# active-visual-inspection

This is an active visual inspection project with simulated drones. The goal is to create an active monitoring system that takes static camera output, uses that information to launch investigative drones, and then those drones actively engage with their environment before concluding their investigation.    
  
**Problem**  
Stationary cameras provide excellent monitoring abilities. However, their static nature naturally leads to some weaknesses. They cannot reorient themselves to the environment and thus are limited when ideal conditions are not present.  
  
**V1 Scenario**  
We are investigating a scenario in which static cameras are paired with active-inspection drones to improve monitoring effectiveness.  
  
**System Flow**  
The proposed system pairs 3 static cameras with a drone. The static cameras run standard CV models are monitor for smoke events. When a potential smoke event is detected, an automonous drone is dispatched to gather more information and ultimately decide on a course of action.  

**Evaluation**  
Our evaluation methods with consider 4 main layers: Monitoring, Dispatch/Search, Active Perception, and General Mission Success. 
  
This project is built on the basis of fire prevention, but is created in a way that the active perception framework can expand beyond that framework.