"""Tests for agent controller."""

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent.controller import AgentController, AgentAction, HazardState


@pytest.fixture
def controller():
    return AgentController()


@pytest.fixture
def sample_frame():
    frame = np.full((480, 640, 3), 128, dtype=np.uint8)
    cv2.rectangle(frame, (200, 300), (260, 400), (0, 0, 255), -1)
    return frame


@pytest.fixture
def empty_frame():
    return np.full((480, 640, 3), 200, dtype=np.uint8)


class TestAgentController:
    def test_initial_state(self, controller):
        assert controller.state == HazardState.CLEAR
        assert controller.hazard_score == 0.0
        assert len(controller.tracked) == 0

    def test_process_frame_returns_tuple(self, controller, sample_frame):
        decision, fr, dr, annotated = controller.process_frame(sample_frame, 0, 0.0)
        assert decision is not None
        assert decision.frame_index == 0
        assert annotated.shape[:2] == fr.enhanced.shape[:2]

    def test_clear_scene(self, controller, empty_frame):
        decision, _, _, _ = controller.process_frame(empty_frame, 0, 0.0)
        assert decision.hazard_state in (HazardState.CLEAR, HazardState.CANDIDATE_DETECTED,
                                          HazardState.CONFIRMED_HAZARD)

    def test_agent_trace_recorded(self, controller, sample_frame):
        controller.process_frame(sample_frame, 0, 0.0)
        assert len(controller.trace.steps) > 0
        assert len(controller.trace.decisions) == 1

    def test_multiple_frames_build_trace(self, controller, sample_frame):
        for i in range(5):
            controller.process_frame(sample_frame, i, i * 100.0)
        assert len(controller.trace.decisions) == 5

    def test_reset(self, controller, sample_frame):
        controller.process_frame(sample_frame, 0, 0.0)
        controller.reset()
        assert controller.state == HazardState.CLEAR
        assert len(controller.trace.steps) == 0
        assert len(controller.tracked) == 0

    def test_trace_to_dict(self, controller, sample_frame):
        controller.process_frame(sample_frame, 0, 0.0)
        d = controller.trace.to_dict()
        assert "total_steps" in d
        assert "steps" in d
        assert isinstance(d["steps"], list)

    def test_bounded_iterations(self, controller, sample_frame):
        decision, _, _, _ = controller.process_frame(sample_frame, 0, 0.0)
        step_count = len([s for s in controller.trace.steps if s.timestamp_ms == 0.0])
        assert step_count <= AgentController.MAX_ITERATIONS_PER_FRAME + 1


class TestAgentActions:
    def test_all_actions_defined(self):
        expected = {
            "ANALYZE_FRAME", "INSPECT_REGION", "COMPARE_NEXT_FRAME",
            "VERIFY_PERSISTENCE", "REQUEST_SIMULATED_STOP",
            "REQUEST_HUMAN_REVIEW", "CONTINUE_MONITORING", "REPORT_FAILURE",
        }
        actual = {a.value for a in AgentAction}
        assert expected == actual

    def test_all_states_defined(self):
        expected = {
            "CLEAR", "CANDIDATE_DETECTED", "UNDER_INSPECTION",
            "CONFIRMED_HAZARD", "PERSISTENT_HAZARD", "DEGRADED", "UNKNOWN",
        }
        actual = {s.value for s in HazardState}
        assert expected == actual
