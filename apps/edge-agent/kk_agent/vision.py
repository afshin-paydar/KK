"""On-device vision detection.

Runs the small detection model locally and yields ONLY structured metadata.
Raw frames never leave this process. Swap `_detect` for the real model
(YOLO/TFLite + picamera2) on the Pi.
"""

from collections.abc import Iterator
from dataclasses import dataclass


@dataclass
class Detection:
    label: str
    count: int
    confidence: float
    zone: str | None = None

    def to_metadata(self) -> dict:
        return {"label": self.label, "count": self.count, "confidence": self.confidence, "zone": self.zone}


class VisionPipeline:
    def __init__(self, camera_index: int, labels_of_interest: list[str], min_confidence: float):
        self.camera_index = camera_index
        self.labels_of_interest = set(labels_of_interest)
        self.min_confidence = min_confidence
        # TODO: open camera (picamera2 / cv2.VideoCapture) + load model here.

    def _detect(self, frame) -> list[Detection]:  # noqa: ANN001 - frame stays local
        """Run the model on a single frame. Replace with real inference."""
        raise NotImplementedError("wire up the on-device model")

    def stream(self) -> Iterator[list[Detection]]:
        """Yield filtered detections per frame. Frames are consumed in-process."""
        raise NotImplementedError("wire up the camera loop")

    def filter(self, dets: list[Detection]) -> list[Detection]:
        return [
            d for d in dets
            if d.label in self.labels_of_interest and d.confidence >= self.min_confidence
        ]
