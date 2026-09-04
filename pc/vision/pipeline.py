"""Shared single- and multi-object contour pipelines over one BGR image."""

from __future__ import annotations

from dataclasses import dataclass

import cv2

from .classifier import Classification, classify_shape
from .config import VisionConfig
from .contours import ContourCandidate, find_contour_candidates
from .preprocess import Image, PreprocessResult, preprocess_image
from .roi import NormalizedRoi


@dataclass(frozen=True)
class ImageAnalysis:
    """Complete observable result for one image."""

    label: str
    confidence: float
    selected_candidate: ContourCandidate | None
    candidates: tuple[ContourCandidate, ...]
    preprocessing: PreprocessResult
    classification: Classification | None

    def to_record(self) -> dict[str, object]:
        selected = self.selected_candidate
        features = selected.features.to_dict() if selected else None
        return {
            "predicted_label": self.label,
            "confidence": self.confidence,
            "passed_contour_filter": selected is not None,
            "features": features,
            "classification_scores": (
                {
                    "topology": self.classification.topology_score,
                    "geometry": self.classification.geometry_score,
                    "quality": round(self.classification.quality_score, 6),
                }
                if self.classification
                else None
            ),
            "otsu_threshold": round(self.preprocessing.otsu_threshold, 3),
            "roi_bounds": list(self.preprocessing.roi_bounds),
            "total_external_contours": len(self.candidates),
            "valid_contours": sum(candidate.passed_filter for candidate in self.candidates),
            "contour_filter_details": [
                {
                    "passed_filter": candidate.passed_filter,
                    "rejection_reasons": list(candidate.rejection_reasons),
                    "features": candidate.features.to_dict(),
                }
                for candidate in self.candidates
            ],
        }


@dataclass(frozen=True)
class DetectedObject:
    """One independently classified valid contour in image coordinates."""

    label: str
    confidence: float
    candidate: ContourCandidate
    classification: Classification
    center: tuple[int, int] | None

    def to_record(self, index: int) -> dict[str, object]:
        return {
            "object_index": index,
            "predicted_label": self.label,
            "confidence": self.confidence,
            "center": list(self.center) if self.center is not None else None,
            "features": self.candidate.features.to_dict(),
            "classification_scores": {
                "topology": self.classification.topology_score,
                "geometry": self.classification.geometry_score,
                "quality": round(self.classification.quality_score, 6),
            },
        }


@dataclass(frozen=True)
class MultiImageAnalysis:
    """All independently valid contours in one frame for M3."""

    detections: tuple[DetectedObject, ...]
    candidates: tuple[ContourCandidate, ...]
    preprocessing: PreprocessResult

    def to_record(self) -> dict[str, object]:
        return {
            "preprocess_mode": self.preprocessing.preprocess_mode,
            "object_count": len(self.detections),
            "predicted_labels": [detection.label for detection in self.detections],
            "objects": [
                detection.to_record(index)
                for index, detection in enumerate(self.detections, start=1)
            ],
            "otsu_threshold": round(self.preprocessing.otsu_threshold, 3),
            "roi_bounds": list(self.preprocessing.roi_bounds),
            "total_external_contours": len(self.candidates),
            "valid_contours": sum(candidate.passed_filter for candidate in self.candidates),
            "contour_filter_details": [
                {
                    "passed_filter": candidate.passed_filter,
                    "rejection_reasons": list(candidate.rejection_reasons),
                    "features": candidate.features.to_dict(),
                }
                for candidate in self.candidates
            ],
        }


def _candidate_center(
    candidate: ContourCandidate,
    roi_bounds: tuple[int, int, int, int],
) -> tuple[int, int] | None:
    moments = cv2.moments(candidate.contour)
    if moments["m00"] == 0:
        return None
    left, top, _, _ = roi_bounds
    return (
        round(moments["m10"] / moments["m00"]) + left,
        round(moments["m01"] / moments["m00"]) + top,
    )


