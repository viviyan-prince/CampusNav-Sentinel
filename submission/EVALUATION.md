# CampusNav Sentinel — Evaluation Results

## Test Environment

| Component | Detail |
|---|---|
| OS | Windows 11 (Build 26200) |
| CPU | AMD (via MINGW64) |
| GPU | NVIDIA GeForce RTX 5050 Laptop GPU, 8 GB VRAM |
| CUDA | 13.1 |
| Python | 3.12.10 |
| OpenCV | 5.0.0 |
| PyTorch | 2.10.0+cu130 |
| YOLO | YOLOv8n (Ultralytics) |

## Pipeline Performance (Synthetic Test Video)

**Input:** 120 frames, 15 FPS, 640×480, synthetic campus shuttle view
**Processed:** 60 frames (--max-frames 60)

| Metric | Value |
|---|---|
| Frames processed | 60 / 120 |
| Failed frames | 0 |
| Total processing time | 9.5 s |
| Average FPS | 6.3 |
| Average YOLO inference | 110.9 ms |
| Total detections | 29 |
| Hazards detected | 29 |
| Persons detected | 29 |
| Vehicles detected | 0 |
| Peak hazard score | 0.700 |
| Agent steps | 115 |
| Timeline events | 42 |
| Simulated stops | 0 |
| Human reviews | 0 |

## Agent Behavior Analysis

### States Visited
- **CLEAR** — Majority of frames (empty scenes and post-hazard)
- **CONFIRMED_HAZARD** — When pedestrian persisted across ≥3 frames

### State Transitions
42 timeline events recorded, including:
- State changes between CLEAR and CONFIRMED_HAZARD
- Detection events with person counts
- The agent correctly returned to CLEAR when the pedestrian exited the frame

### Feedback Loop Evidence
The agent trace contains 115 steps across 60 frames, averaging ~1.9 agent iterations per frame. This exceeds the minimum 1 (ANALYZE_FRAME only), demonstrating that the agent performs additional inspection (INSPECT_REGION, VERIFY_PERSISTENCE) when visual evidence warrants it.

## Test Suite Results

```
31 passed, 0 failed, 14 warnings (matplotlib deprecation)
Test duration: 14.28 seconds
```

### Test Breakdown

| Test File | Tests | Status |
|---|---|---|
| test_perception.py | 13 | All passing |
| test_agent.py | 10 | All passing |
| test_pipeline.py | 8 | All passing |

### Test Coverage

- **FrameAnalyzer:** Normal frames, None input, empty frames, dark frames, bright frames, resize, edge detection, ROI application, serialization, OpenCV 5 version check
- **MotionAnalyzer:** Identical frames (no motion), changed frames (motion detected), reset, serialization
- **AgentController:** Initial state, frame processing, clear scenes, trace recording, multi-frame traces, reset, bounded iterations, all actions defined, all states defined
- **Pipeline:** Video processing, image processing, report structure, invalid input, unsupported format, JSON serialization, agent trace, metrics completeness

## Error Handling Tests

| Scenario | Expected | Result |
|---|---|---|
| None frame input | Returns None | Pass |
| Empty frame input | Returns None | Pass |
| Missing video file | FileNotFoundError | Pass |
| Unsupported format | ValueError | Pass |
| Invalid video codec | RuntimeError | Pass |

## Limitations of This Evaluation

1. **Synthetic data only** — The test video contains drawn geometric shapes, not real pedestrians. YOLO detects these as persons (demonstrates pipeline integration), but this does not represent real-world detection accuracy.
2. **No ground-truth labels** — Without annotated real footage, precision and recall cannot be computed.
3. **Single scenario** — Only one test video with one pedestrian pattern was evaluated.
4. **Vehicle detection** — The synthetic vehicle was not detected by YOLO (drawn too simply), resulting in 0 vehicle detections.
5. **No adverse conditions** — Limited testing of rain, fog, night, or heavy occlusion scenarios.

## Reproducibility

To reproduce these results:

```bash
cd campusnav-sentinel
pip install -r requirements.txt
python scripts/generate_test_video.py --output data/sample/test_campus.mp4 --duration 8
PYTHONPATH=. python app/cli.py data/sample/test_campus.mp4 -o data/output --max-frames 60 -v
PYTHONPATH=. python -m pytest tests/ -v
```
