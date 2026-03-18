from spectrum_tool.computation import build_summary_row, compute_area, create_peak_record, extract_segment
from spectrum_tool.io_utils import read_spectrum
from spectrum_tool.models import PeakRecord, SpectrumDocument
from spectrum_tool.ui import SpectrumApp, main

__all__ = [
    "PeakRecord",
    "SpectrumDocument",
    "read_spectrum",
    "extract_segment",
    "compute_area",
    "create_peak_record",
    "build_summary_row",
    "SpectrumApp",
    "main",
]


if __name__ == "__main__":
    main()
