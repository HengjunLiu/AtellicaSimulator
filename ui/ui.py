#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI模块 - 图形用户界面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time

from .lisui import LisUI

APP_VERSION = "v1.7.0"

class AtellicaUI:
    """Atellica模拟器图形用户界面"""
    
    def __init__(self, config_manager, logger, core, las_server, lis_client):
        """初始化UI
        
        Args:
            config_manager: 配置管理器实例
            logger: 日志管理器实例
            core: 核心模拟逻辑实例
            las_server: LAS服务器实例
            lis_client: LIS客户端实例
        """
        self.config_manager = config_manager
        self.logger = logger
        self.core = core
        self.las_server = las_server
        self.lis_client = lis_client
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title(f"Atellica Solution Simulator {APP_VERSION}")
        self.root.geometry("1200x700")
        self.root.state('zoomed')  # 启动时最大化
        self.root.resizable(True, True)
        
        # 设置主题
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # 状态更新标志
        self.running = False
        self.update_thread = None
        
        # 日志缓冲区，用于存储当前会话的日志
        self.las_log_buffer = []
        self.lis_log_buffer = []
        self.log_max_lines = 500
        
        # 上一次的详细状态文本，用于比较内容变化
        self.last_detail_text = ""
        
        # 设置日志回调函数
        self.logger.set_las_log_callback(self._on_las_log_received)
        self.logger.set_lis_log_callback(self._on_lis_log_received)
        
        # 创建UI组件
        self._create_widgets()
        
        # 启动服务器
        self.las_server.start()
        self.lis_client.start()
        
        # 启动状态更新线程
        self.running = True
        self.update_thread = threading.Thread(target=self._update_status_loop, daemon=True)
        self.update_thread.start()
        
        # 启动日志更新线程
        self.log_update_thread = threading.Thread(target=self._update_logs_loop, daemon=True)
        self.log_update_thread.start()
    
    def _create_widgets(self):
        """创建UI组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题标签
        title_label = ttk.Label(main_frame, text="Atellica Solution Simulator", font=("Arial", 16, "bold"))
        title_label.pack(pady=(10, 0))
        
        # 版本号标签
        version_label = ttk.Label(main_frame, text=f"版本 {APP_VERSION}", font=("Arial", 10), foreground="gray")
        version_label.pack(pady=(0, 10))
        
        # 状态框架
        status_frame = ttk.LabelFrame(main_frame, text="设备状态", padding="5")
        status_frame.pack(fill=tk.X, pady=5)
        
        # 状态指标网格
        status_grid = ttk.Frame(status_frame)
        status_grid.pack(fill=tk.X)
        
        # 自动化接口状态
        ttk.Label(status_grid, text="自动化接口状态:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.automation_status_var = tk.StringVar()
        self.automation_status_label = ttk.Label(status_grid, textvariable=self.automation_status_var, width=15)
        self.automation_status_label.grid(row=0, column=1, padx=5, pady=2)
        
        # 仪器处理状态
        ttk.Label(status_grid, text="仪器处理状态:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.instrument_status_var = tk.StringVar()
        self.instrument_status_label = ttk.Label(status_grid, textvariable=self.instrument_status_var, width=15)
        self.instrument_status_label.grid(row=0, column=3, padx=5, pady=2)
        
        # LIS连接状态
        ttk.Label(status_grid, text="LIS连接状态:").grid(row=0, column=4, sticky=tk.W, padx=5, pady=2)
        self.lis_status_var = tk.StringVar()
        self.lis_status_label = ttk.Label(status_grid, textvariable=self.lis_status_var, width=15)
        self.lis_status_label.grid(row=0, column=5, padx=5, pady=2)
        
        # 接口位置信息
        ttk.Label(status_grid, text="接口位置数量:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.interface_count_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.interface_count_var, width=15).grid(row=1, column=1, padx=5, pady=2)
        
        # 在线试管数量
        ttk.Label(status_grid, text="在线试管数量:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.onboard_tubes_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.onboard_tubes_var, width=15).grid(row=1, column=3, padx=5, pady=2)
        
        # 已完成试管数量
        ttk.Label(status_grid, text="已完成试管数量:").grid(row=1, column=4, sticky=tk.W, padx=5, pady=2)
        self.completed_tubes_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.completed_tubes_var, width=15).grid(row=1, column=5, padx=5, pady=2)
        
        # 队列状态（新增）
        ttk.Label(status_grid, text="可返回样本数:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.return_ready_count_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.return_ready_count_var, width=15).grid(row=2, column=1, padx=5, pady=2)
        
        ttk.Label(status_grid, text="IP0队列长度:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        self.ip0_queue_len_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.ip0_queue_len_var, width=15).grid(row=2, column=3, padx=5, pady=2)
        
        ttk.Label(status_grid, text="IP1队列长度:").grid(row=2, column=4, sticky=tk.W, padx=5, pady=2)
        self.ip1_queue_len_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.ip1_queue_len_var, width=15).grid(row=2, column=5, padx=5, pady=2)
        
        ttk.Label(status_grid, text="IP0锁定状态:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.ip0_locked_var = tk.StringVar()
        self.ip0_locked_label = ttk.Label(status_grid, textvariable=self.ip0_locked_var, width=15)
        self.ip0_locked_label.grid(row=3, column=1, padx=5, pady=2)
        
        ttk.Label(status_grid, text="IP1锁定状态:").grid(row=3, column=2, sticky=tk.W, padx=5, pady=2)
        self.ip1_locked_var = tk.StringVar()
        self.ip1_locked_label = ttk.Label(status_grid, textvariable=self.ip1_locked_var, width=15)
        self.ip1_locked_label.grid(row=3, column=3, padx=5, pady=2)
        
        # 命令状态显示
        ttk.Label(status_grid, text="IP0命令状态:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        self.load_command_status_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.load_command_status_var, width=15).grid(row=4, column=1, padx=5, pady=2)
        
        ttk.Label(status_grid, text="IP1命令状态:").grid(row=4, column=2, sticky=tk.W, padx=5, pady=2)
        self.unload_command_status_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.unload_command_status_var, width=15).grid(row=4, column=3, padx=5, pady=2)
        
        # 中间内容框架（分为左侧参数配置、中间手动处理和右侧状态显示）
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.X, pady=5, expand=False)
        
        # 左侧：参数配置
        config_frame = ttk.LabelFrame(content_frame, text="参数配置", padding="10")
        config_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 配置选项卡
        config_notebook = ttk.Notebook(config_frame)
        config_notebook.pack(fill=tk.BOTH, expand=True)
        
        # 设备状态配置
        device_config_frame = ttk.Frame(config_notebook, padding="10")
        config_notebook.add(device_config_frame, text="设备状态")
        
        # 自动化接口状态配置
        ttk.Label(device_config_frame, text="自动化接口状态:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.automation_status_combobox = ttk.Combobox(device_config_frame, values=["Green", "Red", "Critical"], width=15)
        self.automation_status_combobox.set("Green")
        self.automation_status_combobox.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(device_config_frame, text="应用", command=self._update_automation_status).grid(row=0, column=2, padx=5, pady=5)
        
        # 仪器处理状态配置
        ttk.Label(device_config_frame, text="仪器处理状态:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.instrument_status_combobox = ttk.Combobox(device_config_frame, values=["Green", "Yellow", "Red"], width=15)
        self.instrument_status_combobox.set("Green")
        self.instrument_status_combobox.grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(device_config_frame, text="应用", command=self._update_instrument_status).grid(row=1, column=2, padx=5, pady=5)
        
        # LIS连接状态配置
        ttk.Label(device_config_frame, text="LIS连接状态:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.lis_connection_combobox = ttk.Combobox(device_config_frame, values=["Connected", "Disconnected"], width=15)
        self.lis_connection_combobox.set("Connected")
        self.lis_connection_combobox.grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(device_config_frame, text="应用", command=self._update_lis_status).grid(row=2, column=2, padx=5, pady=5)
        
        # IP0远程控制状态配置
        ttk.Label(device_config_frame, text="IP0远程控制状态:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.ip0_remote_status_combobox = ttk.Combobox(device_config_frame, values=["Offline or Local", "Online Loading Only Mode"], width=25)
        self.ip0_remote_status_combobox.set("Offline or Local")
        self.ip0_remote_status_combobox.grid(row=3, column=1, padx=5, pady=5)
        ttk.Button(device_config_frame, text="应用", command=self._update_ip0_remote_status).grid(row=3, column=2, padx=5, pady=5)
        
        # IP1远程控制状态配置
        ttk.Label(device_config_frame, text="IP1远程控制状态:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.ip1_remote_status_combobox = ttk.Combobox(device_config_frame, values=["Offline or Local", "Online Unloading Only Mode"], width=25)
        self.ip1_remote_status_combobox.set("Offline or Local")
        self.ip1_remote_status_combobox.grid(row=4, column=1, padx=5, pady=5)
        ttk.Button(device_config_frame, text="应用", command=self._update_ip1_remote_status).grid(row=4, column=2, padx=5, pady=5)
        
        # 中间：手动样本处理
        manual_frame = ttk.LabelFrame(content_frame, text="手动样本处理", padding="10")
        manual_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 样本处理提示区域
        self.manual_prompt_frame = ttk.Frame(manual_frame, padding="10")
        self.manual_prompt_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建画布用于绘制提示圆圈
        self.prompt_canvas = tk.Canvas(self.manual_prompt_frame, width=300, height=200, bg="white")
        self.prompt_canvas.pack(pady=10)
        
        # 提示文本
        self.prompt_text = ttk.Label(self.manual_prompt_frame, text="等待样本处理请求...", font=("Arial", 12))
        self.prompt_text.pack(pady=10)
        
        # 按钮区域（输入框和完成按钮水平对齐）
        self.button_frame = ttk.Frame(self.manual_prompt_frame)
        self.button_frame.pack(pady=10)
        
        # 样本ID输入框（用于UNLOAD请求）
        self.sample_id_label = ttk.Label(self.button_frame, text="样本ID:")
        self.sample_id_label.pack(side=tk.LEFT, padx=5)
        
        self.sample_id_entry = ttk.Entry(self.button_frame, width=20)
        self.sample_id_entry.pack(side=tk.LEFT, padx=5)
        
        # 绑定回车键到完成按钮
        self.sample_id_entry.bind('<Return>', lambda event: self._on_complete_button_click())
        
        # 完成按钮
        self.complete_button = ttk.Button(self.button_frame, text="完成", command=self._on_complete_button_click, state=tk.DISABLED)
        self.complete_button.pack(side=tk.LEFT, padx=5)
        
        # 隐藏输入框初始状态
        self.sample_id_label.pack_forget()
        self.sample_id_entry.pack_forget()
        
        # 右侧：详细状态显示
        detail_frame = ttk.LabelFrame(content_frame, text="详细状态", padding="10")
        detail_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 详细状态文本框
        self.detail_text = scrolledtext.ScrolledText(detail_frame, width=60, height=10, wrap=tk.WORD)
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        
        # 底部：日志显示
        logs_frame = ttk.LabelFrame(main_frame, text="通讯日志", padding="10")
        logs_frame.pack(fill=tk.BOTH, expand=False, pady=5)
        
        # 日志选项卡
        logs_notebook = ttk.Notebook(logs_frame)
        logs_notebook.pack(fill=tk.BOTH, expand=True)
        
        # LAS日志
        las_log_frame = ttk.Frame(logs_notebook, padding="10")
        logs_notebook.add(las_log_frame, text="LAS日志")
        self.las_log_text = scrolledtext.ScrolledText(las_log_frame, width=80, height=8, wrap=tk.WORD)
        self.las_log_text.pack(fill=tk.BOTH, expand=True)
        
        # LIS日志
        lis_log_frame = ttk.Frame(logs_notebook, padding="10")
        logs_notebook.add(lis_log_frame, text="LIS日志")
        self.lis_log_text = scrolledtext.ScrolledText(lis_log_frame, width=80, height=8, wrap=tk.WORD)
        self.lis_log_text.pack(fill=tk.BOTH, expand=True)
        
        # 底部按钮区域
        button_frame = ttk.Frame(main_frame, padding="5")
        button_frame.pack(fill=tk.X)
        
        # 添加左侧按钮组
        left_button_frame = ttk.Frame(button_frame)
        left_button_frame.pack(side=tk.LEFT)
        ttk.Button(left_button_frame, text="刷新状态", command=self._update_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_button_frame, text="在机标本", command=self._show_onboard_samples).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_button_frame, text="编辑库存", command=self._show_inventory_editor).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_button_frame, text="清空日志", command=self._clear_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_button_frame, text="LIS模拟", command=self._open_lis_simulation).pack(side=tk.LEFT, padx=5)
        
        # 添加右侧退出按钮
        right_button_frame = ttk.Frame(button_frame)
        right_button_frame.pack(side=tk.RIGHT)
        ttk.Button(right_button_frame, text="退出", command=self._quit).pack(side=tk.RIGHT, padx=5)
    
    def _update_status_loop(self):
        """定期更新状态"""
        while self.running:
            self._update_status()
            time.sleep(2)  # 每2秒更新一次
    
    def _update_logs_loop(self):
        """定期更新日志"""
        while self.running:
            self._update_logs()
            time.sleep(1)  # 每1秒更新一次
    
    def _update_status(self):
        """更新设备状态显示"""
        try:
            # 获取仪器健康状态
            health_status = self.core.get_instrument_health()
            
            # 更新状态标签
            automation_status = health_status['automation_interface_status']
            if automation_status == 1:
                self.automation_status_var.set("Green")
                self.automation_status_label.configure(foreground="green")
            elif automation_status == 3:
                self.automation_status_var.set("Red")
                self.automation_status_label.configure(foreground="red")
            elif automation_status == 4:
                self.automation_status_var.set("Critical")
                self.automation_status_label.configure(foreground="red")
            
            instrument_status = health_status['instrument_process_status']
            if instrument_status == 1:
                self.instrument_status_var.set("Green")
                self.instrument_status_label.configure(foreground="green")
            elif instrument_status == 2:
                self.instrument_status_var.set("Yellow")
                self.instrument_status_label.configure(foreground="orange")
            elif instrument_status == 3:
                self.instrument_status_var.set("Red")
                self.instrument_status_label.configure(foreground="red")
            
            lis_status = health_status['lis_connection_status']
            if lis_status == 1:
                self.lis_status_var.set("Connected")
                self.lis_status_label.configure(foreground="green")
            elif lis_status == 2:
                self.lis_status_var.set("Disconnected")
                self.lis_status_label.configure(foreground="red")
            
            # 更新其他状态信息
            self.interface_count_var.set(str(health_status['interface_positions']))
            self.onboard_tubes_var.set(str(health_status['on_board_tube_count']))
            self.completed_tubes_var.set(str(health_status['completed_tube_count']))
            
            # 更新队列状态信息（新增）
            return_ready_count = self.core.get_return_ready_count()
            self.return_ready_count_var.set(str(return_ready_count))
            
            # 获取队列信息
            ip0_queue = self.core.get_queue_info(0)
            ip1_queue = self.core.get_queue_info(1)
            
            self.ip0_queue_len_var.set(str(len(ip0_queue)))
            self.ip1_queue_len_var.set(str(len(ip1_queue)))
            
            # 获取锁定状态
            ip0_locked = 1 if self.core.locked_carriers[0] else 0
            ip1_locked = 1 if self.core.locked_carriers[1] else 0
            
            if ip0_locked:
                self.ip0_locked_var.set("Locked")
                self.ip0_locked_label.configure(foreground="red")
            else:
                self.ip0_locked_var.set("Unlocked")
                self.ip0_locked_label.configure(foreground="green")
            
            if ip1_locked:
                self.ip1_locked_var.set("Locked")
                self.ip1_locked_label.configure(foreground="red")
            else:
                self.ip1_locked_var.set("Unlocked")
                self.ip1_locked_label.configure(foreground="green")
            
            # 自动更新IP0和IP1的锁所有权（根据程序状态）
            health_status = self.core.get_instrument_health()
            # 锁所有权状态已移除以简化界面
            
            # 更新详细状态文本
            detail_text = f"设备状态详细信息：\n"
            detail_text += f"自动化接口状态：{'Green' if automation_status == 1 else 'Red' if automation_status == 3 else 'Critical' if automation_status == 4 else automation_status}\n"
            detail_text += f"仪器处理状态：{'Green' if instrument_status == 1 else 'Yellow' if instrument_status == 2 else 'Red'}\n"
            detail_text += f"LIS连接状态：{'Connected' if lis_status == 1 else 'Disconnected'}\n"
            detail_text += f"接口位置数量：{health_status['interface_positions']}\n"
            
            for i in range(health_status['interface_positions']):
                remote_status = health_status['remote_control_status'][i] if i < len(health_status['remote_control_status']) else 1
                lock_ownership = health_status['lock_ownership'][i] if i < len(health_status['lock_ownership']) else 2
                
                # 远程控制状态描述
                if i == 0:  # IP0
                    if remote_status == 1:
                        remote_desc = "Offline or Local"
                    elif remote_status == 4:
                        remote_desc = "Online Loading Only Mode"
                    else:
                        remote_desc = str(remote_status)
                else:  # IP1
                    if remote_status == 1:
                        remote_desc = "Offline or Local"
                    elif remote_status == 5:
                        remote_desc = "Online Unloading Only Mode"
                    else:
                        remote_desc = str(remote_status)
                
                # 锁所有权描述
                lock_desc = "Locked by Instrument" if lock_ownership == 1 else "Not Locked by Instrument"
                
                detail_text += f"IP{i} - 远程控制状态：{remote_desc}, 锁所有权：{lock_desc}\n"
            
            detail_text += f"处理积压：{health_status['processing_backlog']}\n"
            detail_text += f"样本获取延迟：{health_status['sample_acquisition_delay']}\n"
            detail_text += f"在线试管数量：{health_status['on_board_tube_count']}\n"
            detail_text += f"已完成试管数量：{health_status['completed_tube_count']}\n"
            
            # 获取队列详细信息
            detail_text += f"\n队列管理详细信息：\n"
            # 队列管理详细信息：
            # 获取IP0和IP1各自的就绪状态
            ip0_ready = self.core.get_ready_to_load(0)
            ip1_ready = self.core.get_ready_to_load(1)
            detail_text += f"IP0就绪状态：{'Ready to Load' if ip0_ready == 1 else 'Not Ready to Load'}\n"
            detail_text += f"IP1就绪状态：{'Ready to Load' if ip1_ready == 1 else 'Not Ready to Load'}\n"
            detail_text += f"可返回样本数：{return_ready_count}\n"
            
            # 更新命令状态显示
            load_status = getattr(self.core, 'load_command_status', 1)
            load_status_map = {
                1: "Success",
                2: "Lock Carrier",
                3: "OK to Unlock",
                4: "Queue Mismatch",
                5: "Interface Offline",
                6: "Load Skipped",
                7: "Skipped Loading",
                8: "Unsupported ID"
            }
            load_status_text = load_status_map.get(load_status, "Success")
            self.load_command_status_var.set(load_status_text)
            
            unload_status = getattr(self.core, 'unload_command_status', 1)
            unload_status_map = {
                1: "Success",
                2: "Lock Carrier",
                3: "OK to Unlock",
                4: "Queue Mismatch",
                5: "Interface Offline",
                6: "Unload Skipped",
                7: "Skipped Unloading"
            }
            unload_status_text = unload_status_map.get(unload_status, "Success")
            self.unload_command_status_var.set(unload_status_text)
            
            # 在详细状态中添加命令状态信息
            detail_text += f"\n命令状态详细信息：\n"
            detail_text += f"IP0命令状态：{load_status_map.get(load_status, load_status)}\n"
            detail_text += f"IP1命令状态：{unload_status_map.get(unload_status, unload_status)}\n"
            
            # IP0队列详细信息
            detail_text += f"\nIP0队列 (长度: {len(ip0_queue)})：\n"
            if ip0_queue:
                for i, item in enumerate(ip0_queue):
                    detail_text += f"  [{i+1}] 样本ID: {item.get('sample_id', 'N/A')}, 操作类型: {item.get('operation', 'N/A')}, "
                    detail_text += f"位置: {item.get('position', 'N/A')}, 状态: {item.get('status', 'N/A')}\n"
            else:
                detail_text += "  队列为空\n"
            detail_text += f"IP0锁定状态：{'Locked' if ip0_locked else 'Unlocked'}\n"
            
            # IP1队列详细信息
            detail_text += f"\nIP1队列 (长度: {len(ip1_queue)})：\n"
            if ip1_queue:
                for i, item in enumerate(ip1_queue):
                    detail_text += f"  [{i+1}] 样本ID: {item.get('sample_id', 'N/A')}, 操作类型: {item.get('operation', 'N/A')}, "
                    detail_text += f"位置: {item.get('position', 'N/A')}, 状态: {item.get('status', 'N/A')}\n"
            else:
                detail_text += "  队列为空\n"
            detail_text += f"IP1锁定状态：{'Locked' if ip1_locked else 'Unlocked'}\n"
            
            # 获取测试库存信息
            test_inventory = self.core.get_test_inventory()
            detail_text += f"\n测试项目数量：{len(test_inventory['tests'])}\n"
            for test in test_inventory['tests'][:5]:  # 只显示前5个测试项目
                detail_text += f"  {test['name']}: 可用数量={test['count']}, 状态={'Green' if test['status'] == 1 else 'Yellow' if test['status'] == 2 else 'Red'}\n"
            if len(test_inventory['tests']) > 5:
                detail_text += f"  ... 等{len(test_inventory['tests']) - 5}个测试项目\n"
            
            # 获取耗材库存信息
            consumable_inventory = self.core.get_consumable_inventory()
            detail_text += f"\n模块数量：{len(consumable_inventory['modules'])}\n"
            for module in consumable_inventory['modules']:
                detail_text += f"  模块 {module['id']}：耗材数量={len(module['consumables'])}\n"
            
            # 只有当详细状态文本内容发生变化时才更新
            if detail_text != self.last_detail_text:
                self.detail_text.delete(1.0, tk.END)
                self.detail_text.insert(tk.END, detail_text)
                # 更新上一次的详细状态文本
                self.last_detail_text = detail_text
            
        except Exception as e:
            self.logger.error(f"Error updating UI status: {str(e)}")
    
    def _on_las_log_received(self, log_message):
        """LAS日志回调函数
        
        Args:
            log_message: 完整的日志消息
        """
        # 将新日志添加到缓冲区
        self.las_log_buffer.append(log_message)
        
        # 限制缓冲区大小
        if len(self.las_log_buffer) > self.log_max_lines:
            self.las_log_buffer = self.las_log_buffer[-self.log_max_lines:]
    
    def _on_lis_log_received(self, log_message):
        """LIS日志回调函数
        
        Args:
            log_message: 完整的日志消息
        """
        # 将新日志添加到缓冲区
        self.lis_log_buffer.append(log_message)
        
        # 限制缓冲区大小
        if len(self.lis_log_buffer) > self.log_max_lines:
            self.lis_log_buffer = self.lis_log_buffer[-self.log_max_lines:]
    
    def _update_logs(self):
        """更新日志显示"""
        try:
            # 更新LAS日志
            las_log_content = '\n'.join(self.las_log_buffer) + '\n'
            self.las_log_text.delete(1.0, tk.END)
            self.las_log_text.insert(tk.END, las_log_content)
            self.las_log_text.see(tk.END)  # 滚动到最后
            
            # 更新LIS日志
            lis_log_content = '\n'.join(self.lis_log_buffer) + '\n'
            self.lis_log_text.delete(1.0, tk.END)
            self.lis_log_text.insert(tk.END, lis_log_content)
            self.lis_log_text.see(tk.END)  # 滚动到最后
            
        except Exception as e:
            self.logger.error(f"Error updating UI logs: {str(e)}")
    
    def _update_automation_status(self):
        """更新自动化接口状态"""
        status = self.automation_status_combobox.get()
        if status == "Green":
            status_code = 1
        elif status == "Red":
            status_code = 3
        elif status == "Critical":
            status_code = 4
        self.core.update_automation_interface_status(status_code)
        self._update_status()
    
    def _update_instrument_status(self):
        """更新仪器处理状态"""
        status = self.instrument_status_combobox.get()
        if status == "Green":
            status_code = 1
        elif status == "Yellow":
            status_code = 2
        else:
            status_code = 3
        self.core.update_instrument_process_status(status_code)
        self._update_status()
    
    def _update_lis_status(self):
        """更新LIS连接状态"""
        status = self.lis_connection_combobox.get()
        status_code = 1 if status == "Connected" else 2
        self.core.update_lis_connection_status(status_code)
        self._update_status()
    
    def _update_ip0_remote_status(self):
        """更新IP0远程控制状态"""
        status = self.ip0_remote_status_combobox.get()
        status_code = 1 if status == "Offline or Local" else 4
        self.core.update_remote_control_status(0, status_code)
        self._update_status()
    
    def _update_ip1_remote_status(self):
        """更新IP1远程控制状态"""
        status = self.ip1_remote_status_combobox.get()
        status_code = 1 if status == "Offline or Local" else 5
        self.core.update_remote_control_status(1, status_code)
        self._update_status()
    
    def _show_inventory_editor(self):
        """显示库存编辑弹窗"""
        editor_window = tk.Toplevel(self.root)
        editor_window.title("库存编辑")
        editor_window.geometry("1100x650")
        editor_window.transient(self.root)
        editor_window.grab_set()
        
        notebook = ttk.Notebook(editor_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self._create_test_inventory_tab(notebook)
        self._create_consumable_inventory_tab(notebook)
        
        button_frame = ttk.Frame(editor_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="保存并关闭", command=editor_window.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="刷新", command=self._refresh_inventory_tabs).pack(side=tk.RIGHT, padx=5)
    
    def _create_test_inventory_tab(self, notebook):
        """创建测试项目库存编辑选项卡"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="测试项目")
        
        # 编辑区域（放在顶部）
        edit_frame = ttk.LabelFrame(frame, text="编辑测试项目", padding="10")
        edit_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(edit_frame, text="测试项目名称:").grid(row=0, column=0, padx=5, pady=5)
        self.test_name_var = tk.StringVar()
        self.test_name_entry = ttk.Entry(edit_frame, textvariable=self.test_name_var, width=25)
        self.test_name_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(edit_frame, text="数量:").grid(row=0, column=2, padx=5, pady=5)
        self.test_count_var = tk.StringVar()
        self.test_count_entry = ttk.Entry(edit_frame, textvariable=self.test_count_var, width=10)
        self.test_count_entry.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(edit_frame, text="状态:").grid(row=0, column=4, padx=5, pady=5)
        self.test_status_var = tk.StringVar()
        self.test_status_combobox = ttk.Combobox(edit_frame, textvariable=self.test_status_var, 
                                                   values=['Green', 'Yellow', 'Red'], width=10)
        self.test_status_combobox.grid(row=0, column=5, padx=5, pady=5)
        
        ttk.Button(edit_frame, text="添加", command=self._add_test_inventory).grid(row=0, column=6, padx=5, pady=5)
        ttk.Button(edit_frame, text="更新", command=self._update_test_inventory).grid(row=0, column=7, padx=5, pady=5)
        ttk.Button(edit_frame, text="删除", command=self._delete_test_inventory).grid(row=0, column=8, padx=5, pady=5)
        
        ttk.Label(edit_frame, text="提示: 输入名称后点击添加，或选择列表中项目后点击更新/删除", 
                  foreground="gray", font=("Arial", 8)).grid(row=1, column=0, columnspan=9, padx=5, pady=5)
        
        # 列表区域
        columns = ('name', 'count', 'status')
        tree = ttk.Treeview(frame, columns=columns, show='headings', height=15, selectmode='browse')
        tree.heading('name', text='测试项目名称')
        tree.heading('count', text='可用数量')
        tree.heading('status', text='状态')
        tree.column('name', width=250)
        tree.column('count', width=100)
        tree.column('status', width=100)
        
        tree.bind('<<TreeviewSelect>>', self._on_test_tree_select)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.test_inventory_tree = tree
        self._load_test_inventory()
    
    def _create_consumable_inventory_tab(self, notebook):
        """创建耗材库存编辑选项卡"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="耗材库存")
        
        # 编辑区域（放在顶部）
        edit_frame = ttk.LabelFrame(frame, text="编辑耗材状态", padding="10")
        edit_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(edit_frame, text="模块ID:").grid(row=0, column=0, padx=5, pady=5)
        self.consumable_module_var = tk.StringVar()
        self.consumable_module_entry = ttk.Entry(edit_frame, textvariable=self.consumable_module_var, width=15)
        self.consumable_module_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(edit_frame, text="耗材ID:").grid(row=0, column=2, padx=5, pady=5)
        self.consumable_id_var = tk.StringVar()
        self.consumable_id_entry = ttk.Entry(edit_frame, textvariable=self.consumable_id_var, width=10)
        self.consumable_id_entry.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(edit_frame, text="状态:").grid(row=0, column=4, padx=5, pady=5)
        self.consumable_status_var = tk.StringVar()
        self.consumable_status_combobox = ttk.Combobox(edit_frame, textvariable=self.consumable_status_var,
                                                         values=['Green', 'Yellow', 'Red'], width=10)
        self.consumable_status_combobox.grid(row=0, column=5, padx=5, pady=5)
        
        ttk.Button(edit_frame, text="添加", command=self._add_consumable_inventory).grid(row=0, column=6, padx=5, pady=5)
        ttk.Button(edit_frame, text="更新", command=self._update_consumable_inventory).grid(row=0, column=7, padx=5, pady=5)
        ttk.Button(edit_frame, text="删除", command=self._delete_consumable_inventory).grid(row=0, column=8, padx=5, pady=5)
        
        ttk.Label(edit_frame, text="提示: 输入模块和耗材ID后点击添加，或选择列表中项目后点击更新/删除", 
                  foreground="gray", font=("Arial", 8)).grid(row=1, column=0, columnspan=9, padx=5, pady=5)
        
        # 列表区域
        columns = ('module', 'consumable', 'status')
        tree = ttk.Treeview(frame, columns=columns, show='headings', height=15, selectmode='browse')
        tree.heading('module', text='模块ID')
        tree.heading('consumable', text='耗材ID')
        tree.heading('status', text='状态')
        tree.column('module', width=150)
        tree.column('consumable', width=100)
        tree.column('status', width=100)
        
        tree.bind('<<TreeviewSelect>>', self._on_consumable_tree_select)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.consumable_inventory_tree = tree
        self._load_consumable_inventory()
    
    def _load_test_inventory(self):
        """加载测试项目库存到Treeview"""
        for item in self.test_inventory_tree.get_children():
            self.test_inventory_tree.delete(item)
        
        for test in self.core.test_inventory['tests']:
            status_text = 'Green' if test['status'] == 1 else 'Yellow' if test['status'] == 2 else 'Red'
            self.test_inventory_tree.insert('', tk.END, values=(test['name'], test['count'], status_text))
    
    def _load_consumable_inventory(self):
        """加载耗材库存到Treeview"""
        for item in self.consumable_inventory_tree.get_children():
            self.consumable_inventory_tree.delete(item)
        
        for module in self.core.consumable_inventory['modules']:
            for cons in module['consumables']:
                status_text = 'Green' if cons['status'] == 1 else 'Yellow' if cons['status'] == 2 else 'Red'
                self.consumable_inventory_tree.insert('', tk.END, 
                    values=(module['id'], cons['id'], status_text))
    
    def _refresh_inventory_tabs(self):
        """刷新库存选项卡"""
        self._load_test_inventory()
        self._load_consumable_inventory()
        
        test_names = [test['name'] for test in self.core.test_inventory['tests']]
        self.test_combobox['values'] = test_names
        
        consumable_ids = []
        for module in self.core.consumable_inventory['modules']:
            for cons in module['consumables']:
                consumable_ids.append(f"{module['id']}_{cons['id']}")
        self.consumable_combobox['values'] = consumable_ids
    
    def _on_test_tree_select(self, event):
        """测试项目列表选择事件"""
        selected = self.test_inventory_tree.selection()
        if selected:
            item = self.test_inventory_tree.item(selected[0])
            values = item['values']
            if values:
                self.test_name_var.set(str(values[0]))
                self.test_count_var.set(str(values[1]))
                self.test_status_var.set(str(values[2]))
    
    def _on_consumable_tree_select(self, event):
        """耗材列表选择事件"""
        selected = self.consumable_inventory_tree.selection()
        if selected:
            item = self.consumable_inventory_tree.item(selected[0])
            values = item['values']
            if values:
                self.consumable_module_var.set(str(values[0]))
                self.consumable_id_var.set(str(values[1]))
                self.consumable_status_var.set(str(values[2]))
    
    def _add_test_inventory(self):
        """添加测试项目库存"""
        test_name = self.test_name_var.get().strip()
        try:
            count = int(self.test_count_var.get())
            status_text = self.test_status_var.get()
            status = 1 if status_text == 'Green' else 2 if status_text == 'Yellow' else 3
            
            if not test_name:
                self.logger.error("Test name cannot be empty")
                return
            
            self.core.add_test_inventory(test_name, count, status)
            self._load_test_inventory()
            self.config_manager.save()
            self.logger.info(f"Added test inventory: {test_name}, count={count}, status={status_text}")
            
            self.test_name_var.set("")
            self.test_count_var.set("")
            self.test_status_var.set("")
        except ValueError:
            self.logger.error("Invalid count value")
    
    def _update_test_inventory(self):
        """更新测试项目库存"""
        test_name = self.test_name_var.get().strip()
        try:
            count = int(self.test_count_var.get())
            status_text = self.test_status_var.get()
            status = 1 if status_text == 'Green' else 2 if status_text == 'Yellow' else 3
            
            if not test_name:
                self.logger.error("Test name cannot be empty")
                return
            
            self.core.update_test_inventory(test_name, count, status)
            self._load_test_inventory()
            self.config_manager.save()
            self.logger.info(f"Updated test inventory: {test_name}, count={count}, status={status_text}")
        except ValueError:
            self.logger.error("Invalid count value")
    
    def _delete_test_inventory(self):
        """删除测试项目库存"""
        test_name = self.test_name_var.get().strip()
        if not test_name:
            self.logger.error("Test name cannot be empty")
            return
        
        self.core.delete_test_inventory(test_name)
        self._load_test_inventory()
        self.config_manager.save()
        self.logger.info(f"Deleted test inventory: {test_name}")
        
        self.test_name_var.set("")
        self.test_count_var.set("")
        self.test_status_var.set("")
    
    def _on_consumable_selected(self, event):
        """耗材选择事件"""
        selection = self.consumable_combobox.get()
        if '_' in selection:
            module_id, cons_id = selection.split('_')
            cons_id = int(cons_id)
            for module in self.core.consumable_inventory['modules']:
                if module['id'] == module_id:
                    for cons in module['consumables']:
                        if cons['id'] == cons_id:
                            status_text = 'Green' if cons['status'] == 1 else 'Yellow' if cons['status'] == 2 else 'Red'
                            self.consumable_status_var.set(status_text)
                            break
    
    def _add_consumable_inventory(self):
        """添加耗材库存"""
        module_id = self.consumable_module_var.get().strip()
        try:
            consumable_id = int(self.consumable_id_var.get())
            status_text = self.consumable_status_var.get()
            status = 1 if status_text == 'Green' else 2 if status_text == 'Yellow' else 3
            
            if not module_id:
                self.logger.error("Module ID cannot be empty")
                return
            
            self.core.add_consumable_inventory(module_id, consumable_id, status)
            self._load_consumable_inventory()
            self.config_manager.save()
            self.logger.info(f"Added consumable inventory: module={module_id}, consumable={consumable_id}, status={status_text}")
            
            self.consumable_module_var.set("")
            self.consumable_id_var.set("")
            self.consumable_status_var.set("")
        except ValueError:
            self.logger.error("Invalid consumable ID value")
    
    def _update_consumable_inventory(self):
        """更新耗材库存"""
        module_id = self.consumable_module_var.get().strip()
        try:
            consumable_id = int(self.consumable_id_var.get())
            status_text = self.consumable_status_var.get()
            status = 1 if status_text == 'Green' else 2 if status_text == 'Yellow' else 3
            
            if not module_id:
                self.logger.error("Module ID cannot be empty")
                return
            
            self.core.update_consumable_inventory(module_id, consumable_id, status)
            self._load_consumable_inventory()
            self.config_manager.save()
            self.logger.info(f"Updated consumable inventory: module={module_id}, consumable={consumable_id}, status={status_text}")
        except ValueError:
            self.logger.error("Invalid consumable ID value")
    
    def _delete_consumable_inventory(self):
        """删除耗材库存"""
        module_id = self.consumable_module_var.get().strip()
        try:
            consumable_id = int(self.consumable_id_var.get())
            
            if not module_id:
                self.logger.error("Module ID cannot be empty")
                return
            
            self.core.delete_consumable_inventory(module_id, consumable_id)
            self._load_consumable_inventory()
            self.config_manager.save()
            self.logger.info(f"Deleted consumable inventory: module={module_id}, consumable={consumable_id}")
            
            self.consumable_module_var.set("")
            self.consumable_id_var.set("")
            self.consumable_status_var.set("")
        except ValueError:
            self.logger.error("Invalid consumable ID value")
    
    def _update_test_inventory(self):
        """更新测试项目库存"""
        test_name = self.test_combobox.get()
        try:
            count = int(self.test_count_var.get())
            status_text = self.test_status_var.get()
            status = 1 if status_text == 'Green' else 2 if status_text == 'Yellow' else 3
            self.core.update_test_inventory(test_name, count, status)
            self._load_test_inventory()
            self.config_manager.save()
            self.logger.info(f"Updated test inventory: {test_name}, count={count}, status={status_text}")
        except ValueError:
            self.logger.error("Invalid count value")
    
    def _update_consumable_inventory(self):
        """更新耗材库存"""
        selection = self.consumable_combobox.get()
        try:
            status_text = self.consumable_status_var.get()
            status = 1 if status_text == 'Green' else 2 if status_text == 'Yellow' else 3
            
            if '_' in selection:
                module_id, cons_id = selection.split('_')
                cons_id = int(cons_id)
                self.core.update_consumable_inventory(module_id, cons_id, status)
                self._load_consumable_inventory()
                self.config_manager.save()
                self.logger.info(f"Updated consumable inventory: {module_id}, consumable={cons_id}, status={status_text}")
        except ValueError as e:
            self.logger.error(f"Invalid consumable update: {str(e)}")
    
    def _clear_logs(self):
        """清空日志"""
        # 清空UI文本框
        self.las_log_text.delete(1.0, tk.END)
        self.lis_log_text.delete(1.0, tk.END)
        # 清空日志缓冲区，防止日志重新显示
        self.las_log_buffer.clear()
        self.lis_log_buffer.clear()
    
    def _open_lis_simulation(self):
        """打开LIS模拟数据窗口"""
        # 创建LisUI实例，传递lis_client
        self.lis_ui = LisUI(self.root, self.logger, self.lis_client)

    
    def _show_manual_prompt(self, request_type, interface_position, sample_id):
        """显示手动处理提示
        
        Args:
            request_type: 请求类型 ('load' 或 'unload')
            interface_position: 接口位置 (0=IP0, 1=IP1)
            sample_id: 样本ID
        
        Returns:
            bool: 是否成功显示提示（如果已有请求正在显示，返回False）
        """
        # 检查是否已有请求正在显示
        if hasattr(self, 'current_request') and self.current_request:
            self.logger.warning(f"Cannot show prompt for {request_type} IP{interface_position}: another request is already being displayed")
            return False
        
        self.prompt_canvas.delete("all")
        
        # 保存请求类型和颜色信息
        # 注意：在手工模式下，LOAD和UNLOAD的实际操作与字面意思相反
        # LOAD请求：实际是从LAS取走样本（对LAS来说是卸载）
        # UNLOAD请求：实际是向LAS放入样本（对LAS来说是装载）
        if request_type == 'load':
            self.circle_color = "lightgreen"
            self.circle_outline = "green"
            self.text_color = "green"
            prompt_text = f"将从LAS的IP{interface_position}取走标本"
        else:
            self.circle_color = "lightyellow"
            self.circle_outline = "yellow"
            self.text_color = "orange"
            prompt_text = f"将向LAS的IP{interface_position}装上标本"
        
        self.prompt_text.configure(text=prompt_text, foreground=self.text_color)
        
        # 绘制初始圆圈
        self.circle = self.prompt_canvas.create_oval(50, 50, 250, 150, 
                                                   fill=self.circle_color, 
                                                   outline=self.circle_outline, 
                                                   width=3)
        
        # 处理样本ID输入框
        if request_type == 'unload':
            # 显示输入框并预填样本ID
            self.sample_id_entry.delete(0, tk.END)
            if sample_id:
                self.sample_id_entry.insert(0, sample_id)
            # 先unpack完成按钮，确保正确的pack顺序：标签→输入框→完成按钮
            self.complete_button.pack_forget()
            self.sample_id_label.pack(side=tk.LEFT, padx=5)
            self.sample_id_entry.pack(side=tk.LEFT, padx=5)
            self.complete_button.pack(side=tk.LEFT, padx=5)
        else:
            # 隐藏输入框，只显示完成按钮
            self.sample_id_label.pack_forget()
            self.sample_id_entry.pack_forget()
        
        # 启用完成按钮
        self.complete_button.configure(state=tk.NORMAL)
        
        # 保存当前请求信息
        self.current_request = {
            'type': request_type,
            'interface_position': interface_position,
            'sample_id': sample_id
        }
        
        # 启动闪烁效果
        self.flash_state = True
        self._start_flash()
        
        return True
    
    def _start_flash(self):
        """启动闪烁效果"""
        if hasattr(self, 'flash_job'):
            self.root.after_cancel(self.flash_job)
        
        # 开始闪烁
        self._toggle_flash()
    
    def _toggle_flash(self):
        """切换闪烁状态"""
        if not hasattr(self, 'current_request'):
            return
        
        self.flash_state = not self.flash_state
        
        if self.flash_state:
            # 显示圆圈和文字
            self.prompt_canvas.itemconfig(self.circle, fill=self.circle_color, outline=self.circle_outline)
            self.prompt_text.configure(foreground=self.text_color)
        else:
            # 隐藏圆圈（变透明）和文字（变浅色）
            self.prompt_canvas.itemconfig(self.circle, fill="", outline="")
            self.prompt_text.configure(foreground="lightgray")
        
        # 继续闪烁，每500毫秒切换一次
        self.flash_job = self.root.after(500, self._toggle_flash)
    
    def _on_complete_button_click(self):
        """完成按钮点击事件"""
        if hasattr(self, 'current_request'):
            # 停止闪烁效果
            if hasattr(self, 'flash_job'):
                self.root.after_cancel(self.flash_job)
                delattr(self, 'flash_job')
            
            # 获取实际使用的样本ID（对于UNLOAD请求，允许手动修改）
            request = self.current_request.copy()
            if request['type'] == 'unload':
                # 从输入框获取样本ID
                actual_sample_id = self.sample_id_entry.get().strip()
                if actual_sample_id:
                    request['sample_id'] = actual_sample_id
            
            # 通知LAS服务器完成处理
            self.las_server.on_manual_operation_complete(request)
            
            # 重置UI
            self.prompt_canvas.delete("all")
            self.prompt_text.configure(text="等待样本处理请求...", foreground="black")
            self.sample_id_label.pack_forget()  # 隐藏输入框标签
            self.sample_id_entry.pack_forget()   # 隐藏输入框
            self.complete_button.configure(state=tk.DISABLED)
            delattr(self, 'current_request')
            if hasattr(self, 'circle_color'):
                delattr(self, 'circle_color')
                delattr(self, 'circle_outline')
                delattr(self, 'text_color')
            
            # 检查是否有其他等待的请求需要显示
            self._check_and_show_pending_requests()
    
    def _check_and_show_pending_requests(self):
        """检查并显示等待中的请求"""
        if not self.las_server:
            return
        
        # 检查IP0和IP1是否有等待的请求
        for ip in [0, 1]:
            pending_list = self.las_server.pending_requests.get(ip, [])
            for request in pending_list[:]:
                if request.get('waiting_for_ui'):
                    # 找到等待UI的请求，尝试显示
                    body = request['body']
                    
                    # 解析body获取请求信息
                    offset = 0
                    interface_position_index = body[offset]
                    offset += 1
                    
                    carrier_occupancy = body[offset]
                    offset += 1
                    
                    sample_id_len = body[offset]
                    offset += 1
                    
                    sample_id = ''
                    if sample_id_len > 0:
                        sample_id = body[offset:offset+sample_id_len].decode('ascii')
                        offset += sample_id_len
                    
                    request_type = 'load' if interface_position_index == 0x00 else 'unload'
                    
                    # 尝试显示提示
                    if self._show_manual_prompt(request_type, interface_position_index, sample_id):
                        # 成功显示，移除waiting_for_ui标记
                        request.pop('waiting_for_ui', None)
                        self.logger.info(f"Now showing pending {request_type} request for IP{interface_position_index}")
                        return  # 只显示一个请求
    
    def _show_onboard_samples(self):
        """显示在机标本列表"""
        # 创建弹窗窗口
        onboard_window = tk.Toplevel(self.root)
        onboard_window.title("在机标本列表")
        onboard_window.geometry("800x400")
        onboard_window.transient(self.root)
        # 注意：不调用grab_set()，避免与手动操作提示的grab_set冲突
        
        # 创建主框架
        main_frame = ttk.Frame(onboard_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 获取在机标本列表
        samples = self.core.get_all_samples()
        onboard_samples = [sample for sample_id, sample in samples.items() 
                          if sample['status'] not in ['unloaded', 'ejected']]
        
        # 创建树视图
        columns = ('sample_id', 'status', 'load_time')
        tree = ttk.Treeview(main_frame, columns=columns, show='headings', selectmode='browse')
        tree.heading('sample_id', text='样本ID')
        tree.heading('status', text='状态')
        tree.heading('load_time', text='装载时间')
        tree.column('sample_id', width=200)
        tree.column('status', width=150)
        tree.column('load_time', width=200)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # 填充数据
        for sample in onboard_samples:
            load_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(sample['load_time']))
            tree.insert('', tk.END, iid=sample['sample_id'], 
                      values=(sample['sample_id'], sample['status'], load_time))
        
        # 布局
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame, padding="10")
        button_frame.pack(fill=tk.X, pady=10)
        
        # 手工弹出按钮
        def on_eject_sample():
            selection = tree.selection()
            if selection:
                # 直接使用 selection[0] 作为 sample_id (即 iid)
                sample_id = selection[0]
                
                # 执行手工弹出
                self._manual_eject_sample(sample_id)
                
                # 刷新样本列表，不关闭弹窗
                # 重新获取样本数据（使用与初始化相同的逻辑）
                samples = self.core.get_all_samples()
                onboard_samples = [sample for sample_id, sample in samples.items() 
                                  if sample['status'] not in ['unloaded', 'ejected']]
                # 清空树
                for item in tree.get_children():
                    tree.delete(item)
                # 重新添加样本
                for sample in onboard_samples:
                    load_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(sample['load_time']))
                    tree.insert('', tk.END, iid=sample['sample_id'], 
                              values=(sample['sample_id'], sample['status'], load_time))
        
        eject_button = ttk.Button(button_frame, text="手工弹出", command=on_eject_sample, state=tk.NORMAL if onboard_samples else tk.DISABLED)
        eject_button.pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="关闭", command=onboard_window.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _manual_eject_sample(self, sample_id):
        """手工弹出样本
        
        Args:
            sample_id: 要弹出的样本ID
        """
        self.logger.info(f"手动弹出样本: {sample_id}")
        
        # 调用LAS服务器的手工弹出方法，该方法会：
        # 1. 更新核心样本状态
        # 2. 发送LOAD_UNLOAD_RESPONSE消息到LAS客户端
        success = self.las_server.manual_eject_sample(sample_id)
        
        if success:
            self.logger.info(f"样本 {sample_id} 已手动弹出，已通知LAS服务器")
            self.logger.log_las(f"Manual ejection: Sample {sample_id} ejected, LAS notified")
        else:
            self.logger.error(f"手动弹出样本 {sample_id} 失败")
            self.logger.log_las(f"Manual ejection failed: Sample {sample_id}")
        
        # 更新UI状态
        self._update_status()
        
    def _quit(self):
        """退出应用"""
        self.running = False
        
        # 停止服务器和客户端
        self.las_server.stop()
        self.lis_client.stop()
        
        # 关闭窗口
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """运行UI主循环"""
        try:
            self.root.mainloop()
        finally:
            self.running = False
