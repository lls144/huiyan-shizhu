import pytest

from pc.vision.config import VisionConfig


def valid_values() -> dict[str, object]:
    return {
        "roi_left": 0.24,
        "roi_top": 0.08,
        "roi_right": 0.76,
        "roi_bottom": 0.75,
        "gaussian_kernel_size": 5,
        "morphology_kernel_size": 3,
        "morphology_open_iterations": 1,
        "canny_low_threshold": 50,
        "canny_high_threshold": 150,
        "min_area_ratio": 0.02,
        "max_area_ratio": 0.25,
        "min_solidity": 0.9,
        "border_margin_pixels": 2,
        "approx_epsilon_ratio": 0.02,
        "rectangle_max_angle_deviation_degrees": 25.0,
        "rectangle_min_fill_ratio": 0.8,
        "circle_min_vertices": 6,
        "circle_min_circularity": 0.78,
        "circle_min_aspect_ratio": 0.8,
        "triangle_confidence_good_circularity": 0.62,
        "triangle_confidence_max_circularity": 0.72,
        "rectangle_confidence_good_angle_deviation_degrees": 5.0,
        "rectangle_confidence_good_fill_ratio": 0.95,
        "circle_confidence_good_vertices": 8,
        "circle_confidence_good_circularity": 0.92,
        "circle_confidence_good_aspect_ratio": 0.95,
        "confidence_good_solidity": 0.98,
        "confidence_good_area_clearance_ratio": 0.03,
        "confidence_topology_weight": 0.5,
        "confidence_geometry_weight": 0.3,
        "confidence_quality_weight": 0.2,
    }


def test_valid_vision_config_is_accepted() -> None:
    config = VisionConfig.from_dict(valid_values())
    assert config.roi_right == 0.76


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("roi_right", 0.1),
        ("gaussian_kernel_size", 4),
        ("canny_high_threshold", 40),
        ("min_area_ratio", 0.3),
        ("min_solidity", 1.1),
        ("approx_epsilon_ratio", 0),
        ("circle_min_vertices", 4),
        ("circle_min_circularity", 0),
        ("confidence_topology_weight", 0.6),
        ("auto_morphology_kernel_size", 4),
        ("auto_min_area_ratio", 0.9),
        ("auto_score_area_weight", 0.3),
        ("auto_inner_margin_ratio", 0.5),
        ("stability_min_votes", 6),
        ("fps_smoothing_window", 1),
        ("live_max_consecutive_read_failures", 0),
        ("live_preview_width", 0),
        ("preprocess_mode", "adaptive"),
        ("comparison_preprocess_mode", "otsu"),
        ("clahe_clip_limit", 0),
        ("clahe_tile_grid_size", 0),
    ],
)
def test_invalid_vision_values_are_rejected(field: str, value: object) -> None:
    values = valid_values()
    values[field] = value
    with pytest.raises(ValueError):
        VisionConfig.from_dict(values)
