# CampusNav Sentinel — Architecture

## System Overview

```mermaid
graph TD
    subgraph Input
        A[Video/Image File] --> B[cv2.VideoCapture]
    end

    subgraph "OpenCV 5 Frame Analysis"
        B --> C[Resize to 640px]
        C --> D[BGR → Grayscale]
        C --> E[BGR → LAB → CLAHE → BGR]
        D --> F[Canny Edge Detection]
        D --> G[Laplacian Blur Score]
        E --> H[ROI Mask via fillPoly + bitwise_and]
    end

    subgraph "Detection & Motion"
        H --> I[YOLOv8n Object Detection<br/>GPU / CUDA]
        D --> J[MOG2 Background Subtraction]
        D --> K[Frame Differencing via absdiff]
        J --> L[Morphological Cleanup]
        K --> L
        L --> M[Contour Extraction]
    end

    subgraph "Agent Controller"
        I --> N{Agent State Machine}
        M --> N
        F --> N
        G --> N

        N -->|ANALYZE_FRAME| O[Full Pipeline Pass]
        N -->|INSPECT_REGION| P[ROI Focus + Track]
        N -->|COMPARE_NEXT_FRAME| Q[Motion Comparison]
        N -->|VERIFY_PERSISTENCE| R[Multi-Frame Check]
        N -->|REQUEST_SIMULATED_STOP| S[Simulated Stop]
        N -->|REQUEST_HUMAN_REVIEW| T[Human Review]
        N -->|CONTINUE_MONITORING| U[Next Frame]
        N -->|REPORT_FAILURE| V[Degraded Mode]
    end

    subgraph Output
        N --> W[Annotated Video/Image]
        N --> X[JSON Report]
        N --> Y[Event Timeline]
        N --> Z[Agent Trace]
    end

    style N fill:#d63031,stroke:#fff,color:#fff
    style I fill:#0984e3,stroke:#fff,color:#fff
    style E fill:#00b894,stroke:#fff,color:#fff
```

## Agent Feedback Loop

```mermaid
stateDiagram-v2
    [*] --> CLEAR

    CLEAR --> CANDIDATE_DETECTED : Hazard detected by YOLO
    CLEAR --> DEGRADED : Frame analysis failed

    CANDIDATE_DETECTED --> UNDER_INSPECTION : High-confidence in ROI
    CANDIDATE_DETECTED --> CLEAR : Below ROI threshold

    UNDER_INSPECTION --> CONFIRMED_HAZARD : Persisted ≥3 frames
    UNDER_INSPECTION --> CLEAR : Not enough persistence

    CONFIRMED_HAZARD --> PERSISTENT_HAZARD : Score ≥ 0.9
    CONFIRMED_HAZARD --> CLEAR : Score decreases / candidate exits

    PERSISTENT_HAZARD --> CLEAR : Hazard resolved
    PERSISTENT_HAZARD --> PERSISTENT_HAZARD : Ongoing critical hazard

    DEGRADED --> CLEAR : Quality recovers
    UNKNOWN --> DEGRADED : Failure reported

    CLEAR --> UNKNOWN : Perception failure
```

## Data Flow Per Frame

```
Frame N
  │
  ├─ FrameAnalyzer
  │   ├─ Resize (640px)
  │   ├─ Grayscale conversion
  │   ├─ CLAHE in LAB color space
  │   ├─ Canny edges → edge_density
  │   ├─ Laplacian → blur_score
  │   ├─ Mean brightness → quality assessment
  │   └─ ROI mask application
  │
  ├─ ObjectDetector (YOLOv8n on GPU)
  │   ├─ Inference on enhanced frame
  │   └─ Filter: hazard classes, confidence ≥ 0.35
  │
  ├─ MotionAnalyzer
  │   ├─ MOG2 foreground mask
  │   ├─ Frame diff with Frame N-1
  │   ├─ Morphological cleanup
  │   └─ Contour → motion_regions
  │
  └─ AgentController (up to 5 iterations)
      │
      ├─ Iteration 1: ANALYZE_FRAME
      │   Evidence: quality, brightness, hazard_count, motion_score
      │   → Decides next action based on evidence
      │
      ├─ Iteration 2: INSPECT_REGION (if hazards found)
      │   Evidence: candidates_in_roi, confidence levels
      │   → Updates tracking state
      │
      ├─ Iteration 3: VERIFY_PERSISTENCE (if high-confidence)
      │   Evidence: seen_count per candidate, frame gaps
      │   → Confirms or drops candidates
      │
      └─ Terminal: CONTINUE_MONITORING / REQUEST_* / REPORT_FAILURE
          → Writes decision to trace
          → Annotates frame with state overlay
          → Emits timeline event if state changed
```

## Module Dependencies

```
app/
├── config.py              ← Environment configuration
├── pipeline.py            ← Orchestrates full video processing
├── cli.py                 ← Command-line entry point
├── perception/
│   ├── frame_analyzer.py  ← OpenCV 5 frame processing (no external deps)
│   ├── motion_analyzer.py ← Background subtraction + frame diff
│   └── detector.py        ← YOLOv8n wrapper (depends on ultralytics, torch)
├── agent/
│   └── controller.py      ← State machine (depends on perception/)
├── api/
│   └── server.py          ← FastAPI web interface (depends on pipeline)
├── templates/
│   └── index.html         ← Dashboard UI
└── static/                ← (reserved for assets)
```

## AWS Architecture (Deployment-Ready)

```mermaid
graph LR
    User[User Browser] --> ALB[Application Load Balancer]
    ALB --> ECS[ECS Fargate<br/>FastAPI + YOLO]
    ECS --> S3[S3 Bucket<br/>Uploads & Outputs]
    ECS --> CW[CloudWatch<br/>Logs & Metrics]
```

**Status:** Infrastructure files prepared (Dockerfile, CloudFormation). Not deployed — AWS CLI not available on development machine. The application runs fully locally without AWS.
