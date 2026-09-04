"""ROI extraction and observable M2/M3 preprocessing."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray

from .config import VisionConfig
from .roi import NormalizedRoi

Image = NDArray[np.uint8]


@dataclass(frozen=True)
class PreprocessResult:
    """Every image stage needed for inspection and reporting."""

    roi_bounds: tuple[int, int, int, int]
    roi: Image
    gray: Image
    normalized_gray: Image
    blurred: Image
    binary: Image
    canny: Image
    otsu_threshold: float
    preprocess_mode: str


def normalized_roi_bounds(
    image: Image,
    config: VisionConfig,
    roi: NormalizedRoi | None = None,
) -> tuple[int, int, int, int]:
    """Convert configured normalized ROI bounds to clamped pixel coordinates."""

    if roi is not None:
        return roi.to_pixels(image.shape)
    height, width = image.shape[:2]
    left = max(0, min(width - 1, round(config.roi_left * width)))
    top = max(0, min(height - 1, round(config.roi_top * height)))
    right = max(left + 1, min(width, round(config.roi_right * width)))
    bottom = max(top + 1, min(height, round(config.roi_bottom * height)))
    return left, top, right, bottom


def preprocess_image(
    image: Image,
    config: VisionConfig,
    roi: NormalizedRoi | None = None,
) -> PreprocessResult:
    """Crop, gray, blur, Otsu-threshold, open, and create diagnostic Canny edges."""

    if image is None or image.size == 0:
        raise ValueError("image must be non-empty")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("image must be a BGR image with three channels")

    bounds = normalized_roi_bounds(image, config, roi)
    left, top, right, bottom = bounds
    roi = image[top:bottom, left:right].copy()
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    if config.preprocess_mode == "clahe_otsu":
        clahe = cv2.createCLAHE(
            clipLimit=config.clahe_clip_limit,
            tileGridSize=(config.clahe_tile_grid_size, config.clahe_tile_grid_size),
        )
        normalized_gray = clahe.apply(gray)
    else:
        normalized_gray = gray.copy()
    kernel = (config.gaussian_kernel_size, config.gaussian_kernel_size)
    blurred = cv2.GaussianBlur(normalized_gray, kernel, 0)
    otsu_threshold, binary = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )
    if config.morphology_open_iterations:
        morphology_kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (config.morphology_kernel_size, config.morphology_kernel_size),
        )
        binary = cv2.morphologyEx(
            binary,
            cv2.MORPH_OPEN,
            morphology_kernel,
            iterations=config.morphology_open_iterations,
        )
    canny = cv2.Canny(
        blurred,
        config.canny_low_threshold,
        config.canny_high_threshold,
    )
    return PreprocessResult(
        bounds,
        roi,
        gray,
        normalized_gray,
        blurred,
        binary,
        canny,
        otsu_threshold,
        config.preprocess_mode,
    )
