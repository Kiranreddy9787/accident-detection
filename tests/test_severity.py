import unittest

from severity import estimate_severity


class SeverityEstimatorTests(unittest.TestCase):
    def test_low_medium_and_high_bands_are_explainable(self):
        low = estimate_severity(0, 0, 0.0, 0.0)
        medium = estimate_severity(3, 2, 0.5, 0.5)
        high = estimate_severity(5, 5, 1.0, 1.0)
        self.assertEqual((low["severity"], low["severity_score"]), ("LOW", 0.0))
        self.assertEqual((medium["severity"], medium["severity_score"]), ("MEDIUM", 51.5))
        self.assertEqual((high["severity"], high["severity_score"]), ("HIGH", 100.0))
        self.assertIn("demonstration-only", high["explanation"])

    def test_invalid_signal_range_is_rejected(self):
        with self.assertRaises(ValueError):
            estimate_severity(1, 1, 1.1, 0.8)


if __name__ == "__main__":
    unittest.main()
