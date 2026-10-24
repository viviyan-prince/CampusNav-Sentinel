# CampusNav Sentinel — Known Limitations

## Data Limitations

1. **Synthetic test data only.** The included test video contains drawn geometric shapes (rectangles representing pedestrians and vehicles), not real campus footage. YOLO detects these shapes as persons, which demonstrates pipeline integration but does not represent detection accuracy on real-world inputs.

2. **No ground-truth annotations.** Without labeled real footage, precision, recall, and mAP cannot be computed. The reported detection counts are raw YOLO outputs, not validated against ground truth.

3. **Single test scenario.** Only one synthetic video pattern was tested (pedestrian crossing, then exiting). Diverse scenarios (crowds, occlusion, varied lighting, rain) were not evaluated.

## Detection Limitations

4. **No calibrated depth estimation.** The system uses a monocular camera. It cannot measure true distance to detected objects. It never claims a pedestrian is "X meters away" — only that a detection exists at a pixel location within or outside the ROI.

5. **COCO-pretrained weights.** YOLOv8n is trained on COCO, which covers common objects but may miss campus-specific items (e.g., electric scooters, campus golf carts, construction barriers). No fine-tuning was performed.

6. **Below real-time throughput.** At 6.3 FPS on an RTX 5050, the pipeline is below the 30 FPS typically required for real-time vehicle operation. This is acceptable for offline analysis and demonstration but not for deployment.

## Agent Limitations

7. **Deterministic rules only.** The agent uses fixed thresholds (persistence = 3 frames, hazard score increments of 0.1). These were chosen as reasonable defaults, not learned from data. Different environments may require different parameters.

8. **No temporal smoothing.** The hazard score can oscillate between frames (e.g., CONFIRMED_HAZARD → CLEAR → CONFIRMED_HAZARD) when a detection flickers. A Kalman filter or exponential moving average would stabilize this.

9. **Tracking by grid cell, not by identity.** Candidates are tracked by quantized grid position (center_x // 50, center_y // 50), not by appearance or re-identification. Two different people in the same grid cell would be merged.

## Infrastructure Limitations

10. **AWS not deployed.** AWS CLI was not available on the development machine. Deployment infrastructure (Dockerfile, CloudFormation) is prepared but not verified against a live AWS account.

11. **No Docker testing.** Docker was not installed on the development machine. The Dockerfile is written based on standard patterns but has not been built or run.

12. **No CI/CD pipeline.** Tests run locally only. No GitHub Actions or equivalent is configured.

## Safety Disclaimer

13. **Research prototype only.** All stop/slow/review actions are simulated outputs written to a log. No physical vehicle, steering, braking, or communication system is connected. This system must not be used to control a real vehicle without extensive additional validation, certification, and safety engineering.

14. **No fail-safe guarantee.** While the agent enters DEGRADED mode on perception failure and never interprets a failed detector as "path clear," this is a software heuristic, not a certified safety mechanism.

## Honest Assessment

This project demonstrates a working agentic vision pipeline with real OpenCV 5 processing and measurable results. It does not claim production readiness, real-world accuracy, or safety certification. The limitations above are inherent to the scope of a competition prototype built by a single developer in limited time.
