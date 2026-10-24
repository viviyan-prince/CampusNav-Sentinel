# CampusNav Sentinel — Technical Report

## Agentic Visual Hazard Analysis for Autonomous Campus Shuttles

**Author:** Viviyan P
**Date:** October 2026
**OpenCV Version:** 5.0.0
**Competition:** OpenCV AI Competition 2026 (Devpost), powered by AWS

---

## 1. Problem and Motivation

Autonomous campus shuttles operate in mixed-traffic environments shared with pedestrians, cyclists, and other vehicles. Unlike highway autonomous driving, campus scenarios involve:

- Unpredictable pedestrian crossing patterns
- Low-speed maneuvers with frequent stops
- Narrow pathways with limited visibility
- Dynamic environments (class changes, events, weather)

A single-pass object detector is insufficient for safety-critical operation. The system must observe a scene, focus attention on regions of concern, verify whether a detected candidate persists over time, and select an appropriate response based on accumulated evidence — mirroring how a human safety operator reasons about visual data.

CampusNav Sentinel addresses this by combining an OpenCV 5 image processing pipeline with a deterministic agentic feedback loop that decides what to inspect next based on what it has already observed.

## 2. Why OpenCV 5

OpenCV 5.0.0 is the foundation of the entire vision pipeline. The competition requires meaningful use of OpenCV 5 for image and video analysis. CampusNav Sentinel uses the following OpenCV functions substantively:

### Frame Decoding and I/O
- **`cv2.VideoCapture`** — Reads input video frame-by-frame with timestamp extraction
- **`cv2.VideoWriter`** — Produces annotated output video with overlaid detections and state indicators
- **`cv2.imread` / `cv2.imwrite`** — Single-image input/output for static analysis mode

### Color Space and Enhancement
- **`cv2.cvtColor`** — Converts BGR → Grayscale for edge/motion analysis and BGR → LAB for perceptual enhancement
- **`cv2.createCLAHE`** — Contrast Limited Adaptive Histogram Equalization applied in LAB color space to improve detection under poor lighting. CLAHE parameters (clipLimit=2.0, tileGridSize=8×8) are tuned for outdoor campus scenes

### Edge Detection
- **`cv2.Canny`** — Edge detection (thresholds 50/150) computes edge density as a scene complexity metric. Edge density feeds into the agent's quality assessment

### Region of Interest
- **`cv2.fillPoly`** — Creates a trapezoidal ROI mask representing the shuttle's forward path
- **`cv2.bitwise_and`** — Applies the ROI mask to restrict hazard analysis to the relevant driving corridor

### Motion Analysis
- **`cv2.createBackgroundSubtractorMOG2`** — Gaussian mixture-based background subtraction for motion detection (history=100, varThreshold=40, shadow detection enabled)
- **`cv2.absdiff`** — Frame differencing between consecutive frames for complementary motion signal
- **`cv2.morphologyEx`** — Morphological open/close operations to clean motion masks (removes noise, fills gaps)
- **`cv2.findContours`** — Extracts motion region contours for bounding box computation
- **`cv2.getStructuringElement`** — Creates elliptical kernel for morphological operations
- **`cv2.threshold`** — Binary thresholding on motion masks and frame differences

### Annotation and Visualization
- **`cv2.rectangle`** — Draws bounding boxes (color-coded: red for persons, orange for hazards, green for non-hazards)
- **`cv2.putText`** — Renders detection labels, confidence scores, state indicators, and hazard scores
- **`cv2.circle`** — Marks detection centers
- **`cv2.line`** — Draws ROI boundary indicator
- **`cv2.resize`** — Normalizes input frames to target width (640px) for consistent processing

### Quality Assessment
- **`cv2.Laplacian`** — Variance of Laplacian measures image blur (threshold: 100.0)
- **`cv2.contourArea`** / **`cv2.boundingRect`** — Computes contour areas and bounding boxes for motion regions

All OpenCV operations run on the CPU. The GPU (RTX 5050) is reserved for YOLO inference through PyTorch/CUDA.

## 3. Object Detection Model

**Model:** YOLOv8n (nano variant) from Ultralytics
**Weights:** Pretrained on COCO (80 classes)
**Inference:** PyTorch 2.10.0 + CUDA 13.1 on NVIDIA RTX 5050 Laptop GPU (8 GB VRAM)
**Confidence threshold:** 0.35

