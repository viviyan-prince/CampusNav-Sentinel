"""Integration tests for the full pipeline."""

import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import Config
from app.pipeline import Pipeline


@pytest.fixture
def test_video(tmp_path):
    path = str(tmp_path / "test.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, 10, (320, 240))
    for i in range(30):
        frame = np.full((240, 320, 3), 128, dtype=np.uint8)
        if 10 <= i <= 20:
            cv2.rectangle(frame, (100, 100), (150, 200), (0, 0, 255), -1)
        writer.write(frame)
    writer.release()
    return path


@pytest.fixture
def test_image(tmp_path):
    path = str(tmp_path / "test.jpg")
    frame = np.full((480, 640, 3), 128, dtype=np.uint8)
    cv2.rectangle(frame, (200, 300), (260, 400), (0, 0, 255), -1)
    cv2.imwrite(path, frame)
    return path


@pytest.fixture
def config():
    cfg = Config()
    cfg.max_frames = 20
    cfg.target_width = 320
    return cfg


class TestPipeline:
    def test_video_processing(self, test_video, config, tmp_path):
        pipeline = Pipeline(config)
        report = pipeline.run(test_video, str(tmp_path / "out"))
        assert report["opencv_version"] == cv2.__version__
        assert report["metrics"]["processed_frames"] > 0
        assert report["metrics"]["failed_frames"] == 0
        assert Path(report["output"]).exists()

    def test_image_processing(self, test_image, config, tmp_path):
        pipeline = Pipeline(config)
        report = pipeline.run(test_image, str(tmp_path / "out"))
        assert report["metrics"]["processed_frames"] == 1
        assert Path(report["output"]).exists()

    def test_report_structure(self, test_video, config, tmp_path):
        pipeline = Pipeline(config)
        report = pipeline.run(test_video, str(tmp_path / "out"))
        assert "metrics" in report
        assert "timeline" in report
        assert "agent_trace" in report
        assert "opencv_version" in report

    def test_invalid_input(self, config, tmp_path):
        pipeline = Pipeline(config)
        with pytest.raises(FileNotFoundError):
            pipeline.run("nonexistent.mp4", str(tmp_path / "out"))

    def test_unsupported_format(self, config, tmp_path):
        bad = tmp_path / "test.xyz"
        bad.write_text("not a video")
        pipeline = Pipeline(config)
        with pytest.raises(ValueError):
            pipeline.run(str(bad), str(tmp_path / "out"))

    def test_report_json_serializable(self, test_video, config, tmp_path):
        pipeline = Pipeline(config)
        report = pipeline.run(test_video, str(tmp_path / "out"))
        serialized = json.dumps(report)
        assert len(serialized) > 100

    def test_agent_trace_in_report(self, test_video, config, tmp_path):
        pipeline = Pipeline(config)
        report = pipeline.run(test_video, str(tmp_path / "out"))
        trace = report["agent_trace"]
        assert trace["total_steps"] > 0
        assert len(trace["steps"]) > 0

    def test_metrics_complete(self, test_video, config, tmp_path):
        pipeline = Pipeline(config)
        report = pipeline.run(test_video, str(tmp_path / "out"))
        m = report["metrics"]
        assert m["avg_fps"] > 0
        assert m["opencv_version"] == cv2.__version__
        assert m["total_time_s"] > 0
