"""Deterministic agentic controller with visual-evidence-driven state machine."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import cv2
import numpy as np

from app.perception.frame_analyzer import FrameAnalyzer, FrameResult
from app.perception.motion_analyzer import MotionAnalyzer, MotionResult
from app.perception.detector import ObjectDetector, DetectionResult, Detection

logger = logging.getLogger(__name__)


class AgentAction(str, Enum):
    ANALYZE_FRAME = "ANALYZE_FRAME"
    INSPECT_REGION = "INSPECT_REGION"
    COMPARE_NEXT_FRAME = "COMPARE_NEXT_FRAME"
    VERIFY_PERSISTENCE = "VERIFY_PERSISTENCE"
    REQUEST_SIMULATED_STOP = "REQUEST_SIMULATED_STOP"
    REQUEST_HUMAN_REVIEW = "REQUEST_HUMAN_REVIEW"
    CONTINUE_MONITORING = "CONTINUE_MONITORING"
    REPORT_FAILURE = "REPORT_FAILURE"


class HazardState(str, Enum):
    CLEAR = "CLEAR"
    CANDIDATE_DETECTED = "CANDIDATE_DETECTED"
    UNDER_INSPECTION = "UNDER_INSPECTION"
    CONFIRMED_HAZARD = "CONFIRMED_HAZARD"
    PERSISTENT_HAZARD = "PERSISTENT_HAZARD"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


@dataclass
class TrackedCandidate:
    detection: Detection
    first_seen_frame: int
    last_seen_frame: int
    seen_count: int = 1
    not_seen_count: int = 0
    region_inspected: bool = False
    region_confidence: float = 0.0
    verified: bool = False


@dataclass
class AgentStep:
    step_number: int
    action: AgentAction
    reason: str
    evidence: dict
    result: dict
    state_before: HazardState
    state_after: HazardState
    timestamp_ms: float


@dataclass
class AgentDecision:
    frame_index: int
    hazard_state: HazardState
    hazard_score: float
    action_taken: AgentAction
    reason: str
    tracked_candidates: int
    confirmed_hazards: int
    simulated_response: Optional[str]


@dataclass
class AgentTrace:
    steps: list[AgentStep] = field(default_factory=list)
    decisions: list[AgentDecision] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_steps": len(self.steps),
            "total_decisions": len(self.decisions),
            "steps": [
                {
                    "step": s.step_number,
                    "action": s.action.value,
                    "reason": s.reason,
                    "state_before": s.state_before.value,
                    "state_after": s.state_after.value,
                    "evidence_summary": s.evidence,
                    "result_summary": s.result,
                }
                for s in self.steps
            ],
        }


class AgentController:
    """Deterministic state-machine agent driven by visual evidence.

    The agent inspects visual analysis outputs and decides what to do next.
    Each decision is recorded in a trace for judge inspection.
    """

    MAX_ITERATIONS_PER_FRAME = 5
    PERSISTENCE_THRESHOLD = 3  # frames to confirm a hazard
    DISAPPEAR_THRESHOLD = 3  # missed frames before dropping candidate
    HIGH_HAZARD_SCORE = 0.7
    CRITICAL_HAZARD_SCORE = 0.9

    def __init__(
        self,
        frame_analyzer: Optional[FrameAnalyzer] = None,
        motion_analyzer: Optional[MotionAnalyzer] = None,
        detector: Optional[ObjectDetector] = None,
    ):
        self.frame_analyzer = frame_analyzer or FrameAnalyzer()
        self.motion_analyzer = motion_analyzer or MotionAnalyzer()
        self.detector = detector or ObjectDetector()

        self.state = HazardState.CLEAR
        self.hazard_score: float = 0.0
        self.tracked: dict[str, TrackedCandidate] = {}
        self.trace = AgentTrace()
        self._step_counter = 0

    def reset(self) -> None:
        self.state = HazardState.CLEAR
        self.hazard_score = 0.0
        self.tracked.clear()
        self.trace = AgentTrace()
        self._step_counter = 0
        self.motion_analyzer.reset()

    def process_frame(
        self,
        frame: np.ndarray,
        frame_index: int,
        timestamp_ms: float,
    ) -> tuple[AgentDecision, FrameResult, DetectionResult, np.ndarray]:
        """Process one frame through the full agentic loop.

        Returns the decision, frame analysis, detections, and annotated frame.
        """
        iteration = 0
        frame_result: Optional[FrameResult] = None
        det_result: Optional[DetectionResult] = None
        motion_result: Optional[MotionResult] = None
        annotated = frame.copy()

        next_action = AgentAction.ANALYZE_FRAME
        reason = "Start of frame processing"

        while iteration < self.MAX_ITERATIONS_PER_FRAME:
            iteration += 1
            state_before = self.state
            self._step_counter += 1

            if next_action == AgentAction.ANALYZE_FRAME:
                frame_result, det_result, motion_result, evidence, result = (
                    self._execute_analyze_frame(frame, frame_index, timestamp_ms)
                )
                if frame_result is None:
                    next_action, reason = self._transition_to_failure(
                        "Frame analysis returned None — possible corrupt input"
                    )
                elif frame_result.quality != "good" and det_result.hazard_count == 0:
                    next_action = AgentAction.REQUEST_HUMAN_REVIEW
                    reason = f"Poor frame quality ({frame_result.quality}) with no detections — uncertain scene"
                elif det_result.hazard_count > 0:
                    next_action = AgentAction.INSPECT_REGION
                    reason = f"Detected {det_result.hazard_count} hazard(s), inspecting closest"
                    self.state = HazardState.CANDIDATE_DETECTED
                elif motion_result.has_significant_motion:
                    next_action = AgentAction.COMPARE_NEXT_FRAME
                    reason = "Significant motion detected but no classified hazards — will compare next frame"
                else:
                    next_action = AgentAction.CONTINUE_MONITORING
                    reason = "Scene clear: no hazards, no significant motion"
                    self.state = HazardState.CLEAR
                    self.hazard_score = max(0.0, self.hazard_score - 0.1)

            elif next_action == AgentAction.INSPECT_REGION:
                evidence, result = self._execute_inspect_region(
                    frame_result, det_result, frame, frame_index
                )
                if result.get("high_confidence_hazards", 0) > 0:
                    self.state = HazardState.UNDER_INSPECTION
                    next_action = AgentAction.VERIFY_PERSISTENCE
                    reason = "High-confidence hazard in ROI — verifying persistence"
                else:
                    next_action = AgentAction.CONTINUE_MONITORING
                    reason = "Candidates below ROI threshold or outside shuttle path"
                    self.state = HazardState.CLEAR

            elif next_action == AgentAction.VERIFY_PERSISTENCE:
                evidence, result = self._execute_verify_persistence(frame_index)
                confirmed = result.get("confirmed_hazards", 0)
                if confirmed > 0:
                    self.state = HazardState.CONFIRMED_HAZARD
                    self.hazard_score = min(1.0, 0.5 + 0.1 * confirmed)
                    if self.hazard_score >= self.CRITICAL_HAZARD_SCORE:
                        next_action = AgentAction.REQUEST_SIMULATED_STOP
                        reason = f"Critical hazard score {self.hazard_score:.2f} — requesting simulated stop"
                        self.state = HazardState.PERSISTENT_HAZARD
                    elif self.hazard_score >= self.HIGH_HAZARD_SCORE:
                        next_action = AgentAction.REQUEST_HUMAN_REVIEW
                        reason = f"High hazard score {self.hazard_score:.2f} — requesting human review"
                    else:
                        next_action = AgentAction.CONTINUE_MONITORING
                        reason = f"Confirmed hazard (score={self.hazard_score:.2f}) below critical threshold"
                else:
                    next_action = AgentAction.CONTINUE_MONITORING
                    reason = "No candidates persisted long enough to confirm"
                    self.state = HazardState.CLEAR

            elif next_action == AgentAction.COMPARE_NEXT_FRAME:
                evidence = {"motion_regions": motion_result.to_dict()["motion_region_count"] if motion_result else 0}
                result = {"action": "flagged_for_comparison", "frame_index": frame_index}
                next_action = AgentAction.CONTINUE_MONITORING
                reason = "Motion flagged — will re-evaluate on next frame"

            elif next_action == AgentAction.REQUEST_SIMULATED_STOP:
                evidence = {"hazard_score": self.hazard_score, "confirmed": len([t for t in self.tracked.values() if t.verified])}
                result = {"simulated_action": "EMERGENCY_STOP", "note": "SIMULATED — no real vehicle control"}
                next_action = AgentAction.CONTINUE_MONITORING
                reason = "Simulated stop issued"

            elif next_action == AgentAction.REQUEST_HUMAN_REVIEW:
                evidence = {"hazard_score": self.hazard_score, "state": self.state.value}
                result = {"simulated_action": "HUMAN_REVIEW_REQUESTED", "note": "SIMULATED — no real alert sent"}
                next_action = AgentAction.CONTINUE_MONITORING
                reason = "Human review requested"
                if self.state == HazardState.UNKNOWN:
                    self.state = HazardState.DEGRADED

            elif next_action == AgentAction.REPORT_FAILURE:
                evidence = {"state": self.state.value}
                result = {"simulated_action": "FAILURE_REPORTED", "note": "Perception system degraded"}
                self.state = HazardState.DEGRADED
                next_action = AgentAction.CONTINUE_MONITORING
                reason = "Failure reported, entering degraded mode"

            elif next_action == AgentAction.CONTINUE_MONITORING:
                self.trace.steps.append(
                    AgentStep(
                        step_number=self._step_counter,
                        action=AgentAction.CONTINUE_MONITORING,
                        reason=reason,
                        evidence={},
                        result={},
                        state_before=state_before,
                        state_after=self.state,
                        timestamp_ms=timestamp_ms,
                    )
                )
                break

            self.trace.steps.append(
                AgentStep(
                    step_number=self._step_counter,
                    action=next_action if next_action != AgentAction.CONTINUE_MONITORING else AgentAction(self.trace.steps[-1].action if self.trace.steps else AgentAction.ANALYZE_FRAME),
                    reason=reason,
                    evidence=evidence if "evidence" in dir() else {},
                    result=result if "result" in dir() else {},
                    state_before=state_before,
                    state_after=self.state,
                    timestamp_ms=timestamp_ms,
                )
            )

            if next_action == AgentAction.CONTINUE_MONITORING:
                break

        if frame_result is None:
            frame_result = FrameResult(
                frame_index=frame_index, timestamp_ms=timestamp_ms,
                original_shape=frame.shape, brightness=0, contrast=0, blur_score=0,
                edge_density=0, roi_mask_applied=False, processing_time_ms=0,
                enhanced=frame, gray=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame,
                edges=np.zeros(frame.shape[:2], dtype=np.uint8),
                roi_frame=frame, quality="unknown",
            )
        if det_result is None:
            det_result = DetectionResult(
                frame_index=frame_index, detections=[], inference_time_ms=0,
                model_name="none", hazard_count=0, person_count=0, vehicle_count=0,
            )

        annotated = self._draw_annotations(frame_result.enhanced, det_result, motion_result)

        simulated_response = None
        if self.state == HazardState.PERSISTENT_HAZARD:
            simulated_response = "SIMULATED_EMERGENCY_STOP"
        elif self.state == HazardState.CONFIRMED_HAZARD:
            simulated_response = "SIMULATED_SLOW_DOWN"
        elif self.state == HazardState.DEGRADED:
            simulated_response = "SIMULATED_HUMAN_REVIEW"

        decision = AgentDecision(
            frame_index=frame_index,
            hazard_state=self.state,
            hazard_score=self.hazard_score,
            action_taken=self.trace.steps[-1].action if self.trace.steps else AgentAction.ANALYZE_FRAME,
            reason=reason,
            tracked_candidates=len(self.tracked),
            confirmed_hazards=len([t for t in self.tracked.values() if t.verified]),
            simulated_response=simulated_response,
        )
        self.trace.decisions.append(decision)

        return decision, frame_result, det_result, annotated

    def _execute_analyze_frame(
        self, frame: np.ndarray, frame_index: int, timestamp_ms: float
    ) -> tuple:
        frame_result = self.frame_analyzer.analyze(frame, frame_index, timestamp_ms)
        if frame_result is None:
            empty_det = DetectionResult(frame_index=frame_index, detections=[], inference_time_ms=0,
                                        model_name="none", hazard_count=0, person_count=0, vehicle_count=0)
            empty_motion = MotionResult(frame_index=frame_index, motion_score=0, motion_regions=[],
                                        has_significant_motion=False, diff_frame=np.zeros((1, 1), dtype=np.uint8))
            return None, empty_det, empty_motion, {}, {}

        det_result = self.detector.detect(frame_result.enhanced, frame_index)
        motion_result = self.motion_analyzer.analyze(frame_result.gray, frame_index)

        evidence = {
            "quality": frame_result.quality,
            "brightness": round(frame_result.brightness, 2),
            "hazard_count": det_result.hazard_count,
            "person_count": det_result.person_count,
            "motion_score": round(motion_result.motion_score, 4),
        }
        result = {
            "detections": det_result.hazard_count,
            "motion_regions": len(motion_result.motion_regions),
            "inference_ms": round(det_result.inference_time_ms, 1),
        }
        return frame_result, det_result, motion_result, evidence, result

    def _execute_inspect_region(
        self, frame_result: FrameResult, det_result: DetectionResult,
        frame: np.ndarray, frame_index: int,
    ) -> tuple[dict, dict]:
        h = frame_result.enhanced.shape[0]
        roi_top = int(h * 0.4)
        high_conf_in_roi = 0

        for d in det_result.detections:
            if not d.is_hazard:
                continue
            _, cy = d.center
            in_roi = cy >= roi_top
            key = f"{d.class_name}_{d.center[0]//50}_{d.center[1]//50}"

            if key in self.tracked:
                tc = self.tracked[key]
                tc.last_seen_frame = frame_index
                tc.seen_count += 1
                tc.detection = d
            else:
                self.tracked[key] = TrackedCandidate(
                    detection=d, first_seen_frame=frame_index, last_seen_frame=frame_index,
                )

            if in_roi and d.confidence >= 0.5:
                self.tracked[key].region_inspected = True
                self.tracked[key].region_confidence = d.confidence
                high_conf_in_roi += 1

        evidence = {"candidates_tracked": len(self.tracked), "in_roi": high_conf_in_roi}
        result = {"high_confidence_hazards": high_conf_in_roi}
        return evidence, result

    def _execute_verify_persistence(self, current_frame: int) -> tuple[dict, dict]:
        confirmed = 0
        dropped = []

        for key, tc in self.tracked.items():
            gap = current_frame - tc.last_seen_frame
            if gap > self.DISAPPEAR_THRESHOLD:
                dropped.append(key)
                continue
            if tc.seen_count >= self.PERSISTENCE_THRESHOLD:
                tc.verified = True
                confirmed += 1

        for key in dropped:
            del self.tracked[key]

        evidence = {"tracked": len(self.tracked), "confirmed": confirmed, "dropped": len(dropped)}
        result = {"confirmed_hazards": confirmed, "dropped_candidates": len(dropped)}
        return evidence, result

    def _transition_to_failure(self, reason: str) -> tuple[AgentAction, str]:
        self.state = HazardState.UNKNOWN
        return AgentAction.REPORT_FAILURE, reason

    def _draw_annotations(
        self, frame: np.ndarray, det_result: DetectionResult,
        motion_result: Optional[MotionResult],
    ) -> np.ndarray:
        annotated = self.detector.annotate(frame, det_result)
        h, w = annotated.shape[:2]

        if motion_result:
            for x, y, bw, bh in motion_result.motion_regions:
                cv2.rectangle(annotated, (x, y), (x + bw, y + bh), (255, 255, 0), 1)

        state_color = {
            HazardState.CLEAR: (0, 200, 0),
            HazardState.CANDIDATE_DETECTED: (0, 200, 255),
            HazardState.UNDER_INSPECTION: (0, 165, 255),
            HazardState.CONFIRMED_HAZARD: (0, 0, 255),
            HazardState.PERSISTENT_HAZARD: (0, 0, 200),
            HazardState.DEGRADED: (128, 128, 128),
            HazardState.UNKNOWN: (128, 128, 128),
        }
        color = state_color.get(self.state, (255, 255, 255))
        cv2.rectangle(annotated, (0, 0), (w, 40), (0, 0, 0), -1)
        cv2.putText(annotated, f"State: {self.state.value}", (10, 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        cv2.putText(annotated, f"Hazard Score: {self.hazard_score:.2f}  |  Tracked: {len(self.tracked)}",
                    (10, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

        roi_top = int(h * 0.4)
        cv2.line(annotated, (0, roi_top), (w, roi_top), (100, 100, 255), 1)
        cv2.putText(annotated, "ROI", (5, roi_top + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 255), 1)

        return annotated
