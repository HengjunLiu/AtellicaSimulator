#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LIS模拟数据界面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox


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
        self.window.geometry("800x600")
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
        self.barcode_entry.grid(row=0, column=1, padx=5, pady=5, columnspan=2)
        
        # 获取申请按钮
        ttk.Button(apply_frame, text="获取申请", command=self._get_apply).grid(row=0, column=3, padx=5, pady=5)
        
        # 获取到的申请项目 - 高度缩小1cm
        ttk.Label(apply_frame, text="获取到的申请项目:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.apply_text = scrolledtext.ScrolledText(apply_frame, width=60, height=3, wrap=tk.WORD)  # 高度从5行减少到3行
        self.apply_text.grid(row=1, column=1, padx=5, pady=5, columnspan=3)
        
        # 第二部分：发送结果
        result_frame = ttk.LabelFrame(main_frame, text="发送结果", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 请输入结果 - 高度缩小1cm
        ttk.Label(result_frame, text="请输入结果:").pack(anchor=tk.W, padx=5, pady=5)
        self.result_text = scrolledtext.ScrolledText(result_frame, width=80, height=15, wrap=tk.WORD)  # 高度从20行减少到15行
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 发送结果按钮
        ttk.Button(result_frame, text="发送结果", command=self._send_result).pack(anchor=tk.E, padx=5, pady=5)
    
    def _get_apply(self):
        """获取申请项目"""
        barcode = self.barcode_entry.get()
        if not barcode:
            self.apply_text.delete(1.0, tk.END)
            self.apply_text.insert(tk.END, "请输入条码")
            return
        
        # 调用LIS客户端的get_apply方法获取申请项目
        apply_items = self.lis_client.get_apply(barcode)
        
        # 显示申请项目
        self.apply_text.delete(1.0, tk.END)
    
        for item in apply_items:
            self.apply_text.insert(tk.END, item + "\n")
    
    def _send_result(self):
        """发送结果"""
        result_data = self.result_text.get(1.0, tk.END).strip()
        if not result_data:
            # 弹出提示
            messagebox.showwarning("提示", "请输入结果数据")
            return
        
        # 模拟发送结果
        self.logger.log_lis(f"发送LIS结果: {result_data}")
        self.logger.info(f"发送LIS结果: {result_data}")
        
        # 弹出成功提示
        messagebox.showinfo("成功", "结果发送成功")
        # 清空结果文本框
        self.result_text.delete(1.0, tk.END)
    
    def _on_error(self, error_msg):
        """错误回调函数，用于显示条码不一致等错误
        
        Args:
            error_msg: 错误信息
        """
        # 在测试项目文本框中显示错误信息
        self.apply_text.delete(1.0, tk.END)
        self.apply_text.insert(tk.END, f"错误: {error_msg}")
