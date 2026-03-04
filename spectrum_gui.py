import csv
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 应用常量
DEFAULT_WINDOW_WIDTH_RATIO = 0.75
DEFAULT_WINDOW_HEIGHT_RATIO = 0.8
MIN_WINDOW_WIDTH = 1000
MIN_WINDOW_HEIGHT = 600
DEFAULT_RANGE_MIN = 600
DEFAULT_RANGE_MAX = 800
ZOOM_SCALE_BASE = 1.15
HIGHLIGHT_COLOR = "#C62828"
HIGHLIGHT_FONT_SIZE = 13


class SpectrumApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("光谱面积计算工具")
        
        # 设置响应式窗口尺寸
        self._set_responsive_geometry()
        
        self.file_path: Optional[Path] = None
        self.x = np.array([])
        self.y = np.array([])

        self.sel_min = tk.StringVar(value=str(DEFAULT_RANGE_MIN))
        self.sel_max = tk.StringVar(value=str(DEFAULT_RANGE_MAX))
        self.view_xmin = tk.StringVar(value="")
        self.view_xmax = tk.StringVar(value="")
        self.view_ymin = tk.StringVar(value="")
        self.view_ymax = tk.StringVar(value="")

        self.result_raw = tk.StringVar(value="原始面积: -")
        self.result_base = tk.StringVar(value="基线面积: -")
        self.result_corr = tk.StringVar(value="扣基线面积: -")
        self.result_pos = tk.StringVar(value="仅正面积: -")
        self.result_points = tk.StringVar(value="数据点数: -")
        self.highlight_peak = tk.StringVar(value="当前峰面积(扣基线): -")
        self.compare_text = tk.StringVar(value="对比结果: 暂无记录")

        self.current_corrected_area: Optional[float] = None
        self.peak_records: list = []

        self._build_ui()
        self._connect_plot_events()

    def _set_responsive_geometry(self):
        """根据屏幕分辨率设置窗口大小"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 计算窗口尺寸（屏幕的75%宽度和80%高度）
        window_width = max(int(screen_width * DEFAULT_WINDOW_WIDTH_RATIO), MIN_WINDOW_WIDTH)
        window_height = max(int(screen_height * DEFAULT_WINDOW_HEIGHT_RATIO), MIN_WINDOW_HEIGHT)
        
        # 居中显示
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        self.root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

    def _build_ui(self):
        """构建用户界面"""
        # 顶部工具栏 - 视图控制
        top = ttk.Frame(self.root, padding=(8, 8, 8, 6))
        top.pack(fill=tk.X)
        ttk.Button(top, text="打开文件", command=self.open_file).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(top, text="图谱可视范围  X最小:").pack(side=tk.LEFT)
        ttk.Entry(top, textvariable=self.view_xmin, width=10).pack(side=tk.LEFT)
        ttk.Label(top, text="  X最大:").pack(side=tk.LEFT)
        ttk.Entry(top, textvariable=self.view_xmax, width=10).pack(side=tk.LEFT)
        ttk.Label(top, text="  Y最小:").pack(side=tk.LEFT)
        ttk.Entry(top, textvariable=self.view_ymin, width=10).pack(side=tk.LEFT)
        ttk.Label(top, text="  Y最大:").pack(side=tk.LEFT)
        ttk.Entry(top, textvariable=self.view_ymax, width=10).pack(side=tk.LEFT)
        ttk.Button(top, text="应用视图", command=self.apply_view_from_entry).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="重置视图", command=self.reset_view_range).pack(side=tk.LEFT)

        # 中间区域 - 图表和侧边栏
        center = ttk.Frame(self.root, padding=(8, 0, 8, 0))
        center.pack(fill=tk.BOTH, expand=True)

        # 左侧 - 主图表区域
        plot_wrap = ttk.Frame(center)
        plot_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.fig = Figure(dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("波长 (nm)")
        self.ax.set_ylabel("吸收值")
        self.ax.grid(alpha=0.25)

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_wrap)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 右侧 - 峰记录和对比
        right = ttk.Frame(center, padding=(10, 0, 0, 0))
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)
        right.config(width=280)

        ttk.Label(right, text="峰面积比例 (列表峰 vs 基准峰)").pack(anchor="w")
        self.pie_fig = Figure(figsize=(3.5, 2.5), dpi=80)
        self.pie_ax = self.pie_fig.add_subplot(111)
        self.pie_canvas = FigureCanvasTkAgg(self.pie_fig, master=right)
        self.pie_canvas.get_tk_widget().pack(fill=tk.X, pady=(4, 10))

        ttk.Label(right, text="峰记录").pack(anchor="w")
        list_frame = ttk.Frame(right)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.records_list = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.records_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.records_list.yview)
        self.records_list.bind("<<ListboxSelect>>", self.on_record_select)
        
        baseline_row = ttk.Frame(right)
        baseline_row.pack(fill=tk.X, pady=(6, 2))
        ttk.Label(baseline_row, text="基准峰:").pack(side=tk.LEFT)
        self.baseline_peak = tk.StringVar(value="")
        self.baseline_combo = ttk.Combobox(
            baseline_row,
            textvariable=self.baseline_peak,
            state="readonly",
            values=[],
        )
        self.baseline_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
        self.baseline_combo.bind("<<ComboboxSelected>>", self.on_record_select)
        ttk.Button(right, text="删除选中记录", command=self.delete_selected_record).pack(fill=tk.X, pady=(6, 0))

        # 底部工具栏 - 积分控制
        bottom = ttk.Frame(self.root, padding=8)
        bottom.pack(fill=tk.X)
        ttk.Label(bottom, text="积分范围  最小值:").pack(side=tk.LEFT)
        ttk.Entry(bottom, textvariable=self.sel_min, width=10).pack(side=tk.LEFT)
        ttk.Label(bottom, text="  最大值:").pack(side=tk.LEFT)
        ttk.Entry(bottom, textvariable=self.sel_max, width=10).pack(side=tk.LEFT)
        ttk.Button(bottom, text="应用范围", command=self.apply_range_from_entry).pack(side=tk.LEFT, padx=6)
        ttk.Button(bottom, text="计算面积", command=self.compute_and_draw).pack(side=tk.LEFT)
        ttk.Button(bottom, text="记录当前峰", command=self.record_current_peak).pack(side=tk.LEFT, padx=(12, 0))

        # 信息显示区域
        info = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        info.pack(fill=tk.X)
        tk.Label(
            info, 
            textvariable=self.highlight_peak, 
            fg=HIGHLIGHT_COLOR, 
            font=("Microsoft YaHei", HIGHLIGHT_FONT_SIZE, "bold")
        ).pack(anchor="w")
        ttk.Label(info, textvariable=self.compare_text).pack(anchor="w", pady=(1, 4))
        ttk.Label(info, textvariable=self.result_raw).pack(anchor="w")
        ttk.Label(info, textvariable=self.result_base).pack(anchor="w")
        ttk.Label(info, textvariable=self.result_corr).pack(anchor="w")
        ttk.Label(info, textvariable=self.result_pos).pack(anchor="w")
        ttk.Label(info, textvariable=self.result_points).pack(anchor="w")
        ttk.Label(info, text="提示: 鼠标滚轮可缩放，图上拖拽可选择积分范围。").pack(anchor="w", pady=(4, 0))

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

    def on_scroll_zoom(self, event):
        """处理鼠标滚轮缩放事件"""
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return
        if event.button not in ("up", "down"):
            return

        scale = 1 / ZOOM_SCALE_BASE if event.button == "up" else ZOOM_SCALE_BASE

        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        xdata = float(event.xdata)
        ydata = float(event.ydata)

        new_x0 = xdata - (xdata - x0) * scale
        new_x1 = xdata + (x1 - xdata) * scale
        new_y0 = ydata - (ydata - y0) * scale
        new_y1 = ydata + (y1 - ydata) * scale

        self.ax.set_xlim(new_x0, new_x1)
        self.ax.set_ylim(new_y0, new_y1)
        self._sync_view_entries_from_axes()
        self.canvas.draw_idle()

    def open_file(self):
        path = filedialog.askopenfilename(
            title="打开光谱文件",
            filetypes=[("文本/CSV", "*.txt *.csv"), ("所有文件", "*.*")],
        )
        if not path:
            return
        self.load_file(Path(path))

    def load_file(self, path: Path):
        try:
            x, y = self.read_spectrum(path)
        except Exception as exc:
            messagebox.showerror("加载失败", f"无法读取文件:\n{exc}")
            return

        self.file_path = path
        self.x = x
        self.y = y
        self.root.title(f"光谱面积计算工具 - {path.name}")

        self.ax.clear()
        self.ax.plot(self.x, self.y, lw=1.0, color="tab:blue", label="光谱")
        self.ax.set_xlabel("波长 (nm)")
        self.ax.set_ylabel("吸收值")
        self.ax.grid(alpha=0.25)
        self.ax.legend(loc="upper right")
        self.reset_view_range(update_entries=True)
        self.canvas.draw_idle()
        self.current_corrected_area = None
        self.highlight_peak.set("当前峰面积(扣基线): -")
        self.compare_text.set("对比结果: 暂无记录")
        self.update_compare_view()

        self.compute_and_draw()

    @staticmethod
    def read_spectrum(path: Path):
        encodings = ["utf-8-sig", "gb18030", "utf-16"]
        rows = None

        for enc in encodings:
            try:
                with path.open("r", encoding=enc, errors="strict") as f:
                    rows = list(csv.reader(f))
                break
            except Exception:
                rows = None

        if rows is None:
            with path.open("r", encoding="gb18030", errors="ignore") as f:
                rows = list(csv.reader(f))

        xs = []
        ys = []
        for row in rows:
            if len(row) < 2:
                continue
            try:
                xv = float(row[0])
                yv = float(row[1])
            except Exception:
                continue
            xs.append(xv)
            ys.append(yv)

        if len(xs) < 2:
            raise ValueError("未找到可解析的数值列 (x, y)。")

        x = np.array(xs, dtype=float)
        y = np.array(ys, dtype=float)

        order = np.argsort(x)
        x = x[order]
        y = y[order]
        return x, y

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
        if self.x.size < 2:
            return
        try:
            self._apply_axis_limits_from_entries()
        except Exception as exc:
            messagebox.showerror("视图范围错误", str(exc))
            return
        self._sync_view_entries_from_axes()
        self.canvas.draw_idle()

    def reset_view_range(self, update_entries: bool = True):
        if self.x.size < 2:
            return

        x_min = float(self.x.min())
        x_max = float(self.x.max())
        y_min = float(self.y.min())
        y_max = float(self.y.max())
        if np.isclose(y_min, y_max):
            pad = max(abs(y_min) * 0.05, 1e-3)
        else:
            pad = (y_max - y_min) * 0.05
        y_low = y_min - pad
        y_high = y_max + pad

        self.ax.set_xlim(x_min, x_max)
        self.ax.set_ylim(y_low, y_high)

        if update_entries:
            self.view_xmin.set(f"{x_min:.3f}")
            self.view_xmax.set(f"{x_max:.3f}")
            self.view_ymin.set(f"{y_low:.6f}")
            self.view_ymax.set(f"{y_high:.6f}")

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
            raise ValueError("请同时填写X轴最小值和最大值。")

        if y_min_str and y_max_str:
            y_min = float(y_min_str)
            y_max = float(y_max_str)
            if y_min >= y_max:
                raise ValueError("Y轴最小值必须小于最大值。")
            self.ax.set_ylim(y_min, y_max)
        elif y_min_str or y_max_str:
            raise ValueError("请同时填写Y轴最小值和最大值。")

    def _sync_view_entries_from_axes(self):
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        self.view_xmin.set(f"{x0:.3f}")
        self.view_xmax.set(f"{x1:.3f}")
        self.view_ymin.set(f"{y0:.6f}")
        self.view_ymax.set(f"{y1:.6f}")

    def record_current_peak(self):
        if self.current_corrected_area is None:
            messagebox.showwarning("无法记录", "请先加载数据并完成一次积分计算。")
            return
        try:
            lo = float(self.sel_min.get())
            hi = float(self.sel_max.get())
        except Exception:
            lo, hi = 0.0, 0.0
        lo, hi = sorted((lo, hi))
        name = f"峰{len(self.peak_records) + 1}"
        record = {
            "name": name,
            "area": float(self.current_corrected_area),
            "xmin": lo,
            "xmax": hi,
        }
        self.peak_records.append(record)
        self.records_list.insert(tk.END, f"{name} | 面积={record['area']:.6f} | 范围={lo:.2f}-{hi:.2f}")
        self.records_list.selection_clear(0, tk.END)
        self.records_list.selection_set(tk.END)
        self._refresh_baseline_options()
        self.update_compare_view()

    def on_record_select(self, _event=None):
        self.update_compare_view()

    def delete_selected_record(self):
        selection = self.records_list.curselection()
        if not selection:
            return
        idx = int(selection[0])
        self.records_list.delete(idx)
        self.peak_records.pop(idx)
        self._refresh_baseline_options()
        self.update_compare_view()

    def update_compare_view(self):
        if not self.peak_records:
            self.compare_text.set("对比结果: 暂无已记录峰，可点击“记录当前峰”后对比")
            self._draw_pie_chart(None, None, "基准峰")
            return

        selection = self.records_list.curselection()
        if selection:
            target_idx = int(selection[0])
        else:
            target_idx = len(self.peak_records) - 1
            self.records_list.selection_clear(0, tk.END)
            self.records_list.selection_set(target_idx)

        baseline_name = self.baseline_peak.get().strip()
        base_idx = self._find_record_index_by_name(baseline_name)
        if base_idx is None:
            base_idx = 0
            self.baseline_peak.set(str(self.peak_records[0]["name"]))

        target = self.peak_records[target_idx]
        baseline = self.peak_records[base_idx]
        target_area = float(target["area"])
        base_area = float(baseline["area"])
        target_name = str(target["name"])
        base_name = str(baseline["name"])

        if np.isclose(base_area, 0.0):
            ratio_text = f"对比结果: 基准峰 {base_name} 面积为0，无法计算比例"
        else:
            ratio = target_area / base_area * 100.0
            ratio_text = f"对比结果: {target_name} / {base_name} = {ratio:.2f}%"
        self.compare_text.set(ratio_text)
        self._draw_pie_chart(abs(target_area), abs(base_area), base_name, target_name)

    def _refresh_baseline_options(self):
        names = [str(item["name"]) for item in self.peak_records]
        self.baseline_combo["values"] = names
        if not names:
            self.baseline_peak.set("")
            return
        current_name = self.baseline_peak.get().strip()
        if current_name not in names:
            self.baseline_peak.set(names[0])

    def _find_record_index_by_name(self, name: str) -> Optional[int]:
        """根据名称查找峰记录索引"""
        for idx, record in enumerate(self.peak_records):
            if str(record["name"]) == name:
                return idx
        return None

    def _draw_pie_chart(
        self,
        target_value: Optional[float],
        base_value: Optional[float],
        base_name: str,
        target_name: str = "选中峰",
    ):
        """绘制峰面积比例饼图"""
        self.pie_ax.clear()
        if target_value is None:
            self.pie_ax.text(0.5, 0.5, "无数据", ha="center", va="center")
            self.pie_ax.set_axis_off()
            self.pie_canvas.draw_idle()
            return

        self.pie_ax.set_axis_on()
        if base_value is None or np.isclose(base_value, 0.0):
            values = [max(target_value, 1e-12)]
            labels = [target_name]
            colors = ["#ff8a65"]
        else:
            c = max(target_value, 1e-12)
            r = max(base_value, 1e-12)
            values = [c, r]
            labels = [target_name, base_name]
            colors = ["#ff8a65", "#64b5f6"]

        self.pie_ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90, colors=colors)
        self.pie_ax.set_title("面积比例(绝对值)")
        self.pie_canvas.draw_idle()

    @staticmethod
    def extract_segment(x: np.ndarray, y: np.ndarray, xmin: float, xmax: float):
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
            xs = np.array([xmin, xmax], dtype=float)
            ys = np.array([y0, y1], dtype=float)
            return xs, ys

        if xs[0] > xmin:
            y0 = np.interp(xmin, x, y)
            xs = np.insert(xs, 0, xmin)
            ys = np.insert(ys, 0, y0)
        elif xs[0] < xmin:
            xs[0] = xmin
            ys[0] = np.interp(xmin, x, y)

        if xs[-1] < xmax:
            y1 = np.interp(xmax, x, y)
            xs = np.append(xs, xmax)
            ys = np.append(ys, y1)
        elif xs[-1] > xmax:
            xs[-1] = xmax
            ys[-1] = np.interp(xmax, x, y)

        return xs, ys

    def compute_area(self, xmin: float, xmax: float):
        xs, ys = self.extract_segment(self.x, self.y, xmin, xmax)

        y_start = ys[0]
        y_end = ys[-1]
        baseline = y_start + (y_end - y_start) * (xs - xs[0]) / (xs[-1] - xs[0])
        corrected = ys - baseline

        raw_area = np.trapezoid(ys, xs)
        baseline_area = np.trapezoid(baseline, xs)
        corrected_area = np.trapezoid(corrected, xs)
        positive_area = np.trapezoid(np.clip(corrected, 0, None), xs)

        return {
            "xs": xs,
            "ys": ys,
            "baseline": baseline,
            "corrected": corrected,
            "raw_area": raw_area,
            "baseline_area": baseline_area,
            "corrected_area": corrected_area,
            "positive_area": positive_area,
            "points": len(xs),
        }

    def compute_and_draw(self):
        if self.x.size < 2:
            return

        try:
            xmin = float(self.sel_min.get())
            xmax = float(self.sel_max.get())
            lo, hi = sorted((xmin, xmax))
            result = self.compute_area(lo, hi)
        except Exception as exc:
            self.current_corrected_area = None
            self.result_raw.set(f"原始面积: 错误 ({exc})")
            self.result_base.set("基线面积: -")
            self.result_corr.set("扣基线面积: -")
            self.result_pos.set("仅正面积: -")
            self.result_points.set("数据点数: -")
            self.highlight_peak.set("当前峰面积(扣基线): -")
            self.update_compare_view()
            self.canvas.draw_idle()
            return

        self.sel_min.set(f"{lo:.3f}")
        self.sel_max.set(f"{hi:.3f}")

        self.result_raw.set(f"原始面积: {result['raw_area']:.6f}")
        self.result_base.set(f"基线面积: {result['baseline_area']:.6f}")
        self.result_corr.set(f"扣基线面积: {result['corrected_area']:.6f}")
        self.result_pos.set(f"仅正面积: {result['positive_area']:.6f}")
        self.result_points.set(f"数据点数: {result['points']}")
        self.current_corrected_area = float(result["corrected_area"])
        self.highlight_peak.set(f"当前峰面积(扣基线): {self.current_corrected_area:.6f}")

        self.ax.clear()
        self.ax.plot(self.x, self.y, lw=1.0, color="tab:blue", label="光谱")
        self.ax.plot(result["xs"], result["baseline"], "--", lw=1.2, color="tab:red", label="基线")
        self.ax.fill_between(result["xs"], result["ys"], result["baseline"], color="tab:orange", alpha=0.25)

        self.ax.axvline(lo, color="gray", lw=0.8, alpha=0.6)
        self.ax.axvline(hi, color="gray", lw=0.8, alpha=0.6)

        self.ax.set_xlabel("波长 (nm)")
        self.ax.set_ylabel("吸收值")
        self.ax.set_title(f"当前选择范围: {lo:.3f} - {hi:.3f} nm")
        self.ax.grid(alpha=0.25)
        self.ax.legend(loc="upper right")
        try:
            self._apply_axis_limits_from_entries()
        except Exception:
            # 如果输入了非法可视范围，保留自动缩放显示，避免打断面积计算流程
            pass
        self.update_compare_view()
        self.canvas.draw_idle()


def main():
    """主程序入口"""
    root = tk.Tk()
    app = SpectrumApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
