# PixelScribe
🤖 An intelligent desktop application that generates detailed text descriptions for images and PDFs using AI (Qwen-VL). Features a modern GUI, batch processing, and history export.
# PixelScribe (AI File Describer) 👁️📝

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-success)

**PixelScribe** 是一个现代化的桌面应用程序，旨在利用多模态大模型（Qwen-VL via DashScope）自动分析并描述图片和 PDF 文档的内容。

无论是需要为数据集打标、快速理解长文档中的图表，还是为无障碍访问生成替代文本，这个工具都能提供帮助。

## ✨ 主要功能

* **现代化 GUI**: 基于 `CustomTkinter` 构建，支持浅色/深色模式及多种主题色。
* **多格式支持**: 支持常见图片格式 (`.jpg`, `.png`, `.bmp` 等) 以及 `.pdf` 文档。
* **PDF 智能处理**: 自动将 PDF 页面转换为图片进行分析，支持自定义处理页数。
* **强大的 AI 后端**: 集成阿里云 DashScope (通义千问 Qwen-VL) 接口，识别精准。
* **批量处理**: 支持单文件或批量选择文件进行队列处理。
* **历史记录**: 自动保存生成记录，支持双击查看、排序及导出为 CSV/Excel。
* **非阻塞体验**: 采用多线程架构，生成描述时 UI 依然流畅响应。

## 🛠️ 安装指南

### 1. 克隆仓库
```bash
git clone [https://github.com/AlvanHarrison/PixelScribe.git](https://github.com/AlvanHarrison/PixelScribe.git)
cd PixelScribe
2. 安装 Python 依赖
建议使用虚拟环境运行本项目：

Bash

pip install -r requirements.txt
如果安装过程中遇到问题，也可以手动安装核心依赖库：

Bash

pip install openai PyPDF2 pdf2image Pillow customtkinter
3. 配置 Poppler (PDF 处理必须)
由于本项目使用了 pdf2image 库来解析 PDF 文件，你需要安装 Poppler 才能正常处理 PDF：

Windows 用户:

下载 Poppler 二进制包 (推荐从 oschwartz10612/poppler-windows 下载)。

解压并将 bin 文件夹的完整路径添加到系统的 环境变量 PATH 中。

Mac 用户:

Bash

brew install poppler
Linux 用户:

Bash

sudo apt-get install poppler-utils
🚀 使用方法
1. 运行程序
在终端中执行以下命令启动应用：

Bash

python FileDescriptor.py
2. 设置 API Key
程序启动后，在顶部工具栏的输入框中填入你的 阿里云 DashScope API Key。

点击 "应用 Key" 按钮。

还没有 Key？请前往 阿里云百炼控制台 申请。

3. 选择文件
点击 "浏览文件" (单选) 或 "批量选择" (多选) 导入你需要描述的图片或 PDF 文档。

4. 生成描述
在界面下方的文本框中调整提示词（Prompt），也可以直接使用默认的通用提示。

点击 "生成描述"。

程序将在后台进行 AI 分析，进度条会显示当前进度，结果将实时显示在右侧文本框中。

⚙️ 配置选项
模型选择: 下拉菜单支持选择 qwen-vl-max-latest, qwen-vl-plus 等不同能力的模型。

PDF 页数限制: 在输入框中设置最大处理页数（默认为 5），防止长文档消耗过多 Token。

外观主题: 点击右上角的 "切换主题" 按钮可在明亮 (Light) 和暗黑 (Dark) 模式间切换；也可以在下拉菜单中更改强调色（蓝色、绿色等）。

📂 项目结构
Plaintext

PixelScribe/
├── FileDescriptor.py    # 主程序入口
├── requirements.txt     # 项目依赖列表
├── filedescriptor.log   # 运行时生成的日志文件
└── README.md            # 项目说明文档
🤝 贡献 (Contributing)
欢迎提交 Issue 反馈 Bug，或提交 Pull Request 来改进代码！

📄 许可证 (License)
本项目采用 MIT 许可证。详情请参阅 LICENSE 文件。
