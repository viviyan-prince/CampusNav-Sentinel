# CampusNav Sentinel — Demo Script (3 Minutes)

## Pre-Demo Setup
```bash
cd campusnav-sentinel
pip install -r requirements.txt
python scripts/generate_test_video.py
```

---

## Demo Flow

### 0:00–0:20 — Introduction
> "CampusNav Sentinel is an agentic visual hazard analysis system for autonomous campus shuttles. It uses OpenCV 5 for vision processing and a deterministic state-machine agent that decides what to inspect next based on what it observes."

### 0:20–0:50 — Show CLI Analysis
Run the pipeline on the test video:
```bash
PYTHONPATH=. python app/cli.py data/sample/test_campus.mp4 -o data/output -v
```

Point out:
- OpenCV 5.0.0 version confirmed in the output
- Real-time processing metrics (FPS, inference time)
- Detection counts and hazard score
- Agent steps and state transitions in the timeline

### 0:50–1:30 — Show Web Dashboard
Start the server:
```bash
PYTHONPATH=. python -m uvicorn app.api.server:app --host 0.0.0.0 --port 8000
```

Open browser to `http://localhost:8000`:
1. Show the dashboard with OpenCV 5 badge
2. Upload the test video
3. Click "Analyze"
4. Show the annotated output video with bounding boxes and state overlay
5. Point out the metrics panel (FPS, detections, hazard score)
6. Show the event timeline (state transitions over time)
7. Show the agent trace (action → state → reason for each step)

### 1:30–2:10 — Explain the Agentic Loop
> "What makes this different from a static detector is the feedback loop."

Walk through a specific trace entry:
1. "Frame 30: ANALYZE_FRAME detects a person — state changes to CANDIDATE_DETECTED"
2. "Same frame, iteration 2: INSPECT_REGION checks if this person is in the shuttle's path ROI"
3. "Same frame, iteration 3: VERIFY_PERSISTENCE — only seen once, not confirmed yet"
4. "Frame 33: Same person detected for the 3rd time — now CONFIRMED_HAZARD"
5. "Frame 45: Person exits — state returns to CLEAR"

> "Each action depends on the result of the previous one. The agent inspects, verifies, and escalates based on accumulated visual evidence."

### 2:10–2:30 — Show Tests
```bash
PYTHONPATH=. python -m pytest tests/ -v
```
> "31 tests, all passing — covering perception, agent logic, and end-to-end pipeline."

### 2:30–2:50 — Failure Handling
> "If the frame is too dark or blurry with no detections, the agent enters DEGRADED mode and requests human review. It never assumes the path is clear when perception fails."

Show the test: `test_perception.py::TestFrameAnalyzer::test_brightness_detection`

### 2:50–3:00 — Closing
> "CampusNav Sentinel: a real agentic vision pipeline using OpenCV 5, with measurable results and a judge-inspectable decision trace. All simulated — no real vehicle control."

---

## Key Points to Emphasize for Judges

1. **OpenCV 5 is used substantively** — not just for I/O but for CLAHE, Canny, MOG2, ROI masking, morphology
2. **The agent loop is real** — visual evidence changes actions, not a fixed pipeline
3. **Every decision is traceable** — JSON report contains the full agent trace
4. **All results are measured** — no fabricated benchmarks
5. **Honest limitations** — synthetic data, no real-world accuracy claims
