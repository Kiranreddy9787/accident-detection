"""YOLO vehicle and person detection for uploaded videos.

This module intentionally performs object detection only. It does not classify
accidents or make emergency-response decisions.
"""

from pathlib import Path
from typing import Any

import cv2


MODEL_FILENAME = "yolov8n.pt"
TARGET_CLASSES = {0: "person", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
BOX_COLORS = {
    "person": (66, 189, 255),
    "car": (98, 230, 136),
    "motorcycle": (255, 180, 67),
    "bus": (238, 103, 103),
    "truck": (184, 116, 255),
}


class DetectionError(RuntimeError):
    """Raised when the YOLO model or video processing cannot be used."""


def get_model(models_directory: str | Path):
    """Load YOLOv8 nano, downloading it to ``models/`` on first use."""
    try:
        from ultralytics import YOLO
    except Exception as error:  # Import can fail if the package is not installed or cannot initialize.
        raise DetectionError(
            "Ultralytics YOLO could not initialize. Ensure dependencies are installed and the "
            "current user can access the Ultralytics configuration directory."
        ) from error

    model_path = Path(models_directory) / MODEL_FILENAME
    model_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Ultralytics downloads the official lightweight pretrained weight file
        # when this local path does not exist.
        return YOLO(str(model_path))
    except Exception as error:
        raise DetectionError(
            "Could not load the YOLOv8 nano model. Check your internet connection "
            "for the first download, then try again."
        ) from error


def _draw_detections(frame, result) -> tuple[int, dict[str, int], float]:
    """Draw filtered YOLO boxes, labels, and confidence values on one frame."""
    detection_count = 0
    object_counts = {name: 0 for name in TARGET_CLASSES.values()}
    confidence_total = 0.0
    boxes = result.boxes
    if boxes is None:
        return detection_count, object_counts, confidence_total

    class_names = result.names
    for box in boxes:
        class_id = int(box.cls[0].item())
        if class_id not in TARGET_CLASSES:
            continue
        label_name = class_names[class_id]
        confidence = float(box.conf[0].item())
        x1, y1, x2, y2 = (int(value) for value in box.xyxy[0].tolist())
        color = BOX_COLORS.get(label_name, (0, 220, 255))
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        label = f"{label_name} {confidence:.0%}"
        (label_width, label_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
        label_top = max(y1, label_height + baseline + 5)
        cv2.rectangle(frame, (x1, label_top - label_height - baseline - 5), (x1 + label_width + 8, label_top), color, -1)
        cv2.putText(frame, label, (x1 + 4, label_top - baseline - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 30, 40), 2)
        detection_count += 1
        object_counts[label_name] += 1
        confidence_total += confidence
    return detection_count, object_counts, confidence_total


def process_video(
    input_path: str | Path,
    output_path: str | Path,
    models_directory: str | Path,
    confidence: float = 0.35,
    image_size: int = 640,
) -> dict[str, Any]:
    """Detect people and road vehicles, writing an annotated MP4 copy.

    Inference uses the YOLO nano model, CPU device, filtered target classes, and
    640px input size to keep the college-project demonstration practical on CPU.
    """
    source = Path(input_path)
    destination = Path(output_path)
    if not source.is_file():
        raise DetectionError("The uploaded source video could not be found.")
    if not 0 < confidence <= 1:
        raise ValueError("confidence must be between 0 and 1.")

    model = get_model(models_directory)
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise DetectionError("OpenCV could not open the uploaded video.")

    fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if width < 1 or height < 1:
        capture.release()
        raise DetectionError("The uploaded video has invalid dimensions.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = destination.with_suffix(".processing.mp4")
    writer = cv2.VideoWriter(str(temporary_output), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        capture.release()
        raise DetectionError("OpenCV could not create the processed MP4 video.")

    frame_count = 0
    detection_count = 0
    object_counts = {name: 0 for name in TARGET_CLASSES.values()}
    confidence_total = 0.0
    try:
        while True:
            has_frame, frame = capture.read()
            if not has_frame:
                break
            results = model.predict(
                frame,
                conf=confidence,
                classes=list(TARGET_CLASSES),
                imgsz=image_size,
                device="cpu",
                verbose=False,
            )
            frame_detections, frame_counts, frame_confidence = _draw_detections(frame, results[0])
            detection_count += frame_detections
            confidence_total += frame_confidence
            for class_name, count in frame_counts.items():
                object_counts[class_name] += count
            writer.write(frame)
            frame_count += 1
    except Exception as error:
        temporary_output.unlink(missing_ok=True)
        raise DetectionError(f"YOLO could not process the video: {error}") from error
    finally:
        capture.release()
        writer.release()

    if frame_count == 0:
        temporary_output.unlink(missing_ok=True)
        raise DetectionError("The uploaded video contains no readable frames.")
    temporary_output.replace(destination)
    return {
        "frame_count": frame_count,
        "fps": round(float(fps), 2),
        "width": width,
        "height": height,
        "detection_count": detection_count,
        "object_counts": object_counts,
        "average_detection_confidence": round(confidence_total / detection_count, 4) if detection_count else 0.0,
    }
