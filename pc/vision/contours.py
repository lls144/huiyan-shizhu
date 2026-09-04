"""Contour feature extraction and validity filtering."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import cv2
import numpy as np
from numpy.typing import NDArray

from .config import VisionConfig

Contour = NDArray[np.int32]


@dataclass(frozen=True)
class ContourFeatures:
    """Explainable geometric measurements for one external contour."""

    area: float
    area_ratio: float
    perimeter: float
    vertices: int
    solidity: float
    circularity: float
    bounding_box: tuple[int, int, int, int]
    aspect_ratio: float
    min_rect_fill_ratio: float
    max_right_angle_deviation_degrees: float | None
    is_convex: bool
    touches_border: bool

    def to_dict(self) -> dict[str, object]:
        values = asdict(self)
        values["bounding_box"] = list(self.bounding_box)
        return values


@dataclass(frozen=True)
class ContourCandidate:
    """A contour paired with its measurements and filter outcome."""

    contour: Contour
    approximation: Contour
    features: ContourFeatures
    passed_filter: bool
    rejection_reasons: tuple[str, ...]


def _max_right_angle_deviation(approximation: Contour) -> float | None:
    if len(approximation) != 4:
        return None
    points = approximation.reshape(-1, 2).astype(np.float64)
    deviations: list[float] = []
    for index in range(4):
        previous = points[(index - 1) % 4] - points[index]
        following = points[(index + 1) % 4] - points[index]
        denominator = float(np.linalg.norm(previous) * np.linalg.norm(following))
        if denominator == 0:
            return None
        cosine = float(np.clip(np.dot(previous, following) / denominator, -1.0, 1.0))
        angle = math.degrees(math.acos(cosine))
        deviations.append(abs(angle - 90.0))
    return max(deviations)


def extract_contour_features(
    contour: Contour,
    roi_shape: tuple[int, ...],
    config: VisionConfig,
) -> tuple[ContourFeatures, Contour]:
    """Measure one contour using only configuration-controlled thresholds."""

    roi_height, roi_width = roi_shape[:2]
    roi_area = float(roi_height * roi_width)
    area = float(cv2.contourArea(contour))
    perimeter = float(cv2.arcLength(contour, True))
    approximation = cv2.approxPolyDP(
        contour,
        config.approx_epsilon_ratio * perimeter,
        True,
    )
    hull = cv2.convexHull(contour)
    hull_area = float(cv2.contourArea(hull))
    solidity = area / hull_area if hull_area else 0.0
    circularity = 4.0 * math.pi * area / (perimeter * perimeter) if perimeter else 0.0
    x, y, width, height = cv2.boundingRect(contour)
    aspect_ratio = min(width, height) / max(width, height) if max(width, height) else 0.0
    minimum_rectangle = cv2.minAreaRect(contour)
    rect_width, rect_height = minimum_rectangle[1]
    rect_area = float(rect_width * rect_height)
    min_rect_fill_ratio = area / rect_area if rect_area else 0.0
    margin = config.border_margin_pixels
    touches_border = (
        x <= margin
        or y <= margin
        or x + width >= roi_width - margin
        or y + height >= roi_height - margin
    )
    features = ContourFeatures(
        area=area,
        area_ratio=area / roi_area if roi_area else 0.0,
        perimeter=perimeter,
        vertices=len(approximation),
        solidity=solidity,
        circularity=circularity,
        bounding_box=(x, y, width, height),
        aspect_ratio=aspect_ratio,
        min_rect_fill_ratio=min_rect_fill_ratio,
        max_right_angle_deviation_degrees=_max_right_angle_deviation(approximation),
        is_convex=bool(cv2.isContourConvex(approximation)),
        touches_border=touches_border,
    )
    return features, approximation


def find_contour_candidates(binary: NDArray[np.uint8], config: VisionConfig) -> list[ContourCandidate]:
    """Find external contours and record every filter decision."""

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[ContourCandidate] = []
    for contour in contours:
        features, approximation = extract_contour_features(contour, binary.shape, config)
        reasons: list[str] = []
        if features.area_ratio < config.min_area_ratio:
            reasons.append("area_ratio_below_minimum")
        if features.area_ratio > config.max_area_ratio:
            reasons.append("area_ratio_above_maximum")
        if features.solidity < config.min_solidity:
            reasons.append("solidity_below_minimum")
        if features.touches_border:
            reasons.append("touches_roi_border")
        candidates.append(
            ContourCandidate(
                contour=contour,
                approximation=approximation,
                features=features,
                passed_filter=not reasons,
                rejection_reasons=tuple(reasons),
            )
        )
    return sorted(candidates, key=lambda candidate: candidate.features.area, reverse=True)
