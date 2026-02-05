#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LIS模拟数据界面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import time


class LisUI:
    """LIS模拟数据界面"""
    
    def __init__(self, parent, logger, lis_client):
        """初始化LIS模拟数据界面
        
        Args:
            parent: 父窗口
            logger: 日志管理器实例
            lis_client: LIS客户端实例
        """
        self.parent = parent
        self.logger = logger
        self.lis_client = lis_client
        
        # 创建窗口
        self.window = tk.Toplevel(parent)
        self.window.title("LIS模拟数据")
        self.window.geometry("700x300")
        self.window.resizable(True, True)
        
        # 设置错误回调函数
        self.lis_client.set_error_callback(self._on_error)
        
        # 创建UI组件
        self._create_widgets()
    
    def _create_widgets(self):
        """创建UI组件"""
        # 主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 第一部分：获取申请
        apply_frame = ttk.LabelFrame(main_frame, text="获取申请", padding="10")
        apply_frame.pack(fill=tk.X, pady=10)
        
        # 输入条码
        ttk.Label(apply_frame, text="输入条码:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.barcode_entry = ttk.Entry(apply_frame, width=30)
        self.barcode_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # 获取申请按钮
        ttk.Button(apply_frame, text="获取申请", command=self._get_apply).grid(row=0, column=2, padx=5, pady=5)
        
        # 发送结果按钮
        ttk.Button(apply_frame, text="发送结果", command=self._send_result).grid(row=0, column=3, padx=5, pady=5)
        
        # 获取到的申请项目 - 高度缩小1cm
        ttk.Label(apply_frame, text="获取到的申请项目:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.apply_text = scrolledtext.ScrolledText(apply_frame, width=60, height=3, wrap=tk.WORD)  # 高度从5行减少到3行
        self.apply_text.grid(row=1, column=1, padx=5, pady=5, columnspan=3)
    
    def _get_apply(self):
        """获取申请项目"""
        barcode = self.barcode_entry.get()
        if not barcode:
            self.apply_text.delete(1.0, tk.END)
            self.apply_text.insert(tk.END, "请输入条码")
            return
        
        # 清空上次接收到的内容
        self.apply_text.delete(1.0, tk.END)
        self.apply_text.insert(tk.END, "正在获取申请项目...")
        
        # 在后台线程中执行获取申请操作
        def get_apply_thread():
            # 调用LIS客户端的get_apply方法获取申请项目
            apply_items = self.lis_client.get_apply(barcode)
            
            # 更新UI（必须在主线程中执行）
            def update_ui():
                self.apply_text.delete(1.0, tk.END)
                # 显示申请项目
                for item in apply_items:
                    self.apply_text.insert(tk.END, item + "\n")
                if not apply_items:
                    self.apply_text.insert(tk.END, "未获取到申请项目")
            
            # 在主线程中更新UI
            self.window.after(0, update_ui)
        
        # 启动后台线程
        import threading
        thread = threading.Thread(target=get_apply_thread)
        thread.daemon = True
        thread.start()
    
    def _send_result(self):
        """发送结果"""
        # 获取条码
        barcode = self.barcode_entry.get()
        if not barcode:
            messagebox.showwarning("提示", "请输入条码")
            return
        
        # 获取申请项目
        apply_text = self.apply_text.get(1.0, tk.END).strip()
        if not apply_text:
            messagebox.showwarning("提示", "请先获取申请项目")
            return
        
        # 提取申请项目列表
        test_items = [line.strip() for line in apply_text.split('\n') if line.strip()]
        
        if not test_items:
            messagebox.showwarning("提示", "没有找到测试项目")
            return
        
        # 在后台线程中执行发送结果操作
        def send_result_thread():
            # 调用LIS客户端的send_result方法发送结果
            success, message = self.lis_client.send_result(barcode, test_items)
            
            # 只记录到日志，不弹出弹窗
            if success:
                self.logger.info(f"发送结果成功: {message}")
            else:
                self.logger.error(f"发送结果失败: {message}")
        
        # 启动后台线程
        import threading
        thread = threading.Thread(target=send_result_thread)
        thread.daemon = True
        thread.start()
    
    def _on_error(self, error_msg):
        """错误回调函数，用于显示条码不一致等错误
        
        Args:
            error_msg: 错误信息
        """
        # 在测试项目文本框中显示错误信息
        self.apply_text.delete(1.0, tk.END)
        self.apply_text.insert(tk.END, f"错误: {error_msg}")
