"""Object detection using YOLOv8 with GPU acceleration."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

HAZARD_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    9: "traffic light",
    11: "stop sign",
    13: "bench",
    15: "cat",
    16: "dog",
}


@dataclass
class Detection:
    class_id: int
    class_name: str
    confidence: float
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    center: tuple[int, int]
    area: int
    is_hazard: bool

    def to_dict(self) -> dict:
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": round(self.confidence, 3),
            "bbox": {"x1": self.bbox[0], "y1": self.bbox[1], "x2": self.bbox[2], "y2": self.bbox[3]},
            "center": {"x": self.center[0], "y": self.center[1]},
            "area": self.area,
            "is_hazard": self.is_hazard,
        }


@dataclass
class DetectionResult:
    frame_index: int
    detections: list[Detection]
    inference_time_ms: float
    model_name: str
    hazard_count: int
    person_count: int
    vehicle_count: int

    def to_dict(self) -> dict:
        return {
            "frame_index": self.frame_index,
            "detection_count": len(self.detections),
            "hazard_count": self.hazard_count,
            "person_count": self.person_count,
            "vehicle_count": self.vehicle_count,
            "inference_time_ms": round(self.inference_time_ms, 2),
            "model": self.model_name,
            "detections": [d.to_dict() for d in self.detections],
        }


class ObjectDetector:
    """YOLOv8-based object detector for campus hazards."""

    VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck", "bicycle"}

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        confidence_threshold: float = 0.35,
        device: Optional[str] = None,
    ):
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self._model = None
        self._device = device
        self._available = False
        self._load_model()

    def _load_model(self) -> None:
        try:
            from ultralytics import YOLO
            import torch

            if self._device is None:
                self._device = "cuda" if torch.cuda.is_available() else "cpu"

            self._model = YOLO(self.model_name)
            self._available = True
            logger.info("YOLO model loaded: %s on %s", self.model_name, self._device)
        except Exception as e:
            logger.warning("YOLO model load failed: %s — detector will return empty results", e)
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def detect(self, frame: np.ndarray, frame_index: int = 0) -> DetectionResult:
        if not self._available or frame is None or frame.size == 0:
            return DetectionResult(
                frame_index=frame_index,
                detections=[],
                inference_time_ms=0.0,
                model_name=self.model_name,
                hazard_count=0,
                person_count=0,
                vehicle_count=0,
            )

        t0 = time.perf_counter()
        results = self._model(frame, conf=self.confidence_threshold, device=self._device, verbose=False)
        inference_ms = (time.perf_counter() - t0) * 1000.0

        detections: list[Detection] = []
        for r in results:
            boxes = r.boxes
            if boxes is None:
                continue
            for i in range(len(boxes)):
                cls_id = int(boxes.cls[i].item())
                conf = float(boxes.conf[i].item())
                x1, y1, x2, y2 = [int(v) for v in boxes.xyxy[i].tolist()]
                class_name = r.names.get(cls_id, f"class_{cls_id}")
                is_hazard = cls_id in HAZARD_CLASSES
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                area = (x2 - x1) * (y2 - y1)
                detections.append(
                    Detection(
                        class_id=cls_id,
                        class_name=class_name,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        center=(cx, cy),
                        area=area,
                        is_hazard=is_hazard,
                    )
                )

        hazards = [d for d in detections if d.is_hazard]
        persons = [d for d in detections if d.class_name == "person"]
        vehicles = [d for d in detections if d.class_name in self.VEHICLE_CLASSES]

        return DetectionResult(
            frame_index=frame_index,
            detections=detections,
            inference_time_ms=inference_ms,
            model_name=self.model_name,
            hazard_count=len(hazards),
            person_count=len(persons),
            vehicle_count=len(vehicles),
        )

    def annotate(self, frame: np.ndarray, det_result: DetectionResult) -> np.ndarray:
        annotated = frame.copy()
        for d in det_result.detections:
            color = (0, 0, 255) if d.class_name == "person" else (0, 165, 255) if d.is_hazard else (0, 255, 0)
            x1, y1, x2, y2 = d.bbox
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            label = f"{d.class_name} {d.confidence:.0%}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
            cv2.putText(annotated, label, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        return annotated
