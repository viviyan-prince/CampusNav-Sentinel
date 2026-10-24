"""Generate a synthetic test video simulating a campus shuttle view.

Creates scenes with pedestrians (colored rectangles), road markings,
and varying conditions to test the full pipeline without real footage.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import cv2
import numpy as np


def draw_road(frame: np.ndarray) -> None:
    h, w = frame.shape[:2]
    road_top = int(h * 0.35)
    pts = np.array([[0, h], [w // 4, road_top], [3 * w // 4, road_top], [w, h]], np.int32)
    cv2.fillPoly(frame, [pts], (80, 80, 80))
    for i in range(5):
        y = road_top + (h - road_top) * i // 5
        left = int(w * 0.5 - (w * 0.1 * (i + 1)))
        right = int(w * 0.5 + (w * 0.1 * (i + 1)))
        cv2.line(frame, (left + 20, y), (left + 50, y), (200, 200, 200), 2)
        cv2.line(frame, (right - 50, y), (right - 20, y), (200, 200, 200), 2)


def draw_pedestrian(frame: np.ndarray, x: int, y: int, size: int = 30) -> None:
    head_r = size // 4
    cv2.circle(frame, (x, y - size + head_r), head_r, (180, 140, 100), -1)
    cv2.rectangle(frame, (x - size // 4, y - size + 2 * head_r),
                  (x + size // 4, y - size // 3), (50, 50, 200), -1)
    cv2.line(frame, (x - size // 6, y - size // 3), (x - size // 6, y), (40, 40, 40), 2)
    cv2.line(frame, (x + size // 6, y - size // 3), (x + size // 6, y), (40, 40, 40), 2)


def draw_vehicle(frame: np.ndarray, x: int, y: int, w: int = 80, h: int = 40) -> None:
    cv2.rectangle(frame, (x, y), (x + w, y + h), (200, 60, 60), -1)
    cv2.rectangle(frame, (x + w // 6, y - h // 3), (x + 5 * w // 6, y), (150, 150, 200), -1)
    cv2.circle(frame, (x + w // 5, y + h), h // 5, (30, 30, 30), -1)
    cv2.circle(frame, (x + 4 * w // 5, y + h), h // 5, (30, 30, 30), -1)


def generate(output_path: str, width: int = 640, height: int = 480,
             fps: int = 15, duration_s: int = 10, seed: int = 42) -> str:
    random.seed(seed)
    np.random.seed(seed)
    total_frames = fps * duration_s

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    ped_x = width // 2 + 100
    ped_y = int(height * 0.7)
    ped_dx = -2

    for fi in range(total_frames):
        frame = np.full((height, width, 3), (180, 210, 160), dtype=np.uint8)

        sky_h = int(height * 0.35)
        frame[:sky_h] = (210, 180, 140)

        draw_road(frame)

        if fi < total_frames * 0.2:
            pass
        elif fi < total_frames * 0.7:
            ped_x += ped_dx
            ped_size = 30 + (fi - int(total_frames * 0.2)) // 4
            ped_size = min(ped_size, 60)
            draw_pedestrian(frame, ped_x, ped_y, ped_size)

            if fi > total_frames * 0.5:
                draw_pedestrian(frame, ped_x + 50, ped_y - 10, ped_size - 10)
        else:
            ped_x += abs(ped_dx) * 2
            if ped_x < width + 100:
                draw_pedestrian(frame, ped_x, ped_y, 40)

        if 60 < fi < 100:
            vx = width - 120 - (fi - 60) * 3
            draw_vehicle(frame, vx, int(height * 0.55))

        if fi % 30 < 2:
            noise = np.random.randint(0, 30, frame.shape, dtype=np.uint8)
            frame = cv2.add(frame, noise)

        if total_frames * 0.8 < fi < total_frames * 0.85:
            frame = (frame * 0.3).astype(np.uint8)

        cv2.putText(frame, f"Frame {fi}/{total_frames}", (10, height - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        writer.write(frame)

    writer.release()
    print(f"Generated {total_frames} frames -> {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/sample/test_campus.mp4")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=15)
    parser.add_argument("--duration", type=int, default=10)
    args = parser.parse_args()
    generate(args.output, args.width, args.height, args.fps, args.duration)
