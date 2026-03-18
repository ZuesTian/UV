import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

DEFAULT_WINDOW_WIDTH_RATIO = 0.78
DEFAULT_WINDOW_HEIGHT_RATIO = 0.82
MIN_WINDOW_WIDTH = 1240
MIN_WINDOW_HEIGHT = 720
DEFAULT_RANGE_MIN = 600.0
DEFAULT_RANGE_MAX = 800.0
ZOOM_SCALE_BASE = 1.15
HIGHLIGHT_COLOR = "#C62828"
HIGHLIGHT_FONT_SIZE = 13
LEFT_PANEL_WIDTH = 300
RIGHT_PANEL_WIDTH = 320
COMPARE_LIST_HEIGHT = 7
Y_PADDING_RATIO = 0.05
MIN_Y_PADDING = 1e-3
AREA_TEXT_EPS = 1e-12
CSV_FILE_TYPES = [("CSV 文件", "*.csv"), ("所有文件", "*.*")]
SPECTRUM_COLORS = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
]
