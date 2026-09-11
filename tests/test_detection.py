import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from app import create_app


class DetectionRouteTests(unittest.TestCase):
    def setUp(self):
        self.test_id = uuid.uuid4().hex
        self.video_directory = Path.cwd() / "videos"
        self.processed_directory = self.video_directory / "processed"
        self.source_name = f"_test_detection_{self.test_id}.avi"
        self.processed_name = f"detected__test_detection_{self.test_id}.mp4"
        self.source_path = self.video_directory / self.source_name
        self.output_path = self.processed_directory / self.processed_name
        self.created_snapshots = []
        self._create_sample_video()

        self.app = create_app()
        self.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 1
            session["user_name"] = "Test Admin"
            session["user_role"] = "admin"
            session["uploaded_video"] = {
                "filename": self.source_name,
                "original_name": "traffic.avi",
                "frame_count": 3,
                "width": 32,
                "height": 24,
                "duration_seconds": 0.3,
            }

    def tearDown(self):
        self.source_path.unlink(missing_ok=True)
        self.output_path.unlink(missing_ok=True)
        for snapshot_path in self.created_snapshots:
            snapshot_path.unlink(missing_ok=True)

    def _create_sample_video(self):
        writer = cv2.VideoWriter(str(self.source_path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (32, 24))
        self.assertTrue(writer.isOpened())
        for value in (20, 100, 200):
            writer.write(np.full((24, 32, 3), value, dtype=np.uint8))
        writer.release()

    @patch("app.process_video")
    def test_processing_keeps_original_and_shows_processed_playback(self, process_video):
        original_content = self.source_path.read_bytes()

        def create_annotated_copy(source, output, _models_directory):
            Path(output).write_bytes(Path(source).read_bytes())
            return {"frame_count": 3, "fps": 10.0, "width": 32, "height": 24, "detection_count": 2}

        process_video.side_effect = create_annotated_copy
        response = self.client.post("/process-video")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.source_path.read_bytes(), original_content)
        self.assertTrue(self.output_path.is_file())

        dashboard = self.client.get("/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"YOLO Detection Result", dashboard.data)
        self.assertIn(b"Model not trained/available", dashboard.data)
        playback = self.client.get(f"/processed-videos/{self.processed_name}")
        self.assertEqual(playback.status_code, 200)
        self.assertGreater(len(playback.data), 0)
        playback.close()

    def test_accident_severity_is_saved_with_the_event(self):
        detection_result = {
            "frame_count": 3, "fps": 10.0, "width": 32, "height": 24,
            "detection_count": 8,
            "object_counts": {"person": 3, "car": 3, "motorcycle": 1, "bus": 0, "truck": 0},
            "average_detection_confidence": 0.9,
        }
        classification = {
            "status": "classified", "label": "ACCIDENT", "confidence": 0.9,
            "accident_probability": 0.9, "frames_evaluated": 8, "positive_frames": 7,
        }

        def create_annotated_copy(source, output, _models_directory):
            Path(output).write_bytes(Path(source).read_bytes())
            return detection_result

        with patch("app.process_video", side_effect=create_annotated_copy), patch(
            "app.classify_video_window", return_value=classification
        ), patch("app.db.find_recent_accident_event", return_value=None), patch(
            "app.db.save_accident_event_from_video", return_value=42
        ) as save_event, patch("app.generate_alert", return_value={"alert_id": 55, "message": "Demo alert", "email_results": []}):
            response = self.client.post("/process-video")
            self.assertEqual(response.status_code, 302)
            with self.client.session_transaction() as session:
                severity = session["severity_estimate"]
                event = session["current_accident_event"]
            self.created_snapshots.append(Path(self.app.config["SNAPSHOT_FOLDER"]) / event["snapshot"]["filename"])
            self.assertEqual(severity["severity"], "HIGH")
            self.assertTrue(severity["database_saved"])
            self.assertEqual(severity["accident_event_id"], 42)
            self.assertEqual(session["current_alert"]["alert_id"], 55)
            self.assertTrue(self.created_snapshots[0].is_file())
            snapshot_response = self.client.get(f"/snapshots/{event['snapshot']['filename']}")
            self.assertEqual(snapshot_response.status_code, 200)
            snapshot_response.close()

            # A second processing request for the same source is grouped.
            self.client.post("/process-video")
            save_event.assert_called_once()
            with self.client.session_transaction() as session:
                self.assertIn("Grouped with a recent accident event", session["severity_estimate"]["database_message"])


if __name__ == "__main__":
    unittest.main()
