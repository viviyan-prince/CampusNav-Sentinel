"""Configuration with environment variable overrides."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    target_width: int = 640
    roi_bottom_fraction: float = 0.6
    detector_model: str = "yolov8n.pt"
    detector_confidence: float = 0.35
    detector_device: str | None = None
    motion_threshold: float = 0.02
    frame_skip: int = 1
    max_frames: int = 0  # 0 = all
    output_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / "output")
    upload_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / "uploads")
    max_upload_mb: int = 100
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    aws_region: str = "us-east-1"
    aws_s3_bucket: str = ""
    aws_enabled: bool = False
    log_level: str = "INFO"
    nebius_api_key: str = ""
    nebius_model: str = "meta-llama/Llama-3.3-70B-Instruct"
    nebius_enabled: bool = True
    nebius_interval: int = 5  # Analyze every Nth processed frame

    @classmethod
    def from_env(cls) -> Config:
        cfg = cls()
        cfg.target_width = int(os.getenv("CN_TARGET_WIDTH", cfg.target_width))
        cfg.roi_bottom_fraction = float(os.getenv("CN_ROI_FRACTION", cfg.roi_bottom_fraction))
        cfg.detector_model = os.getenv("CN_DETECTOR_MODEL", cfg.detector_model)
        cfg.detector_confidence = float(os.getenv("CN_DETECTOR_CONFIDENCE", cfg.detector_confidence))
        cfg.detector_device = os.getenv("CN_DETECTOR_DEVICE", cfg.detector_device)
        cfg.motion_threshold = float(os.getenv("CN_MOTION_THRESHOLD", cfg.motion_threshold))
        cfg.frame_skip = int(os.getenv("CN_FRAME_SKIP", cfg.frame_skip))
        cfg.max_frames = int(os.getenv("CN_MAX_FRAMES", cfg.max_frames))
        cfg.api_host = os.getenv("CN_API_HOST", cfg.api_host)
        cfg.api_port = int(os.getenv("CN_API_PORT", cfg.api_port))
        cfg.aws_region = os.getenv("AWS_DEFAULT_REGION", cfg.aws_region)
        cfg.aws_s3_bucket = os.getenv("CN_S3_BUCKET", cfg.aws_s3_bucket)
        cfg.aws_enabled = os.getenv("CN_AWS_ENABLED", "false").lower() == "true"
        cfg.log_level = os.getenv("CN_LOG_LEVEL", cfg.log_level)
        cfg.nebius_api_key = os.getenv("NEBIUS_API_KEY", cfg.nebius_api_key)
        cfg.nebius_model = os.getenv("NEBIUS_MODEL", cfg.nebius_model)
        cfg.nebius_enabled = os.getenv("NEBIUS_ENABLED", "true").lower() == "true"
        cfg.nebius_interval = int(os.getenv("NEBIUS_INTERVAL", cfg.nebius_interval))
        return cfg
