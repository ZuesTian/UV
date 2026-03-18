import tkinter as tk
from typing import Optional

from .models import SpectrumDocument
from .ui_constants import DEFAULT_RANGE_MAX, DEFAULT_RANGE_MIN
from .ui_file_mixin import UiFileMixin
from .ui_layout_mixin import UiLayoutMixin
from .ui_peak_mixin import UiPeakMixin
from .ui_summary_mixin import UiSummaryMixin
from .ui_view_mixin import UiViewMixin


class SpectrumApp(UiLayoutMixin, UiFileMixin, UiViewMixin, UiPeakMixin, UiSummaryMixin):
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("\u5149\u8c31\u9762\u79ef\u8ba1\u7b97\u5de5\u5177")

        self.documents: list[SpectrumDocument] = []
        self.current_doc_index: Optional[int] = None
        self.summary_rows: list[dict] = []
        self.summary_sort_column = "file_name"
        self.summary_sort_desc = False
        self.summary_window: Optional[tk.Toplevel] = None
        self.summary_tree = None
        self.overlay_preview_results: dict[int, dict] = {}

        self.sel_min = tk.StringVar(value=f"{DEFAULT_RANGE_MIN:.3f}")
        self.sel_max = tk.StringVar(value=f"{DEFAULT_RANGE_MAX:.3f}")
        self.view_xmin = tk.StringVar(value="")
        self.view_xmax = tk.StringVar(value="")
        self.view_ymin = tk.StringVar(value="")
        self.view_ymax = tk.StringVar(value="")
        self.current_file_name = tk.StringVar(value="")
        self.loaded_files_text = tk.StringVar(value="\u5df2\u52a0\u8f7d\u6587\u4ef6: 0")
        self.overlay_summary = tk.StringVar(value="\u56fe\u8c31\u5bf9\u6bd4: \u5f53\u524d\u4ec5\u663e\u793a\u6d3b\u52a8\u6587\u4ef6")
        self.baseline_peak = tk.StringVar(value="")

        self.result_raw = tk.StringVar(value="\u539f\u59cb\u9762\u79ef: -")
        self.result_base = tk.StringVar(value="\u57fa\u7ebf\u9762\u79ef: -")
        self.result_corr = tk.StringVar(value="\u6263\u57fa\u7ebf\u9762\u79ef: -")
        self.result_pos = tk.StringVar(value="\u4ec5\u6b63\u9762\u79ef: -")
        self.result_points = tk.StringVar(value="\u6570\u636e\u70b9\u6570: -")
        self.highlight_peak = tk.StringVar(value="\u5f53\u524d\u5cf0\u9762\u79ef(\u6263\u57fa\u7ebf): -")
        self.compare_text = tk.StringVar(value="\u5bf9\u6bd4\u7ed3\u679c: \u6682\u65e0\u8bb0\u5f55")

        self._set_responsive_geometry()
        self._build_ui()
        self._connect_plot_events()


def main():
    root = tk.Tk()
    SpectrumApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
