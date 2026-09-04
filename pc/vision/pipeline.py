"""Single-object M2 pipeline over one offline BGR image."""

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
