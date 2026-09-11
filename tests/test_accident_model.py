import unittest
from pathlib import Path

from accident_model import MODEL_FILENAME, classify_video_window, get_model_status


class AccidentModelAvailabilityTests(unittest.TestCase):
    def test_missing_model_reports_unavailable_without_a_prediction(self):
        missing_model = Path("models") / f"missing_{MODEL_FILENAME}"
        status = get_model_status(missing_model)
        self.assertEqual(status["status"], "model_unavailable")
        self.assertIn("Model not trained/available", status["message"])

        result = classify_video_window("does-not-need-to-exist.avi", missing_model)
        self.assertEqual(result["status"], "model_unavailable")
        self.assertNotIn("label", result)
        self.assertNotIn("confidence", result)


if __name__ == "__main__":
    unittest.main()
