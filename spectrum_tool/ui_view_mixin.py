from tkinter import messagebox

import numpy as np

from .computation import compute_area, create_peak_record
from .ui_constants import MIN_Y_PADDING, Y_PADDING_RATIO, ZOOM_SCALE_BASE
from .ui_plotting import plot_overlay_spectra


class UiViewMixin:
    def on_scroll_zoom(self, event):
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return
        if event.button not in ("up", "down"):
            return

        scale = 1 / ZOOM_SCALE_BASE if event.button == "up" else ZOOM_SCALE_BASE
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        xdata = float(event.xdata)
        ydata = float(event.ydata)

        self.ax.set_xlim(xdata - (xdata - x0) * scale, xdata + (x1 - xdata) * scale)
        self.ax.set_ylim(ydata - (ydata - y0) * scale, ydata + (y1 - ydata) * scale)
        self._sync_view_entries_from_axes()
        self._save_current_document_state()
        self.canvas.draw_idle()

    def on_span_select(self, xmin: float, xmax: float):
        if xmin == xmax:
            return
        lo, hi = sorted((xmin, xmax))
        self.sel_min.set(f"{lo:.3f}")
        self.sel_max.set(f"{hi:.3f}")
        self.compute_and_draw()

    def apply_range_from_entry(self):
        self.compute_and_draw()

    def apply_view_from_entry(self):
        if self.current_doc_index is None:
            return
        try:
            self._apply_axis_limits_from_entries()
        except ValueError as exc:
            messagebox.showerror("视图范围错误", str(exc))
            return
        self._sync_view_entries_from_axes()
        self._save_current_document_state()
        self.canvas.draw_idle()

    def reset_view_range(self, update_entries: bool = True):
        doc = self.get_current_document()
        if doc is None:
            return

        overlay_indices = self.get_overlay_indices() or [self.current_doc_index]
        xs = [self.documents[idx].x for idx in overlay_indices if idx is not None]
        ys = [self.documents[idx].y for idx in overlay_indices if idx is not None]
        x_min = float(min(np.min(item) for item in xs))
        x_max = float(max(np.max(item) for item in xs))
        y_min = float(min(np.min(item) for item in ys))
        y_max = float(max(np.max(item) for item in ys))
        pad = max(abs(y_min) * Y_PADDING_RATIO, MIN_Y_PADDING) if np.isclose(y_min, y_max) else (y_max - y_min) * Y_PADDING_RATIO
        y_low = y_min - pad
        y_high = y_max + pad

        self.ax.set_xlim(x_min, x_max)
        self.ax.set_ylim(y_low, y_high)
        if update_entries:
            self.view_xmin.set(f"{x_min:.3f}")
            self.view_xmax.set(f"{x_max:.3f}")
            self.view_ymin.set(f"{y_low:.6f}")
            self.view_ymax.set(f"{y_high:.6f}")
        doc.view_limits = (x_min, x_max, y_low, y_high)
        self.canvas.draw_idle()

    def _apply_axis_limits_from_entries(self):
        x_min_str = self.view_xmin.get().strip()
        x_max_str = self.view_xmax.get().strip()
        y_min_str = self.view_ymin.get().strip()
        y_max_str = self.view_ymax.get().strip()

        if x_min_str and x_max_str:
            x_min = float(x_min_str)
            x_max = float(x_max_str)
            if x_min >= x_max:
                raise ValueError("X轴最小值必须小于最大值。")
            self.ax.set_xlim(x_min, x_max)
        elif x_min_str or x_max_str:
            raise ValueError("请同时填写 X 轴最小值和最大值。")

        if y_min_str and y_max_str:
            y_min = float(y_min_str)
            y_max = float(y_max_str)
            if y_min >= y_max:
                raise ValueError("Y轴最小值必须小于最大值。")
            self.ax.set_ylim(y_min, y_max)
        elif y_min_str or y_max_str:
            raise ValueError("请同时填写 Y 轴最小值和最大值。")

    def _sync_view_entries_from_axes(self):
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        self.view_xmin.set(f"{x0:.3f}")
        self.view_xmax.set(f"{x1:.3f}")
        self.view_ymin.set(f"{y0:.6f}")
        self.view_ymax.set(f"{y1:.6f}")

    def _apply_saved_or_default_view(self):
        doc = self.get_current_document()
        if doc is None:
            return
        if doc.view_limits is None:
            self.reset_view_range(update_entries=True)
            return
        x0, x1, y0, y1 = doc.view_limits
        self.ax.set_xlim(x0, x1)
        self.ax.set_ylim(y0, y1)
        self._sync_view_entries_from_axes()

    def _build_overlay_preview_results(self, lo: float, hi: float, current_result: dict) -> dict[int, dict]:
        overlay_indices = self.get_overlay_indices()
        if not overlay_indices and self.current_doc_index is not None:
            overlay_indices = [self.current_doc_index]

        preview_results: dict[int, dict] = {}
        if self.current_doc_index is None:
            return preview_results

        current_doc = self.documents[self.current_doc_index]
        current_doc.current_record = create_peak_record("当前峰", current_result, lo, hi, "preview")
        preview_results[self.current_doc_index] = {"result": current_result, "record": current_doc.current_record}

        for idx in overlay_indices:
            if idx == self.current_doc_index:
                continue
            doc = self.documents[idx]
            try:
                result = compute_area(doc.x, doc.y, lo, hi)
            except Exception:
                doc.current_record = None
                continue
            doc.current_record = create_peak_record("当前峰", result, lo, hi, "preview")
            preview_results[idx] = {"result": result, "record": doc.current_record}

        return preview_results

    def _plot_overlay_spectra(self):
        indices = self.get_overlay_indices()
        if not indices and self.current_doc_index is not None:
            indices = [self.current_doc_index]
        self._update_overlay_summary()
        plot_overlay_spectra(self.ax, self.documents, indices, self.current_doc_index, self.overlay_preview_results)

    def compute_and_draw(self):
        doc = self.get_current_document()
        if doc is None:
            return

        try:
            lo, hi = sorted((float(self.sel_min.get()), float(self.sel_max.get())))
            result = compute_area(doc.x, doc.y, lo, hi)
        except Exception as exc:
            doc.current_record = None
            self.result_raw.set(f"原始面积: 错误 ({exc})")
            self.result_base.set("基线面积: -")
            self.result_corr.set("扣基线面积: -")
            self.result_pos.set("仅正面积: -")
            self.result_points.set("数据点数: -")
            self.highlight_peak.set("当前峰面积(扣基线): -")
            self.overlay_preview_results = {}
            self.update_compare_view()
            self.canvas.draw_idle()
            return

        doc.sel_min = lo
        doc.sel_max = hi
        self.overlay_preview_results = self._build_overlay_preview_results(lo, hi, result)
        if self.current_doc_index is not None and self.current_doc_index in self.overlay_preview_results:
            doc.current_record = self.overlay_preview_results[self.current_doc_index]["record"]
        else:
            doc.current_record = create_peak_record("当前峰", result, lo, hi, "current")

        self.sel_min.set(f"{lo:.3f}")
        self.sel_max.set(f"{hi:.3f}")
        self.result_raw.set(f"原始面积: {doc.current_record.raw_area:.6f}")
        self.result_base.set(f"基线面积: {doc.current_record.baseline_area:.6f}")
        self.result_corr.set(f"扣基线面积: {doc.current_record.corrected_area:.6f}")
        self.result_pos.set(f"仅正面积: {doc.current_record.positive_area:.6f}")
        self.result_points.set(f"数据点数: {doc.current_record.points}")
        self.highlight_peak.set(f"当前峰面积(扣基线): {doc.current_record.corrected_area:.6f}")

        self.ax.clear()
        self._plot_overlay_spectra()
        self.ax.axvline(lo, color="gray", lw=0.8, alpha=0.6)
        self.ax.axvline(hi, color="gray", lw=0.8, alpha=0.6)
        self.ax.set_xlabel("波长 (nm)")
        self.ax.set_ylabel("吸收值")
        self.ax.set_title(f"{doc.path.name} | 当前积分范围: {lo:.3f} - {hi:.3f} nm")
        self.ax.grid(alpha=0.25)
        self.ax.legend(loc="upper right", fontsize=8)

        try:
            self._apply_saved_or_default_view()
        except Exception:
            self.reset_view_range(update_entries=True)

        doc.view_limits = self._get_current_view_limits()
        self.update_compare_view()
        self.canvas.draw_idle()
