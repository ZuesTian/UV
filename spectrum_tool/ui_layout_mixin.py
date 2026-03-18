import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector

from .ui_constants import (
    COMPARE_LIST_HEIGHT,
    DEFAULT_WINDOW_HEIGHT_RATIO,
    DEFAULT_WINDOW_WIDTH_RATIO,
    HIGHLIGHT_COLOR,
    HIGHLIGHT_FONT_SIZE,
    LEFT_PANEL_WIDTH,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    RIGHT_PANEL_WIDTH,
)


class UiLayoutMixin:
    def _set_responsive_geometry(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = max(int(screen_width * DEFAULT_WINDOW_WIDTH_RATIO), MIN_WINDOW_WIDTH)
        window_height = max(int(screen_height * DEFAULT_WINDOW_HEIGHT_RATIO), MIN_WINDOW_HEIGHT)
        x_position = max((screen_width - window_width) // 2, 0)
        y_position = max((screen_height - window_height) // 2, 0)
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        self.root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=(8, 8, 8, 6))
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(3, weight=1)

        ttk.Button(top, text="打开文件", command=self.open_file).grid(row=0, column=0, padx=(0, 8), sticky="w")
        ttk.Button(top, text="追加文件", command=self.append_files).grid(row=0, column=1, padx=(0, 12), sticky="w")

        ttk.Label(top, text="当前文件:").grid(row=0, column=2, sticky="w")
        self.file_combo = ttk.Combobox(
            top,
            textvariable=self.current_file_name,
            state="readonly",
            values=[],
            width=40,
        )
        self.file_combo.grid(row=0, column=3, padx=(6, 12), sticky="ew")
        self.file_combo.bind("<<ComboboxSelected>>", self.on_file_select)
        ttk.Label(top, textvariable=self.loaded_files_text).grid(row=0, column=4, padx=(0, 12), sticky="w")

        center = ttk.Frame(self.root, padding=(8, 0, 8, 0))
        center.grid(row=1, column=0, sticky="nsew")
        center.columnconfigure(0, weight=1)
        center.rowconfigure(0, weight=1)

        self.main_paned = ttk.Panedwindow(center, orient=tk.HORIZONTAL)
        self.main_paned.grid(row=0, column=0, sticky="nsew")

        left_panel = ttk.Frame(self.main_paned, width=LEFT_PANEL_WIDTH)
        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(0, weight=1)
        self.left_paned = ttk.Panedwindow(left_panel, orient=tk.VERTICAL)
        self.left_paned.grid(row=0, column=0, sticky="nsew")

        file_section = ttk.LabelFrame(left_panel, text="文件管理", padding=10)
        file_section.columnconfigure(0, weight=1)
        file_section.rowconfigure(1, weight=1)
        self._build_file_tab(file_section)

        calc_section = ttk.LabelFrame(left_panel, text="积分计算", padding=10)
        calc_section.columnconfigure(0, weight=1)
        self._build_calc_tab(calc_section)

        self.left_paned.add(file_section, weight=2)
        self.left_paned.add(calc_section, weight=3)

        plot_wrap = ttk.Frame(self.main_paned)
        plot_wrap.columnconfigure(0, weight=1)
        plot_wrap.rowconfigure(0, weight=1)

        self.fig = Figure(dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("波长 (nm)")
        self.ax.set_ylabel("吸收值")
        self.ax.grid(alpha=0.25)

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_wrap)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        right_panel = ttk.Frame(self.main_paned, width=RIGHT_PANEL_WIDTH)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        self._build_peak_tab(right_panel)

        self.main_paned.add(left_panel, weight=0)
        self.main_paned.add(plot_wrap, weight=1)
        self.main_paned.add(right_panel, weight=0)

        bottom = ttk.Frame(self.root, padding=8)
        bottom.grid(row=2, column=0, sticky="ew")
        ttk.Label(bottom, text="视图范围  X最小:").pack(side=tk.LEFT)
        ttk.Entry(bottom, textvariable=self.view_xmin, width=10).pack(side=tk.LEFT)
        ttk.Label(bottom, text="  X最大:").pack(side=tk.LEFT)
        ttk.Entry(bottom, textvariable=self.view_xmax, width=10).pack(side=tk.LEFT)
        ttk.Label(bottom, text="  Y最小:").pack(side=tk.LEFT)
        ttk.Entry(bottom, textvariable=self.view_ymin, width=10).pack(side=tk.LEFT)
        ttk.Label(bottom, text="  Y最大:").pack(side=tk.LEFT)
        ttk.Entry(bottom, textvariable=self.view_ymax, width=10).pack(side=tk.LEFT)
        ttk.Button(bottom, text="应用视图", command=self.apply_view_from_entry).pack(side=tk.LEFT, padx=6)
        ttk.Button(bottom, text="重置视图", command=self.reset_view_range).pack(side=tk.LEFT)

        self.root.after_idle(self._initialize_pane_sizes)

    def _build_file_tab(self, parent: ttk.Frame):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        ttk.Label(
            parent,
            text="文件列表同时也是多谱对比选择区。勾选后会叠加显示并参与当前区域面积对比。",
            wraplength=330,
            justify="left",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 8))

        list_frame = ttk.Frame(parent)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        compare_scrollbar = ttk.Scrollbar(list_frame)
        compare_scrollbar.grid(row=0, column=1, sticky="ns")
        self.compare_list = tk.Listbox(
            list_frame,
            selectmode=tk.MULTIPLE,
            exportselection=False,
            yscrollcommand=compare_scrollbar.set,
            height=COMPARE_LIST_HEIGHT,
        )
        self.compare_list.grid(row=0, column=0, sticky="nsew")
        compare_scrollbar.config(command=self.compare_list.yview)
        self.compare_list.bind("<<ListboxSelect>>", self.on_compare_selection_change)

        button_row = ttk.Frame(parent)
        button_row.grid(row=2, column=0, sticky="ew", pady=(8, 6))
        ttk.Button(button_row, text="全选", command=self.select_all_compare_files).pack(side=tk.LEFT)
        ttk.Button(button_row, text="清空", command=self.clear_compare_selection).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(button_row, text="仅当前", command=self.select_only_current_file).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(button_row, text="清空列表", command=self.clear_files).pack(side=tk.LEFT, padx=(6, 0))

        ttk.Label(parent, textvariable=self.overlay_summary, wraplength=330, justify="left").grid(
            row=3, column=0, sticky="ew"
        )

    def _build_calc_tab(self, parent: ttk.Frame):
        parent.columnconfigure(0, weight=1)

        range_frame = ttk.LabelFrame(parent, text="积分范围")
        range_frame.grid(row=0, column=0, sticky="ew")
        ttk.Label(range_frame, text="最小值:").grid(row=0, column=0, sticky="w", padx=(8, 4), pady=8)
        ttk.Entry(range_frame, textvariable=self.sel_min, width=12).grid(row=0, column=1, sticky="w", pady=8)
        ttk.Label(range_frame, text="最大值:").grid(row=0, column=2, sticky="w", padx=(12, 4), pady=8)
        ttk.Entry(range_frame, textvariable=self.sel_max, width=12).grid(row=0, column=3, sticky="w", pady=8)

        action_row = ttk.Frame(parent)
        action_row.grid(row=1, column=0, sticky="ew", pady=(10, 10))
        ttk.Button(action_row, text="应用范围", command=self.apply_range_from_entry).pack(side=tk.LEFT)
        ttk.Button(action_row, text="计算当前", command=self.compute_and_draw).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(action_row, text="批量计算所有文件", command=self.batch_calculate_all).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(action_row, text="记录当前峰", command=self.record_current_peak).pack(side=tk.LEFT, padx=(6, 0))

        summary_frame = ttk.LabelFrame(parent, text="当前结果")
        summary_frame.grid(row=2, column=0, sticky="ew")
        summary_frame.columnconfigure(0, weight=1)

        tk.Label(
            summary_frame,
            textvariable=self.highlight_peak,
            fg=HIGHLIGHT_COLOR,
            font=("Microsoft YaHei", HIGHLIGHT_FONT_SIZE, "bold"),
            justify="left",
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))
        ttk.Label(summary_frame, textvariable=self.result_raw).grid(row=1, column=0, sticky="w", padx=8)
        ttk.Label(summary_frame, textvariable=self.result_base).grid(row=2, column=0, sticky="w", padx=8)
        ttk.Label(summary_frame, textvariable=self.result_corr).grid(row=3, column=0, sticky="w", padx=8)
        ttk.Label(summary_frame, textvariable=self.result_pos).grid(row=4, column=0, sticky="w", padx=8)
        ttk.Label(summary_frame, textvariable=self.result_points).grid(row=5, column=0, sticky="w", padx=8)
        ttk.Label(
            summary_frame,
            text="提示: 鼠标滚轮可缩放，图上拖拽可选择积分范围。",
            wraplength=330,
            justify="left",
        ).grid(row=6, column=0, sticky="ew", padx=8, pady=(4, 8))

    def _build_peak_tab(self, parent: ttk.Frame):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        self.right_paned = ttk.Panedwindow(parent, orient=tk.VERTICAL)
        self.right_paned.grid(row=0, column=0, sticky="nsew")

        records_frame = ttk.LabelFrame(parent, text="峰记录", padding=8)
        records_frame.columnconfigure(0, weight=1)
        records_frame.rowconfigure(0, weight=1)

        list_frame = ttk.Frame(records_frame)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=6, pady=(6, 4))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.records_list = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=10)
        self.records_list.grid(row=0, column=0, sticky="nsew")
        scrollbar.config(command=self.records_list.yview)
        self.records_list.bind("<<ListboxSelect>>", self.on_record_select)

        baseline_row = ttk.Frame(records_frame)
        baseline_row.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 4))
        baseline_row.columnconfigure(1, weight=1)
        ttk.Label(baseline_row, text="基准峰:").grid(row=0, column=0, sticky="w")
        self.baseline_combo = ttk.Combobox(
            baseline_row,
            textvariable=self.baseline_peak,
            state="readonly",
            values=[],
        )
        self.baseline_combo.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self.baseline_combo.bind("<<ComboboxSelected>>", self.on_baseline_select)

        compare_frame = ttk.LabelFrame(parent, text="峰面积比较", padding=8)
        compare_frame.columnconfigure(0, weight=1)
        self.pie_fig = Figure(figsize=(3.5, 2.4), dpi=80)
        self.pie_ax = self.pie_fig.add_subplot(111)
        self.pie_canvas = FigureCanvasTkAgg(self.pie_fig, master=compare_frame)
        self.pie_canvas.get_tk_widget().grid(row=0, column=0, sticky="ew", padx=4, pady=4)

        ttk.Label(compare_frame, textvariable=self.compare_text, wraplength=320, justify="right", anchor="e").grid(
            row=1, column=0, sticky="sew", padx=4, pady=(4, 8)
        )

        action_frame = ttk.LabelFrame(compare_frame, text="汇总与导出", padding=8)
        action_frame.grid(row=2, column=0, sticky="ew")
        action_row = ttk.Frame(action_frame)
        action_row.grid(row=0, column=0, sticky="ew")
        ttk.Button(action_row, text="删除选中记录", command=self.delete_selected_record).pack(side=tk.LEFT)
        ttk.Button(action_row, text="查看汇总", command=self.show_summary_window).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(action_row, text="导出 CSV", command=self.export_summary_csv).pack(side=tk.LEFT, padx=(6, 0))

        self.right_paned.add(records_frame, weight=3)
        self.right_paned.add(compare_frame, weight=2)

    def _connect_plot_events(self):
        self.span = SpanSelector(
            self.ax,
            self.on_span_select,
            "horizontal",
            useblit=True,
            props=dict(alpha=0.2, facecolor="tab:orange"),
            interactive=True,
            drag_from_anywhere=True,
        )
        self.canvas.mpl_connect("scroll_event", self.on_scroll_zoom)

    def _initialize_pane_sizes(self, retries: int = 5):
        try:
            total_width = max(self.main_paned.winfo_width(), self.root.winfo_width())
            left_height = self.left_paned.winfo_height()
            right_height = self.right_paned.winfo_height()

            if total_width < 200 or left_height < 100 or right_height < 100:
                if retries > 0:
                    self.root.after(120, lambda: self._initialize_pane_sizes(retries - 1))
                return

            if total_width > 0:
                left_width = min(max(int(total_width * 0.22), 220), 320)
                right_width = min(max(int(total_width * 0.24), 240), 340)
                self.main_paned.sashpos(0, left_width)
                self.main_paned.sashpos(1, max(total_width - right_width, left_width + 240))

            if left_height > 0:
                file_height = min(max(int(left_height * 0.38), 170), 240)
                self.left_paned.sashpos(0, file_height)

            if right_height > 0:
                records_height = min(max(int(right_height * 0.52), 220), 380)
                self.right_paned.sashpos(0, records_height)
        except tk.TclError:
            return