### Hazard Classes
The detector classifies 80 COCO categories but only a subset are treated as campus hazards:
- **Persons** (class 0) — primary hazard
- **Vehicles** — bicycle, car, motorcycle, bus, truck
- **Infrastructure** — traffic light, stop sign, bench
- **Animals** — cat, dog

Non-hazard detections are tracked but do not trigger agent escalation.

### Why YOLOv8n
- Fast inference (~111 ms/frame) enables near-real-time processing
- Pretrained COCO weights cover all relevant campus classes
- No training required — avoids overfitting on limited campus data
- GPU-accelerated via PyTorch CUDA backend

## 4. Agent Architecture

The agent is a deterministic state machine with explicit actions and states. It is not an LLM-based agent — all decisions follow configurable, auditable rules driven by visual evidence.

### Actions (8)

| Action | Description |
|---|---|
| `ANALYZE_FRAME` | Full-frame analysis: CLAHE enhancement, edge detection, object detection, motion analysis |
| `INSPECT_REGION` | Focus on detected hazard candidates within the ROI; update tracking data |
| `COMPARE_NEXT_FRAME` | Flag motion for comparison on the subsequent frame |
| `VERIFY_PERSISTENCE` | Check whether tracked candidates have persisted across enough frames to confirm |
| `REQUEST_SIMULATED_STOP` | Issue a simulated emergency stop (hazard score ≥ 0.9) |
| `REQUEST_HUMAN_REVIEW` | Request simulated human operator review (high score or degraded perception) |
| `CONTINUE_MONITORING` | No escalation needed; continue to next frame |
| `REPORT_FAILURE` | Perception system failure; enter degraded mode |

### States (7)

| State | Meaning |
|---|---|
| `CLEAR` | No hazards detected; safe to proceed |
| `CANDIDATE_DETECTED` | Object detector found a potential hazard; needs inspection |
| `UNDER_INSPECTION` | High-confidence candidate found in ROI; verifying persistence |
| `CONFIRMED_HAZARD` | Candidate persisted across ≥3 frames; hazard confirmed |
| `PERSISTENT_HAZARD` | Critical hazard score (≥0.9); simulated stop issued |
| `DEGRADED` | Perception failed or quality too poor for reliable analysis |
| `UNKNOWN` | System state indeterminate; requesting human review |

### Decision Flow

For each frame, the agent executes up to 5 iterations (bounded to prevent infinite loops):

1. **ANALYZE_FRAME** — Run the full OpenCV pipeline and YOLO detection
2. If hazards detected → **INSPECT_REGION** — Check if candidates are within the shuttle path ROI
3. If high-confidence in ROI → **VERIFY_PERSISTENCE** — Check tracking history across frames
4. Based on persistence and hazard score → choose **REQUEST_SIMULATED_STOP**, **REQUEST_HUMAN_REVIEW**, or **CONTINUE_MONITORING**

If frame analysis fails or quality is poor with no detections, the agent transitions to **REPORT_FAILURE** → **DEGRADED** state and requests human review. The system never interprets a failed detector as proof that the path is clear.

### Hazard Score Calculation

The hazard score is a transparent, configurable value:
- Starts at 0.0 (CLEAR)
- Increases by 0.1 per confirmed hazard candidate (base 0.5 for first confirmation)
- Decreases by 0.1 per clear frame
- Capped at [0.0, 1.0]

Thresholds:
- ≥ 0.7: High — request human review
- ≥ 0.9: Critical — request simulated stop

## 5. Agentic Feedback Loop

The core competition requirement is that visual analysis outputs determine subsequent actions. Here is a concrete trace:

**Frame 30:** ANALYZE_FRAME detects 1 person (confidence 0.72) in frame
→ Evidence: `{hazard_count: 1, person_count: 1, motion_score: 0.031}`
→ State: CLEAR → CANDIDATE_DETECTED
→ Next action: INSPECT_REGION

**Frame 30 (iteration 2):** INSPECT_REGION checks if detection is within ROI
→ Evidence: `{candidates_tracked: 1, in_roi: 1}`
→ Result: `{high_confidence_hazards: 1}`
→ State: CANDIDATE_DETECTED → UNDER_INSPECTION
→ Next action: VERIFY_PERSISTENCE

**Frame 30 (iteration 3):** VERIFY_PERSISTENCE checks tracking history
→ Evidence: `{tracked: 1, confirmed: 0, dropped: 0}` (only seen 1 frame so far)
→ State: UNDER_INSPECTION → CLEAR (not enough persistence yet)
→ Next action: CONTINUE_MONITORING

