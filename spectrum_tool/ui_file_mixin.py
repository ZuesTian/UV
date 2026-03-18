import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional

import numpy as np

from .io_utils import read_spectrum
from .models import SpectrumDocument
from .ui_constants import DEFAULT_RANGE_MAX, DEFAULT_RANGE_MIN


class UiFileMixin:
    def open_file(self):
        paths = filedialog.askopenfilenames(
            title="打开光谱文件",
            filetypes=[("文本/CSV", "*.txt *.csv"), ("所有文件", "*.*")],
        )
        if paths:
            self.load_files([Path(item) for item in paths], append=False)

    def append_files(self):
        paths = filedialog.askopenfilenames(
            title="追加光谱文件",
            filetypes=[("文本/CSV", "*.txt *.csv"), ("所有文件", "*.*")],
        )
        if paths:
            self.load_files([Path(item) for item in paths], append=True)

    def clear_files(self):
        self.documents = []
        self.current_doc_index = None
        self.summary_rows = []
        self.overlay_preview_results = {}
        self.root.title("光谱面积计算工具")
        self.file_combo["values"] = []
        self.current_file_name.set("")
        self.loaded_files_text.set("已加载文件: 0")
        self.baseline_peak.set("")
        self.view_xmin.set("")
        self.view_xmax.set("")
        self.view_ymin.set("")
        self.view_ymax.set("")
        self.sel_min.set(f"{DEFAULT_RANGE_MIN:.3f}")
        self.sel_max.set(f"{DEFAULT_RANGE_MAX:.3f}")
        self.compare_list.delete(0, tk.END)
        self.records_list.delete(0, tk.END)
        self.baseline_combo["values"] = []
        self.overlay_summary.set("图谱对比: 当前仅显示活动文件")
        self.compare_text.set("对比结果: 暂无记录")
        self.highlight_peak.set("当前峰面积(扣基线): -")
        self.result_raw.set("原始面积: -")
        self.result_base.set("基线面积: -")
        self.result_corr.set("扣基线面积: -")
        self.result_pos.set("仅正面积: -")
        self.result_points.set("数据点数: -")
        self.ax.clear()
        self.ax.set_xlabel("波长 (nm)")
        self.ax.set_ylabel("吸收值")
        self.ax.grid(alpha=0.25)
        if self._has_live_summary_tree():
            self.summary_tree.delete(*self.summary_tree.get_children())
        self.canvas.draw_idle()

    def load_files(self, paths: list[Path], append: bool):
        existing_paths = {doc.path.resolve(): idx for idx, doc in enumerate(self.documents)} if append else {}
        documents = list(self.documents) if append else []
        failures: list[str] = []
        added_any = False

        for path in paths:
            resolved = path.resolve()
            if resolved in existing_paths:
                continue
            try:
                x, y = read_spectrum(path)
            except Exception as exc:
                failures.append(f"{path.name}: {exc}")
                continue
            doc = self._create_document(path, x, y)
            documents.append(doc)
            existing_paths[resolved] = len(documents) - 1
            added_any = True

        if not documents:
            messagebox.showerror("加载失败", "\n".join(failures) if failures else "未选择可加载文件。")
            return

        self.documents = documents
        self.loaded_files_text.set(f"已加载文件: {len(self.documents)}")
        self.file_combo["values"] = self._file_display_names()
        self._refresh_compare_list()

        if failures:
            messagebox.showwarning("部分文件未加载", "\n".join(failures))

        if self.current_doc_index is None or not append or added_any:
            self.switch_document(0 if self.current_doc_index is None or not append else len(self.documents) - 1)
        else:
            self.switch_document(self.current_doc_index)

    def _create_document(self, path: Path, x: np.ndarray, y: np.ndarray) -> SpectrumDocument:
        x_min = float(x.min())
        x_max = float(x.max())
        sel_min = max(DEFAULT_RANGE_MIN, x_min)
        sel_max = min(DEFAULT_RANGE_MAX, x_max)
        if sel_min >= sel_max:
            sel_min = x_min
            sel_max = x_max
        return SpectrumDocument(path=path, x=x, y=y, sel_min=sel_min, sel_max=sel_max)

    def _file_display_names(self) -> list[str]:
        return [f"{idx + 1}. {doc.path.name}" for idx, doc in enumerate(self.documents)]

    def _refresh_compare_list(self):
        self.compare_list.delete(0, tk.END)
        for idx, label in enumerate(self._file_display_names()):
            suffix = " [当前]" if idx == self.current_doc_index else ""
            self.compare_list.insert(tk.END, f"{label}{suffix}")
            if self.documents[idx].compare_enabled:
                self.compare_list.selection_set(idx)

    def on_compare_selection_change(self, _event=None):
        selected = set(self.compare_list.curselection())
        for idx, doc in enumerate(self.documents):
            doc.compare_enabled = idx in selected
        self.compute_and_draw()

    def select_all_compare_files(self):
        self.compare_list.selection_set(0, tk.END)
        self.on_compare_selection_change()

    def clear_compare_selection(self):
        self.compare_list.selection_clear(0, tk.END)
        self.on_compare_selection_change()

    def select_only_current_file(self):
        self.compare_list.selection_clear(0, tk.END)
        if self.current_doc_index is not None:
            self.compare_list.selection_set(self.current_doc_index)
        self.on_compare_selection_change()

    def get_overlay_indices(self) -> list[int]:
        indices = [idx for idx, doc in enumerate(self.documents) if doc.compare_enabled]
        if self.current_doc_index is not None and self.current_doc_index not in indices:
            indices.insert(0, self.current_doc_index)
        return indices

    def _update_overlay_summary(self):
        indices = self.get_overlay_indices()
        if not indices:
            self.overlay_summary.set("图谱对比: 当前仅显示活动文件")
            return
        if len(indices) == 1:
            self.overlay_summary.set(f"图谱对比: 当前显示 1 个文件 ({self.documents[indices[0]].path.name})")
            return
        self.overlay_summary.set(f"图谱对比: 当前叠加 {len(indices)} 个文件")

    def on_file_select(self, _event=None):
        index = self.file_combo.current()
        if index >= 0:
            self.switch_document(index)

    def switch_document(self, index: int):
        if not (0 <= index < len(self.documents)):
            return

        self._save_current_document_state()

        doc = self.documents[index]
        self.current_doc_index = index
        self.current_file_name.set(self._file_display_names()[index])
        self.file_combo.current(index)
        self.root.title(f"光谱面积计算工具 - {doc.path.name}")

        self.sel_min.set(f"{doc.sel_min:.3f}")
        self.sel_max.set(f"{doc.sel_max:.3f}")
        self.baseline_peak.set(doc.baseline_peak_name)
        self._refresh_records_list()
        self._refresh_baseline_options()
        self._refresh_compare_list()
        self.compute_and_draw()

    def _save_current_document_state(self):
        doc = self.get_current_document()
        if doc is None:
            return
        doc.baseline_peak_name = self.baseline_peak.get().strip()
        doc.view_limits = self._get_current_view_limits()
        try:
            doc.sel_min = float(self.sel_min.get())
            doc.sel_max = float(self.sel_max.get())
        except ValueError:
            pass

    def _get_current_view_limits(self) -> Optional[tuple[float, float, float, float]]:
        if self.current_doc_index is None:
            return None
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        return float(x0), float(x1), float(y0), float(y1)

    def get_current_document(self) -> Optional[SpectrumDocument]:
        if self.current_doc_index is None:
            return None
        if not (0 <= self.current_doc_index < len(self.documents)):
            return None
        return self.documents[self.current_doc_index]
