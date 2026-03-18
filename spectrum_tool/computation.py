from typing import Optional

import numpy as np

from .models import PeakRecord, SpectrumDocument


def extract_segment(x: np.ndarray, y: np.ndarray, xmin: float, xmax: float) -> tuple[np.ndarray, np.ndarray]:
    if xmin >= xmax:
        raise ValueError("范围最小值必须小于最大值。")
    if xmax < x.min() or xmin > x.max():
        raise ValueError("所选范围超出数据边界。")

    xmin = max(xmin, float(x.min()))
    xmax = min(xmax, float(x.max()))
    mask = (x >= xmin) & (x <= xmax)
    xs = x[mask]
    ys = y[mask]

    if xs.size == 0:
        y0 = np.interp(xmin, x, y)
        y1 = np.interp(xmax, x, y)
        return np.array([xmin, xmax], dtype=float), np.array([y0, y1], dtype=float)

    if xs[0] > xmin:
        xs = np.insert(xs, 0, xmin)
        ys = np.insert(ys, 0, np.interp(xmin, x, y))
    elif xs[0] < xmin:
        xs[0] = xmin
        ys[0] = np.interp(xmin, x, y)

    if xs[-1] < xmax:
        xs = np.append(xs, xmax)
        ys = np.append(ys, np.interp(xmax, x, y))
    elif xs[-1] > xmax:
        xs[-1] = xmax
        ys[-1] = np.interp(xmax, x, y)
    return xs, ys


def compute_area(x: np.ndarray, y: np.ndarray, xmin: float, xmax: float) -> dict:
    xs, ys = extract_segment(x, y, xmin, xmax)
    baseline = ys[0] + (ys[-1] - ys[0]) * (xs - xs[0]) / (xs[-1] - xs[0])
    corrected = ys - baseline
    return {
        "xs": xs,
        "ys": ys,
        "baseline": baseline,
        "corrected": corrected,
        "raw_area": np.trapezoid(ys, xs),
        "baseline_area": np.trapezoid(baseline, xs),
        "corrected_area": np.trapezoid(corrected, xs),
        "positive_area": np.trapezoid(np.clip(corrected, 0, None), xs),
        "points": len(xs),
    }


def create_peak_record(name: str, result: dict, lo: float, hi: float, source: str) -> PeakRecord:
    return PeakRecord(
        name=name,
        xmin=lo,
        xmax=hi,
        raw_area=float(result["raw_area"]),
        baseline_area=float(result["baseline_area"]),
        corrected_area=float(result["corrected_area"]),
        positive_area=float(result["positive_area"]),
        points=int(result["points"]),
        source=source,
    )


def build_summary_row(doc: SpectrumDocument, record: PeakRecord, baseline_area: Optional[float]) -> dict:
    ratio = None if baseline_area is None or np.isclose(baseline_area, 0.0) else record.corrected_area / baseline_area * 100.0
    return {
        "file_name": doc.path.name,
        "file_path": str(doc.path),
        "peak_name": record.name,
        "range_text": record.range_text,
        "corrected_area": record.corrected_area,
        "positive_area": record.positive_area,
        "ratio_text": "-" if ratio is None else f"{ratio:.2f}%",
        "ratio_value": float("-inf") if ratio is None else ratio,
        "source": record.source,
    }
