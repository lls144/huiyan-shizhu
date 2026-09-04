"""Startup-only ROI calibration for M2 live recognition."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal

import cv2
import numpy as np
from numpy.typing import NDArray

from .config import VisionConfig

Image = NDArray[np.uint8]

RoiMode = Literal["auto", "manual", "fixed_normalized"]
StatusCallback = Callable[[str], None]
ManualSelector = Callable[[Image], tuple[int, int, int, int] | None]


@dataclass(frozen=True)
class NormalizedRoi:
    """Resolution-independent axis-aligned ROI bounds."""

    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        if not (0 <= self.left < self.right <= 1):
            raise ValueError("ROI horizontal bounds must satisfy 0 <= left < right <= 1")
        if not (0 <= self.top < self.bottom <= 1):
            raise ValueError("ROI vertical bounds must satisfy 0 <= top < bottom <= 1")

    @classmethod
    def from_dict(cls, values: dict[str, object]) -> "NormalizedRoi":
        return cls(
            left=float(values["left"]),
            top=float(values["top"]),
            right=float(values["right"]),
            bottom=float(values["bottom"]),
        )

    @classmethod
    def from_pixel_rect(
        cls,
        x: int,
        y: int,
        width: int,
        height: int,
        frame_shape: tuple[int, ...],
    ) -> "NormalizedRoi":
        frame_height, frame_width = frame_shape[:2]
        if frame_width <= 0 or frame_height <= 0:
            raise ValueError("frame dimensions must be positive")
        if width <= 0 or height <= 0:
            raise ValueError("ROI dimensions must be positive")
        if x < 0 or y < 0 or x + width > frame_width or y + height > frame_height:
            raise ValueError("pixel ROI must stay inside the frame")
        return cls(x / frame_width, y / frame_height, (x + width) / frame_width, (y + height) / frame_height)

    def to_pixels(self, frame_shape: tuple[int, ...]) -> tuple[int, int, int, int]:
        frame_height, frame_width = frame_shape[:2]
        if frame_width <= 0 or frame_height <= 0:
            raise ValueError("frame dimensions must be positive")
        left = max(0, min(frame_width - 1, round(self.left * frame_width)))
        top = max(0, min(frame_height - 1, round(self.top * frame_height)))
        right = max(left + 1, min(frame_width, round(self.right * frame_width)))
        bottom = max(top + 1, min(frame_height, round(self.bottom * frame_height)))
        return left, top, right, bottom

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class AutoRoiResult:
    success: bool
    roi: NormalizedRoi | None
    score: float | None
    reason: str
    candidates_examined: int


@dataclass(frozen=True)
class CalibrationResult:
    requested_mode: RoiMode
    selected_mode: RoiMode
    source: str
    roi: NormalizedRoi
    pixel_bounds: tuple[int, int, int, int]
    fallback_messages: tuple[str, ...]
    auto_score: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_mode": self.requested_mode,
            "selected_mode": self.selected_mode,
            "source": self.source,
            "normalized_roi": self.roi.to_dict(),
            "pixel_roi": list(self.pixel_bounds),
            "fallback_messages": list(self.fallback_messages),
            "auto_score": self.auto_score,
        }


def fixed_roi(config: VisionConfig) -> NormalizedRoi:
    return NormalizedRoi(config.roi_left, config.roi_top, config.roi_right, config.roi_bottom)


def _score_between(value: float, minimum: float, preferred: float, maximum: float) -> float:
    if value <= preferred:
        denominator = preferred - minimum
        return 1.0 if denominator == 0 else max(0.0, min(1.0, (value - minimum) / denominator))
    denominator = maximum - preferred
    return 1.0 if denominator == 0 else max(0.0, min(1.0, (maximum - value) / denominator))


def detect_auto_roi(frame: Image, config: VisionConfig) -> AutoRoiResult:
    """Locate a central bright, low-saturation convex quadrilateral once."""

    if frame is None or frame.size == 0 or frame.ndim != 3 or frame.shape[2] != 3:
        return AutoRoiResult(False, None, None, "frame is not a non-empty BGR image", 0)
    frame_height, frame_width = frame.shape[:2]
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower = np.array([0, 0, config.auto_hsv_min_value], dtype=np.uint8)
    upper = np.array([179, config.auto_hsv_max_saturation, 255], dtype=np.uint8)
    bright_mask = cv2.inRange(hsv, lower, upper)
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (config.auto_morphology_kernel_size, config.auto_morphology_kernel_size),
    )
    if config.auto_morphology_close_iterations:
        bright_mask = cv2.morphologyEx(
            bright_mask,
            cv2.MORPH_CLOSE,
            kernel,
            iterations=config.auto_morphology_close_iterations,
        )
    if config.auto_morphology_open_iterations:
        bright_mask = cv2.morphologyEx(
            bright_mask,
            cv2.MORPH_OPEN,
            kernel,
            iterations=config.auto_morphology_open_iterations,
        )
    contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    frame_area = float(frame_width * frame_height)
    candidates: list[tuple[float, NormalizedRoi]] = []
    rejected: dict[str, int] = {}

    def reject(reason: str) -> None:
        rejected[reason] = rejected.get(reason, 0) + 1

    for contour in contours:
        area = float(cv2.contourArea(contour))
        area_ratio = area / frame_area if frame_area else 0.0
        if not config.auto_min_area_ratio <= area_ratio <= config.auto_max_area_ratio:
            reject("area")
            continue
        perimeter = float(cv2.arcLength(contour, True))
        approximation = cv2.approxPolyDP(contour, config.auto_approx_epsilon_ratio * perimeter, True)
        if len(approximation) != 4 or not cv2.isContourConvex(approximation):
            reject("not_convex_quadrilateral")
            continue
        rect_width, rect_height = cv2.minAreaRect(contour)[1]
        rect_area = float(rect_width * rect_height)
        rectangularity = area / rect_area if rect_area else 0.0
        if rectangularity < config.auto_min_rectangularity:
            reject("rectangularity")
            continue
        moments = cv2.moments(contour)
        if moments["m00"] == 0:
            reject("zero_moment")
            continue
        center_x = moments["m10"] / moments["m00"] / frame_width
        center_y = moments["m01"] / moments["m00"] / frame_height
        center_distance = math.hypot(center_x - 0.5, center_y - 0.5) / math.hypot(0.5, 0.5)
        if center_distance > config.auto_max_center_distance_ratio:
            reject("off_center")
            continue
        contour_mask = np.zeros_like(bright_mask)
        cv2.drawContours(contour_mask, [contour], -1, 255, -1)
        contour_pixels = cv2.countNonZero(contour_mask)
        bright_pixels = cv2.countNonZero(cv2.bitwise_and(bright_mask, contour_mask))
        bright_fraction = bright_pixels / contour_pixels if contour_pixels else 0.0
        if bright_fraction < config.auto_min_bright_fraction:
            reject("brightness")
            continue
        x, y, width, height = cv2.boundingRect(contour)
        margin_x = round(width * config.auto_inner_margin_ratio)
        margin_y = round(height * config.auto_inner_margin_ratio)
        inner_x = x + margin_x
        inner_y = y + margin_y
        inner_width = width - 2 * margin_x
        inner_height = height - 2 * margin_y
        if inner_width <= 0 or inner_height <= 0:
            reject("inner_roi_too_small")
            continue
        roi = NormalizedRoi.from_pixel_rect(inner_x, inner_y, inner_width, inner_height, frame.shape)
        area_score = _score_between(
            area_ratio,
            config.auto_min_area_ratio,
            config.auto_preferred_area_ratio,
            config.auto_max_area_ratio,
        )
        rectangularity_score = min(
            1.0,
            (rectangularity - config.auto_min_rectangularity)
            / max(1e-9, 1.0 - config.auto_min_rectangularity),
        )
        center_score = max(0.0, 1.0 - center_distance / config.auto_max_center_distance_ratio)
        brightness_score = min(
            1.0,
            (bright_fraction - config.auto_min_bright_fraction)
            / max(1e-9, 1.0 - config.auto_min_bright_fraction),
        )
        score = (
            area_score * config.auto_score_area_weight
            + rectangularity_score * config.auto_score_rectangularity_weight
            + center_score * config.auto_score_center_weight
            + brightness_score * config.auto_score_brightness_weight
        )
        candidates.append((score, roi))

    if not candidates:
        details = ", ".join(f"{key}={value}" for key, value in sorted(rejected.items())) or "no contours"
        return AutoRoiResult(
            False,
            None,
            None,
            f"auto ROI found no acceptable central white quadrilateral ({details})",
            len(contours),
        )
    score, roi = max(candidates, key=lambda item: item[0])
    if score < config.auto_min_score:
        return AutoRoiResult(
            False,
            None,
            score,
            f"best auto ROI score {score:.3f} is below minimum {config.auto_min_score:.3f}",
            len(contours),
        )
    return AutoRoiResult(
        True,
        roi,
        score,
        f"auto ROI accepted with score {score:.3f}",
        len(contours),
    )


def select_manual_roi(frame: Image, config: VisionConfig) -> tuple[int, int, int, int] | None:
    """Use OpenCV's mouse rectangle selector and return x/y/width/height."""

    window_name = "M2 ROI calibration - drag ROI, ENTER/SPACE accept, C cancel"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, config.live_preview_width, config.live_preview_height)
    try:
        rectangle = cv2.selectROI(window_name, frame, showCrosshair=True, fromCenter=False)
    finally:
        cv2.destroyWindow(window_name)
    x, y, width, height = (int(value) for value in rectangle)
    if width < config.manual_min_width_pixels or height < config.manual_min_height_pixels:
        return None
    return x, y, width, height


