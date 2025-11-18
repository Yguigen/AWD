import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext
import subprocess
import threading
import time
import os
import sys
from datetime import datetime
import queue

class ScriptRunnerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AWD脚本自动化运行器")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 确保中文显示正常
        if sys.platform.startswith('win'):
            # Windows系统下尝试设置系统默认字体
            self.font = ('Microsoft YaHei UI', 10)
            self.bold_font = ('Microsoft YaHei UI', 10, 'bold')
        else:
            # 非Windows系统
            self.font = ('SimHei', 10)
            self.bold_font = ('SimHei', 10, 'bold')
        
        # 日志队列，用于线程安全的日志更新
        self.log_queue = queue.Queue()
        self.is_log_thread_running = False
        
        # 状态变量
        self.scripts = []
        self.is_running = False
        self.is_paused = False
        self.timer_thread = None
        self.interval = 60  # 默认间隔60秒
        
        # 创建UI
        self.create_widgets()
        
        # 填充默认脚本
        self.add_default_scripts()
    
    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 1. 脚本列表区域
        script_frame = ttk.LabelFrame(main_frame, text="脚本列表", padding="10")
        script_frame.pack(fill=tk.X, pady=5)
        
        # 脚本列表
        self.script_listbox = tk.Listbox(script_frame, width=80, height=6, font=self.font)
        self.script_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 脚本列表滚动条
        scrollbar = ttk.Scrollbar(script_frame, orient=tk.VERTICAL, command=self.script_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.script_listbox.config(yscrollcommand=scrollbar.set)
        
        # 脚本按钮区域
        button_frame = ttk.Frame(script_frame, padding="5")
        button_frame.pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(button_frame, text="添加脚本", command=self.add_script).pack(fill=tk.X, pady=2)
        ttk.Button(button_frame, text="删除脚本", command=self.remove_script).pack(fill=tk.X, pady=2)
        ttk.Button(button_frame, text="上移", command=lambda: self.move_script(-1)).pack(fill=tk.X, pady=2)
        ttk.Button(button_frame, text="下移", command=lambda: self.move_script(1)).pack(fill=tk.X, pady=2)
        
        # 2. 定时设置区域
        timer_frame = ttk.LabelFrame(main_frame, text="定时设置", padding="10")
        timer_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(timer_frame, text="运行间隔 (秒):", font=self.font).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.interval_var = tk.StringVar(value="300")  # 默认5分钟
        interval_entry = ttk.Entry(timer_frame, textvariable=self.interval_var, width=10, font=self.font)
        interval_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 3. 控制按钮区域
        control_frame = ttk.Frame(main_frame, padding="10")
        control_frame.pack(fill=tk.X, pady=5)
        
        self.start_button = ttk.Button(control_frame, text="开始运行", command=self.start_running, width=15)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.pause_button = ttk.Button(control_frame, text="暂停", command=self.pause_running, width=15, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(control_frame, text="停止", command=self.stop_running, width=15, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # 立即执行一次
        ttk.Button(control_frame, text="立即执行一次", command=self.run_scripts_once, width=15).pack(side=tk.LEFT, padx=5)
        
        # 4. 日志显示区域
        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, font=self.font)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # 启动日志更新线程
        self.start_log_thread()
    
    def add_default_scripts(self):
        # 添加默认脚本到列表
        default_scripts = [
            "POST型shell获取信息.py",
            "从响应中提取flag并提交.py"
        ]
        
        for script in default_scripts:
            if os.path.exists(script):
                self.scripts.append(script)
                self.script_listbox.insert(tk.END, script)
                self.log(f"已添加默认脚本: {script}")
    
    def add_script(self):
        file_path = filedialog.askopenfilename(
            title="选择Python脚本",
            filetypes=[("Python文件", "*.py"), ("所有文件", "*.*")]
        )
        
        if file_path:
            # 获取文件名部分
            script_name = os.path.basename(file_path)
            
            # 检查文件是否已存在
            if script_name not in self.scripts:
                # 如果文件不在当前目录，复制到当前目录
                if not os.path.exists(script_name):
                    try:
                        import shutil
                        shutil.copy2(file_path, script_name)
                        self.log(f"已复制脚本到当前目录: {script_name}")
                    except Exception as e:
                        self.log(f"复制脚本失败: {str(e)}")
                        return
                
                self.scripts.append(script_name)
                self.script_listbox.insert(tk.END, script_name)
                self.log(f"已添加脚本: {script_name}")
            else:
                self.log(f"脚本已存在: {script_name}")
    
    def remove_script(self):
        selection = self.script_listbox.curselection()
        if selection:
            index = selection[0]
            script_name = self.scripts.pop(index)
            self.script_listbox.delete(index)
            self.log(f"已删除脚本: {script_name}")
    
    def move_script(self, direction):
        selection = self.script_listbox.curselection()
        if selection:
            index = selection[0]
            new_index = index + direction
            
            if 0 <= new_index < len(self.scripts):
                # 交换脚本位置
                self.scripts[index], self.scripts[new_index] = self.scripts[new_index], self.scripts[index]
                
                # 更新列表框
                self.script_listbox.delete(0, tk.END)
                for script in self.scripts:
                    self.script_listbox.insert(tk.END, script)
                
                # 重新选中移动后的项
                self.script_listbox.selection_set(new_index)
                self.script_listbox.see(new_index)
                
                self.log(f"已调整脚本顺序")
    
    def start_running(self):
        if not self.scripts:
            self.log("错误: 脚本列表为空，请先添加脚本")
            return
        
        try:
            self.interval = int(self.interval_var.get())
            if self.interval <= 0:
                self.log("错误: 运行间隔必须大于0")
                return
        except ValueError:
            self.log("错误: 请输入有效的数字作为运行间隔")
            return
        
        self.is_running = True
        self.is_paused = False
        
        # 更新按钮状态
        self.start_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.NORMAL)
        
        self.log(f"开始定时运行脚本，间隔 {self.interval} 秒")
        
        # 启动定时器线程
        self.timer_thread = threading.Thread(target=self.timer_runner, daemon=True)
        self.timer_thread.start()
    
    def pause_running(self):
        if self.is_paused:
            self.is_paused = False
            self.pause_button.config(text="暂停")
            self.log("已恢复运行")
        else:
            self.is_paused = True
            self.pause_button.config(text="恢复")
            self.log("已暂停运行")
    
    def stop_running(self):
        self.is_running = False
        self.is_paused = False
        
        # 更新按钮状态
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED, text="暂停")
        self.stop_button.config(state=tk.DISABLED)
        
        self.log("已停止运行")
    
    def timer_runner(self):
        while self.is_running:
            if not self.is_paused:
                self.run_scripts_once()
            
            # 等待下一次运行
            for _ in range(self.interval):
                if not self.is_running:
                    break
                time.sleep(1)
    
    def run_scripts_once(self):
        if not self.scripts:
            self.log("错误: 脚本列表为空")
            return
        
        self.log(f"\n{'-'*50}")
        self.log(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始执行脚本序列")
        
        for script in self.scripts:
            if not self.is_running or self.is_paused:
                break
                
            self.log(f"\n[{datetime.now().strftime('%H:%M:%S')}] 执行脚本: {script}")
            self.run_script(script)
        
        if not self.is_paused:
            self.log(f"[{datetime.now().strftime('%H:%M:%S')}] 脚本序列执行完成")
            self.log(f"{'-'*50}")
    
    def run_script(self, script_name):
        try:
            # 为Windows环境配置编码环境变量
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'
            
            # 使用subprocess运行脚本
            process = subprocess.Popen(
                [sys.executable, script_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                env=env  # 使用配置了编码的环境变量
            )
            
            # 实时获取输出
            for line in iter(process.stdout.readline, ''):
                if not self.is_running or self.is_paused:
                    break
                if line.strip():
                    # 确保正确处理中文编码
                    try:
                        # 先尝试直接使用，已经通过encoding='utf-8'处理过
                        clean_line = line.strip()
                        # 移除控制字符
                        clean_line = ''.join(char for char in clean_line if ord(char) >= 32 or char in '\n\t')
                        self.log(f"[{script_name}] {clean_line}")
                    except Exception as e:
                        # 如果处理失败，使用安全的方式记录
                        self.log(f"[{script_name}] 输出处理异常: {str(e)}")
            
            # 获取错误输出
            for line in iter(process.stderr.readline, ''):
                if line.strip():
                    try:
                        clean_line = line.strip()
                        clean_line = ''.join(char for char in clean_line if ord(char) >= 32 or char in '\n\t')
                        self.log(f"[{script_name}] 错误: {clean_line}")
                    except Exception as e:
                        self.log(f"[{script_name}] 错误输出处理异常: {str(e)}")
            
            # 等待进程完成
            process.wait()
            
            if process.returncode == 0:
                self.log(f"[{script_name}] 执行成功")
            else:
                self.log(f"[{script_name}] 执行失败，返回码: {process.returncode}")
                
        except Exception as e:
            self.log(f"[{script_name}] 运行异常: {str(e)}")
    
    def start_log_thread(self):
        """启动日志更新线程"""
        if not self.is_log_thread_running:
            self.is_log_thread_running = True
            self.log_thread = threading.Thread(target=self.log_updater, daemon=True)
            self.log_thread.start()
    
    def log_updater(self):
        """日志更新线程函数"""
        while self.is_log_thread_running:
            try:
                # 从队列中获取日志消息
                message = self.log_queue.get(timeout=0.1)
                
                # 在主线程中更新UI
                self.root.after(0, self._update_log_text, message)
                
                self.log_queue.task_done()
            except queue.Empty:
                pass
            except Exception as e:
                print(f"日志线程错误: {str(e)}")
    
    def _update_log_text(self, message):
        """在主线程中更新日志文本框"""
        try:
            # 确保消息是字符串类型且正确编码
            if not isinstance(message, str):
                message = str(message)
                
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)  # 滚动到末尾
            self.log_text.config(state=tk.DISABLED)
        except Exception as e:
            print(f"更新日志UI错误: {str(e)}")
    
    def log(self, message):
        """添加日志到队列，确保正确处理中文"""
        try:
            # 确保消息是字符串类型且正确编码
            if not isinstance(message, str):
                message = str(message)
            
            # 增强的编码处理
            try:
                # 首先尝试直接使用
                processed_message = message
                # 在终端也打印一条，用于调试
                print(f"调试 - {processed_message}")
            except Exception:
                # 如果有编码问题，尝试不同的处理方式
                try:
                    processed_message = message.encode('utf-8', errors='replace').decode('utf-8')
                except Exception:
                    try:
                        processed_message = message.encode('cp936', errors='replace').decode('utf-8')
                    except Exception:
                        processed_message = "[编码错误] 无法处理的消息"
            
            self.log_queue.put(processed_message)
        except Exception as e:
            error_msg = f"添加日志到队列失败: {str(e)}"
            print(error_msg)
            # 尝试将错误信息也添加到日志队列
            try:
                self.log_queue.put(error_msg)
            except:
                pass

def main():
    root = tk.Tk()
    # 设置窗口标题编码
    root.title("AWD脚本自动化运行器".encode('utf-8').decode('utf-8'))
    
    app = ScriptRunnerApp(root)
    
    # 处理窗口关闭事件
    def on_closing():
        # 安全停止所有线程
        app.is_log_thread_running = False
        app.stop_running()
        # 给线程一些时间清理资源
        time.sleep(0.5)
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()