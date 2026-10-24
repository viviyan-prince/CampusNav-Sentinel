"""Frame-difference and motion analysis using OpenCV 5."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np


@dataclass
class MotionResult:
    frame_index: int
    motion_score: float
    motion_regions: list[tuple[int, int, int, int]]
    has_significant_motion: bool
    diff_frame: np.ndarray = field(repr=False)

    def to_dict(self) -> dict:
        return {
            "frame_index": self.frame_index,
            "motion_score": round(self.motion_score, 4),
            "motion_region_count": len(self.motion_regions),
            "has_significant_motion": self.has_significant_motion,
            "motion_regions": [
                {"x": x, "y": y, "w": w, "h": h}
                for x, y, w, h in self.motion_regions
            ],
        }


class MotionAnalyzer:
    """Detects motion between consecutive frames via background subtraction."""

    def __init__(
        self,
        motion_threshold: float = 0.02,
        min_contour_area: int = 500,
        history: int = 100,
        var_threshold: float = 40.0,
    ):
        self.motion_threshold = motion_threshold
        self.min_contour_area = min_contour_area
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history, varThreshold=var_threshold, detectShadows=True
        )
        self._prev_gray: Optional[np.ndarray] = None

    def reset(self) -> None:
        self._prev_gray = None
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=100, varThreshold=40.0, detectShadows=True
        )

    def analyze(self, gray: np.ndarray, frame_index: int = 0) -> MotionResult:
        fg_mask = self.bg_subtractor.apply(gray)
        fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)[1]
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

        if self._prev_gray is not None and self._prev_gray.shape == gray.shape:
            diff = cv2.absdiff(self._prev_gray, gray)
            _, diff_thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            combined = cv2.bitwise_or(fg_mask, diff_thresh)
        else:
            combined = fg_mask
            diff_thresh = fg_mask

        self._prev_gray = gray.copy()

        h, w = combined.shape
        motion_score = float(np.count_nonzero(combined) / (h * w))

        contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        regions = []
        for c in contours:
            area = cv2.contourArea(c)
            if area >= self.min_contour_area:
                x, y, bw, bh = cv2.boundingRect(c)
                regions.append((x, y, bw, bh))

        return MotionResult(
            frame_index=frame_index,
            motion_score=motion_score,
            motion_regions=regions,
            has_significant_motion=motion_score > self.motion_threshold,
            diff_frame=combined,
        )
