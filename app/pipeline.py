"""End-to-end video analysis pipeline."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from app.agent.controller import AgentController, AgentDecision, HazardState
from app.config import Config
from app.nebius_client import NebiusClient, NebiusAnalysis
from app.perception.detector import DetectionResult
from app.perception.frame_analyzer import FrameAnalyzer, FrameResult

logger = logging.getLogger(__name__)


@dataclass
class PipelineMetrics:
    total_frames: int = 0
    processed_frames: int = 0
    failed_frames: int = 0
    total_time_s: float = 0.0
    avg_fps: float = 0.0
    avg_inference_ms: float = 0.0
    total_detections: int = 0
    total_hazards: int = 0
    total_persons: int = 0
    total_vehicles: int = 0
    agent_steps: int = 0
    simulated_stops: int = 0
    human_reviews: int = 0
    peak_hazard_score: float = 0.0
    opencv_version: str = ""
    nebius_calls: int = 0
    nebius_successes: int = 0
    nebius_model: str = ""

    def to_dict(self) -> dict:
        return {k: round(v, 3) if isinstance(v, float) else v for k, v in self.__dict__.items()}


@dataclass
class TimelineEvent:
    frame_index: int
    timestamp_ms: float
    event_type: str
    description: str
    hazard_state: str
    hazard_score: float

    def to_dict(self) -> dict:
        return {
            "frame": self.frame_index,
            "time_ms": round(self.timestamp_ms, 1),
            "type": self.event_type,
            "description": self.description,
            "state": self.hazard_state,
            "score": round(self.hazard_score, 3),
        }


class Pipeline:
    """Processes a video file through the full CampusNav Sentinel pipeline."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.from_env()
        self.agent = AgentController(
            frame_analyzer=FrameAnalyzer(target_width=self.config.target_width,
                                          roi_bottom_fraction=self.config.roi_bottom_fraction),
            detector=None,
        )
        self.nebius_client = NebiusClient(
            api_key=self.config.nebius_api_key,
            model=self.config.nebius_model,
        ) if self.config.nebius_enabled else None
        self.metrics = PipelineMetrics(opencv_version=cv2.__version__)
        self.timeline: list[TimelineEvent] = []
        self.frame_results: list[dict] = []
        self.nebius_analyses: list[dict] = []
        self._initialized = False

    def _ensure_detector(self) -> None:
        if not self._initialized:
            from app.perception.detector import ObjectDetector
            self.agent.detector = ObjectDetector(
                model_name=self.config.detector_model,
                confidence_threshold=self.config.detector_confidence,
                device=self.config.detector_device,
            )
            self._initialized = True

    def run(
        self,
        input_path: str | Path,
        output_dir: Optional[str | Path] = None,
    ) -> dict:
        self._ensure_detector()
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input not found: {input_path}")

        out = Path(output_dir) if output_dir else self.config.output_dir
        out.mkdir(parents=True, exist_ok=True)

        if input_path.suffix.lower() in (".mp4", ".avi", ".mov", ".mkv", ".webm"):
            return self._process_video(input_path, out)
        elif input_path.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp"):
            return self._process_image(input_path, out)
        else:
            raise ValueError(f"Unsupported format: {input_path.suffix}")

    def _process_video(self, video_path: Path, out_dir: Path) -> dict:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.metrics.total_frames = total

        out_w = self.config.target_width
        out_h = int(h * (out_w / w)) if w > 0 else 480
        writer_path = str(out_dir / "annotated_output.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(writer_path, fourcc, fps, (out_w, out_h))

        self.agent.reset()
        self.timeline.clear()
        self.frame_results.clear()
        t_start = time.perf_counter()

        frame_idx = 0
        inference_times = []
        prev_state = HazardState.CLEAR

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if self.config.max_frames > 0 and frame_idx >= self.config.max_frames:
                break

            if frame_idx % max(1, self.config.frame_skip) != 0:
                frame_idx += 1
                continue

            timestamp_ms = (frame_idx / fps) * 1000.0

            try:
                decision, fr, dr, annotated = self.agent.process_frame(frame, frame_idx, timestamp_ms)

                self.metrics.processed_frames += 1
                self.metrics.total_detections += len(dr.detections)
                self.metrics.total_hazards += dr.hazard_count
                self.metrics.total_persons += dr.person_count
                self.metrics.total_vehicles += dr.vehicle_count
                inference_times.append(dr.inference_time_ms)

                if decision.hazard_score > self.metrics.peak_hazard_score:
                    self.metrics.peak_hazard_score = decision.hazard_score

                if decision.simulated_response == "SIMULATED_EMERGENCY_STOP":
                    self.metrics.simulated_stops += 1
                if decision.simulated_response == "SIMULATED_HUMAN_REVIEW":
                    self.metrics.human_reviews += 1

                if decision.hazard_state != prev_state:
                    self.timeline.append(TimelineEvent(
                        frame_index=frame_idx,
                        timestamp_ms=timestamp_ms,
                        event_type="state_change",
                        description=f"{prev_state.value} -> {decision.hazard_state.value}: {decision.reason}",
                        hazard_state=decision.hazard_state.value,
                        hazard_score=decision.hazard_score,
                    ))
                    prev_state = decision.hazard_state

                if dr.hazard_count > 0:
                    self.timeline.append(TimelineEvent(
                        frame_index=frame_idx,
                        timestamp_ms=timestamp_ms,
                        event_type="detection",
                        description=f"{dr.hazard_count} hazards detected ({dr.person_count}P/{dr.vehicle_count}V)",
                        hazard_state=decision.hazard_state.value,
                        hazard_score=decision.hazard_score,
                    ))

                # Call Nebius AI for scene analysis at intervals
                nebius_analysis = None
                if (
                    self.nebius_client
                    and self.nebius_client.enabled
                    and self.metrics.processed_frames % self.config.nebius_interval == 0
                ):
                    det_list = [
                        {
                            "class": d.class_name,
                            "confidence": d.confidence,
                            "x": d.x,
                            "y": d.y,
                        }
                        for d in dr.detections
                    ]
                    metadata = {
                        "frame_index": frame_idx,
                        "timestamp_ms": timestamp_ms,
                        "hazard_state": decision.hazard_state.value,
                        "hazard_score": decision.hazard_score,
                    }
                    nebius_analysis = self.nebius_client.analyze_scene(det_list, metadata)
                    self.metrics.nebius_calls += 1
                    if nebius_analysis.success:
                        self.metrics.nebius_successes += 1
                        self.metrics.nebius_model = nebius_analysis.model_used
                        self.nebius_analyses.append({
                            "frame": frame_idx,
                            "time_ms": round(timestamp_ms, 1),
                            "scene": nebius_analysis.scene_description,
                            "risk": nebius_analysis.risk_assessment,
                            "action": nebius_analysis.recommendations,
                            "model": nebius_analysis.model_used,
                        })
                        logger.info(
                            "Nebius analysis [frame %d]: %s | Risk: %s",
                            frame_idx,
                            nebius_analysis.scene_description[:60],
                            nebius_analysis.risk_assessment,
                        )

                self.frame_results.append({
                    "frame": frame_idx,
                    "time_ms": round(timestamp_ms, 1),
                    "state": decision.hazard_state.value,
                    "score": round(decision.hazard_score, 3),
                    "detections": dr.hazard_count,
                    "persons": dr.person_count,
                })

                # Overlay Nebius analysis on annotated frame if available
                if nebius_analysis and nebius_analysis.success:
                    h, w = annotated.shape[:2]
                    # Add a semi-transparent overlay box at the top for Nebius results
                    overlay = annotated.copy()
                    cv2.rectangle(overlay, (10, 10), (w - 10, 100), (0, 0, 0), -1)
                    annotated = cv2.addWeighted(annotated, 0.7, overlay, 0.3, 0)

                    font = cv2.FONT_HERSHEY_SIMPLEX
                    cv2.putText(
                        annotated,
                        f"NEBIUS AI: {nebius_analysis.scene_description[:50]}",
                        (15, 30),
                        font,
                        0.5,
                        (0, 255, 255),
                        1,
                    )
                    cv2.putText(
                        annotated,
                        f"RISK: {nebius_analysis.risk_assessment[:40]}",
                        (15, 55),
                        font,
                        0.5,
                        (0, 200, 255),
                        1,
                    )
                    cv2.putText(
                        annotated,
                        f"ACTION: {nebius_analysis.recommendations[:45]}",
                        (15, 80),
                        font,
                        0.5,
                        (0, 255, 200),
                        1,
                    )

                ah, aw = annotated.shape[:2]
                if (aw, ah) != (out_w, out_h):
                    annotated = cv2.resize(annotated, (out_w, out_h))
                writer.write(annotated)

            except Exception as e:
                logger.error("Frame %d failed: %s", frame_idx, e)
                self.metrics.failed_frames += 1

            frame_idx += 1

        cap.release()
        writer.release()

        elapsed = time.perf_counter() - t_start
        self.metrics.total_time_s = elapsed
        self.metrics.avg_fps = self.metrics.processed_frames / elapsed if elapsed > 0 else 0
        self.metrics.avg_inference_ms = sum(inference_times) / len(inference_times) if inference_times else 0
        self.metrics.agent_steps = len(self.agent.trace.steps)

        report = self._build_report(str(video_path), writer_path)
        report_path = out_dir / "report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info("Pipeline complete: %d frames in %.1fs (%.1f FPS)",
                     self.metrics.processed_frames, elapsed, self.metrics.avg_fps)

        return report

    def _process_image(self, image_path: Path, out_dir: Path) -> dict:
        self._ensure_detector()
        frame = cv2.imread(str(image_path))
        if frame is None:
            raise RuntimeError(f"Cannot read image: {image_path}")

        self.agent.reset()
        self.metrics.total_frames = 1

        t_start = time.perf_counter()
        decision, fr, dr, annotated = self.agent.process_frame(frame, 0, 0.0)
        elapsed = time.perf_counter() - t_start

        self.metrics.processed_frames = 1
        self.metrics.total_time_s = elapsed
        self.metrics.total_detections = len(dr.detections)
        self.metrics.total_hazards = dr.hazard_count
        self.metrics.total_persons = dr.person_count
        self.metrics.total_vehicles = dr.vehicle_count
        self.metrics.peak_hazard_score = decision.hazard_score
        self.metrics.agent_steps = len(self.agent.trace.steps)

        # Nebius analysis for single image
        if self.nebius_client and self.nebius_client.enabled:
            det_list = [
                {"class": d.class_name, "confidence": d.confidence, "x": d.x, "y": d.y}
                for d in dr.detections
            ]
            metadata = {
                "frame_index": 0,
                "timestamp_ms": 0.0,
                "hazard_state": decision.hazard_state.value,
                "hazard_score": decision.hazard_score,
            }
            nebius_analysis = self.nebius_client.analyze_scene(det_list, metadata)
            self.metrics.nebius_calls = 1
            if nebius_analysis.success:
                self.metrics.nebius_successes = 1
                self.metrics.nebius_model = nebius_analysis.model_used
                self.nebius_analyses.append({
                    "frame": 0,
                    "time_ms": 0.0,
                    "scene": nebius_analysis.scene_description,
                    "risk": nebius_analysis.risk_assessment,
                    "action": nebius_analysis.recommendations,
                    "model": nebius_analysis.model_used,
                })

                # Overlay Nebius analysis
                h, w = annotated.shape[:2]
                overlay = annotated.copy()
                cv2.rectangle(overlay, (10, 10), (w - 10, 100), (0, 0, 0), -1)
                annotated = cv2.addWeighted(annotated, 0.7, overlay, 0.3, 0)

                font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.putText(
                    annotated,
                    f"NEBIUS AI: {nebius_analysis.scene_description[:50]}",
                    (15, 30),
                    font,
                    0.5,
                    (0, 255, 255),
                    1,
                )
                cv2.putText(
                    annotated,
                    f"RISK: {nebius_analysis.risk_assessment[:40]}",
                    (15, 55),
                    font,
                    0.5,
                    (0, 200, 255),
                    1,
                )
                cv2.putText(
                    annotated,
                    f"ACTION: {nebius_analysis.recommendations[:45]}",
                    (15, 80),
                    font,
                    0.5,
                    (0, 255, 200),
                    1,
                )

        out_path = str(out_dir / "annotated_output.jpg")
        cv2.imwrite(out_path, annotated)

        report = self._build_report(str(image_path), out_path)
        report_path = out_dir / "report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        return report

    def _build_report(self, input_path: str, output_path: str) -> dict:
        return {
            "input": input_path,
            "output": output_path,
            "opencv_version": cv2.__version__,
            "metrics": self.metrics.to_dict(),
            "timeline": [e.to_dict() for e in self.timeline],
            "agent_trace": self.agent.trace.to_dict(),
            "frame_summary": self.frame_results[-20:] if len(self.frame_results) > 20 else self.frame_results,
            "nebius_analyses": self.nebius_analyses,
        }
