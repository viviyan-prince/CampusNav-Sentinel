"""OpenCV 5 frame analysis pipeline for campus shuttle hazard detection."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np


@dataclass
class FrameResult:
    frame_index: int
    timestamp_ms: float
    original_shape: tuple[int, int, int]
    brightness: float
    contrast: float
    blur_score: float
    edge_density: float
    roi_mask_applied: bool
    processing_time_ms: float
    enhanced: np.ndarray = field(repr=False)
    gray: np.ndarray = field(repr=False)
    edges: np.ndarray = field(repr=False)
    roi_frame: np.ndarray = field(repr=False)
    quality: str = "good"

    def to_dict(self) -> dict:
        return {
            "frame_index": self.frame_index,
            "timestamp_ms": round(self.timestamp_ms, 2),
            "shape": list(self.original_shape),
            "brightness": round(self.brightness, 3),
            "contrast": round(self.contrast, 3),
            "blur_score": round(self.blur_score, 3),
            "edge_density": round(self.edge_density, 4),
            "quality": self.quality,
            "processing_time_ms": round(self.processing_time_ms, 2),
        }


class FrameAnalyzer:
    """Processes individual frames using OpenCV 5 operations."""

    def __init__(
        self,
        target_width: int = 640,
        roi_bottom_fraction: float = 0.6,
        clahe_clip: float = 2.0,
        clahe_grid: int = 8,
        canny_low: int = 50,
        canny_high: int = 150,
        blur_threshold: float = 100.0,
        brightness_low: float = 0.2,
        brightness_high: float = 0.8,
    ):
        self.target_width = target_width
        self.roi_bottom_fraction = roi_bottom_fraction
        self.clahe = cv2.createCLAHE(
            clipLimit=clahe_clip, tileGridSize=(clahe_grid, clahe_grid)
        )
        self.canny_low = canny_low
        self.canny_high = canny_high
        self.blur_threshold = blur_threshold
        self.brightness_low = brightness_low
        self.brightness_high = brightness_high

    def analyze(
        self,
        frame: np.ndarray,
        frame_index: int = 0,
        timestamp_ms: float = 0.0,
    ) -> Optional[FrameResult]:
        if frame is None or frame.size == 0:
            return None

        t0 = time.perf_counter()
        original_shape = frame.shape

        resized = self._resize(frame)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        brightness = float(np.mean(gray) / 255.0)
        contrast = float(np.std(gray) / 128.0)
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        quality = "good"
        if brightness < self.brightness_low:
            quality = "dark"
        elif brightness > self.brightness_high:
            quality = "overexposed"
        if blur_score < self.blur_threshold:
            quality = "blurry" if quality == "good" else f"{quality}+blurry"

        enhanced_gray = self.clahe.apply(gray)

        enhanced_bgr = resized.copy()
        lab = cv2.cvtColor(enhanced_bgr, cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0]
        lab[:, :, 0] = self.clahe.apply(l_channel)
        enhanced_bgr = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        edges = cv2.Canny(enhanced_gray, self.canny_low, self.canny_high)
        h, w = edges.shape
        edge_density = float(np.count_nonzero(edges) / (h * w))

        roi_frame, roi_applied = self._apply_roi(enhanced_bgr)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return FrameResult(
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
            original_shape=original_shape,
            brightness=brightness,
            contrast=contrast,
            blur_score=blur_score,
            edge_density=edge_density,
            roi_mask_applied=roi_applied,
            processing_time_ms=elapsed_ms,
            enhanced=enhanced_bgr,
            gray=enhanced_gray,
            edges=edges,
            roi_frame=roi_frame,
            quality=quality,
        )

    def _resize(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        if w == self.target_width:
            return frame
        scale = self.target_width / w
        new_h = int(h * scale)
        return cv2.resize(frame, (self.target_width, new_h), interpolation=cv2.INTER_AREA)

    def _apply_roi(self, frame: np.ndarray) -> tuple[np.ndarray, bool]:
        h, w = frame.shape[:2]
        roi_top = int(h * (1.0 - self.roi_bottom_fraction))
        mask = np.zeros((h, w), dtype=np.uint8)
        pts = np.array(
            [[0, h], [0, roi_top], [w // 2, int(roi_top * 0.8)], [w, roi_top], [w, h]],
            dtype=np.int32,
        )
        cv2.fillPoly(mask, [pts], 255)
        roi_frame = cv2.bitwise_and(frame, frame, mask=mask)
        return roi_frame, True
