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
