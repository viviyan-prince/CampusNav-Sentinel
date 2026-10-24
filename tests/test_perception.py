"""Tests for perception modules."""

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.perception.frame_analyzer import FrameAnalyzer
from app.perception.motion_analyzer import MotionAnalyzer


@pytest.fixture
def sample_frame():
    frame = np.full((480, 640, 3), 128, dtype=np.uint8)
    cv2.rectangle(frame, (200, 300), (260, 400), (0, 0, 255), -1)
    return frame


@pytest.fixture
def dark_frame():
    return np.full((480, 640, 3), 20, dtype=np.uint8)


@pytest.fixture
def blank_frame():
    return np.full((480, 640, 3), 200, dtype=np.uint8)


class TestFrameAnalyzer:
    def test_analyze_returns_result(self, sample_frame):
        analyzer = FrameAnalyzer()
        result = analyzer.analyze(sample_frame, frame_index=0, timestamp_ms=0.0)
        assert result is not None
        assert result.frame_index == 0
        assert result.processing_time_ms > 0

    def test_analyze_none_frame(self):
        analyzer = FrameAnalyzer()
        result = analyzer.analyze(None)
        assert result is None

    def test_analyze_empty_frame(self):
        analyzer = FrameAnalyzer()
        result = analyzer.analyze(np.array([]))
        assert result is None

    def test_brightness_detection(self, dark_frame, blank_frame):
        analyzer = FrameAnalyzer()
        dark_result = analyzer.analyze(dark_frame)
        bright_result = analyzer.analyze(blank_frame)
        assert dark_result.brightness < 0.2
        assert bright_result.brightness > 0.7
        assert "dark" in dark_result.quality

    def test_roi_applied(self, sample_frame):
        analyzer = FrameAnalyzer()
        result = analyzer.analyze(sample_frame)
        assert result.roi_mask_applied is True

    def test_resize(self, sample_frame):
        analyzer = FrameAnalyzer(target_width=320)
        result = analyzer.analyze(sample_frame)
        assert result.enhanced.shape[1] == 320

    def test_edge_detection(self, sample_frame):
        analyzer = FrameAnalyzer()
        result = analyzer.analyze(sample_frame)
        assert result.edge_density >= 0.0
        assert result.edges.shape[:2] == result.gray.shape[:2]

    def test_to_dict(self, sample_frame):
        analyzer = FrameAnalyzer()
        result = analyzer.analyze(sample_frame)
        d = result.to_dict()
        assert "brightness" in d
        assert "edge_density" in d
        assert "quality" in d
        assert isinstance(d["processing_time_ms"], float)

    def test_opencv_version(self):
        major = int(cv2.__version__.split(".")[0])
        assert major >= 5, f"OpenCV {cv2.__version__} — expected 5.x"


class TestMotionAnalyzer:
    def test_no_motion_on_identical_frames(self, sample_frame):
        analyzer = MotionAnalyzer()
        gray = cv2.cvtColor(sample_frame, cv2.COLOR_BGR2GRAY)
        analyzer.analyze(gray, 0)
        result = analyzer.analyze(gray, 1)
        assert result.motion_score < 0.05

    def test_motion_detected_on_change(self, sample_frame):
        analyzer = MotionAnalyzer()
        gray1 = cv2.cvtColor(sample_frame, cv2.COLOR_BGR2GRAY)
        analyzer.analyze(gray1, 0)

        moved = sample_frame.copy()
        cv2.rectangle(moved, (400, 300), (500, 400), (255, 0, 0), -1)
        gray2 = cv2.cvtColor(moved, cv2.COLOR_BGR2GRAY)
        result = analyzer.analyze(gray2, 1)
        assert result.motion_score > 0.0

    def test_reset(self, sample_frame):
        analyzer = MotionAnalyzer()
        gray = cv2.cvtColor(sample_frame, cv2.COLOR_BGR2GRAY)
        analyzer.analyze(gray, 0)
        analyzer.reset()
        assert analyzer._prev_gray is None

    def test_to_dict(self, sample_frame):
        analyzer = MotionAnalyzer()
        gray = cv2.cvtColor(sample_frame, cv2.COLOR_BGR2GRAY)
        result = analyzer.analyze(gray, 0)
        d = result.to_dict()
        assert "motion_score" in d
        assert "has_significant_motion" in d
