# 光谱面积计算工具 (Spectrum Area Calculator)

这是一个基于 Python 的图形化界面工具，用于分析光谱数据并计算指定波长范围内的峰面积。支持自动基线扣除和多种面积计算模式。

## 功能特点

- **数据导入**: 支持读取 `.txt` 和 `.csv` 格式的光谱数据文件。
- **交互式图表**: 使用 Matplotlib 绘制光谱图，支持缩放、平移和鼠标交互选择范围。
- **面积计算**:
  - **原始面积**: 曲线下的总面积。
  - **基线面积**: 选定范围两端点连线下的面积。
  - **扣基线面积**: 原始面积减去基线面积。
  - **仅正面积**: 扣除基线后仅计算正值部分的面积。
- **响应式界面**: 窗口大小自适应，支持全屏操作。
- **中文支持**: 图表和界面完美支持中文显示。
- **轻量化**: 经过 UPX 压缩优化，生成的可执行文件体积小巧。

## 安装与运行

### 源码运行

1. 克隆仓库:
   ```bash
   git clone https://github.com/ZuesTian/UV.git
   cd UV
   ```

2. 创建虚拟环境 (推荐):
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. 安装依赖:
   ```bash
   pip install -r requirements.txt
   ```

4. 运行程序:
   ```bash
   python spectrum_gui.py
   ```

### 打包构建 (Windows)

本项目配置了 PyInstaller 和 UPX 进行压缩打包。

1. 确保已安装 UPX 并配置好路径（或将 `upx.exe` 放在项目根目录）。
2. 运行构建命令:
   ```bash
   pyinstaller --noconfirm --onefile --windowed --upx-dir=. --name="SpectrumTool_Optimized" spectrum_gui.py
   ```
3. 构建完成后，可执行文件位于 `dist/SpectrumTool_Optimized.exe`。

## 使用说明

1. 点击“打开文件”选择光谱数据文件。
2. 在图表中拖动鼠标选择感兴趣的波长范围，或者在顶部输入框手动输入范围。
3. 点击“应用范围”或“计算面积”更新结果。
4. 界面左侧将显示详细的计算结果。
