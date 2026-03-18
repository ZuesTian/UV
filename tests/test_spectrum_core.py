import tempfile
import unittest
from pathlib import Path

import numpy as np

from spectrum_tool.computation import build_summary_row, compute_area, create_peak_record, extract_segment
from spectrum_tool.io_utils import read_spectrum
from spectrum_tool.models import SpectrumDocument


class SpectrumCoreTests(unittest.TestCase):
    def test_read_spectrum_skips_bad_rows_and_sorts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.txt"
            path.write_text("x,y\n700,0.5\n650,坏数据\n600,0.1\n650,0.3\n", encoding="utf-8")

            x, y = read_spectrum(path)

        np.testing.assert_allclose(x, np.array([600.0, 650.0, 700.0]))
        np.testing.assert_allclose(y, np.array([0.1, 0.3, 0.5]))

    def test_extract_segment_adds_interpolated_bounds(self):
        x = np.array([500.0, 600.0, 700.0, 800.0])
        y = np.array([0.0, 1.0, 1.0, 0.0])

        xs, ys = extract_segment(x, y, 550.0, 750.0)

        np.testing.assert_allclose(xs, np.array([550.0, 600.0, 700.0, 750.0]))
        np.testing.assert_allclose(ys, np.array([0.5, 1.0, 1.0, 0.5]))

    def test_compute_area_returns_expected_triangle_area(self):
        x = np.array([0.0, 1.0, 2.0])
        y = np.array([0.0, 2.0, 0.0])

        result = compute_area(x, y, 0.0, 2.0)

        self.assertAlmostEqual(result["raw_area"], 2.0)
        self.assertAlmostEqual(result["baseline_area"], 0.0)
        self.assertAlmostEqual(result["corrected_area"], 2.0)
        self.assertAlmostEqual(result["positive_area"], 2.0)
        self.assertEqual(result["points"], 3)

    def test_build_summary_row_generates_ratio_text(self):
        x = np.array([0.0, 1.0, 2.0])
        y = np.array([0.0, 2.0, 0.0])
        result = compute_area(x, y, 0.0, 2.0)
        record = create_peak_record("峰1", result, 0.0, 2.0, "batch")
        doc = SpectrumDocument(path=Path("demo.txt"), x=x, y=y, sel_min=0.0, sel_max=2.0)

        row = build_summary_row(doc, record, baseline_area=1.0)

        self.assertEqual(row["file_name"], "demo.txt")
        self.assertEqual(row["peak_name"], "峰1")
        self.assertEqual(row["range_text"], "0.000 - 2.000")
        self.assertEqual(row["ratio_text"], "200.00%")


if __name__ == "__main__":
    unittest.main()