**Frame 33:** Same person detected again (3rd consecutive frame)
→ VERIFY_PERSISTENCE: `{confirmed: 1}` — persistence threshold met
→ State: CLEAR → CONFIRMED_HAZARD
→ Hazard score: 0.60
→ Next action: CONTINUE_MONITORING (below critical threshold)

**Frame 40:** Person exits frame
→ ANALYZE_FRAME: `{hazard_count: 0, motion_score: 0.01}`
→ State: CONFIRMED_HAZARD → CLEAR
→ Hazard score decreases to 0.50

This trace demonstrates that:
- Visual evidence (detection count, confidence, ROI position) determines the next action
- Persistence verification uses multi-frame tracking, not single-frame decisions
- State transitions are driven by observed evidence changes
- The agent's behavior changes when visual inputs change

## 6. AWS Integration

### Status: Deployment-Ready (Not Deployed)

AWS CLI was not available on the development machine. Deployment infrastructure has been prepared:

- **Dockerfile** — Multi-stage build for the FastAPI application
- **docker-compose.yml** — Local development orchestration
- **CloudFormation template** — ECS Fargate deployment with ALB, S3, CloudWatch
- **S3 integration code** — Optional artifact upload behind `CN_AWS_ENABLED=true`

### Planned Architecture
1. **ECS Fargate** — Runs the containerized FastAPI application (GPU instance for YOLO inference)
2. **Application Load Balancer** — HTTPS endpoint for the web dashboard
3. **S3** — Stores uploaded videos and analysis outputs
4. **CloudWatch** — Application logs and operational metrics

The application works fully without AWS. AWS integration is isolated behind the `CN_AWS_ENABLED` environment variable.

## 7. Evaluation Methodology

### Test Environment
- **Hardware:** NVIDIA RTX 5050 Laptop GPU (8 GB VRAM), Windows 11
- **Software:** Python 3.12.10, OpenCV 5.0.0, PyTorch 2.10.0+cu130, Ultralytics YOLOv8n

### Test Data
A synthetic test video (120 frames, 15 FPS, 640×480) simulating campus shuttle view with:
- Empty road scenes (frames 0–23)
- Pedestrian entering and crossing (frames 24–83)
- Second pedestrian appearing (frames 60–83)
- Pedestrians exiting (frames 84–119)
- Simulated vehicle passing (frames 60–99)
- Noise injection and lighting changes

### Measured Results (60 frames processed)

| Metric | Value |
|---|---|
| Frames processed | 60 / 120 |
| Failed frames | 0 |
| Processing time | 9.5 s |
| Average FPS | 6.3 |
| Average inference | 110.9 ms |
| Total detections | 29 |
| Persons detected | 29 |
| Vehicles detected | 0 |
| Peak hazard score | 0.700 |
| Agent steps | 115 |
| Simulated stops | 0 |
| Human reviews | 0 |
| Timeline events | 42 |
| Unique states visited | CLEAR, CONFIRMED_HAZARD |

### Test Suite
- **31 tests**, all passing
- Unit tests: FrameAnalyzer, MotionAnalyzer, AgentController
- Integration tests: full pipeline on video and image inputs
- Error handling: invalid input, corrupt files, unsupported formats

### Limitations of Evaluation
- Synthetic test video — not real campus footage
- YOLO detects drawn rectangles as persons (demonstrates pipeline, not detection accuracy on real pedestrians)
- No ground-truth annotation for precision/recall metrics
- Single test video — broader evaluation would require diverse scenarios

## 8. Limitations and Future Work

### Current Limitations
1. Synthetic test data only — no real campus footage used
2. No calibrated depth estimation — monocular camera cannot measure true distance
3. Hazard score uses simple additive rules, not learned weights
4. No multi-camera fusion or LiDAR integration
5. Agent is deterministic — no learned policy optimization
6. Processing at 6.3 FPS — below real-time (30 FPS) requirements for deployment
7. AWS deployment prepared but not verified live
8. No night/rain/fog testing

### Future Work
- Real campus footage collection with IRB approval
- Ground-truth annotation for precision/recall evaluation
- MobileNet or EfficientDet for faster inference
- Temporal smoothing for hazard score (Kalman filter)
- Multi-camera stitching for full 360° coverage
- ROS 2 integration for real shuttle communication
- Reinforcement learning for adaptive agent behavior
- Edge deployment on NVIDIA Jetson platform
