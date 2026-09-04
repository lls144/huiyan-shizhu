"""Presentation-only overlay for the GUI viewport."""

from __future__ import annotations

import cv2

from pc.events.models import Detection, ObjectState
from pc.vision.pipeline import MultiImageAnalysis
from pc.vision.preprocess import Image

from .theme import OVERLAY


def _display_label(detection: Detection, object_id: int | None) -> str:
    identity = f"#{object_id}  " if object_id is not None else ""
    return f"{identity}{detection.label.upper()}  {detection.confidence * 100:.1f}%"


def _class_color(label: str) -> tuple[int, int, int]:
    return {
        "triangle": OVERLAY.triangle_bgr,
        "rectangle": OVERLAY.rectangle_bgr,
        "circle": OVERLAY.circle_bgr,
    }.get(label, OVERLAY.unknown_bgr)


def _contrasting_text(background_bgr: tuple[int, int, int]) -> tuple[int, int, int]:
    blue, green, red = background_bgr
    luminance = 0.0722 * blue + 0.7152 * green + 0.2126 * red
    return (18, 18, 18) if luminance >= 145 else (250, 250, 250)


def annotated_gui_frame(
    image: Image,
    analysis: MultiImageAnalysis,
    detections: tuple[Detection, ...],
    object_states: tuple[ObjectState, ...],
) -> Image:
    """Draw subdued ROI and compact ID-aware detection labels on a copy."""

    output = image.copy()
    left, top, right, bottom = analysis.preprocessing.roi_bounds
    cv2.rectangle(
        output,
        (left, top),
        (right - 1, bottom - 1),
        OVERLAY.roi_bgr,
        OVERLAY.roi_thickness,
        cv2.LINE_AA,
    )
    state_ids = {
        (state.label, state.bbox): state.object_id
        for state in object_states
        if state.active
    }
    for detection in detections:
        x, y, width, height = detection.bbox
        color = _class_color(detection.label)
        cv2.rectangle(
            output,
            (x, y),
            (x + width - 1, y + height - 1),
            OVERLAY.bbox_outline_bgr,
            OVERLAY.bbox_outline_thickness,
            cv2.LINE_AA,
        )
        cv2.rectangle(
            output,
            (x, y),
            (x + width - 1, y + height - 1),
            color,
            OVERLAY.bbox_thickness,
            cv2.LINE_AA,
        )
        text = _display_label(detection, state_ids.get((detection.label, detection.bbox)))
        (text_width, text_height), baseline = cv2.getTextSize(
            text,
            cv2.FONT_HERSHEY_SIMPLEX,
            OVERLAY.font_scale,
            OVERLAY.font_thickness,
        )
        label_height = text_height + baseline + OVERLAY.label_padding_y * 2
        label_top = y - label_height if y >= label_height else y
        label_right = min(output.shape[1] - 1, x + text_width + OVERLAY.label_padding_x * 2)
        cv2.rectangle(
            output,
            (x, label_top),
            (label_right, label_top + label_height),
            color,
            cv2.FILLED,
        )
        cv2.putText(
            output,
            text,
            (x + OVERLAY.label_padding_x, label_top + OVERLAY.label_padding_y + text_height),
            cv2.FONT_HERSHEY_SIMPLEX,
            OVERLAY.font_scale,
            _contrasting_text(color),
            OVERLAY.font_thickness,
            cv2.LINE_AA,
        )
    return output
