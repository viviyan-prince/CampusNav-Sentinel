# CampusNav Sentinel — Judge Setup Guide

## Quick Start (Under 5 Minutes)

### Prerequisites
- Python 3.10+ (tested on 3.12)
- NVIDIA GPU with CUDA support (recommended; CPU works but slower)
- ~2 GB disk space (for YOLO model weights + test data)

### Step 1: Install Dependencies
```bash
cd campusnav-sentinel
pip install -r requirements.txt
```

This installs OpenCV 5.0.0, PyTorch, Ultralytics YOLOv8, and FastAPI. On first run, YOLOv8n weights (~6 MB) are downloaded automatically.

### Step 2: Verify OpenCV 5
```bash
python -c "import cv2; print(cv2.__version__)"
# Expected: 5.0.0
```

### Step 3: Generate Test Video
```bash
python scripts/generate_test_video.py
```
Creates `data/sample/test_campus.mp4` (120 frames, 8 seconds).

### Step 4: Run CLI Analysis
```bash
PYTHONPATH=. python app/cli.py data/sample/test_campus.mp4 -o data/output -v
```

**Expected output:**
- Processing metrics (FPS, inference time, detection counts)
- Event timeline with state transitions
- `data/output/annotated_output.mp4` — video with overlaid detections
- `data/output/report.json` — full analysis report with agent trace

### Step 5: Run Web Dashboard (Optional)
```bash
PYTHONPATH=. python -m uvicorn app.api.server:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in a browser:
1. Upload the test video (or any MP4/image)
2. Click "Analyze"
3. View annotated output, metrics, timeline, and agent trace

### Step 6: Run Tests
```bash
PYTHONPATH=. python -m pytest tests/ -v
```
Expected: 31 tests, all passing.

## What to Look For

### OpenCV 5 Usage
Open `app/perception/frame_analyzer.py` — every frame passes through CLAHE, Canny, ROI masking, and quality assessment using OpenCV 5 functions.

### Agentic Feedback Loop
Open `data/output/report.json` → `agent_trace.steps`:
- Each step shows the action taken, evidence observed, and state transition
- Notice how INSPECT_REGION and VERIFY_PERSISTENCE only trigger when prior evidence warrants them
- States change based on accumulated multi-frame tracking, not single-frame decisions

### Agent Trace Format
```json
{
  "step": 5,
  "action": "VERIFY_PERSISTENCE",
  "reason": "High-confidence hazard in ROI — verifying persistence",
  "state_before": "UNDER_INSPECTION",
  "state_after": "CONFIRMED_HAZARD",
  "evidence_summary": {"tracked": 2, "confirmed": 1, "dropped": 0}
}
```

## Troubleshooting

| Issue | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'app'` | Ensure `PYTHONPATH=.` is set |
| YOLO download fails | Check internet connectivity; weights are cached after first download |
| `CUDA out of memory` | Set `--device cpu` in CLI or `CN_DETECTOR_DEVICE=cpu` env var |
| Port 8000 in use | Change with `--port 8080` |

## Windows Users
On Windows without bash, use:
```cmd
set PYTHONPATH=.
python app\cli.py data\sample\test_campus.mp4 -o data\output -v
```
