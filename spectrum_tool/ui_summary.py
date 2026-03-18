import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

SUMMARY_COLUMNS = ("file_name", "peak_name", "range_text", "corrected_area", "positive_area", "ratio_text", "source")
SUMMARY_HEADINGS = {
    "file_name": "文件名",
    "peak_name": "峰名",
    "range_text": "积分范围",
    "corrected_area": "扣基线面积",
    "positive_area": "仅正面积",
    "ratio_text": "与基准比值",
    "source": "来源",
}
SUMMARY_WIDTHS = {
    "file_name": 220,
    "peak_name": 90,
    "range_text": 130,
    "corrected_area": 120,
    "positive_area": 120,
    "ratio_text": 110,
    "source": 80,
}


def has_live_summary_tree(tree: Optional[ttk.Treeview]) -> bool:
    return tree is not None and bool(tree.winfo_exists())


def create_summary_window(
    root: tk.Misc,
    on_close: Callable[[], None],
    on_sort: Callable[[str], None],
) -> tuple[tk.Toplevel, ttk.Treeview]:
    window = tk.Toplevel(root)
    window.title("批量计算汇总表")
    window.geometry("920x420")
    window.protocol("WM_DELETE_WINDOW", on_close)

    frame = ttk.Frame(window, padding=8)
    frame.pack(fill=tk.BOTH, expand=True)

    tree = ttk.Treeview(frame, columns=SUMMARY_COLUMNS, show="headings")
    for column in SUMMARY_COLUMNS:
        tree.heading(column, text=SUMMARY_HEADINGS[column], command=lambda col=column: on_sort(col))
        tree.column(column, width=SUMMARY_WIDTHS[column], anchor="center")

    y_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
    x_scroll = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=tree.xview)
    tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
    tree.grid(row=0, column=0, sticky="nsew")
    y_scroll.grid(row=0, column=1, sticky="ns")
    x_scroll.grid(row=1, column=0, sticky="ew")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)
    return window, tree


def populate_summary_tree(
    tree: ttk.Treeview,
    rows: list[dict],
    sort_column: str,
    sort_desc: bool,
) -> None:
    key_map = {
        "file_name": lambda item: item["file_name"],
        "peak_name": lambda item: item["peak_name"],
        "range_text": lambda item: item["range_text"],
        "corrected_area": lambda item: item["corrected_area"],
        "positive_area": lambda item: item["positive_area"],
        "ratio_text": lambda item: item["ratio_value"],
        "source": lambda item: item["source"],
    }
    ordered = sorted(rows, key=key_map[sort_column], reverse=sort_desc)
    tree.delete(*tree.get_children())
    for row in ordered:
        tree.insert(
            "",
            tk.END,
            values=(
                row["file_name"],
                row["peak_name"],
                row["range_text"],
                f"{row['corrected_area']:.6f}",
                f"{row['positive_area']:.6f}",
                row["ratio_text"],
                row["source"],
            ),
        )
