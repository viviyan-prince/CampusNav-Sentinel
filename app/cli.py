"""Command-line interface for CampusNav Sentinel."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import cv2


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CampusNav Sentinel — Agentic Visual Hazard Analysis",
    )
    parser.add_argument("input", help="Path to video or image file")
    parser.add_argument("-o", "--output", default="data/output", help="Output directory")
    parser.add_argument("--max-frames", type=int, default=0, help="Max frames (0=all)")
    parser.add_argument("--frame-skip", type=int, default=1, help="Process every Nth frame")
    parser.add_argument("--confidence", type=float, default=0.35, help="Detection confidence")
    parser.add_argument("--device", default=None, help="cuda or cpu")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("campusnav")

    logger.info("CampusNav Sentinel v1.0.0")
    logger.info("OpenCV %s", cv2.__version__)

    from app.config import Config
    from app.pipeline import Pipeline

    config = Config.from_env()
    config.max_frames = args.max_frames
    config.frame_skip = args.frame_skip
    config.detector_confidence = args.confidence
    config.detector_device = args.device

    pipeline = Pipeline(config)

    try:
        report = pipeline.run(args.input, args.output)
    except Exception as e:
        logger.error("Pipeline failed: %s", e, exc_info=True)
        return 1

    m = report["metrics"]
    print("\n" + "=" * 60)
    print("  CAMPUSNAV SENTINEL — ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"  OpenCV Version:    {m['opencv_version']}")
    print(f"  Frames Processed:  {m['processed_frames']}/{m['total_frames']}")
    print(f"  Failed Frames:     {m['failed_frames']}")
    print(f"  Processing Time:   {m['total_time_s']:.1f}s")
    print(f"  Average FPS:       {m['avg_fps']:.1f}")
    print(f"  Avg Inference:     {m['avg_inference_ms']:.1f}ms")
    print(f"  Total Detections:  {m['total_detections']}")
    print(f"  Hazards Detected:  {m['total_hazards']}")
    print(f"  Persons Detected:  {m['total_persons']}")
    print(f"  Vehicles Detected: {m['total_vehicles']}")
    print(f"  Peak Hazard Score: {m['peak_hazard_score']:.3f}")
    print(f"  Agent Steps:       {m['agent_steps']}")
    print(f"  Simulated Stops:   {m['simulated_stops']}")
    print(f"  Human Reviews:     {m['human_reviews']}")
    print(f"  Nebius AI Calls:   {m['nebius_calls']}")
    print(f"  Nebius Successes:  {m['nebius_successes']}")
    if m.get('nebius_model'):
        print(f"  Nebius Model:      {m['nebius_model']}")
    print(f"  Output:            {report['output']}")
    print("=" * 60)

    if report.get("timeline"):
        print("\n  EVENT TIMELINE (last 10):")
        for ev in report["timeline"][-10:]:
            print(f"    [{ev['frame']:>5}] {ev['time_ms']:>8.0f}ms  {ev['type']:<15} {ev['description'][:60]}")

    if report.get("nebius_analyses"):
        print("\n  NEBIUS AI ANALYSES:")
        for na in report["nebius_analyses"]:
            print(f"    [Frame {na['frame']:>3}] Scene: {na['scene'][:50]}")
            print(f"                Risk: {na['risk']}")
            print(f"                Action: {na['action'][:55]}")
            print()

    print(f"\n  Full report: {Path(args.output) / 'report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
