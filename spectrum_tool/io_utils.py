import csv
from pathlib import Path
from typing import Optional

import numpy as np


def read_spectrum(path: Path) -> tuple[np.ndarray, np.ndarray]:
    encodings = ["utf-8-sig", "gb18030", "utf-16"]
    rows: Optional[list[list[str]]] = None

    for encoding in encodings:
        try:
            with path.open("r", encoding=encoding, errors="strict") as file_obj:
                rows = list(csv.reader(file_obj))
            break
        except Exception:
            rows = None

    if rows is None:
        with path.open("r", encoding="gb18030", errors="ignore") as file_obj:
            rows = list(csv.reader(file_obj))

    xs: list[float] = []
    ys: list[float] = []
    for row in rows:
        if len(row) < 2:
            continue
        try:
            x_value = float(row[0])
            y_value = float(row[1])
        except ValueError:
            continue
        xs.append(x_value)
        ys.append(y_value)

    if len(xs) < 2:
        raise ValueError("未找到可解析的数值列 (x, y)。")

    x = np.array(xs, dtype=float)
    y = np.array(ys, dtype=float)
    order = np.argsort(x)
    return x[order], y[order]
