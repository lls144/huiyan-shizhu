"""Configurable OpenCV shape recognition for M2 offline images."""

from .config import VisionConfig, load_vision_config
from .pipeline import ImageAnalysis, analyze_image

__all__ = ["ImageAnalysis", "VisionConfig", "analyze_image", "load_vision_config"]
