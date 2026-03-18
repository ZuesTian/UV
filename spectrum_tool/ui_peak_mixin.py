import tkinter as tk
from tkinter import messagebox

import numpy as np

from .models import PeakRecord, SpectrumDocument
from .ui_plotting import draw_multi_file_area_chart, draw_pie_chart


class UiPeakMixin:
    def _refresh_records_list(self):
        self.records_list.delete(0, tk.END)
        doc = self.get_current_document()
        if doc is None:
            return
        for record in doc.peak_records:
            self.records_list.insert(
                tk.END,
                f"{record.name} | 面积={record.corrected_area:.6f} | 范围={record.xmin:.2f}-{record.xmax:.2f}",
            )

    def _refresh_baseline_options(self):
        doc = self.get_current_document()
        names = [] if doc is None else [item.name for item in doc.peak_records]
        self.baseline_combo["values"] = names
        if not names:
            self.baseline_peak.set("")
            if doc is not None:
                doc.baseline_peak_name = ""
            return
        current_name = self.baseline_peak.get().strip()
        if current_name not in names:
            current_name = names[0]
            self.baseline_peak.set(current_name)
        if doc is not None:
            doc.baseline_peak_name = current_name

    def on_record_select(self, _event=None):
        self.update_compare_view()

    def on_baseline_select(self, _event=None):
        doc = self.get_current_document()
        if doc is None:
            return
        doc.baseline_peak_name = self.baseline_peak.get().strip()
        self.update_compare_view()

    def delete_selected_record(self):
        doc = self.get_current_document()
        selection = self.records_list.curselection()
        if doc is None or not selection:
            return
        idx = int(selection[0])
        doc.peak_records.pop(idx)
        self._refresh_records_list()
        self._refresh_baseline_options()
        self.update_compare_view()

    def record_current_peak(self):
        doc = self.get_current_document()
        if doc is None or doc.current_record is None:
            messagebox.showwarning("无法记录", "请先加载数据并完成一次积分计算。")
            return
        record = PeakRecord(
            name=f"峰{len(doc.peak_records) + 1}",
            xmin=doc.current_record.xmin,
            xmax=doc.current_record.xmax,
            raw_area=doc.current_record.raw_area,
            baseline_area=doc.current_record.baseline_area,
            corrected_area=doc.current_record.corrected_area,
            positive_area=doc.current_record.positive_area,
            points=doc.current_record.points,
            source="manual",
        )
        doc.peak_records.append(record)
        if not doc.baseline_peak_name:
            doc.baseline_peak_name = record.name
        self._refresh_records_list()
        self._refresh_baseline_options()
        last_index = self.records_list.size() - 1
        if last_index >= 0:
            self.records_list.selection_clear(0, tk.END)
            self.records_list.selection_set(last_index)
        self.update_compare_view()

    def update_compare_view(self):
        overlay_items = self._get_overlay_preview_items()
        if len(overlay_items) > 1:
            self._update_multi_file_compare_view(overlay_items)
            return

        doc = self.get_current_document()
        if doc is None or not doc.peak_records:
            self._set_peak_compare_mode()
            self.compare_text.set("对比结果: 暂无已记录峰，可点击“记录当前峰”后对比")
            draw_pie_chart(self.pie_ax, self.pie_canvas, None, None, "基准峰")
            return

        self._set_peak_compare_mode()
        selection = self.records_list.curselection()
        target_idx = int(selection[0]) if selection else len(doc.peak_records) - 1
        target = doc.peak_records[target_idx]

        base_name = self.baseline_peak.get().strip()
        baseline = next((item for item in doc.peak_records if item.name == base_name), None)
        if baseline is None:
            baseline = doc.peak_records[0]
            self.baseline_peak.set(baseline.name)
            doc.baseline_peak_name = baseline.name

        if np.isclose(baseline.corrected_area, 0.0):
            self.compare_text.set(f"对比结果: 基准峰 {baseline.name} 面积为 0，无法计算比例")
        else:
            ratio = target.corrected_area / baseline.corrected_area * 100.0
            self.compare_text.set(f"对比结果: {target.name} / {baseline.name} = {ratio:.2f}%")
        draw_pie_chart(
            self.pie_ax,
            self.pie_canvas,
            abs(target.corrected_area),
            abs(baseline.corrected_area),
            baseline.name,
            target.name,
        )

    def _set_peak_compare_mode(self):
        self.baseline_combo.configure(state="readonly")

    def _set_multi_file_compare_mode(self):
        self.baseline_combo.configure(state="disabled")

    def _get_overlay_preview_items(self) -> list[tuple[int, SpectrumDocument, PeakRecord]]:
        items: list[tuple[int, SpectrumDocument, PeakRecord]] = []
        for idx in self.get_overlay_indices():
            preview = self.overlay_preview_results.get(idx)
            if preview is None:
                continue
            record = preview.get("record")
            if record is None:
                continue
            items.append((idx, self.documents[idx], record))
        return items

    def _update_multi_file_compare_view(self, overlay_items: list[tuple[int, SpectrumDocument, PeakRecord]]):
        self._set_multi_file_compare_mode()

        sorted_items = sorted(overlay_items, key=lambda item: item[2].corrected_area, reverse=True)
        current_idx = self.current_doc_index
        current_item = next((item for item in overlay_items if item[0] == current_idx), sorted_items[0])
        leader = sorted_items[0]
        trailer = sorted_items[-1]

        rank = next(
            (position for position, item in enumerate(sorted_items, 1) if item[0] == current_item[0]),
            1,
        )
        current_area = current_item[2].corrected_area
        if np.isclose(leader[2].corrected_area, 0.0):
            ratio_text = "当前区域多文件对比: 参考面积为 0，无法计算相对比例"
        else:
            ratio = current_area / leader[2].corrected_area * 100.0
            ratio_text = (
                f"当前区域多文件对比: 当前文件排名 {rank}/{len(sorted_items)}，"
                f"相对最大面积为 {ratio:.2f}%"
            )

        summary_text = (
            f"{ratio_text}；最大 {leader[1].path.name} = {leader[2].corrected_area:.6f}，"
            f"最小 {trailer[1].path.name} = {trailer[2].corrected_area:.6f}"
        )
        self.compare_text.set(summary_text)
        draw_multi_file_area_chart(self.pie_ax, self.pie_fig, self.pie_canvas, overlay_items, self.current_doc_index)
