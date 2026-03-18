from typing import Optional

import numpy as np
from matplotlib.axes import Axes
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .models import PeakRecord, SpectrumDocument
from .ui_constants import AREA_TEXT_EPS, SPECTRUM_COLORS


def pick_peak_label_position(result: dict) -> tuple[float, float]:
    corrected = np.asarray(result["corrected"])
    xs = np.asarray(result["xs"])
    ys = np.asarray(result["ys"])
    baseline = np.asarray(result["baseline"])
    if corrected.size == 0:
        return 0.0, 0.0
    peak_idx = int(np.argmax(np.abs(corrected)))
    x_value = float(xs[peak_idx])
    y_value = float(max(ys[peak_idx], baseline[peak_idx]))
    return x_value, y_value


def draw_multi_file_area_chart(
    pie_ax: Axes,
    pie_fig: Figure,
    pie_canvas: FigureCanvasTkAgg,
    overlay_items: list[tuple[int, SpectrumDocument, PeakRecord]],
    current_doc_index: Optional[int],
) -> None:
    pie_ax.clear()

    labels = []
    values = []
    colors = []
    for order, (idx, doc, record) in enumerate(overlay_items):
        label = doc.path.stem
        if len(label) > 18:
            label = f"{label[:18]}..."
        if idx == current_doc_index:
            label = f"{label} *"
        labels.append(label)
        values.append(record.corrected_area)
        colors.append(SPECTRUM_COLORS[order % len(SPECTRUM_COLORS)])

    y_pos = np.arange(len(labels))
    bars = pie_ax.barh(y_pos, values, color=colors, alpha=0.85)
    pie_ax.axvline(0.0, color="#666666", lw=0.8)
    pie_ax.set_yticks(y_pos, labels=labels)
    pie_ax.invert_yaxis()
    pie_ax.set_title("当前区域面积对比")
    pie_ax.set_xlabel("扣基线面积")

    value_span = max((abs(value) for value in values), default=1.0)
    text_offset = max(value_span * 0.02, 1e-6)
    for bar, value in zip(bars, values):
        x_pos = value + text_offset if value >= 0 else value - text_offset
        align = "left" if value >= 0 else "right"
        pie_ax.text(
            x_pos,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.3f}",
            va="center",
            ha=align,
            fontsize=8,
        )

    pie_fig.tight_layout()
    pie_canvas.draw_idle()


def draw_pie_chart(
    pie_ax: Axes,
    pie_canvas: FigureCanvasTkAgg,
    target_value: Optional[float],
    base_value: Optional[float],
    base_name: str,
    target_name: str = "选中峰",
) -> None:
    pie_ax.clear()
    if target_value is None:
        pie_ax.text(0.5, 0.5, "无数据", ha="center", va="center")
        pie_ax.set_axis_off()
        pie_canvas.draw_idle()
        return
    pie_ax.set_axis_on()
    if base_value is None or np.isclose(base_value, 0.0):
        values = [max(target_value, AREA_TEXT_EPS)]
        labels = [target_name]
        colors = ["#ff8a65"]
    else:
        values = [max(target_value, AREA_TEXT_EPS), max(base_value, AREA_TEXT_EPS)]
        labels = [target_name, base_name]
        colors = ["#ff8a65", "#64b5f6"]
    pie_ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90, colors=colors)
    pie_ax.set_title("面积比例(绝对值)")
    pie_canvas.draw_idle()


def plot_overlay_spectra(
    ax: Axes,
    documents: list[SpectrumDocument],
    overlay_indices: list[int],
    current_doc_index: Optional[int],
    overlay_preview_results: dict[int, dict],
) -> None:
    for order, idx in enumerate(overlay_indices):
        doc = documents[idx]
        is_current = idx == current_doc_index
        color = SPECTRUM_COLORS[order % len(SPECTRUM_COLORS)]
        area_label = ""
        if doc.current_record is not None:
            area_label = f" | A={doc.current_record.corrected_area:.3f}"
        ax.plot(
            doc.x,
            doc.y,
            lw=1.8 if is_current else 1.0,
            alpha=1.0 if is_current else 0.65,
            color=color,
            label=f"{doc.path.name}{' (当前)' if is_current else ''}{area_label}",
            zorder=4 if is_current else 2,
        )

        preview = overlay_preview_results.get(idx)
        if preview is None:
            continue

        result = preview["result"]
        baseline_alpha = 0.95 if is_current else 0.55
        fill_alpha = 0.26 if is_current else 0.12
        baseline_label = "当前文件基线" if is_current else "_nolegend_"
        ax.plot(
            result["xs"],
            result["baseline"],
            "--",
            lw=1.4 if is_current else 1.0,
            color=color,
            alpha=baseline_alpha,
            label=baseline_label,
            zorder=5 if is_current else 3,
        )
        ax.fill_between(
            result["xs"],
            result["ys"],
            result["baseline"],
            color=color,
            alpha=fill_alpha,
            zorder=4 if is_current else 2,
        )
        x_text, y_text = pick_peak_label_position(result)
        ax.text(
            x_text,
            y_text,
            f"{preview['record'].corrected_area:.2f}",
            color=color,
            fontsize=8,
            ha="center",
            va="bottom",
        )
