"""Frame-detection to discrete-event conversion for M4."""

from .config import EventConfig, load_event_config
from .models import Detection, EventType, FrameUpdate, ObjectState, VisionEvent
from .tracker import ObjectStateManager

__all__ = [
    "Detection",
    "EventConfig",
    "EventType",
    "FrameUpdate",
    "ObjectState",
    "ObjectStateManager",
    "VisionEvent",
    "load_event_config",
]
