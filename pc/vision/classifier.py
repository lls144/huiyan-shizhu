"""Explainable shape rules and non-probabilistic geometric confidence."""

from __future__ import annotations

from dataclasses import dataclass

from .config import VisionConfig
from .contours import ContourFeatures


@dataclass(frozen=True)
class Classification:
    """A rule result; confidence is rule conformity, never a probability."""

    label: str
    confidence: float
    topology_score: float
    geometry_score: float
    quality_score: float


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _higher_is_better(value: float, threshold: float, good: float) -> float:
    if good <= threshold:
        return 1.0 if value >= threshold else 0.0
    return _clamp((value - threshold) / (good - threshold))


def _lower_is_better(value: float, threshold: float, good: float) -> float:
    if good >= threshold:
        return 1.0 if value <= threshold else 0.0
    return _clamp((threshold - value) / (threshold - good))


def _quality_score(features: ContourFeatures, config: VisionConfig) -> float:
    solidity = _higher_is_better(
        features.solidity,
        config.min_solidity,
        config.confidence_good_solidity,
    )
    lower_clearance = features.area_ratio - config.min_area_ratio
    upper_clearance = config.max_area_ratio - features.area_ratio
    area = _clamp(
        min(lower_clearance, upper_clearance) / config.confidence_good_area_clearance_ratio
    )
    return (solidity + area) / 2.0


def _weighted_confidence(
    topology: float,
    geometry: float,
    quality: float,
    config: VisionConfig,
) -> float:
    value = (
        topology * config.confidence_topology_weight
        + geometry * config.confidence_geometry_weight
        + quality * config.confidence_quality_weight
    )
    return round(_clamp(value), 6)


def classify_shape(features: ContourFeatures, config: VisionConfig) -> Classification:
    """Classify one already-filtered contour with explicit geometric rules."""

    quality = _quality_score(features, config)

    if features.is_convex and features.vertices == 3:
        topology = 1.0
        geometry = _lower_is_better(
            features.circularity,
            config.triangle_confidence_max_circularity,
            config.triangle_confidence_good_circularity,
        )
        confidence = _weighted_confidence(topology, geometry, quality, config)
        return Classification("triangle", confidence, topology, geometry, quality)

    angle_deviation = features.max_right_angle_deviation_degrees
    if (
        features.is_convex
        and features.vertices == 4
        and angle_deviation is not None
        and angle_deviation <= config.rectangle_max_angle_deviation_degrees
        and features.min_rect_fill_ratio >= config.rectangle_min_fill_ratio
    ):
        topology = 1.0
        angle_score = _lower_is_better(
            angle_deviation,
            config.rectangle_max_angle_deviation_degrees,
            config.rectangle_confidence_good_angle_deviation_degrees,
        )
        fill_score = _higher_is_better(
            features.min_rect_fill_ratio,
            config.rectangle_min_fill_ratio,
            config.rectangle_confidence_good_fill_ratio,
        )
        geometry = (angle_score + fill_score) / 2.0
        confidence = _weighted_confidence(topology, geometry, quality, config)
        return Classification("rectangle", confidence, topology, geometry, quality)

    if (
        features.is_convex
        and features.vertices >= config.circle_min_vertices
        and features.circularity >= config.circle_min_circularity
        and features.aspect_ratio >= config.circle_min_aspect_ratio
    ):
        topology = _higher_is_better(
            float(features.vertices),
            float(config.circle_min_vertices),
            float(config.circle_confidence_good_vertices),
        )
        circularity_score = _higher_is_better(
            features.circularity,
            config.circle_min_circularity,
            config.circle_confidence_good_circularity,
        )
        aspect_score = _higher_is_better(
            features.aspect_ratio,
            config.circle_min_aspect_ratio,
            config.circle_confidence_good_aspect_ratio,
        )
        geometry = (circularity_score + aspect_score) / 2.0
        confidence = _weighted_confidence(topology, geometry, quality, config)
        return Classification("circle", confidence, topology, geometry, quality)

    return Classification("unknown", 0.0, 0.0, 0.0, quality)
