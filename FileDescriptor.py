import base64
import os
import tempfile
import io
from openai import OpenAI
from pdf2image import convert_from_path
from PIL import Image, ImageTk
import logging
import traceback
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import customtkinter as ctk
import threading
import queue
from datetime import datetime
import csv

class FileDescriptor:
    def __init__(self):
        # 初始化OpenAI客户端 - 通过界面输入 API Key 来初始化客户端
        self.client = None
        self.openai_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

        # 支持的文件类型
        self.supported_image_types = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
        self.supported_pdf_types = ['.pdf']

        # 预览图片引用，防止被垃圾回收
        self._preview_photo = None

        # 最近保存或查看历史
        self.history = []
        # Treeview iid 映射到历史索引/对象，便于更新/删除
        self._history_iid_map = {}

        # 存储文件列表和当前结果
        self.file_list = []
        self.current_result = ""

        # 异步队列与线程控制
        self.queue = queue.Queue()
        self.worker_thread = None
        self.is_processing = False

        # 用于取消后台任务
        self.cancel_event = threading.Event()

        # 日志
        self.logger = logging.getLogger('FileDescriptor')
        self.logger.setLevel(logging.DEBUG)
        try:
            fh = logging.FileHandler('filedescriptor.log', encoding='utf-8')
            fmt = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
            fh.setFormatter(fmt)
            self.logger.addHandler(fh)
        except OSError:
            self.logger.warning("Unable to open log file", exc_info=True)

        # 创建 GUI
        self.create_gui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def create_gui(self):
        # 初始化外观与窗口
        ctk.set_appearance_mode("light")  # 可选 "dark" 或 "system"
        ctk.set_default_color_theme("blue")  # 可选 "blue", "green", "dark-blue"

        self.root = ctk.CTk()
        self.root.title("文件内容描述工具")
        self.root.geometry("950x720")
        self.root.resizable(True, True)

        # 主框架
        main_frame = ctk.CTkFrame(self.root, corner_radius=18)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # 工具栏（包含 API Key、主题切换、清除等）
        toolbar = ctk.CTkFrame(main_frame, corner_radius=12)
        toolbar.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(toolbar, text="API Key:", width=70).pack(side="left", padx=(8,4))
        self.api_key_var = ctk.StringVar()
        self.api_entry = ctk.CTkEntry(toolbar, textvariable=self.api_key_var, width=360, show="*")
        self.api_entry.pack(side="left", padx=(0,8))
        ctk.CTkButton(toolbar, text="应用 Key", width=90, command=self.apply_api_key).pack(side="left", padx=6)
        ctk.CTkButton(toolbar, text="清除选择", width=90, command=self.clear_selection).pack(side="left", padx=6)

        # 主题切换
        def _toggle_theme():
            mode = "dark" if ctk.get_appearance_mode().lower() == "light" else "light"
            ctk.set_appearance_mode(mode)

        ctk.CTkButton(toolbar, text="切换主题", width=90, command=_toggle_theme).pack(side="right", padx=6)

        # 颜色主题选择
        def _change_color_theme(choice):
            try:
                ctk.set_default_color_theme(choice)
                if hasattr(self, 'status_var'):
                    self.status_var.set(f"色彩主题：{choice}")
            except Exception:
                pass

        self.color_theme_var = ctk.StringVar(value="blue")
        ctk.CTkComboBox(toolbar, variable=self.color_theme_var, values=["blue", "green", "dark-blue"], width=120, command=_change_color_theme).pack(side="right", padx=6)

        # 操作按钮区域（生成/保存/取消）
        button_frame = ctk.CTkFrame(main_frame, corner_radius=12)
        button_frame.pack(fill="x", pady=(0, 12))
        ctk.CTkButton(button_frame, text="生成描述", command=self.generate_description, fg_color="#007aff", hover_color="#0051a8", width=120).pack(side="left", padx=10)
        ctk.CTkButton(button_frame, text="保存结果", command=self.save_result, width=120).pack(side="left", padx=10)
        ctk.CTkButton(button_frame, text="取消任务", command=self.cancel_task, width=120).pack(side="left", padx=10)

        # 文件选择与模型配置区域
        file_frame = ctk.CTkFrame(main_frame, corner_radius=15)
        file_frame.pack(fill="x", pady=(0, 12))
        self.file_path_var = ctk.StringVar()
        ctk.CTkEntry(file_frame, textvariable=self.file_path_var, width=520, font=("Helvetica", 12)).pack(side="left", padx=10, pady=8)
        ctk.CTkButton(file_frame, text="浏览文件", command=self.browse_file).pack(side="left", padx=8)
        ctk.CTkButton(file_frame, text="批量选择", command=self.browse_files).pack(side="left", padx=8)

        model_frame = ctk.CTkFrame(main_frame, corner_radius=15)
        model_frame.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(model_frame, text="选择模型:", font=("Helvetica", 12)).pack(side="left", padx=10)
        self.model_var = ctk.StringVar(value="qwen-vl-max-latest")
        ctk.CTkComboBox(model_frame, variable=self.model_var, values=["qwen-vl-max-latest", "qwen-vl-plus", "qwen-plus"], width=220).pack(side="left", padx=10)
        ctk.CTkLabel(model_frame, text="PDF最大处理页数:", font=("Helvetica", 12)).pack(side="left", padx=10)
        self.max_pages_var = ctk.StringVar(value="5")
        ctk.CTkEntry(model_frame, textvariable=self.max_pages_var, width=60, font=("Helvetica", 12)).pack(side="left", padx=10)

        # 描述要求区域
        prompt_frame = ctk.CTkFrame(main_frame, corner_radius=12)
        prompt_frame.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(prompt_frame, text="请输入描述要求:", font=("Helvetica", 12)).pack(anchor="w", padx=10, pady=(8,0))
        self.prompt_text = ctk.CTkTextbox(prompt_frame, height=80, font=("Helvetica", 12))
        self.prompt_text.pack(fill="x", padx=10, pady=8)
        self.prompt_text.insert("end", "请详细描述图片/文档中的内容，包括主要元素、颜色、布局等信息。")

        # 结果区域与预览（左右布局）
        content_frame = ctk.CTkFrame(main_frame, corner_radius=12)
        content_frame.pack(fill="both", expand=True, pady=(0, 12))

        # 渐变标题条（视觉效果）
        try:
            def _create_gradient(w, h, c1=(10,132,255), c2=(0,122,255)):
                img = Image.new('RGB', (w, h), color=0)
                for x in range(w):
                    r = int(c1[0] + (c2[0]-c1[0]) * x / max(1, w-1))
                    g = int(c1[1] + (c2[1]-c1[1]) * x / max(1, w-1))
                    b = int(c1[2] + (c2[2]-c1[2]) * x / max(1, w-1))
                    for y in range(h):
                        img.putpixel((x,y),(r,g,b))
                # 使用 customtkinter 的 CTkImage 避免高 DPI 警告
                try:
                    return ctk.CTkImage(light_image=img, size=(w, h))
                except Exception:
                    # 回退到 PhotoImage（兼容性保护）
                    return ImageTk.PhotoImage(img)

            grad = _create_gradient(900, 36)
            header = ctk.CTkLabel(main_frame, image=grad, text="  文件内容描述工具", compound="left", anchor="w", font=("Helvetica", 14, "bold"))
            # 保留引用以防被回收
            header.image = grad
            header.pack(fill="x", pady=(0,8))
        except Exception:
            pass

        # 左侧：预览 + 历史
        left_panel = ctk.CTkFrame(content_frame, width=300, corner_radius=12)
        left_panel.pack(side="left", fill="y", padx=(10,8), pady=10)

        ctk.CTkLabel(left_panel, text="预览", anchor="w").pack(fill="x", padx=8, pady=(8,0))
        self.preview_label = ctk.CTkLabel(left_panel, text="(未选择)", width=260, height=180, corner_radius=8)
        self.preview_label.pack(padx=8, pady=8)

        preview_btn_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        preview_btn_frame.pack(fill="x", padx=8)
        ctk.CTkButton(preview_btn_frame, text="复制描述", command=self.copy_result, width=120).pack(side="left", padx=6)
        ctk.CTkButton(preview_btn_frame, text="清空结果", command=self.clear_result, width=120).pack(side="left", padx=6)

        # 历史记录（可排序的 Treeview）
        ctk.CTkLabel(left_panel, text="历史记录", anchor="w").pack(fill="x", padx=8, pady=(10,0))
        cols = ("ts", "snippet", "path")
        self.history_tree = ttk.Treeview(left_panel, columns=cols, show='headings', height=8)
        # 设置列标题并绑定排序回调
        self.history_tree.heading('ts', text='时间', command=lambda: self.treeview_sort_column(self.history_tree, 'ts', False))
        self.history_tree.heading('snippet', text='摘要', command=lambda: self.treeview_sort_column(self.history_tree, 'snippet', False))
        self.history_tree.heading('path', text='路径', command=lambda: self.treeview_sort_column(self.history_tree, 'path', False))
        self.history_tree.column('ts', width=140, anchor='w')
        self.history_tree.column('snippet', width=160, anchor='w')
        self.history_tree.column('path', width=220, anchor='w')
        self.history_tree.pack(fill="both", padx=8, pady=6, expand=False)
        # 双击打开路径或查看详情
        self.history_tree.bind('<Double-1>', self.on_history_open)

        # 历史操作按钮
        hist_btn_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        hist_btn_frame.pack(fill="x", padx=8, pady=(4,8))
        ctk.CTkButton(hist_btn_frame, text="导出历史", width=110, command=self.export_history).pack(side="left", padx=6)
        ctk.CTkButton(hist_btn_frame, text="清理历史", width=110, command=self.clear_history).pack(side="left", padx=6)
        ctk.CTkButton(hist_btn_frame, text="导出错误栈", width=120, command=self.export_traceback).pack(side="left", padx=6)

        # 右侧：主结果展示
        right_panel = ctk.CTkFrame(content_frame, corner_radius=12)
        right_panel.pack(side="left", fill="both", expand=True, padx=(8,10), pady=10)

        self.result_text = ctk.CTkTextbox(right_panel, font=("Helvetica", 12))
        self.result_text.pack(fill="both", expand=True, padx=10, pady=10)

        # 进度条
        self.progress = ctk.CTkProgressBar(right_panel)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=12, pady=(0,10))

        # 状态栏
        self.status_var = ctk.StringVar(value="就绪")
        status_bar = ctk.CTkLabel(self.root, textvariable=self.status_var, anchor="w", font=("Helvetica", 11), height=30)
        status_bar.pack(side="bottom", fill="x", padx=0, pady=0)

        # 开始轮询队列以在主线程更新 UI
        self.root.after(150, self._process_queue)
        # 启动一个模拟队列注入，仅在环境变量 FD_SIM=1 时启用（用于 smoke 测试）
        try:
            if os.environ.get('FD_SIM', '0') == '1':
                self.root.after(800, self._simulate_queue)
        except Exception:
            pass

    def _process_queue(self):
        """在主线程轮询后台线程发送的消息并更新 UI"""
        try:
            while not self.queue.empty():
                try:
                    typ, data = self.queue.get_nowait()
                except queue.Empty:
                    break

                if typ == 'status':
                    self.status_var.set(data if data else '')

                elif typ == 'append_result':
                    try:
                        # 追加到结果窗口并保存到 current_result
                        self.current_result += (data + "\n")
                        self.result_text.insert(tk.END, data + "\n")
                        # 自动滚动到底部
                        self.result_text.see(tk.END)
                    except Exception:
                        pass

                elif typ == 'progress':
                    try:
                        val = float(data) if data is not None else 0.0
                        self.progress.set(max(0.0, min(1.0, val)))
                    except Exception:
                        pass

                elif typ == 'history_add':
                    try:
                        h = data or {}
                        self._insert_history(h)
                    except Exception:
                        pass

                elif typ == 'error':
                    # 以状态显示错误简短信息，并记录最后错误
                    self.status_var.set(f"错误: {data}")

                elif typ == 'done':
                    self.is_processing = False

        except Exception as e:
            # 记录并展示
            self._record_exception(e)
        finally:
            # 继续轮询
            try:
                self.root.after(150, self._process_queue)
            except Exception:
                pass

    def _insert_history(self, h: dict):
        """插入历史：去重（基于 path+snippet）、插入 Treeview，并修剪超过长度限制。"""
        try:
            key = (h.get('path',''), h.get('snippet',''))
            # 去重：删除已有相同 key 的历史项
            for idx, existing in enumerate(list(self.history)):
                if (existing.get('path',''), existing.get('snippet','')) == key:
                    # 删除对应 treeview 项
                    for iid in self.history_tree.get_children(''):
                        vals = self.history_tree.item(iid, 'values')
                        if vals and vals[1] == existing.get('snippet','') and vals[2] == existing.get('path',''):
                            try:
                                self.history_tree.delete(iid)
                                if iid in self._history_iid_map:
                                    del self._history_iid_map[iid]
                            except Exception:
                                pass
                    try:
                        self.history.remove(existing)
                    except Exception:
                        pass
                    break

            # 插入到内存与 Treeview
            self.history.insert(0, h)
            iid = self.history_tree.insert('', 0, values=(h.get('ts',''), h.get('snippet',''), h.get('path','')))
            try:
                self._history_iid_map[iid] = h
            except Exception:
                pass

            # 修剪历史长度
            self._prune_history()
        except Exception:
            pass

    def _prune_history(self, max_len: int = 200):
        """限制历史长度，保持最近的 max_len 条记录"""
        try:
            while len(self.history) > max_len:
                old = self.history.pop()
                # 删除 treeview 中的对应项
                for iid in list(self.history_tree.get_children('')):
                    vals = self.history_tree.item(iid, 'values')
                    if vals and vals[1] == old.get('snippet','') and vals[2] == old.get('path',''):
                        try:
                            self.history_tree.delete(iid)
                            if iid in self._history_iid_map:
                                del self._history_iid_map[iid]
                        except Exception:
                            pass
                        break
        except Exception:
            pass

    def _simulate_queue(self):
        """注入模拟队列消息以验证 UI 更新（用于 smoke 测试）"""
        try:
            # 模拟状态更新
            self.queue.put(('status', '模拟测试：开始'))
            # 模拟进度与结果
            self.queue.put(('progress', 0.1))
            self.queue.put(('append_result', '模拟：这是测试描述片段 1'))
            self.queue.put(('progress', 0.4))
            # 模拟历史记录
            hist = {'ts': datetime.now().isoformat(), 'snippet': '模拟历史条目', 'path': ''}
            self.queue.put(('history_add', hist))
            self.queue.put(('append_result', '模拟：这是测试描述片段 2'))
            self.queue.put(('progress', 0.9))
            # 完成
            self.queue.put(('status', '模拟测试：完成'))
            self.queue.put(('done', None))
            # 2秒后打印一些控件值到终端，作为自动验证
            try:
                self.root.after(2000, self._print_validation)
            except Exception:
                pass
        except Exception:
            pass

    def _print_validation(self):
        """从 UI 中读取关键控件状态并打印到终端，便于自动化 smoke 验证。"""
        try:
            status = self.status_var.get() if hasattr(self, 'status_var') else '<no status_var>'
            try:
                prog = self.progress.get() if hasattr(self, 'progress') else None
            except Exception:
                prog = None
            # 取结果文本前 200 字用于检查
            try:
                txt = self.result_text.get('1.0', tk.END).strip()
                snippet = txt[:200].replace('\n', ' | ')
            except Exception:
                snippet = '<no result_text>'

            try:
                hist_count = len(self.history)
                tree_count = len(self.history_tree.get_children(''))
            except Exception:
                hist_count = tree_count = -1

            print('--- 自动验证输出 START ---')
            print('status_var:', status)
            print('progress:', prog)
            print('result_snippet:', snippet)
            print('history_count (list):', hist_count)
            print('history_count (tree):', tree_count)
            print('--- 自动验证输出 END ---')
        except Exception as e:
            print('自动验证发生异常:', e)

    def on_history_open(self, evt):
        """双击历史项：尝试打开路径或显示详情"""
        try:
            sel = self.history_tree.selection()
            if not sel:
                return
            iid = sel[0]
            vals = self.history_tree.item(iid, 'values')
            path = vals[2] if len(vals) > 2 else ''
            if path and os.path.exists(path):
                try:
                    if os.name == 'nt':
                        os.startfile(path)
                    else:
                        import subprocess
                        subprocess.Popen(['xdg-open', path])
                except Exception as e:
                    messagebox.showerror('打开文件失败', f'无法打开路径: {e}')
            else:
                # 显示详情
                messagebox.showinfo('历史详情', f"摘要: {vals[1]}\n路径: {path}\n时间: {vals[0]}")
        except Exception as e:
            self._record_exception(e)

    def cancel_task(self):
        """发出取消信号给后台线程"""
        if not self.is_processing:
            self.status_var.set('没有正在运行的任务')
            return
        self.cancel_event.set()
        self.status_var.set('已请求取消任务，正在停止...')

    def treeview_sort_column(self, tv, col, reverse):
        """对 Treeview 指定列进行排序（支持时间/文本）"""
        try:
            l = [(tv.set(k, col), k) for k in tv.get_children('')]
            # 如果列为时间（ISO 格式），尝试把它转为 datetime 比较
            if col == 'ts':
                l = []
                for k in tv.get_children(''):
                    val = tv.set(k, col)
                    try:
                        dt = datetime.fromisoformat(val)
                        l.append(((1, dt.isoformat()), k))
                    except Exception:
                        l.append(((0, str(val)), k))
            l.sort(reverse=reverse)
            # 重新排列
            for index, (val, k) in enumerate(l):
                tv.move(k, '', index)
            # 反转标志以便下次排序反向
            tv.heading(col, command=lambda: self.treeview_sort_column(tv, col, not reverse))
        except Exception as e:
            self._record_exception(e)

    def export_traceback(self):
        """导出最后一次错误栈到文件"""
        tb = getattr(self, '_last_traceback', None)
        if not tb:
            messagebox.showinfo('无错误', '当前没有记录的错误栈')
            return
        save_path = filedialog.asksaveasfilename(defaultextension='.log', filetypes=[('日志文件','*.log'),('所有文件','*.*')])
        if not save_path:
            return
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(tb)
            messagebox.showinfo('导出成功', f'错误栈已导出至 {save_path}')
        except Exception as e:
            messagebox.showerror('导出失败', f'导出失败: {e}')

    def _record_exception(self, exc: Exception):
        """记录异常堆栈并保存到内存/日志"""
        tb = traceback.format_exc()
        self._last_traceback = tb
        try:
            self.logger.error('Exception: %s', str(exc))
            self.logger.error(tb)
        except Exception:
            pass
        # Tk calls must remain on the main thread, including failure dialogs.
        if threading.current_thread() is not threading.main_thread():
            self.queue.put(('error', f'{type(exc).__name__}: {exc}'))
            return
        # 弹出错误对话并提供查看与导出选项
        try:
            # 使用自定义对话显示更多信息
            if messagebox.askyesno('发生错误', f'错误: {exc}\n\n是否查看完整错误栈并导出？'):
                # 弹出带详细错误栈的小窗口
                win = tk.Toplevel(self.root)
                win.title('错误详情')
                txt = tk.Text(win, height=20, width=100)
                txt.pack(fill='both', expand=True)
                txt.insert('1.0', tb)
                def _export():
                    save_path = filedialog.asksaveasfilename(defaultextension='.log', filetypes=[('日志文件','*.log'),('所有文件','*.*')])
                    if save_path:
                        try:
                            with open(save_path, 'w', encoding='utf-8') as f:
                                f.write(tb)
                            messagebox.showinfo('导出成功', f'错误栈已导出至 {save_path}')
                        except Exception as ee:
                            messagebox.showerror('导出失败', f'导出失败: {ee}')
                btn = tk.Button(win, text='导出错误栈', command=_export)
                btn.pack(pady=6)
        except Exception:
            pass

    def _describe_image(self, image_path, prompt, model):
        encoded = self.encode_image(image_path)
        if not encoded:
            raise ValueError("图片编码失败")
        for attempt in range(4):
            if self.cancel_event.is_set():
                return None
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "你是一个专业的内容描述助手，擅长详细描述图片和文档内容。"},
                        {"role": "user", "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
                            {"type": "text", "text": prompt},
                        ]},
                    ],
                )
                if self.cancel_event.is_set():
                    return None
                description = response.choices[0].message.content
                if not isinstance(description, str) or not description.strip():
                    raise ValueError("模型未返回描述文本")
                return description
            except Exception as exc:
                if getattr(exc, 'status_code', None) != 429 or attempt == 3:
                    raise
                delay = 2 ** attempt
                self.queue.put(('status', f'被限流，{delay}s 后重试...'))
                if self.cancel_event.wait(delay):
                    return None
        return None

    def _worker(self, files, prompt, model, max_pages):
        """Keep network/file work off Tk; every UI update goes through the queue."""
        failed = 0
        try:
            for index, file_path in enumerate(files):
                if self.cancel_event.is_set():
                    break
                image_paths = []
                file_name = os.path.basename(file_path)
                self.queue.put(('status', f'正在处理 {file_name} ({index + 1}/{len(files)})'))
                try:
                    extension = os.path.splitext(file_path)[1].lower()
                    if extension in self.supported_pdf_types:
                        image_paths = self.pdf_to_images(file_path, max_pages)
                        if not image_paths:
                            raise ValueError('PDF 未生成可处理的页面')
                        inputs = image_paths
                    elif extension in self.supported_image_types:
                        inputs = [file_path]
                    else:
                        raise ValueError(f'不支持的文件类型: {extension}')
                    for page, image_path in enumerate(inputs, 1):
                        if self.cancel_event.is_set():
                            break
                        request_prompt = f'{prompt} 这是PDF的第 {page} 页。' if image_paths else prompt
                        description = self._describe_image(image_path, request_prompt, model)
                        if description is None:
                            break
                        heading = f'=== {file_name} 第 {page} 页 ===' if image_paths else f'=== {file_name} 的描述 ==='
                        self.queue.put(('append_result', heading + '\n' + description))
                        self.queue.put(('history_add', {
                            'ts': datetime.now().isoformat(), 'snippet': description.splitlines()[0][:60], 'path': file_path,
                        }))
                        self.queue.put(('progress', (index + page / len(inputs)) / len(files)))
                except Exception as exc:
                    failed += 1
                    self._record_exception(exc)
                finally:
                    for image_path in image_paths:
                        try:
                            os.remove(image_path)
                        except OSError:
                            self.logger.warning('Temporary image cleanup failed', exc_info=True)
            if self.cancel_event.is_set():
                status = '任务已取消'
            elif failed:
                status = f'处理结束，{failed} 个文件失败'
            else:
                status = '描述生成完成'
            self.queue.put(('status', status))
        finally:
            self.queue.put(('done', None))

    def generate_description(self):
        """启动后台线程生成文件内容描述（非阻塞 UI）"""
        if self.is_processing or (self.worker_thread and self.worker_thread.is_alive()):
            self.status_var.set("任务正在处理中")
            return
        if not self.file_list:
            messagebox.showwarning("警告", "请先选择文件")
            return

        # 确保客户端已初始化
        try:
            self.ensure_client()
        except Exception:
            return

        prompt = self.prompt_text.get(1.0, tk.END).strip()
        model = self.model_var.get()
        try:
            max_pages = int(self.max_pages_var.get())
            if max_pages < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning("警告", "PDF 页数必须是正整数")
            return

        # 清理旧结果
        self.result_text.delete(1.0, tk.END)
        self.current_result = ""
        self.is_processing = True
        self.status_var.set("任务已提交，后台处理中...")

        files_copy = list(self.file_list)
        # 启动线程
        # 清理取消标志并保存线程引用以便后续管理
        try:
            self.cancel_event.clear()
        except Exception:
            pass
        t = threading.Thread(target=self._worker, args=(files_copy, prompt, model, max_pages), daemon=True)
        self.worker_thread = t
        t.start()

    def browse_file(self):
        """浏览单个文件"""
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("支持的文件", " ".join("*" + ext for ext in self.supported_image_types + self.supported_pdf_types)),
                ("图片文件", " ".join("*" + ext for ext in self.supported_image_types)),
                ("PDF文件", "*.pdf"),
                ("所有文件", "*.*")
            ]
        )
        if file_path:
            self.file_path_var.set(file_path)
            self.file_list = [file_path]
            # 更新预览
            self.show_preview(file_path)

    def browse_files(self):
        """浏览多个文件"""
        file_paths = filedialog.askopenfilenames(
            filetypes=[
                ("支持的文件", " ".join("*" + ext for ext in self.supported_image_types + self.supported_pdf_types)),
                ("图片文件", " ".join("*" + ext for ext in self.supported_image_types)),
                ("PDF文件", "*.pdf"),
                ("所有文件", "*.*")
            ]
        )
        if file_paths:
            self.file_path_var.set(f"已选择 {len(file_paths)} 个文件")
            self.file_list = list(file_paths)
            # 预览第一个
            if self.file_list:
                self.show_preview(self.file_list[0])

    def encode_image(self, image_path):
        """Normalize supported formats to PNG so payload bytes match their MIME type."""
        with Image.open(image_path) as source:
            with source.convert('RGB') as rgb, io.BytesIO() as buffer:
                rgb.save(buffer, format='PNG')
                return base64.b64encode(buffer.getvalue()).decode('ascii')

    def pdf_to_images(self, pdf_path, max_pages=None):
        # Compatibility: direct UI callers may omit the page limit. Workers pass a snapshot.
        if max_pages is None:
            max_pages = int(self.max_pages_var.get())
        if max_pages < 1:
            raise ValueError('PDF 页数必须是正整数')
        images = []
        pages = convert_from_path(pdf_path, dpi=300, first_page=1,
                                  last_page=max_pages, fmt='png', timeout=60)
        try:
            for page in pages:
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    images.append(temp_file.name)
                    page.save(temp_file, 'PNG')
            return images
        except Exception:
            for image_path in images:
                try:
                    os.remove(image_path)
                except OSError:
                    self.logger.warning('Temporary image cleanup failed', exc_info=True)
            raise
        finally:
            for page in pages:
                page.close()

    def apply_api_key(self):
        """使用界面输入的 API Key 初始化 OpenAI 客户端"""
        if self.is_processing:
            self.status_var.set("请等待当前任务结束后更换 Key")
            return
        key = self.api_key_var.get().strip()
        if not key:
            messagebox.showwarning("警告", "请输入 API Key 后再应用")
            return
        try:
            client = OpenAI(api_key=key, base_url=self.openai_base_url, timeout=60.0, max_retries=0)
            if self.client is not None:
                self.client.close()
            self.client = client
            self.status_var.set("API Key 已应用")
        except Exception as e:
            messagebox.showerror("错误", f"初始化 OpenAI 客户端失败：{e}")

    def ensure_client(self):
        if not self.client:
            messagebox.showwarning("警告", "尚未应用 API Key，请先在顶部输入并点击 '应用 Key'")
            raise RuntimeError("OpenAI client 未初始化")

    def show_preview(self, path):
        """在预览窗口显示图片或PDF的第一页缩略图"""
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext in self.supported_image_types:
                img = Image.open(path)
            elif ext in self.supported_pdf_types:
                pages = convert_from_path(path, dpi=150, first_page=1, last_page=1)
                if not pages:
                    raise RuntimeError("无法从PDF生成预览")
                img = pages[0]
            else:
                self.preview_label.configure(text="(不支持预览)")
                return

            try:
                img.thumbnail((420, 300))
                self._preview_photo = ImageTk.PhotoImage(img)
            finally:
                img.close()
            self.preview_label.configure(image=self._preview_photo, text="")
        except Exception as e:
            self.preview_label.configure(text="(预览失败)")
            self.status_var.set(f"预览错误: {e}")



    def export_history(self):
        """导出历史为 CSV 文件（包含时间戳、摘要、路径）"""
        if not self.history:
            messagebox.showinfo("提示", "没有历史可导出")
            return
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV 文件","*.csv"), ("所有文件","*.*")])
        if not save_path:
            return
        try:
            with open(save_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'snippet', 'path'])
                for h in self.history:
                    writer.writerow([h.get('ts',''), h.get('snippet',''), h.get('path','')])
            self.status_var.set(f"历史已导出至: {save_path}")
            messagebox.showinfo("成功", f"历史已导出至: {save_path}")
        except Exception as e:
            self.status_var.set(f"导出失败: {e}")
            messagebox.showerror("导出失败", f"导出历史时出错：{e}")

    def clear_history(self):
        """清空历史列表"""
        self.history.clear()
        self._history_iid_map.clear()
        try:
            # 清空 treeview
            for iid in self.history_tree.get_children():
                self.history_tree.delete(iid)
        except Exception:
            pass
        self.status_var.set("历史已清理")

    def save_result(self):
        """保存描述结果"""
        if not self.current_result.strip():
            messagebox.showwarning("警告", "没有可保存的结果")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )

        if save_path:
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(self.current_result)
                self.status_var.set(f"结果已保存至: {save_path}")
                messagebox.showinfo("成功", f"结果已保存至: {save_path}")
                # 更新历史（字典格式）
                short = self.current_result.strip().splitlines()[0][:60]
                hist = {'ts': datetime.now().isoformat(), 'snippet': short, 'path': save_path}
                self._insert_history(hist)
            except Exception as e:
                self.status_var.set(f"保存失败: {str(e)}")
                messagebox.showerror("保存失败", f"保存文件时出错：{str(e)}")

    def copy_result(self):
        txt = self.current_result.strip()
        if not txt:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(txt)
        self.status_var.set("已复制到剪贴板")

    def clear_result(self):
        self.current_result = ""
        self.result_text.delete("0.0", tk.END)
        self.status_var.set("结果已清空")

    def clear_selection(self):
        self.file_list = []
        self.file_path_var.set("")
        self.preview_label.configure(image=None, text="(未选择)")
        self._preview_photo = None
        self.status_var.set("已清除选择")



    def close(self):
        """Finish cleanup before closing the client; never block Tk with join()."""
        self.cancel_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.status_var.set('正在取消任务并关闭...')
            self.root.after(100, self.close)
            return
        if self.client is not None:
            self.client.close()
        self.root.destroy()

    def run(self):
        """运行程序"""
        self.root.mainloop()


if __name__ == "__main__":
    app = FileDescriptor()
    app.run()
