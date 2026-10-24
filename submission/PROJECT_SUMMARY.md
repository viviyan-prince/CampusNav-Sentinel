# CampusNav Sentinel — Project Summary

## Agentic Visual Hazard Analysis for Autonomous Campus Shuttles

**Developer:** Viviyan P, CSE Student, India
**Competition:** OpenCV AI Competition 2026, powered by AWS (Devpost)
**Category:** Agentic Vision

---

### Problem

Autonomous campus shuttles operating on shared pedestrian pathways need continuous visual hazard analysis. Unlike highway self-driving, campus environments feature unpredictable pedestrian movement, bicycles, and low-speed mixed traffic. A single detection pass is insufficient — the system must observe, inspect, verify, and decide, exactly as a human safety operator would.

### Solution

CampusNav Sentinel is a video intelligence system that processes campus shuttle footage through a multi-stage OpenCV 5 vision pipeline and a deterministic agentic feedback loop. The agent does not simply detect objects — it inspects regions of interest, tracks candidate hazards across frames, verifies persistence, and selects context-appropriate responses based on accumulated visual evidence.

### Key Technical Highlights

| Component | Detail |
|---|---|
| **Vision Engine** | OpenCV 5.0.0 — CLAHE enhancement, Canny edge detection, MOG2 background subtraction, ROI masking |
| **Object Detection** | YOLOv8n (COCO-pretrained) on NVIDIA RTX 5050 GPU |
| **Agent Architecture** | Deterministic state machine with 8 actions, 7 states, bounded iteration |
| **Feedback Loop** | Visual evidence from each action determines the next action — inspect, verify persistence, escalate, or continue |
| **Interface** | FastAPI web dashboard + CLI with annotated video output, JSON reports, event timeline, agent trace |
| **Language** | Python 3.12 |

### Measured Performance (Synthetic Test Video, 60 frames)

- **6.3 FPS** processing throughput
- **110.9 ms** average YOLO inference time
- **29 pedestrians** detected across 60 frames
- **115 agent steps** with state transitions between CLEAR, CANDIDATE_DETECTED, and CONFIRMED_HAZARD
- **Peak hazard score: 0.700**
- **31/31 tests passing** (unit + integration)
- **0 failed frames**

### Agentic Vision Demonstration

1. Frame analyzed → pedestrian candidate detected near shuttle path
2. Region inspected → candidate confirmed in ROI with high confidence
3. Next frames compared → candidate persists across 3+ frames
4. Hazard verified → state transitions to CONFIRMED_HAZARD
5. Hazard score exceeds threshold → simulated response issued
6. Evidence changes (pedestrian exits frame) → state returns to CLEAR

Every step is recorded in a judge-inspectable trace with the action taken, evidence observed, and state transition.

### What Makes This Different

This is not a detector with a chatbot. The agent loop is the core product. Each visual analysis output drives the next tool call. The decision trace proves that subsequent actions depend on prior observations — not a fixed pipeline.

All stop/slow actions are simulated outputs only. No real vehicle is controlled.
