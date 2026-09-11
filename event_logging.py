"""Snapshot capture and cooldown grouping for confirmed accident events."""

from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import cv2


class EventLoggingError(RuntimeError):
    """Raised when an event snapshot cannot be created."""


class AccidentEventGrouper:
    """Avoid repeated event records from the same source during a cooldown."""

    def __init__(self, cooldown_seconds: int = 120):
        self.cooldown = timedelta(seconds=cooldown_seconds)
        self._last_event_by_source: dict[str, datetime] = {}

    def is_in_cooldown(self, source_key: str, now: datetime | None = None) -> bool:
        now = now or datetime.now()
        previous = self._last_event_by_source.get(source_key)
        return previous is not None and now - previous < self.cooldown

    def mark_event(self, source_key: str, now: datetime | None = None) -> None:
        self._last_event_by_source[source_key] = now or datetime.now()


def capture_accident_snapshot(
    video_path: str | Path,
    frame_index: int,
    snapshots_directory: str | Path,
) -> dict[str, str | int]:
    """Capture one relevant frame with a unique filename in ``snapshots/``."""
    source = Path(video_path)
    if not source.is_file():
        raise EventLoggingError("The source video for the accident snapshot could not be found.")

    capture = cv2.VideoCapture(str(source))
    try:
        if not capture.isOpened():
            raise EventLoggingError("OpenCV could not open the source video for a snapshot.")
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        selected_frame = min(max(frame_index, 0), max(total_frames - 1, 0))
        capture.set(cv2.CAP_PROP_POS_FRAMES, selected_frame)
        readable, frame = capture.read()
        if not readable:
            raise EventLoggingError("The selected accident frame could not be read.")
    finally:
        capture.release()

    timestamp = datetime.now()
    filename = f"accident_{timestamp:%Y%m%d_%H%M%S}_{uuid4().hex[:10]}.jpg"
    destination = Path(snapshots_directory)
    destination.mkdir(parents=True, exist_ok=True)
    output_path = destination / filename
    if not cv2.imwrite(str(output_path), frame):
        raise EventLoggingError("OpenCV could not save the accident snapshot.")
    return {
        "filename": filename,
        "captured_at": timestamp.isoformat(timespec="seconds"),
        "frame_index": selected_frame,
    }
