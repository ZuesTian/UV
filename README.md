# 光谱面积计算工具

这是一个面向光谱积分分析的桌面 GUI 工具，适合对 `.txt` / `.csv` 光谱数据做交互式选区、峰面积计算、多文件对比和批量汇总导出。

## 当前版本功能

- 支持一次打开多个光谱文件，也支持在现有列表上继续追加。
- 左侧文件管理区可直接勾选多条光谱进行叠加显示与当前区域面积对比。
- 图表区支持鼠标拖拽选区、滚轮缩放、手动输入积分范围和手动设置视图范围。
- 右侧可记录多个峰，支持单文件峰面积比例比较。
- 多文件模式下，当前选区会同步计算所有已勾选光谱，并在图上同时显示各自峰区、基线和面积标注。
- 支持批量计算所有已加载文件，生成汇总表并导出 `CSV`。
- 主界面采用可拖拽分栏，能适配不同尺寸和分辨率的屏幕。

## 界面布局

- 顶部：文件打开、追加与当前文件切换。
- 左侧：文件列表、多谱对比选择、积分计算与当前结果。
- 中间：主光谱图。
- 右侧：峰记录、峰面积比较、汇总与导出。
- 底部：视图范围控制。

## 安装与运行

```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
python spectrum_gui.py
```

## 运行测试

```bash
python -m unittest discover -s tests -v
```

## 使用流程

1. 点击“打开文件”重新载入一批文件，或点击“追加文件”继续加入更多光谱。
2. 在左侧文件列表勾选需要叠加比较的光谱。
3. 在图上拖拽选择积分区间，或直接输入最小值/最大值。
4. 点击“计算当前”查看当前文件结果，点击“记录当前峰”保存到峰记录。
5. 需要批量比较时，点击“批量计算所有文件”生成汇总结果。
6. 点击“查看汇总”查看表格，或点击“导出 CSV”导出结果。

## 项目结构

- `spectrum_gui.py`：兼容启动入口。
- `spectrum_tool/models.py`：`PeakRecord` 和 `SpectrumDocument` 数据模型。
- `spectrum_tool/io_utils.py`：光谱文件读取逻辑。
- `spectrum_tool/computation.py`：选区截取、面积计算和汇总行生成。
- `spectrum_tool/ui.py`：`SpectrumApp` 壳层与程序入口。
- `spectrum_tool/ui_constants.py`：界面常量和 Matplotlib 默认配置。
- `spectrum_tool/ui_layout_mixin.py`：窗口布局、面板构建和响应式尺寸逻辑。
- `spectrum_tool/ui_file_mixin.py`：文件加载、切换、多文件选择和状态同步。
- `spectrum_tool/ui_view_mixin.py`：图表交互、视图范围控制和积分计算流程。
- `spectrum_tool/ui_peak_mixin.py`：峰记录、多文件面积比较和峰对比逻辑。
- `spectrum_tool/ui_summary_mixin.py`：批量计算、汇总导出和汇总窗口调度。
- `spectrum_tool/ui_plotting.py`：多谱绘图和面积对比图辅助逻辑。
- `spectrum_tool/ui_summary.py`：汇总表弹窗和排序填充逻辑。
- `tests/`：最小回归测试。

## 打包

Windows 下可继续使用 PyInstaller：

```bash
pyinstaller --noconfirm --onefile --windowed --name="SpectrumTool_Optimized" spectrum_gui.py
```
