"""Thin adapters from the existing M3 result model to M4 detections."""

from __future__ import annotations

from pc.vision.pipeline import MultiImageAnalysis

from .models import Detection


def detections_from_analysis(
    analysis: MultiImageAnalysis,
    frame_index: int,
) -> tuple[Detection, ...]:
    """Convert ROI-local M3 boxes to full-frame (x, y, width, height) boxes."""

    left, top, _, _ = analysis.preprocessing.roi_bounds
    return tuple(
        Detection(
            label=item.label,
            confidence=item.confidence,
            bbox=(
                item.candidate.features.bounding_box[0] + left,
                item.candidate.features.bounding_box[1] + top,
                item.candidate.features.bounding_box[2],
                item.candidate.features.bounding_box[3],
            ),
            frame_index=frame_index,
        )
        for item in analysis.detections
    )
