# PixelScribe (AI File Describer) 👁️📝

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-success)

> 🤖 An intelligent desktop application that generates detailed text descriptions for images and PDFs using AI (Qwen-VL). Features a modern GUI, batch processing, and history export.

**PixelScribe** is a modern desktop application designed to automatically analyze and describe the contents of images and PDF documents using multimodal large models (Qwen-VL via DashScope).

Whether you need to label datasets, quickly understand charts in long documents, or generate alternative text for accessibility, this tool provides a powerful solution.

## ✨ Key Features

* **Modern GUI**: Built with `CustomTkinter`, supporting Light/Dark modes and multiple color themes.
* **Multi-Format Support**: Supports common image formats (`.jpg`, `.png`, `.bmp`, etc.) and `.pdf` documents.
* **Smart PDF Processing**: Automatically converts PDF pages to images for analysis, with customizable page limits.
* **Powerful AI Backend**: Integrated with Alibaba Cloud DashScope (Qwen-VL) for precise recognition.
* **Batch Processing**: Supports single file selection or batch queuing for efficient processing.
* **History Management**: Automatically saves generation records, supporting double-click to view, sorting, and exporting to CSV/Excel.
* **Non-Blocking Experience**: Uses a multi-threaded architecture, ensuring the UI remains responsive while descriptions are generating.

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone [https://github.com/AlvanHarrison/PixelScribe.git](https://github.com/AlvanHarrison/PixelScribe.git)
cd PixelScribe

```

### 2. Install Python Dependencies

It is recommended to run this project in a virtual environment:

```bash
pip install -r requirements.txt

```

If you encounter issues during installation, you can manually install the core libraries:

```bash
pip install openai PyPDF2 pdf2image Pillow customtkinter

```

### 3. Configure Poppler (Required for PDF)

Since this project uses `pdf2image` to parse PDF files, you must install **Poppler** to process PDFs correctly:

* **Windows Users:**
1. Download the Poppler binary (Recommended: [oschwartz10612/poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases)).
2. Extract the files and add the full path of the `bin` folder to your system's **Environment Variables (PATH)**.


* **Mac Users:**
```bash
brew install poppler

```


* **Linux Users:**
```bash
sudo apt-get install poppler-utils

```



## 🚀 Usage

### 1. Run the Application

Execute the following command in your terminal to start the app:

```bash
python FileDescriptor.py

```

### 2. Set API Key

1. After the program starts, enter your **Alibaba Cloud DashScope API Key** in the input box on the top toolbar.
2. Click the **"Apply Key"** button.
* *Don't have a Key? Apply for one at the [Alibaba Cloud Bailian Console](https://bailian.console.aliyun.com/).*



### 3. Select Files

Click **"Browse File"** (Single) or **"Batch Select"** (Multiple) to import the images or PDF documents you wish to describe.

### 4. Generate Descriptions

1. Adjust the prompt in the text box at the bottom of the interface, or use the default generic prompt.
2. Click **"Generate Description"**.
3. The program will perform AI analysis in the background. A progress bar will indicate status, and results will appear in real-time in the text box on the right.

## ⚙️ Configuration Options

* **Model Selection**: Use the dropdown menu to choose between models with different capabilities, such as `qwen-vl-max-latest` or `qwen-vl-plus`.
* **PDF Page Limit**: Set the maximum number of pages to process (default is 5) in the settings to prevent long documents from consuming too many tokens.
* **Appearance**: Click the **"Switch Theme"** button in the top right to toggle between Light and Dark modes; you can also change the accent color (Blue, Green, etc.) via the dropdown menu.

## 📂 Project Structure

```plaintext
PixelScribe/
├── FileDescriptor.py    # Main application entry point
├── requirements.txt     # List of project dependencies
├── filedescriptor.log   # Runtime log file
└── README.md            # Project documentation

```

## 🤝 Contributing

Contributions are welcome! Feel free to submit Issues for bugs or Pull Requests to improve the code.

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](https://www.google.com/search?q=LICENSE) file for details.

```

```
