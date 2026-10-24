# CampusNav Sentinel — AI-Powered Visual Hazard Analysis

**🏆 Nebius × NVIDIA Global AI Hackathon 2026 Submission**

CampusNav Sentinel is a camera-only visual intelligence system that combines computer vision (OpenCV 5.0 + YOLOv8) with **Nebius AI Cloud** to provide real-time hazard detection and contextual risk assessment. The system leverages **NVIDIA-powered language models** (meta-llama/Llama-3.3-70B-Instruct) through Nebius to transform raw object detections into actionable safety insights for autonomous shuttle operations.

**🌟 Key Innovation**: Hybrid intelligence combining fast CV detection with deep language model reasoning for contextual safety analysis.

## Features

- **OpenCV 5.0.0** — Frame decoding, CLAHE enhancement, color-space conversion, Canny edge detection, ROI masking, morphological operations, background subtraction
- **YOLOv8n Object Detection** — GPU-accelerated pedestrian, vehicle, and obstacle detection via ultralytics
- **Nebius AI Cloud Integration** ⭐ — Real-time scene analysis using NVIDIA models (meta-llama/Llama-3.3-70B-Instruct) for contextual safety assessment and recommendations
- **Agentic Feedback Loop** — Deterministic state machine with 8 explicit actions and 7 hazard states
- **Evidence-Driven Decisions** — Detection outputs determine the next tool call; subsequent frames can confirm, escalate, or clear a hazard
- **AI-Powered Risk Assessment** ⭐ — Nebius analyzes detected objects and scene context to provide risk levels and actionable recommendations
- **Full Decision Trace** — Every agent step records action, reason, evidence, state before/after, and timestamp
- **Annotated Output** — Bounding boxes, hazard state overlay, Nebius AI analysis overlay, ROI line, motion regions, and HUD on every frame
- **Structured Reports** — JSON report with metrics, event timeline, agent trace, frame summary, and AI analyses
- **FastAPI Web Interface** — Upload video/image, view annotated output, inspect metrics and agent trace
- **Failure Handling** — Corrupt frames, missing models, low confidence, degraded perception, and empty scenes handled gracefully

## Architecture

```
Input Video/Image
       |
  [Frame Decoder] ── OpenCV 5 VideoCapture
       |
  [Frame Analyzer] ── Resize, CLAHE, Color-space, Canny, ROI Mask
       |
  [Object Detector] ── YOLOv8n (GPU/CUDA)
       |
  [Motion Analyzer] ── Background subtraction + frame differencing
       |
  [Agent Controller] ── Deterministic state machine
       |                  ├─ ANALYZE_FRAME
       |                  ├─ INSPECT_REGION
       |                  ├─ VERIFY_PERSISTENCE
       |                  ├─ REQUEST_SIMULATED_STOP
       |                  └─ CONTINUE_MONITORING
       |
  [Pipeline] ── Annotated video + JSON report + timeline
       |
  [FastAPI Server] ── Web UI + REST API
```

## 🚀 Quick Start for Hackathon Judges

**Prerequisites**: Python 3.10+, pip, NVIDIA GPU with CUDA (optional)

**30-Second Demo:**
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Nebius API key
export NEBIUS_API_KEY=your_nebius_api_key_here

# 3. Run verification
PYTHONPATH=. python verify_nebius.py

# 4. Process sample video
PYTHONPATH=. python app/cli.py data/sample/test_campus.mp4 -o data/output --max-frames 30