def analyze_multiple_objects(
    image: Image,
    config: VisionConfig,
    roi: NormalizedRoi | None = None,
) -> MultiImageAnalysis:
    """Classify every valid external contour and return detections left-to-right."""

    preprocessing = preprocess_image(image, config, roi)
    candidates = tuple(find_contour_candidates(preprocessing.binary, config))
    detections = [
        DetectedObject(
            label=classification.label,
            confidence=classification.confidence,
            candidate=candidate,
            classification=classification,
            center=_candidate_center(candidate, preprocessing.roi_bounds),
        )
        for candidate in candidates
        if candidate.passed_filter
        for classification in (classify_shape(candidate.features, config),)
    ]
    detections.sort(
        key=lambda detection: (
            detection.center is None,
            detection.center or (0, 0),
        )
    )
    return MultiImageAnalysis(tuple(detections), candidates, preprocessing)


def analyze_image(
    image: Image,
    config: VisionConfig,
    roi: NormalizedRoi | None = None,
) -> ImageAnalysis:
    """Analyze one image, selecting only the largest valid contour for M2."""

    preprocessing = preprocess_image(image, config, roi)
    candidates = tuple(find_contour_candidates(preprocessing.binary, config))
    selected = next((candidate for candidate in candidates if candidate.passed_filter), None)
    if selected is None:
        return ImageAnalysis("no_object", 0.0, None, candidates, preprocessing, None)
    classification = classify_shape(selected.features, config)
    return ImageAnalysis(
        classification.label,
        classification.confidence,
        selected,
        candidates,
        preprocessing,
        classification,
    )


def annotated_image(image: Image, analysis: ImageAnalysis, draw_summary: bool = True) -> Image:
    """Draw configured ROI and the selected contour on a copy of the source image."""

    output = image.copy()
    left, top, right, bottom = analysis.preprocessing.roi_bounds
    cv2.rectangle(output, (left, top), (right - 1, bottom - 1), (255, 128, 0), 3)
    selected = analysis.selected_candidate
    if selected is not None:
        translated = selected.contour.copy()
        translated[:, 0, 0] += left
        translated[:, 0, 1] += top
        cv2.drawContours(output, [translated], -1, (0, 255, 0), 4)
        text = f"{analysis.label}  geometric={analysis.confidence:.3f}"
    else:
        text = "no_object  geometric=0.000"
    if draw_summary:
        cv2.putText(output, text, (left + 10, max(35, top + 35)), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
    return output


def annotated_multi_image(
    image: Image,
    analysis: MultiImageAnalysis,
    draw_summary: bool = True,
) -> Image:
    """Draw every M3 detection without adding tracking or event identity."""

    output = image.copy()
    left, top, right, bottom = analysis.preprocessing.roi_bounds
    cv2.rectangle(output, (left, top), (right - 1, bottom - 1), (255, 128, 0), 3)
    for index, detection in enumerate(analysis.detections, start=1):
        translated = detection.candidate.contour.copy()
        translated[:, 0, 0] += left
        translated[:, 0, 1] += top
        cv2.drawContours(output, [translated], -1, (0, 255, 0), 4)
        x, y, width, height = detection.candidate.features.bounding_box
        cv2.rectangle(
            output,
            (x + left, y + top),
            (x + left + width - 1, y + top + height - 1),
            (0, 200, 255),
            2,
        )
        anchor = (x + left, max(25, y + top - 8))
        label = f"{index}:{detection.label} {detection.confidence:.3f}"
        cv2.putText(output, label, anchor, cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 4)
        cv2.putText(output, label, anchor, cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
        if detection.center is not None:
            cv2.drawMarker(output, detection.center, (255, 255, 0), cv2.MARKER_CROSS, 18, 2)
    if draw_summary:
        summary = (
            f"objects={len(analysis.detections)} "
            f"mode={analysis.preprocessing.preprocess_mode}"
        )
        cv2.putText(
            output,
            summary,
            (left + 10, max(35, top + 35)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
        )
    return output