def calibrate_roi(
    frame: Image,
    config: VisionConfig,
    requested_mode: RoiMode,
    manual_selector: ManualSelector,
    status_callback: StatusCallback | None = None,
) -> CalibrationResult:
    """Calibrate once with explicit auto -> manual -> fixed fallback behavior."""

    if requested_mode not in {"auto", "manual", "fixed_normalized"}:
        raise ValueError(f"unsupported ROI mode: {requested_mode}")
    announce = status_callback or (lambda _: None)
    messages: list[str] = []
    if requested_mode == "auto":
        auto = detect_auto_roi(frame, config)
        announce(auto.reason)
        if auto.success and auto.roi is not None:
            return CalibrationResult(
                requested_mode,
                "auto",
                "detected",
                auto.roi,
                auto.roi.to_pixels(frame.shape),
                tuple(messages),
                auto.score,
            )
        messages.append(auto.reason)
        announce("auto ROI failed; opening manual ROI selection")

    if requested_mode in {"auto", "manual"}:
        rectangle = manual_selector(frame)
        if rectangle is not None:
            x, y, width, height = rectangle
            if width >= config.manual_min_width_pixels and height >= config.manual_min_height_pixels:
                roi = NormalizedRoi.from_pixel_rect(x, y, width, height, frame.shape)
                announce("manual ROI accepted and locked for this run")
                return CalibrationResult(
                    requested_mode,
                    "manual",
                    "selected",
                    roi,
                    roi.to_pixels(frame.shape),
                    tuple(messages),
                )
        message = "manual ROI was cancelled or smaller than the configured minimum"
        messages.append(message)
        announce(f"{message}; using fixed_normalized fallback")

    roi = fixed_roi(config)
    return CalibrationResult(
        requested_mode,
        "fixed_normalized",
        "configured_fallback" if requested_mode != "fixed_normalized" else "configured",
        roi,
        roi.to_pixels(frame.shape),
        tuple(messages),
    )


