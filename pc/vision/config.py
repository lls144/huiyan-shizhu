"""Load and validate shared M2/M3 vision parameters from one JSON file."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VisionConfig:
    """Configuration for single- and multi-object contour pipelines."""

    roi_left: float
    roi_top: float
    roi_right: float
    roi_bottom: float
    gaussian_kernel_size: int
    morphology_kernel_size: int
    morphology_open_iterations: int
    canny_low_threshold: int
    canny_high_threshold: int
    min_area_ratio: float
    max_area_ratio: float
    min_solidity: float
    border_margin_pixels: int
    approx_epsilon_ratio: float
    rectangle_max_angle_deviation_degrees: float
    rectangle_min_fill_ratio: float
    circle_min_vertices: int
    circle_min_circularity: float
    circle_min_aspect_ratio: float
    triangle_confidence_good_circularity: float
    triangle_confidence_max_circularity: float
    rectangle_confidence_good_angle_deviation_degrees: float
    rectangle_confidence_good_fill_ratio: float
    circle_confidence_good_vertices: int
    circle_confidence_good_circularity: float
    circle_confidence_good_aspect_ratio: float
    confidence_good_solidity: float
    confidence_good_area_clearance_ratio: float
    confidence_topology_weight: float
    confidence_geometry_weight: float
    confidence_quality_weight: float
    auto_hsv_min_value: int = 140
    auto_hsv_max_saturation: int = 100
    auto_morphology_kernel_size: int = 11
    auto_morphology_close_iterations: int = 2
    auto_morphology_open_iterations: int = 1
    auto_min_area_ratio: float = 0.12
    auto_max_area_ratio: float = 0.85
    auto_preferred_area_ratio: float = 0.35
    auto_min_rectangularity: float = 0.70
    auto_max_center_distance_ratio: float = 0.50
    auto_min_bright_fraction: float = 0.60
    auto_approx_epsilon_ratio: float = 0.03
    auto_inner_margin_ratio: float = 0.04
    auto_min_score: float = 0.45
    auto_score_area_weight: float = 0.20
    auto_score_rectangularity_weight: float = 0.30
    auto_score_center_weight: float = 0.25
    auto_score_brightness_weight: float = 0.25
    manual_min_width_pixels: int = 80
    manual_min_height_pixels: int = 80
    stability_window_size: int = 5
    stability_min_votes: int = 3
    fps_smoothing_window: int = 30
    live_max_consecutive_read_failures: int = 30
    live_preview_width: int = 1280
    live_preview_height: int = 720
    preprocess_mode: str = "otsu"
    comparison_preprocess_mode: str = "clahe_otsu"
    clahe_clip_limit: float = 2.0
    clahe_tile_grid_size: int = 8

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "VisionConfig":
        config = cls(**values)
        config.validate()
        return config

    def validate(self) -> None:
        if not (0 <= self.roi_left < self.roi_right <= 1):
            raise ValueError("ROI horizontal bounds must satisfy 0 <= left < right <= 1")
        if not (0 <= self.roi_top < self.roi_bottom <= 1):
            raise ValueError("ROI vertical bounds must satisfy 0 <= top < bottom <= 1")
        for name in ("gaussian_kernel_size", "morphology_kernel_size"):
            value = getattr(self, name)
            if value <= 0 or value % 2 == 0:
                raise ValueError(f"{name} must be a positive odd integer")
        if self.morphology_open_iterations < 0:
            raise ValueError("morphology_open_iterations must be non-negative")
        if not 0 <= self.canny_low_threshold < self.canny_high_threshold <= 255:
            raise ValueError("Canny thresholds must satisfy 0 <= low < high <= 255")
        if not 0 < self.min_area_ratio < self.max_area_ratio < 1:
            raise ValueError("area ratios must satisfy 0 < min < max < 1")
        if not 0 < self.min_solidity <= 1:
            raise ValueError("min_solidity must be in (0, 1]")
        if self.border_margin_pixels < 0:
            raise ValueError("border_margin_pixels must be non-negative")
        if not 0 < self.approx_epsilon_ratio < 1:
            raise ValueError("approx_epsilon_ratio must be in (0, 1)")
        if not 0 < self.rectangle_max_angle_deviation_degrees < 90:
            raise ValueError("rectangle angle tolerance must be in (0, 90)")
        if not 0 < self.rectangle_min_fill_ratio <= 1:
            raise ValueError("rectangle_min_fill_ratio must be in (0, 1]")
        if self.circle_min_vertices < 5:
            raise ValueError("circle_min_vertices must be at least 5")
        for name in (
            "circle_min_circularity",
            "circle_min_aspect_ratio",
            "triangle_confidence_good_circularity",
            "triangle_confidence_max_circularity",
            "rectangle_confidence_good_fill_ratio",
            "circle_confidence_good_circularity",
            "circle_confidence_good_aspect_ratio",
            "confidence_good_solidity",
        ):
            value = getattr(self, name)
            if not 0 < value <= 1:
                raise ValueError(f"{name} must be in (0, 1]")
        if self.triangle_confidence_good_circularity >= self.triangle_confidence_max_circularity:
            raise ValueError("triangle confidence good circularity must be below its maximum")
        if self.rectangle_confidence_good_angle_deviation_degrees < 0:
            raise ValueError("rectangle confidence good angle deviation must be non-negative")
        if (
            self.rectangle_confidence_good_angle_deviation_degrees
            >= self.rectangle_max_angle_deviation_degrees
        ):
            raise ValueError("rectangle confidence good angle must be below the decision tolerance")
        if self.rectangle_confidence_good_fill_ratio < self.rectangle_min_fill_ratio:
            raise ValueError("rectangle confidence good fill must meet the decision threshold")
        if self.circle_confidence_good_vertices < self.circle_min_vertices:
            raise ValueError("circle confidence good vertices must meet the decision threshold")
        if self.circle_confidence_good_circularity < self.circle_min_circularity:
            raise ValueError("circle confidence good circularity must meet the decision threshold")
        if self.circle_confidence_good_aspect_ratio < self.circle_min_aspect_ratio:
            raise ValueError("circle confidence good aspect ratio must meet the decision threshold")
        if self.confidence_good_solidity < self.min_solidity:
            raise ValueError("confidence_good_solidity must meet min_solidity")
        if self.confidence_good_area_clearance_ratio <= 0:
            raise ValueError("confidence_good_area_clearance_ratio must be positive")
        weights = (
            self.confidence_topology_weight,
            self.confidence_geometry_weight,
            self.confidence_quality_weight,
        )
        if any(weight < 0 for weight in weights) or abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError("confidence weights must be non-negative and sum to 1")
        if not 0 <= self.auto_hsv_min_value <= 255:
            raise ValueError("auto_hsv_min_value must be in [0, 255]")
        if not 0 <= self.auto_hsv_max_saturation <= 255:
            raise ValueError("auto_hsv_max_saturation must be in [0, 255]")
        if self.auto_morphology_kernel_size <= 0 or self.auto_morphology_kernel_size % 2 == 0:
            raise ValueError("auto_morphology_kernel_size must be a positive odd integer")
        if self.auto_morphology_close_iterations < 0 or self.auto_morphology_open_iterations < 0:
            raise ValueError("auto morphology iterations must be non-negative")
        if not 0 < self.auto_min_area_ratio < self.auto_max_area_ratio <= 1:
            raise ValueError("auto area ratios must satisfy 0 < min < max <= 1")
        if not self.auto_min_area_ratio <= self.auto_preferred_area_ratio <= self.auto_max_area_ratio:
            raise ValueError("auto_preferred_area_ratio must be inside the auto area range")
        for name in (
            "auto_min_rectangularity",
            "auto_max_center_distance_ratio",
            "auto_min_bright_fraction",
            "auto_approx_epsilon_ratio",
            "auto_min_score",
        ):
            value = getattr(self, name)
            if not 0 < value <= 1:
                raise ValueError(f"{name} must be in (0, 1]")
        if not 0 <= self.auto_inner_margin_ratio < 0.5:
            raise ValueError("auto_inner_margin_ratio must be in [0, 0.5)")
        auto_weights = (
            self.auto_score_area_weight,
            self.auto_score_rectangularity_weight,
            self.auto_score_center_weight,
            self.auto_score_brightness_weight,
        )
        if any(weight < 0 for weight in auto_weights) or abs(sum(auto_weights) - 1.0) > 1e-9:
            raise ValueError("auto ROI score weights must be non-negative and sum to 1")
        if self.manual_min_width_pixels <= 0 or self.manual_min_height_pixels <= 0:
            raise ValueError("manual ROI minimum dimensions must be positive")
        if self.stability_window_size <= 0:
            raise ValueError("stability_window_size must be positive")
        if not 0 < self.stability_min_votes <= self.stability_window_size:
            raise ValueError("stability_min_votes must be in (0, stability_window_size]")
        if self.fps_smoothing_window <= 1:
            raise ValueError("fps_smoothing_window must be greater than one")
        if self.live_max_consecutive_read_failures <= 0:
            raise ValueError("live_max_consecutive_read_failures must be positive")
        if self.live_preview_width <= 0 or self.live_preview_height <= 0:
            raise ValueError("live preview dimensions must be positive")
        supported_preprocess_modes = {"otsu", "clahe_otsu"}
        if self.preprocess_mode not in supported_preprocess_modes:
            raise ValueError(f"unsupported preprocess_mode: {self.preprocess_mode}")
        if self.comparison_preprocess_mode not in supported_preprocess_modes:
            raise ValueError(
                f"unsupported comparison_preprocess_mode: {self.comparison_preprocess_mode}"
            )
        if self.preprocess_mode == self.comparison_preprocess_mode:
            raise ValueError("preprocess comparison modes must be different")
        if self.clahe_clip_limit <= 0:
            raise ValueError("clahe_clip_limit must be positive")
        if self.clahe_tile_grid_size <= 0:
            raise ValueError("clahe_tile_grid_size must be positive")


def load_vision_config(path: str | Path) -> VisionConfig:
    """Read UTF-8 JSON settings and return a validated configuration."""

    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as stream:
        values = json.load(stream)
    if not isinstance(values, dict):
        raise ValueError("vision config root must be a JSON object")
    return VisionConfig.from_dict(values)
