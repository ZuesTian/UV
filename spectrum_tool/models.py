from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np


@dataclass
class PeakRecord:
    name: str
    xmin: float
    xmax: float
    raw_area: float
    baseline_area: float
    corrected_area: float
    positive_area: float
    points: int
    source: str = "manual"

    @property
    def range_text(self) -> str:
        return f"{self.xmin:.3f} - {self.xmax:.3f}"


@dataclass
class SpectrumDocument:
    path: Path
    x: np.ndarray
    y: np.ndarray
    sel_min: float
    sel_max: float
    peak_records: list[PeakRecord] = field(default_factory=list)
    baseline_peak_name: str = ""
    current_record: Optional[PeakRecord] = None
    view_limits: Optional[tuple[float, float, float, float]] = None
    compare_enabled: bool = False
