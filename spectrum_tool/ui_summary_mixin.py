import csv
from tkinter import filedialog, messagebox
from typing import Optional

from .computation import build_summary_row, compute_area, create_peak_record
from .ui_constants import CSV_FILE_TYPES
from .ui_summary import create_summary_window, has_live_summary_tree, populate_summary_tree


class UiSummaryMixin:
    def batch_calculate_all(self):
        if not self.documents:
            messagebox.showwarning("无法批量计算", "请先加载至少一个光谱文件。")
            return
        try:
            lo, hi = sorted((float(self.sel_min.get()), float(self.sel_max.get())))
        except ValueError:
            messagebox.showerror("积分范围错误", "请输入有效的积分范围。")
            return

        rows: list[dict] = []
        baseline_area: Optional[float] = None
        for idx, doc in enumerate(self.documents):
            result = compute_area(doc.x, doc.y, lo, hi)
            record = create_peak_record(f"批量峰{len(doc.peak_records) + 1}", result, lo, hi, "batch")
            doc.current_record = record
            doc.peak_records.append(record)
            if idx == 0:
                baseline_area = record.corrected_area
            rows.append(build_summary_row(doc, record, baseline_area))

        self.summary_rows = rows
        if self.current_doc_index is not None:
            current_doc = self.documents[self.current_doc_index]
            current_doc.sel_min = lo
            current_doc.sel_max = hi
            self._refresh_records_list()
            self._refresh_baseline_options()
            self.compute_and_draw()
        self.show_summary_window()

    def _rows_for_export(self) -> list[dict]:
        if self.summary_rows:
            return self.summary_rows
        rows: list[dict] = []
        for doc in self.documents:
            baseline_area = doc.peak_records[0].corrected_area if doc.peak_records else None
            for record in doc.peak_records:
                rows.append(build_summary_row(doc, record, baseline_area))
        return rows

    def export_summary_csv(self):
        rows = self._rows_for_export()
        if not rows:
            messagebox.showwarning("无法导出", "当前没有可导出的结果。")
            return
        path = filedialog.asksaveasfilename(
            title="导出汇总 CSV",
            defaultextension=".csv",
            filetypes=CSV_FILE_TYPES,
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as file_obj:
            writer = csv.writer(file_obj)
            writer.writerow(["文件名", "峰名", "积分范围", "扣基线面积", "仅正面积", "与基准比值", "来源", "文件路径"])
            for row in rows:
                writer.writerow(
                    [
                        row["file_name"],
                        row["peak_name"],
                        row["range_text"],
                        f"{row['corrected_area']:.6f}",
                        f"{row['positive_area']:.6f}",
                        row["ratio_text"],
                        row["source"],
                        row["file_path"],
                    ]
                )
        messagebox.showinfo("导出成功", f"已导出到:\n{path}")

    def show_summary_window(self):
        rows = self._rows_for_export()
        if not rows:
            messagebox.showwarning("暂无汇总", "请先执行批量计算或记录峰数据。")
            return

        if self.summary_window is None or not self.summary_window.winfo_exists():
            self.summary_window, self.summary_tree = create_summary_window(
                self.root,
                self._close_summary_window,
                self.sort_summary_rows,
            )
        else:
            self.summary_window.deiconify()
            self.summary_window.lift()

        self._populate_summary_tree(rows)

    def sort_summary_rows(self, column: str):
        if self.summary_sort_column == column:
            self.summary_sort_desc = not self.summary_sort_desc
        else:
            self.summary_sort_column = column
            self.summary_sort_desc = False
        self._populate_summary_tree(self._rows_for_export())

    def _populate_summary_tree(self, rows: list[dict]):
        if not self._has_live_summary_tree():
            return
        populate_summary_tree(self.summary_tree, rows, self.summary_sort_column, self.summary_sort_desc)

    def _has_live_summary_tree(self) -> bool:
        return has_live_summary_tree(self.summary_tree)

    def _close_summary_window(self):
        if self.summary_window is not None and self.summary_window.winfo_exists():
            self.summary_window.destroy()
        self.summary_window = None
        self.summary_tree = None