def save_runtime_calibration(
    calibration: CalibrationResult,
    frame_shape: tuple[int, ...],
    path: Path,
) -> None:
    """Persist normalized runtime calibration without changing vision.json."""

    frame_height, frame_width = frame_shape[:2]
    payload = {
        "schema_version": 1,
        "saved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "frame_resolution": {"width": frame_width, "height": frame_height},
        "calibration": calibration.to_dict(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_runtime_calibration(path: Path, frame_shape: tuple[int, ...]) -> CalibrationResult:
    """Restore an explicitly requested saved normalized calibration."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("calibration"), dict):
        raise ValueError("unsupported runtime calibration schema")
    values = payload["calibration"]
    roi = NormalizedRoi.from_dict(values["normalized_roi"])
    selected_mode = str(values["selected_mode"])
    requested_mode = str(values["requested_mode"])
    if selected_mode not in {"auto", "manual", "fixed_normalized"}:
        raise ValueError("saved calibration has an invalid selected_mode")
    if requested_mode not in {"auto", "manual", "fixed_normalized"}:
        raise ValueError("saved calibration has an invalid requested_mode")
    return CalibrationResult(
        requested_mode=requested_mode,  # type: ignore[arg-type]
        selected_mode=selected_mode,  # type: ignore[arg-type]
        source="restored",
        roi=roi,
        pixel_bounds=roi.to_pixels(frame_shape),
        fallback_messages=tuple(str(item) for item in values.get("fallback_messages", [])),
        auto_score=float(values["auto_score"]) if values.get("auto_score") is not None else None,
    )
