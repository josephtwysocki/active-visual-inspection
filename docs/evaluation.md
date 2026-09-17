## **Layered Evaluation Approach**  
  
#### **General Evaluation Philosphy**
This is a complicated project with multiple moving parts. We will evaluate success across multiple levels to ensure that we are properly understanding the strengths and weaknesses of the program.  

#### **Layer 1: Monitoring**  
`Did the passive system recognize that sometihng warranted investigation?`  

The metrics used here will eventually include detection recall, false-positive rate, detection latency, and initial confidence.  
  
#### **Layer 2: Dispatch/Search**  
`Did the fixed-camera observation give the drone enough information to find the suspected event?`

The metrics used here will include reacquisition rate, time to reacquisition, distance traveled, and initial search-region error.

#### **Layer 3: Active Perception**  
`Did actively acquiring additional observations improve what the system knew?`

This layer is critically important to the purpose of the competition. The metrics we build out here will center around cmoparison of intitial vs post-inspection behavior. 

#### **Layer 4: Mission**  
`Did the decision made correctly match the ground truth?`  
Each ground truth event has a corresponding response. We want to know how often our system correctly assigned the response to the given situation. We can consider this `mission success rate`, which will be our primary objective, while also layering in other metrics, such as response time.  