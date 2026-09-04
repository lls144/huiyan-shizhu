"""Configurable OpenCV shape recognition shared by M2 and M3."""

from .config import VisionConfig, load_vision_config
from .pipeline import ImageAnalysis, MultiImageAnalysis, analyze_image, analyze_multiple_objects

__all__ = [
    "ImageAnalysis",
    "MultiImageAnalysis",
    "VisionConfig",
    "analyze_image",
    "analyze_multiple_objects",
    "load_vision_config",
]