# 5. View results
# - Video: data/output/annotated_output.mp4
# - Report: data/output/report.json
```

**Without Nebius API key**: System works in fallback mode (OpenCV + YOLO detection only). Set `NEBIUS_API_KEY` to enable AI scene analysis.

## Full Installation Guide

### Prerequisites

- Python 3.10+
- NVIDIA GPU with CUDA (optional, falls back to CPU)
- pip

### Install

```bash
cd campusnav-sentinel
pip install -r requirements.txt
```

Verify OpenCV 5:

```bash
python -c "import cv2; print(cv2.__version__)"
# Expected: 5.0.0
```

### Configure Nebius AI (Optional but Recommended)

Set your Nebius API key to enable AI-powered scene analysis:

```bash
export NEBIUS_API_KEY=your_nebius_api_key_here
```

Or create a `.env` file:

```bash
cp .env.example .env
# Edit .env and add your NEBIUS_API_KEY
```

**Without a Nebius API key**, the system works normally with OpenCV + YOLO detection only. See [NEBIUS_INTEGRATION.md](NEBIUS_INTEGRATION.md) for details.

### Generate Test Video

```bash
python scripts/generate_test_video.py --output data/sample/test_campus.mp4 --duration 10
```

### Run CLI Analysis

```bash
PYTHONPATH=. python app/cli.py data/sample/test_campus.mp4 -o data/output -v
```

Output: `data/output/annotated_output.mp4` and `data/output/report.json`

### Run Web API

```bash
PYTHONPATH=. uvicorn app.api.server:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in a browser. Upload a video or image and click Analyze.

### Run Tests

```bash
PYTHONPATH=. python -m pytest tests/ -v
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Service health check with OpenCV version |
| `/analyze` | POST | Upload video/image for analysis (multipart form) |
| `/results/{job_id}` | GET | Retrieve analysis results by job ID |
| `/results/{job_id}/output` | GET | Download annotated output file |
| `/metrics` | GET | Aggregate job metrics |

## Configuration

All settings can be overridden via environment variables:

| Variable | Default | Description |
|---|---|---|
| `CN_TARGET_WIDTH` | 640 | Frame resize width |
| `CN_ROI_FRACTION` | 0.6 | Bottom fraction of frame used as ROI |
| `CN_DETECTOR_MODEL` | yolov8n.pt | YOLO model file |
| `CN_DETECTOR_CONFIDENCE` | 0.35 | Detection confidence threshold |
| `CN_DETECTOR_DEVICE` | auto | `cuda` or `cpu` |
| `CN_MOTION_THRESHOLD` | 0.02 | Motion score threshold |
| `CN_FRAME_SKIP` | 1 | Process every Nth frame |
| `CN_MAX_FRAMES` | 0 | Limit frames (0 = all) |
| `CN_API_HOST` | 0.0.0.0 | API bind host |
| `CN_API_PORT` | 8000 | API bind port |
| `CN_AWS_ENABLED` | false | Enable AWS integration |
| `CN_S3_BUCKET` | — | S3 bucket for artifacts |
| `CN_LOG_LEVEL` | INFO | Logging level |
| `NEBIUS_API_KEY` | — | Nebius AI Cloud API key |
| `NEBIUS_MODEL` | meta-llama/Llama-3.3-70B-Instruct | NVIDIA model for scene analysis |
| `NEBIUS_ENABLED` | true | Enable/disable Nebius AI integration |
| `NEBIUS_INTERVAL` | 5 | Analyze every Nth processed frame |

## Verified Environment

- **OpenCV**: 5.0.0
- **Python**: 3.12.10
- **PyTorch**: 2.10.0+cu130
- **GPU**: NVIDIA GeForce RTX 5050 Laptop GPU (8 GB, CUDA 13.1)
- **Detector**: YOLOv8n (110.9 ms avg inference on GPU)
- **Tests**: 31/31 passing

## Project Structure

```
campusnav-sentinel/
├── app/
│   ├── perception/       # OpenCV 5 frame analysis, motion, detection
│   ├── agent/            # Deterministic state-machine controller
│   ├── api/              # FastAPI server
│   ├── templates/        # Web UI
│   ├── static/
│   ├── config.py
│   ├── pipeline.py       # End-to-end video processing
│   └── cli.py            # Command-line interface
├── tests/                # Unit and integration tests
├── scripts/              # Test video generation
├── data/                 # Sample, input, and output data
├── deploy/               # Docker and AWS deployment
├── submission/           # Competition submission package
├── docs/                 # Additional documentation
├── requirements.txt
├── STATUS.md
└── README.md
```

## Safety Disclaimer

This is a research and demonstration prototype. All stop requests and vehicle actions are **simulated outputs only**. This system is not connected to and must never be connected to physical steering, braking, or vehicle control systems. No unverified output may control a real vehicle.

## License

MIT
