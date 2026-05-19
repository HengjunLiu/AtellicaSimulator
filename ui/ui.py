#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI模块 - 图形用户界面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import struct

from .lisui import LisUI

APP_VERSION = "v1.8.0"

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
        
        # 顶部容器框架（设备状态 + 按钮）
        top_container = ttk.Frame(main_frame)
        top_container.pack(fill=tk.X, pady=3)
        
        # 状态框架（不自动扩展，保持固定宽度）
        status_frame = ttk.LabelFrame(top_container, text="设备状态", padding="3")
        status_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        
        # 状态指标网格
        status_grid = ttk.Frame(status_frame)
        status_grid.pack(fill=tk.X)
        
        # 自动化接口状态
        ttk.Label(status_grid, text="自动化接口状态:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.automation_status_var = tk.StringVar()
        self.automation_status_label = ttk.Label(status_grid, textvariable=self.automation_status_var, width=12)
        self.automation_status_label.grid(row=0, column=1, padx=5, pady=2)
        
        # 仪器处理状态
        ttk.Label(status_grid, text="仪器处理状态:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.instrument_status_var = tk.StringVar()
        self.instrument_status_label = ttk.Label(status_grid, textvariable=self.instrument_status_var, width=12)
        self.instrument_status_label.grid(row=0, column=3, padx=5, pady=2)
        
        # LIS连接状态
        ttk.Label(status_grid, text="LIS连接状态:").grid(row=0, column=4, sticky=tk.W, padx=5, pady=2)
        self.lis_status_var = tk.StringVar()
        self.lis_status_label = ttk.Label(status_grid, textvariable=self.lis_status_var, width=12)
        self.lis_status_label.grid(row=0, column=5, padx=5, pady=2)
        
        # 接口位置信息
        ttk.Label(status_grid, text="接口位置数量:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.interface_count_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.interface_count_var, width=12).grid(row=1, column=1, padx=5, pady=2)
        
        # 脱线试管数量
        ttk.Label(status_grid, text="脱线试管数量:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.onboard_tubes_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.onboard_tubes_var, width=12).grid(row=1, column=3, padx=5, pady=2)
        
        # 已完成试管数量
        ttk.Label(status_grid, text="已完成试管数量:").grid(row=1, column=4, sticky=tk.W, padx=5, pady=2)
        self.completed_tubes_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.completed_tubes_var, width=12).grid(row=1, column=5, padx=5, pady=2)
        
        # 队列状态（新增）
        ttk.Label(status_grid, text="可返回样本数:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.return_ready_count_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.return_ready_count_var, width=12).grid(row=2, column=1, padx=5, pady=2)
        
        ttk.Label(status_grid, text="IP0队列长度:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        self.ip0_queue_len_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.ip0_queue_len_var, width=12).grid(row=2, column=3, padx=5, pady=2)
        
        ttk.Label(status_grid, text="IP1队列长度:").grid(row=2, column=4, sticky=tk.W, padx=5, pady=2)
        self.ip1_queue_len_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.ip1_queue_len_var, width=12).grid(row=2, column=5, padx=5, pady=2)
        
        ttk.Label(status_grid, text="IP0锁定状态:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.ip0_locked_var = tk.StringVar()
        self.ip0_locked_label = ttk.Label(status_grid, textvariable=self.ip0_locked_var, width=12)
        self.ip0_locked_label.grid(row=3, column=1, padx=5, pady=2)
        
        ttk.Label(status_grid, text="IP1锁定状态:").grid(row=3, column=2, sticky=tk.W, padx=5, pady=2)
        self.ip1_locked_var = tk.StringVar()
        self.ip1_locked_label = ttk.Label(status_grid, textvariable=self.ip1_locked_var, width=12)
        self.ip1_locked_label.grid(row=3, column=3, padx=5, pady=2)
        
        # 命令状态显示
        ttk.Label(status_grid, text="IP0命令状态:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        self.load_command_status_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.load_command_status_var, width=12).grid(row=4, column=1, padx=5, pady=2)
        
        ttk.Label(status_grid, text="IP1命令状态:").grid(row=4, column=2, sticky=tk.W, padx=5, pady=2)
        self.unload_command_status_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.unload_command_status_var, width=15).grid(row=4, column=3, padx=5, pady=2)
        
        # 中间内容框架（分为左侧参数配置、中间手动处理和右侧状态显示）
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.X, pady=5)
        
        # 左侧：参数配置
        config_frame = ttk.LabelFrame(content_frame, text="参数配置", padding="10")
        config_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 配置选项卡
        config_notebook = ttk.Notebook(config_frame)
        config_notebook.pack(fill=tk.BOTH, expand=True)
        
        # 设备状态配置
        device_config_frame = ttk.Frame(config_notebook, padding="10")
        config_notebook.add(device_config_frame, text="设备状态")
        
        # IP0抓取场景配置
        scenario_config_frame = ttk.Frame(config_notebook, padding="10")
        config_notebook.add(scenario_config_frame, text="IP0抓取场景")
        
        # ===== IP0 LOAD反馈状态码场景按钮区域 =====
        ip0_load_scenario_frame = ttk.LabelFrame(scenario_config_frame, text="LOAD反馈状态码场景", padding="10")
        ip0_load_scenario_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 场景按钮说明标签
        ttk.Label(ip0_load_scenario_frame, text="点击下方场景按钮将设置相应的Load Response状态码并发送到LAS", 
                 foreground="gray", font=("Arial", 9)).pack(anchor=tk.W, pady=(0, 10))
        
        # 创建4行2列的场景按钮布局
        scenario_buttons_frame = ttk.Frame(ip0_load_scenario_frame)
        scenario_buttons_frame.pack(fill=tk.X)
        
        # 场景1-4（第一列）
        ttk.Button(scenario_buttons_frame, text="LOAD场景1：Success (0x01) - 加载成功", 
                  command=lambda: self._trigger_ip0_load_scenario(1), width=38).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(scenario_buttons_frame, text="LOAD场景2：Lock Carrier (0x02) - 锁定载体", 
                  command=lambda: self._trigger_ip0_load_scenario(2), width=38).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(scenario_buttons_frame, text="LOAD场景3：OK to Unlock (0x03) - 可解锁载体", 
                  command=lambda: self._trigger_ip0_load_scenario(3), width=38).grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(scenario_buttons_frame, text="LOAD场景4：Queue Flush (0x04) - 队列刷新", 
                  command=lambda: self._trigger_ip0_load_scenario(4), width=38).grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        
        # 场景5-8（第二列）
        ttk.Button(scenario_buttons_frame, text="LOAD场景5：Interface Offline (0x05)",
                  command=lambda: self._trigger_ip0_load_scenario(5), width=38).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        self.load_scenario6_button = ttk.Button(scenario_buttons_frame, text="LOAD场景6：Mode Error (0x06) - 模式错误",
                  command=lambda: self._trigger_ip0_load_scenario(6), width=38, state=tk.DISABLED)
        self.load_scenario6_button.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(scenario_buttons_frame, text="LOAD场景7：Skipped Loading (0x07) - 跳过加载", 
                  command=lambda: self._trigger_ip0_load_scenario(7), width=38).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(scenario_buttons_frame, text="LOAD场景8：Unsupported ID (0x08) - 不支持的ID", 
                  command=lambda: self._trigger_ip0_load_scenario(8), width=38).grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 恢复确认按钮区域
        ip0_recovery_frame = ttk.LabelFrame(scenario_config_frame, text="场景恢复控制", padding="10")
        ip0_recovery_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(ip0_recovery_frame, text="点击恢复按钮将清除当前场景状态并恢复到正常运行状态", 
                 foreground="gray", font=("Arial", 9)).pack(anchor=tk.W, pady=(0, 10))
        
        recovery_buttons_frame = ttk.Frame(ip0_recovery_frame)
        recovery_buttons_frame.pack(fill=tk.X)
        
        # 恢复按钮（简化为1个全局恢复按钮）
        ttk.Button(recovery_buttons_frame, text="恢复所有状态（全局恢复）", 
                  command=self._trigger_scenario_8, width=38).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        # 当前场景状态显示
        self.ip0_scenario_status_var = tk.StringVar()
        self.ip0_scenario_status_var.set("当前场景：无")
        ttk.Label(ip0_recovery_frame, textvariable=self.ip0_scenario_status_var, 
                 font=("Arial", 10, "bold"), foreground="blue").pack(anchor=tk.W, pady=(10, 0))

        # IP1卸载场景配置
        ip1_scenario_config_frame = ttk.Frame(config_notebook, padding="10")
        config_notebook.add(ip1_scenario_config_frame, text="IP1卸载场景")

        # ===== IP1 UNLOAD反馈状态码场景按钮区域 =====
        ip1_unload_scenario_frame = ttk.LabelFrame(ip1_scenario_config_frame, text="UNLOAD反馈状态码场景", padding="10")
        ip1_unload_scenario_frame.pack(fill=tk.X, pady=(0, 10))

        # 场景按钮说明标签
        ttk.Label(ip1_unload_scenario_frame, text="点击下方场景按钮将设置相应的Unload Response状态码并发送到LAS",
                 foreground="gray", font=("Arial", 9)).pack(anchor=tk.W, pady=(0, 10))

        # 创建4行2列的场景按钮布局
        ip1_scenario_buttons_frame = ttk.Frame(ip1_unload_scenario_frame)
        ip1_scenario_buttons_frame.pack(fill=tk.X)

        # 场景17-20（第一列）
        ttk.Button(ip1_scenario_buttons_frame, text="UNLOAD场景1：Success (0x01) - 卸载成功",
                  command=lambda: self._trigger_ip1_unload_scenario(1), width=38).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        ttk.Button(ip1_scenario_buttons_frame, text="UNLOAD场景2：Lock Carrier (0x02) - 锁定载体",
                  command=lambda: self._trigger_ip1_unload_scenario(2), width=38).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        ttk.Button(ip1_scenario_buttons_frame, text="UNLOAD场景3：OK to Unlock (0x03) - 可解锁载体",
                  command=lambda: self._trigger_ip1_unload_scenario(3), width=38).grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)

        ttk.Button(ip1_scenario_buttons_frame, text="UNLOAD场景4：Queue Flush (0x04) - 队列刷新",
                  command=lambda: self._trigger_ip1_unload_scenario(4), width=38).grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)

        # 场景5-8（第二列）
        ttk.Button(ip1_scenario_buttons_frame, text="UNLOAD场景5：Interface Offline (0x05)",
                  command=lambda: self._trigger_ip1_unload_scenario(5), width=38).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        self.unload_scenario6_button = ttk.Button(ip1_scenario_buttons_frame, text="UNLOAD场景6：Mode Error (0x06) - 模式错误",
                  command=lambda: self._trigger_ip1_unload_scenario(6), width=38, state=tk.DISABLED)
        self.unload_scenario6_button.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Button(ip1_scenario_buttons_frame, text="UNLOAD场景7：Skipped Unloading (0x07) - 跳过卸载",
                  command=lambda: self._trigger_ip1_unload_scenario(7), width=38).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Button(ip1_scenario_buttons_frame, text="UNLOAD场景8：Release Next (0x08) - 释放下一个",
                  command=lambda: self._trigger_ip1_unload_scenario(8), width=38).grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

        # 恢复确认按钮区域
        ip1_recovery_frame = ttk.LabelFrame(ip1_scenario_config_frame, text="场景恢复控制", padding="10")
        ip1_recovery_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(ip1_recovery_frame, text="点击恢复按钮将清除当前场景状态并恢复到正常运行状态",
                 foreground="gray", font=("Arial", 9)).pack(anchor=tk.W, pady=(0, 10))

        ip1_recovery_buttons_frame = ttk.Frame(ip1_recovery_frame)
        ip1_recovery_buttons_frame.pack(fill=tk.X)

        # 恢复按钮
        ttk.Button(ip1_recovery_buttons_frame, text="恢复所有状态（全局恢复）",
                  command=self._trigger_scenario_ip1_24, width=38).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        # 当前场景状态显示
        self.ip1_scenario_status_var = tk.StringVar()
        self.ip1_scenario_status_var.set("当前场景：无")
        ttk.Label(ip1_recovery_frame, textvariable=self.ip1_scenario_status_var,
                 font=("Arial", 10, "bold"), foreground="blue").pack(anchor=tk.W, pady=(10, 0))

        # 队列实时显示页签
        queue_display_frame = ttk.Frame(config_notebook, padding="10")
        config_notebook.add(queue_display_frame, text="队列显示")

        # ===== IP0队列显示区域 =====
        ip0_queue_frame = ttk.LabelFrame(queue_display_frame, text="IP0 队列", padding="10")
        ip0_queue_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # IP0队列信息标签
        ip0_info_frame = ttk.Frame(ip0_queue_frame)
        ip0_info_frame.pack(fill=tk.X, pady=(0, 5))
        self.ip0_queue_count_label = ttk.Label(ip0_info_frame, text="队列数量: 0", font=("Arial", 10, "bold"))
        self.ip0_queue_count_label.pack(side=tk.LEFT, padx=5)
        self.ip0_queue_ready_label = ttk.Label(ip0_info_frame, text="就绪状态: 否", font=("Arial", 10))
        self.ip0_queue_ready_label.pack(side=tk.LEFT, padx=20)
        self.ip0_queue_locked_label = ttk.Label(ip0_info_frame, text="锁定Carrier: 无", font=("Arial", 10))
        self.ip0_queue_locked_label.pack(side=tk.LEFT, padx=20)

        # IP0队列Treeview
        ip0_tree_frame = ttk.Frame(ip0_queue_frame)
        ip0_tree_frame.pack(fill=tk.BOTH, expand=True)

        self.ip0_queue_tree = ttk.Treeview(ip0_tree_frame, columns=("index", "sample_id", "occupancy", "priority", "tube_info"), show="headings", height=6)
        self.ip0_queue_tree.heading("index", text="序号")
        self.ip0_queue_tree.heading("sample_id", text="样本ID")
        self.ip0_queue_tree.heading("occupancy", text="Carrier类型")
        self.ip0_queue_tree.heading("priority", text="优先级")
        self.ip0_queue_tree.heading("tube_info", text="试管信息")
        self.ip0_queue_tree.column("index", width=50, anchor="center")
        self.ip0_queue_tree.column("sample_id", width=120, anchor="center")
        self.ip0_queue_tree.column("occupancy", width=100, anchor="center")
        self.ip0_queue_tree.column("priority", width=80, anchor="center")
        self.ip0_queue_tree.column("tube_info", width=150, anchor="center")
        self.ip0_queue_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ip0_scrollbar = ttk.Scrollbar(ip0_tree_frame, orient="vertical", command=self.ip0_queue_tree.yview)
        ip0_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.ip0_queue_tree.configure(yscrollcommand=ip0_scrollbar.set)

        # ===== IP1队列显示区域 =====
        ip1_queue_frame = ttk.LabelFrame(queue_display_frame, text="IP1 队列", padding="10")
        ip1_queue_frame.pack(fill=tk.BOTH, expand=True)

        # IP1队列信息标签
        ip1_info_frame = ttk.Frame(ip1_queue_frame)
        ip1_info_frame.pack(fill=tk.X, pady=(0, 5))
        self.ip1_queue_count_label = ttk.Label(ip1_info_frame, text="队列数量: 0", font=("Arial", 10, "bold"))
        self.ip1_queue_count_label.pack(side=tk.LEFT, padx=5)
        self.ip1_queue_ready_label = ttk.Label(ip1_info_frame, text="就绪状态: 否", font=("Arial", 10))
        self.ip1_queue_ready_label.pack(side=tk.LEFT, padx=20)
        self.ip1_queue_locked_label = ttk.Label(ip1_info_frame, text="锁定Carrier: 无", font=("Arial", 10))
        self.ip1_queue_locked_label.pack(side=tk.LEFT, padx=20)

        # IP1队列Treeview
        ip1_tree_frame = ttk.Frame(ip1_queue_frame)
        ip1_tree_frame.pack(fill=tk.BOTH, expand=True)

        self.ip1_queue_tree = ttk.Treeview(ip1_tree_frame, columns=("index", "sample_id", "occupancy", "priority", "tube_info"), show="headings", height=6)
        self.ip1_queue_tree.heading("index", text="序号")
        self.ip1_queue_tree.heading("sample_id", text="样本ID")
        self.ip1_queue_tree.heading("occupancy", text="Carrier类型")
        self.ip1_queue_tree.heading("priority", text="优先级")
        self.ip1_queue_tree.heading("tube_info", text="试管信息")
        self.ip1_queue_tree.column("index", width=50, anchor="center")
        self.ip1_queue_tree.column("sample_id", width=120, anchor="center")
        self.ip1_queue_tree.column("occupancy", width=100, anchor="center")
        self.ip1_queue_tree.column("priority", width=80, anchor="center")
        self.ip1_queue_tree.column("tube_info", width=150, anchor="center")
        self.ip1_queue_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ip1_scrollbar = ttk.Scrollbar(ip1_tree_frame, orient="vertical", command=self.ip1_queue_tree.yview)
        ip1_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.ip1_queue_tree.configure(yscrollcommand=ip1_scrollbar.set)

        # 启动队列刷新定时器
        self._start_queue_refresh()

        """"

名称	                    来自哪里	            管什么	    核心含义	                LAS 最关心什么
Automation Interface Status	Instrument Health 里面	安全	    机械手是否挡在轨道上	    能不能动托盘
Automation Status（0x0003）	独立消息	             机械手好坏	    机械手是否故障 / 异常	    能不能收标本
====================
Interface Status = 轨道安全（挡不挡） 
Automation Status = 机械手好坏（坏没坏）
Analyzer Ready = 收样总开关（收不收）
====================

┌─────────────────────────────────────────────────────────────┐
│                      分析仪 整机                             │
└───────────────────────┬─────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
┌───────▼───────┐               ┌───────▼───────┐
│  机械/自动化部分 │               │  分析检测部分   │
└───────┬───────┘               └───────────────┘
        │
┌───────▼───────┐
│ 1. Automation Interface Status     │
│    （Instrument Health 里）         │
│    → 0x01 Green   = 不挡轨【安全】   │
│    → 0x04 Critical= 挡轨道【危险】   │
│    ✅ 只管：轨道能不能动托盘         │
└───────────────┘
        │
┌───────▼───────┐
│ 2. Automation Status (0x0003)       │
│    → 0x00 Normal = 机械手正常       │
│    → 0x02 Error  = 机械手故障       │
│    ✅ 只管：机械手本身好坏           │
└───────────────┘
        │
┌───────▼───────┐
│ 3. Analyzer Ready (0x0002) 【总开关】│
│    → 0x01 Ready   = 可以收样本       │
│    → 0x00 Not Ready= 禁止收样本      │
│    ✅ 只管：LAS 能不能往 IP0 送样     │
└───────────────┘
==============
┌─────────────────────────────────────────────────────────────────────┐
│                       【 正常运行状态 】                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ● Automation Interface Status = Green (0x01)                      │
│  ● Analyzer Ready = Ready (0x01)                                    │
│  ● 机械手缩回，不挡轨道                                              │
│  ● LAS 正常向 IP0 投递、移动托盘                                     │
│                                                                     │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       【 机械手发生异常 】                           │
│  （抓手卡阻、超时、位置错误、门打开、碰撞保护）                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. 机械手自动停止，保持当前位置                                    │
│  2. 若机械手停在轨道区域 → **挡轨风险**                             │
│                                                                     │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│               分析仪 → LAS 发送关键状态更新                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ① Instrument Health 推送：                                          │
│     → Automation Interface Status = Critical (0x04) 【危险·堵轨】   │
│                                                                     │
│  ② 发送 0x0003 Automation Status：                                  │
│     → Status = Error (0x02) 【机械手异常】                          │
│                                                                     │
│  ③ 发送 0x0002 Analyzer Ready：                                     │
│     → Ready = Not Ready (0x00) 【不可收样】                          │
│                                                                     │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       【 LAS 侧动作 】                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ● 收到 Critical → **立即停止移动 IP0/IP1 托盘**                    │
│  ● 收到 Not Ready → 暂停向 IP0 投递新标本                           │
│  ● 进入等待恢复状态                                                  │
│                                                                     │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  【 维修 / 复位 / 自动恢复 】                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ● 机械手复位成功                                                    │
│  ● 机械手回到安全位置（缩回，不挡轨道）                              │
│  ● 无挡轨风险                                                        │
│                                                                     │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│               分析仪 → LAS 发送【恢复通知】                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ① Instrument Health 推送：                                          │
│     → Automation Interface Status = Green (0x01) 【正常·可通轨】    │
│                                                                     │
│  ② 发送 0x0003 Automation Status：                                  │
│     → Status = Normal (0x00) 【机械手恢复】                         │
│                                                                     │
│  ③ 发送 0x0002 Analyzer Ready：                                     │
│     → Ready = Ready (0x01) 【可收样】                               │
│                                                                     │
└───────────────────────┬─────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       【 LAS 恢复运行 】                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ● Green + Ready 双条件满足                                          │
│  ● 恢复移动托盘                                                      │
│  ● 恢复向 IP0 投递标本                                               │
│  ● 回到【正常运行状态】                                             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
        """






        # 自动化接口健康状态配置（Instrument Health消息）   机械手是否堵在轨道上
        ttk.Label(device_config_frame, text="自动化接口健康状态:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.automation_status_combobox = ttk.Combobox(device_config_frame, values=["Green", "Red", "Critical"], width=15)
        self.automation_status_combobox.set("Green")
        self.automation_status_combobox.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(device_config_frame, text="应用", command=self._update_automation_status).grid(row=0, column=2, padx=5, pady=5)
        
        # 仪器处理状态配置                                 试剂耗材全不全 能不能做检测、出结果
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
        
        # 自动化接口状态配置（机械手异常恢复 - Automation Status Update消息）
        ttk.Label(device_config_frame, text="自动化接口恢复状态:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.automation_recovery_status_combobox = ttk.Combobox(device_config_frame, values=["Normal", "Busy", "Error"], width=15)
        self.automation_recovery_status_combobox.set("Normal")
        self.automation_recovery_status_combobox.grid(row=3, column=1, padx=5, pady=5)
        ttk.Button(device_config_frame, text="应用", command=self._update_automation_recovery_status).grid(row=3, column=2, padx=5, pady=5)
        
        # 分析仪就绪状态配置（机械手异常恢复 - Analyzer Ready Notification消息）    机械手能不能收标本
        ttk.Label(device_config_frame, text="分析仪就绪状态:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.analyzer_ready_combobox = ttk.Combobox(device_config_frame, values=["Ready", "Not Ready"], width=15)
        self.analyzer_ready_combobox.set("Ready")
        self.analyzer_ready_combobox.grid(row=4, column=1, padx=5, pady=5)
        ttk.Button(device_config_frame, text="应用", command=self._update_analyzer_ready_status).grid(row=4, column=2, padx=5, pady=5)
        
        # Load失败原因配置（用于Load Status = 1-8）
        ttk.Label(device_config_frame, text="Load失败原因:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        self.load_failure_reason_combobox = ttk.Combobox(device_config_frame, 
            values=["Success", "Lock Carrier", "OK to Unlock Carrier", "Queue Flush", "Queue Rebuild", "Skipped", "Release Next"], width=20)
        self.load_failure_reason_combobox.set("Success")
        self.load_failure_reason_combobox.grid(row=5, column=1, padx=5, pady=5)
        ttk.Button(device_config_frame, text="应用", command=self._update_load_failure_reason).grid(row=5, column=2, padx=5, pady=5)
        
        # 注意：0x0004 Sample Result 在 uRAP 协议中不存在
        # 样本结果通过 Load/Unload Response 中的 Sample Processing Status 传递
        # 已删除 Sample Result 配置控件
        
        # IP0远程控制状态配置
        ttk.Label(device_config_frame, text="IP0远程控制状态:").grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        self.ip0_remote_status_combobox = ttk.Combobox(device_config_frame, values=["Offline or Local", "Online Loading Only Mode"], width=25)
        self.ip0_remote_status_combobox.set("Offline or Local")
        self.ip0_remote_status_combobox.grid(row=6, column=1, padx=5, pady=5)
        ttk.Button(device_config_frame, text="应用", command=self._update_ip0_remote_status).grid(row=6, column=2, padx=5, pady=5)

        # IP1远程控制状态配置
        ttk.Label(device_config_frame, text="IP1远程控制状态:").grid(row=7, column=0, sticky=tk.W, padx=5, pady=5)
        self.ip1_remote_status_combobox = ttk.Combobox(device_config_frame, values=["Offline or Local", "Online Unloading Only Mode"], width=25)
        self.ip1_remote_status_combobox.set("Offline or Local")
        self.ip1_remote_status_combobox.grid(row=7, column=1, padx=5, pady=5)
        ttk.Button(device_config_frame, text="应用", command=self._update_ip1_remote_status).grid(row=7, column=2, padx=5, pady=5)
        
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
        logs_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 日志选项卡
        logs_notebook = ttk.Notebook(logs_frame)
        logs_notebook.pack(fill=tk.BOTH, expand=True)
        
        # LAS日志
        las_log_frame = ttk.Frame(logs_notebook, padding="10")
        logs_notebook.add(las_log_frame, text="LAS日志")
        self.las_log_text = scrolledtext.ScrolledText(las_log_frame, width=80, height=8, wrap=tk.WORD)
        self.las_log_text.pack(fill=tk.BOTH, expand=True)
        
        # 添加右键菜单
        las_log_menu = tk.Menu(self.root, tearoff=0)
        las_log_menu.add_command(label="复制", command=lambda: self._copy_las_log())
        las_log_menu.add_command(label="清空", command=lambda: self.las_log_text.delete(1.0, tk.END))
        self.las_log_text.bind("<Button-3>", lambda e: self.las_log_text.post(las_log_menu, x=e.x_root, y=e.y_root))
        
        # LIS日志
        lis_log_frame = ttk.Frame(logs_notebook, padding="10")
        logs_notebook.add(lis_log_frame, text="LIS日志")
        self.lis_log_text = scrolledtext.ScrolledText(lis_log_frame, width=80, height=8, wrap=tk.WORD)
        self.lis_log_text.pack(fill=tk.BOTH, expand=True)
        
        # 添加右键菜单
        lis_log_menu = tk.Menu(self.root, tearoff=0)
        lis_log_menu.add_command(label="复制", command=lambda: self._copy_lis_log())
        lis_log_menu.add_command(label="清空", command=lambda: self.lis_log_text.delete(1.0, tk.END))
        self.lis_log_text.bind("<Button-3>", lambda e: self.lis_log_text.post(lis_log_menu, x=e.x_root, y=e.y_root))
        
        # 右侧按钮区域（位于设备状态组框右侧）
        button_frame = ttk.Frame(top_container, padding="5")
        button_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0))
        
        # 添加按钮组（横向排列）
        ttk.Button(button_frame, text="刷新状态", command=self._update_status).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_frame, text="脱线标本", command=self._show_onboard_samples).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_frame, text="编辑库存", command=self._show_inventory_editor).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_frame, text="清空日志", command=self._clear_logs).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_frame, text="LIS模拟", command=self._open_lis_simulation).pack(side=tk.LEFT, padx=3)
        ttk.Button(button_frame, text="退出", command=self._quit).pack(side=tk.LEFT, padx=3)
    
    def _update_status_loop(self):
        """定期更新状态"""
        while self.running:
            try:
                self._update_status()
            except Exception as e:
                self.logger.error(f"Error in status update loop: {e}")
            time.sleep(2)  # 每2秒更新一次
    
    def _update_logs_loop(self):
        """定期更新日志"""
        while self.running:
            try:
                self._update_logs()
            except Exception as e:
                self.logger.error(f"Error in logs update loop: {e}")
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
                    # 更新IP0远程控制状态下拉框
                    if remote_status == 1:
                        self.ip0_remote_status_combobox.set("Offline or Local")
                    elif remote_status == 4:
                        self.ip0_remote_status_combobox.set("Online Loading Only Mode")
                else:  # IP1
                    if remote_status == 1:
                        remote_desc = "Offline or Local"
                    elif remote_status == 5:
                        remote_desc = "Online Unloading Only Mode"
                    else:
                        remote_desc = str(remote_status)
                    # 更新IP1远程控制状态下拉框
                    if remote_status == 1:
                        self.ip1_remote_status_combobox.set("Offline or Local")
                    elif remote_status == 5:
                        self.ip1_remote_status_combobox.set("Online Unloading Only Mode")
                
                # 锁所有权描述
                lock_desc = "Locked by Instrument" if lock_ownership == 1 else "Not Locked by Instrument"
                
                detail_text += f"IP{i} - 远程控制状态：{remote_desc}, 锁所有权：{lock_desc}\n"
            
            detail_text += f"处理积压：{health_status['processing_backlog']}\n"
            detail_text += f"样本获取延迟：{health_status['sample_acquisition_delay']}\n"
            detail_text += f"脱线试管数量：{health_status['on_board_tube_count']}\n"
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
            detail_text += f"\nIP0队列 (长度: {len(ip0_queue)}):\n"
            if ip0_queue:
                for i, item in enumerate(ip0_queue):
                    occupancy_map = {0: 'Empty', 1: 'Sample', 2: 'Sample', 3: 'Sample'}
                    occupancy = occupancy_map.get(item.get('carrier_occupancy', 0), 'Unknown')
                    detail_text += f"  [{i+1}] 样本ID: {item.get('sample_id', 'N/A')}, 占用类型: {occupancy}, "
                    detail_text += f"优先级: {item.get('sample_priority', 'N/A')}, 高度: {item.get('tube_height', 'N/A')}, 直径: {item.get('tube_diameter', 'N/A')}\n"
            else:
                detail_text += "  队列为空\n"
            detail_text += f"IP0锁定状态：{'Locked' if ip0_locked else 'Unlocked'}\n"
            
            # IP1队列详细信息
            detail_text += f"\nIP1队列 (长度: {len(ip1_queue)}):\n"
            if ip1_queue:
                for i, item in enumerate(ip1_queue):
                    occupancy_map = {0: 'Empty', 1: 'Sample', 2: 'Sample', 3: 'Sample'}
                    occupancy = occupancy_map.get(item.get('carrier_occupancy', 0), 'Unknown')
                    detail_text += f"  [{i+1}] 样本ID: {item.get('sample_id', 'N/A')}, 占用类型: {occupancy}, "
                    detail_text += f"优先级: {item.get('sample_priority', 'N/A')}, 高度: {item.get('tube_height', 'N/A')}, 直径: {item.get('tube_diameter', 'N/A')}\n"
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
        """LIS日志回调函数"""
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
            
            # 更新LIS日志（方案3：直接追加，不删除所有）
            lis_log_content = '\n'.join(self.lis_log_buffer) + '\n'
            self.lis_log_text.delete(1.0, tk.END)
            self.lis_log_text.insert(tk.END, lis_log_content)
            self.lis_log_text.see(tk.END)  # 滚动到最后
            
        except Exception as e:
            self.logger.error(f"Error updating UI logs: {str(e)}")
    
    def _copy_las_log(self):
        """复制LAS日志到剪贴板"""
        try:
            selected_text = self.las_log_text.get("sel.first", "sel.last")
            if selected_text:
                self.root.clipboard_clear()
                self.root.clipboard_append(selected_text)
                self.logger.info(f"Copied LAS log to clipboard: {selected_text[:50]}...")
        except Exception as e:
            self.logger.error(f"Error copying LAS log: {str(e)}")
    
    def _copy_lis_log(self):
        """复制LIS日志到剪贴板"""
        try:
            selected_text = self.lis_log_text.get("sel.first", "sel.last")
            if selected_text:
                self.root.clipboard_clear()
                self.root.clipboard_append(selected_text)
                self.logger.info(f"Copied LIS log to clipboard: {selected_text[:50]}...")
        except Exception as e:
            self.logger.error(f"Error copying LIS log: {str(e)}")
    
    def _update_automation_status(self, auto_send_health=True):
        """更新自动化接口状态
        
        Args:
            auto_send_health: 是否自动发送Instrument Health（默认True）
        """
        status = self.automation_status_combobox.get()
        if status == "Green":
            status_code = 1
        elif status == "Red":
            status_code = 3
        elif status == "Critical":
            status_code = 4
        self.core.update_automation_interface_status(status_code, auto_send_health=auto_send_health)
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
    
    def _update_automation_recovery_status(self):
        """更新自动化接口状态（机械手异常恢复）"""
        status = self.automation_recovery_status_combobox.get()
        if status == "Normal":
            status_code = 0x00
        elif status == "Busy":
            status_code = 0x01
        else:
            status_code = 0x02
        self.core.update_automation_status(status_code)
        self._update_status()
    
    def _update_analyzer_ready_status(self):
        """更新分析仪就绪状态（机械手异常恢复）"""
        status = self.analyzer_ready_combobox.get()
        status_code = 0x01 if status == "Ready" else 0x00
        self.core.update_analyzer_ready(status_code)
        self._update_status()
    
    def _update_load_failure_reason(self):
        """更新Load失败原因"""
        reason = self.load_failure_reason_combobox.get()
        reason_map = {
            "Success": 1,
            "Lock Carrier": 2,
            "OK to Unlock Carrier": 3,
            "Queue Flush": 4,
            "Queue Rebuild": 5,
            "Skipped": 7,
            "Release Next": 8
        }
        reason_code = reason_map.get(reason, 1)
        self.core.update_load_failure_reason(reason_code)
        self._update_status()
    
    # 注意：0x0004 Sample Result 在 uRAP 协议中不存在
    # _send_sample_result 方法已删除
    
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

    def _start_queue_refresh(self):
        """启动队列刷新定时器"""
        self._refresh_queue_display()
        # 每1秒刷新一次队列显示
        self.queue_refresh_job = self.root.after(1000, self._start_queue_refresh)

    def _refresh_queue_display(self):
        """刷新队列显示"""
        try:
            # 获取队列信息
            ip0_queue = self.core.queues.get(0, [])
            ip1_queue = self.core.queues.get(1, [])

            # 更新IP0队列显示
            self._update_ip0_queue_display(ip0_queue)

            # 更新IP1队列显示
            self._update_ip1_queue_display(ip1_queue)

        except Exception as e:
            # 避免刷新错误影响主程序，但记录错误日志
            self.logger.error(f"Error refreshing queue display: {e}")

    def _update_ip0_queue_display(self, queue):
        """更新IP0队列显示

        Args:
            queue: IP0队列数据
        """
        # 清空现有内容
        for item in self.ip0_queue_tree.get_children():
            self.ip0_queue_tree.delete(item)

        # 更新队列数量
        count = len(queue)
        self.ip0_queue_count_label.config(text=f"队列数量: {count}")

        # 更新就绪状态
        ready = self.core.ready_to_load.get(0, False)
        self.ip0_queue_ready_label.config(text=f"就绪状态: {'是' if ready else '否'}")

        # 更新锁定状态
        locked = self.core.locked_carriers.get(0)
        if locked:
            self.ip0_queue_locked_label.config(text=f"锁定Carrier: {locked.get('sample_id', '未知')}")
        else:
            self.ip0_queue_locked_label.config(text="锁定Carrier: 无")

        # 填充队列数据
        for idx, carrier in enumerate(queue):
            sample_id = carrier.get('sample_id', 'N/A')
            occupancy = carrier.get('carrier_occupancy', 'N/A')
            priority = carrier.get('sample_priority', 'N/A')
            tube_height = carrier.get('tube_height', 'N/A')
            tube_diameter = carrier.get('tube_diameter', 'N/A')
            tube_info = f"H:{tube_height}mm D:{tube_diameter}mm"

            self.ip0_queue_tree.insert("", tk.END, values=(
                idx + 1,
                sample_id,
                occupancy,
                priority,
                tube_info
            ))

    def _update_ip1_queue_display(self, queue):
        """更新IP1队列显示

        Args:
            queue: IP1队列数据
        """
        # 清空现有内容
        for item in self.ip1_queue_tree.get_children():
            self.ip1_queue_tree.delete(item)

        # 更新队列数量
        count = len(queue)
        self.ip1_queue_count_label.config(text=f"队列数量: {count}")

        # 更新就绪状态
        ready = self.core.ready_to_load.get(1, False)
        self.ip1_queue_ready_label.config(text=f"就绪状态: {'是' if ready else '否'}")

        # 更新锁定状态
        locked = self.core.locked_carriers.get(1)
        if locked:
            self.ip1_queue_locked_label.config(text=f"锁定Carrier: {locked.get('sample_id', '未知')}")
        else:
            self.ip1_queue_locked_label.config(text="锁定Carrier: 无")

        # 填充队列数据
        for idx, carrier in enumerate(queue):
            sample_id = carrier.get('sample_id', 'N/A')
            occupancy = carrier.get('carrier_occupancy', 'N/A')
            priority = carrier.get('sample_priority', 'N/A')
            tube_height = carrier.get('tube_height', 'N/A')
            tube_diameter = carrier.get('tube_diameter', 'N/A')
            tube_info = f"H:{tube_height}mm D:{tube_diameter}mm"

            self.ip1_queue_tree.insert("", tk.END, values=(
                idx + 1,
                sample_id,
                occupancy,
                priority,
                tube_info
            ))

    def _trigger_scenario_8(self):
        """场景8：恢复所有状态（类似程序初始化）"""
        self.logger.log_las("场景8：开始执行恢复所有状态（类似程序初始化）")
        
        # 重新初始化数据库，确保表结构正确
        self.logger.log_las("场景8：重新初始化数据库...")
        self.core.reinit_database()
        
        # 注意：不再清理样本数据，保持当前在机标本信息
        # 当LAS发送Onboard Sample Info Request时，ATS会正确返回当前在机标本列表
        self.logger.log_las("场景8：保持当前在机标本数据（不执行clear_all_samples）")
        
        self.automation_status_combobox.set("Green")
        self._update_automation_status()
        
        self.instrument_status_combobox.set("Green")
        self._update_instrument_status()
        
        self.automation_recovery_status_combobox.set("Normal")
        self._update_automation_recovery_status()
        
        self.analyzer_ready_combobox.set("Ready")
        self._update_analyzer_ready_status()
        
        self.load_failure_reason_combobox.set("Success")
        self._update_load_failure_reason()
        
        # 注意：IP0需要设置为Online Loading Only Mode（status=4），LAS才会发送Load请求
        # Offline or Local (status=1) 会阻止LAS发送Load请求
        self.ip0_remote_status_combobox.set("Online Loading Only Mode")
        self.core.update_remote_control_status(0, 4)  # 4 = Online Loading Only Mode
        
        # IP1设置为Online Unloading Only Mode（status=5），允许Unload操作
        self.ip1_remote_status_combobox.set("Online Unloading Only Mode")
        self.core.update_remote_control_status(1, 5)  # 5 = Online Unloading Only Mode
        
        # 注意：0x0304 Load Unload Response 不应该在场景8中发送
        # 0x0304是对特定Load/Unload请求的响应，应该在点击"完成"按钮时发送
        # 场景8的目的是恢复系统状态，让LAS能继续自动运行
        
        # 步骤1：清理pending_requests，释放卡住的请求
        self.logger.log_las("场景8：步骤1 - 清理pending_requests，释放卡住的请求")
        if hasattr(self.core.las_server, 'pending_requests'):
            for ip in [0, 1]:
                if self.core.las_server.pending_requests[ip]:
                    self.logger.log_las(f"场景8：清理IP{ip}的pending_requests，数量: {len(self.core.las_server.pending_requests[ip])}")
                    self.core.las_server.pending_requests[ip] = []
        
        # 步骤2：强制释放IP0和IP1锁定的carrier（本地清理）
        # 注意：不应该由ATS simulator主动发送Clear Queue Request到LAS
        # Clear Queue Request应该由LAS发送到ATS，ATS只负责响应
        # 本地清理队列即可，LAS收到恢复状态后会自行决定是否需要清空队列
        self.logger.log_las("场景8：步骤2 - 本地清理IP0和IP1队列")
        self.core.clear_queue(0, force=True)  # IP0
        self.core.clear_queue(1, force=True)  # IP1
        
        # 步骤3：恢复设备状态并通知LAS
        # 根据URAP协议，只有通信层故障才需要断开重连
        # 业务层错误（如Load Response状态码）只需恢复设备状态
        if hasattr(self.core, 'las_server') and self.core.las_server:
            self.logger.log_las("场景8：步骤3 - 发送状态恢复消息给LAS")
            try:
                import time
                
                # 发送Instrument Health Response（包含所有状态信息）
                try:
                    self.logger.log_las("场景8：发送Instrument Health Response（报Green）")
                    self.core.las_server.send_instrument_health_response()
                    time.sleep(0.3)
                    self.logger.log_las("场景8：LAS收到恢复消息后应继续自动运行")
                except Exception as e:
                    self.logger.error(f"场景8：发送Instrument Health失败: {str(e)}")
                
                # 注意：0x0002和0x0003消息类型在uRAP协议中不存在
                # 状态信息已通过Instrument Health Response (0x0202)传递
                
            except Exception as e:
                self.logger.error(f"场景8：发送恢复消息失败: {str(e)}")
                # 如果发送消息失败，说明可能是通信层故障，尝试断开重连
                self.logger.log_las("场景8：检测到可能的通信层故障，尝试断开连接触发LAS重连")
                try:
                    with self.core.las_server.connection_lock:
                        connections_to_close = list(self.core.las_server.connections)
                        self.core.las_server.connections.clear()
                    
                    for conn in connections_to_close:
                        try:
                            conn.close()
                        except:
                            pass
                    
                    # 重置初始化状态
                    self.core.las_server.initialized_requests = {
                        'clear_queue': set(),
                        'transfer_status': set(),
                        'instrument_health': False,
                        'test_inventory': False,
                        'onboard_sample_info': False,
                        'consumable_inventory': False
                    }
                    self.logger.log_las("场景8：已断开连接并重置初始化状态，LAS将重新发起初始化序列")
                except Exception as e2:
                    self.logger.error(f"场景8：断开连接失败: {str(e2)}")
        else:
            self.logger.log_las("场景8：警告 - LAS服务器未初始化")
        
        self.logger.log_las("场景8：已恢复所有状态到正常并释放锁定的carrier")
    
    def _trigger_scenario_8a(self):
        """场景8a：IP0紧急放行（解决FIFO死锁）
        
        协议原文解法：
        - IP0是Loading Only接口，严格FIFO
        - 第一个标本Load失败但没给放行码，导致死锁
        - 必须给第一个标本回复状态码7（Instrument Skipped Loading）
        - LAS收到7 = 直接放走第一个托盘
        - 第二个托盘自动前移，恢复正常
        
        绝对不能回：
        - 02（Lock Carrier）= 锁死
        - 06（Mode Error）= LAS不会放
        """
        self.logger.log_las("【场景8a】IP0紧急放行 - 解决FIFO死锁")
        self.logger.log_las("场景8a：协议要求 - 给第一个标本回状态码7，LAS放走托盘")
        
        # 步骤0：检查IP0队列状态
        # 注意：对于FIFO死锁，不应该发送Skip Queue/Clear Queue！
        # 因为托盘还在物理轨道上，只需要回复Load Response = 7，LAS就会放走托盘
        self.logger.log_las("场景8a：步骤0 - 检查IP0队列状态")
        ip0_queue = self.core.get_queue_info(0)
        if ip0_queue:
            self.logger.log_las(f"场景8a：IP0队列中有 {len(ip0_queue)} 个标本")
            self.logger.log_las("场景8a：【重要】不发送Skip Queue/Clear Queue，让LAS保持队列")
            self.logger.log_las("场景8a：【原理】托盘在物理轨道上，回复Load=7后LAS会自动放走")
        else:
            self.logger.log_las("场景8a：IP0队列为空")
        
        # 步骤1：设置Load失败原因为7（Instrument Skipped Loading）
        self.logger.log_las("场景8a：步骤1 - 设置Load Response = 7（Instrument Skipped Loading）")
        self.load_failure_reason_combobox.set("Instrument Skipped Loading")
        self._update_load_failure_reason()
        # 关键：直接设置load_command_status为7，确保下次Load返回0x07
        self.core.load_command_status = 7  # Instrument Skipped Loading
        self.logger.log_las("场景8a：已设置Load Command Status = 7 (Instrument Skipped Loading)")
        
        # 步骤2：确保IP0处于Online Loading Only Mode
        self.logger.log_las("场景8a：步骤2 - 确保IP0处于Online Loading Only Mode")
        self.ip0_remote_status_combobox.set("Online Loading Only Mode")
        self.core.update_remote_control_status(0, 4)
        
        # 步骤3：恢复其他状态为正常（让LAS知道仪器已就绪）
        self.logger.log_las("场景8a：步骤3 - 恢复其他状态为正常")
        self.automation_status_combobox.set("Green")
        self._update_automation_status()
        self.analyzer_ready_combobox.set("Ready")
        self._update_analyzer_ready_status()
        
        # 步骤4：清理pending_requests，确保新的Load请求能被处理
        self.logger.log_las("场景8a：步骤4 - 清理pending_requests")
        if hasattr(self.core.las_server, 'pending_requests'):
            for ip in [0, 1]:
                if self.core.las_server.pending_requests[ip]:
                    self.logger.log_las(f"场景8a：清理IP{ip}的pending_requests，数量: {len(self.core.las_server.pending_requests[ip])}")
                    self.core.las_server.pending_requests[ip] = []
        
        # 步骤5：强制释放IP0锁定的carrier（本地清理）
        self.logger.log_las("场景8a：步骤5 - 强制释放IP0锁定的carrier")
        self.core.clear_queue(0, force=True)
        
        # 步骤6：发送Instrument Health Response（报Green）
        self.logger.log_las("场景8a：步骤6 - 发送Instrument Health Response")
        if hasattr(self.core, 'las_server') and self.core.las_server:
            try:
                self.core.las_server.send_instrument_health_response()
                self.logger.log_las("场景8a：已发送Instrument Health Response")
            except Exception as e:
                self.logger.error(f"场景8a：发送Instrument Health失败: {str(e)}")
        
        self.logger.log_las("场景8a：完成！LAS应该：")
        self.logger.log_las("  1. 收到Skip Queue，从LAS队列中删除IP0标本")
        self.logger.log_las("  2. 收到Clear Queue，清空IP0队列")
        self.logger.log_las("  3. 收到Load Response = 7，放走托盘")
        self.logger.log_las("  4. 恢复正常流程")
    
    def _trigger_ip0_load_scenario(self, scenario_num):
        """IP0 LOAD反馈状态码场景触发器（场景1-8）
        
        Args:
            scenario_num: 场景编号（1-8）
        """
        scenario_config = {
            1: {
                'name': 'LOAD场景1：Success (0x01)',
                'desc': '加载成功',
                'load_response': 0x01,
                'automation_interface': 'Green',
                'automation_status': 'Normal',
                'analyzer_ready': 'Ready',
                'instrument_status': 'Green'
            },
            2: {
                'name': 'LOAD场景2：Lock Carrier (0x02)',
                'desc': '锁定载体',
                'load_response': 0x02,
                'automation_interface': 'Critical' ,
                'automation_status': 'Normal',
                'analyzer_ready': 'Ready',
                'instrument_status': 'Green'
            },
            3: {
                'name': 'LOAD场景3：OK to Unlock (0x03)',
                'desc': '可解锁载体',
                'load_response': 0x03,
                'automation_interface': 'Red',#1，3，4
                'automation_status': 'Error',
                'analyzer_ready': 'Not Ready',
                'instrument_status': 'Red'
            },
            4: {
                'name': 'LOAD场景4：Queue Flush (0x04)',#软件 错误
                'desc': '队列刷新',
                'load_response': 0x04,
                'automation_interface': 'Green',
                'automation_status': 'Normal',
                'analyzer_ready': 'Ready', 
                'instrument_status': 'Green'
            },
            5: {
                'name': 'LOAD场景5：机械手下线 (0x05)',
                'desc': '机械手下线',
                'load_response': 0x05,
                'automation_interface': 'Green',
                'automation_status': 'Normal',
                'analyzer_ready': 'Ready', #'Not Ready'
                'instrument_status': 'Green'
            },
            6: {
                'name': 'LOAD场景6：Mode Error (0x06)',#不存在
                'desc': '模式错误',
                'load_response': 0x06,
                'automation_interface': 'Critical',
                'automation_status': 'Error',
                'analyzer_ready': 'Not Ready',
                'instrument_status': 'Red'
            },
            7: {
                'name': 'LOAD场景7：Skipped Loading (0x07)', #软件
                'desc': '跳过加载',
                'load_response': 0x07,
                'automation_interface': 'Green',
                'automation_status': 'Normal',
                'analyzer_ready': 'Ready',
                'instrument_status': 'Green'
            },
            8: {
                'name': 'LOAD场景8：Unsupported ID (0x08)',
                'desc': '不支持的ID',
                'load_response': 0x08,
                'automation_interface': 'Green',
                'automation_status': 'Normal',
                'analyzer_ready': 'Ready',
                'instrument_status': 'Green'
            }
        }
        
        config = scenario_config.get(scenario_num)
        if not config:
            self.logger.error(f"未知的场景编号: {scenario_num}")
            return
        
        self.logger.info(f"【按钮点击】{config['name']} - 用户触发了此场景")
        self.logger.log_las(f"{config['name']}：开始执行IP0 LOAD场景（{config['desc']}）")
        
        # 记录当前场景
        scenario_key = f'ip0_load_{scenario_num}'
        self.core.active_scenario = scenario_key
        self.core.active_scenario_data = {
            'scenario_num': scenario_num,
            'load_response': config['load_response'],
            'description': config['desc']
        }
        
        # 更新场景状态显示
        self.ip0_scenario_status_var.set(f"当前场景：{config['name']} - {config['desc']}")
        
        import threading
        
        def run_scenario():
            self.logger.log_las(f"{config['name']}：步骤1 - 设置设备状态参数")
            

            # 设置自动化接口状态（机械手状态）
            if config['automation_status'] == 'Normal':
                self.automation_recovery_status_combobox.set("Normal")
                self._update_automation_recovery_status()
            elif config['automation_status'] == 'Error':
                self.automation_recovery_status_combobox.set("Error")
                self._update_automation_recovery_status()
            self.logger.log_las(f"{config['name']}：设置Automation Status = {config['automation_status']}")
            
            # 设置分析仪就绪状态
            self.analyzer_ready_combobox.set(config['analyzer_ready'])
            self._update_analyzer_ready_status()
            self.logger.log_las(f"{config['name']}：设置Analyzer Ready = {config['analyzer_ready']}")
            
            # 设置仪器处理状态
            self.instrument_status_combobox.set(config['instrument_status'])
            self._update_instrument_status()
            self.logger.log_las(f"{config['name']}：设置Instrument Status = {config['instrument_status']}")
            
            # 设置自动化接口健康状态（不自动发送，稍后统一发送）
            self.automation_status_combobox.set(config['automation_interface'])
            self._update_automation_status(auto_send_health=False)
            self.logger.log_las(f"{config['name']}：设置Automation Interface Status = {config['automation_interface']}")
            

            # 设置Load Response状态码
            self.logger.log_las(f"{config['name']}：步骤2 - 设置Load Response = 0x{config['load_response']:02X}")
            self.core.load_command_status = config['load_response']
            
            # 更新Load失败原因下拉框（如果有对应项）
            response_map = {
                0x01: "Success",
                0x02: "Lock Carrier",
                0x03: "OK to Unlock Carrier",
                0x04: "Queue Flush",
                0x05: "Queue Rebuild",
                0x06: "Mode Error",
                0x07: "Skipped",
                0x08: "Release Next"
            }
            reason_text = response_map.get(config['load_response'], "Success")
            self.load_failure_reason_combobox.set(reason_text)
            self._update_load_failure_reason()
            
            self.logger.log_las(f"{config['name']}：已设置Load Command Status = 0x{config['load_response']:02X}")
            
            # 发送相关消息给LAS
            if hasattr(self.core, 'las_server') and self.core.las_server:
                self.logger.log_las(f"{config['name']}：步骤3 - 发送状态消息给LAS")
                
                import time
                
                # 发送Instrument Health Response（包含所有状态信息）
                try:
                    self.core.las_server.send_instrument_health_response()
                    self.logger.log_las(f"{config['name']}：已发送Instrument Health Response")
                    time.sleep(0.2)
                except Exception as e:
                    self.logger.error(f"{config['name']}：发送Instrument Health失败: {str(e)}")
                
                # 注意：0x0002和0x0003消息类型在uRAP协议中不存在
                # 状态信息已通过Instrument Health Response (0x0202)传递
            
            self.logger.log_las(f"{config['name']}：场景执行完成")
            self.logger.log_las(f"{config['name']}：LAS收到Load Response = 0x{config['load_response']:02X}后将执行相应操作")
            
            # 检查是否有正在处理的手动标本处理请求
            if hasattr(self, 'current_request') and self.current_request:
                self.logger.log_las(f"{config['name']}：检测到正在处理的手动标本处理请求，自动触发完成按钮")
                self._on_complete_button_click()
            else:
                # 检查LAS是否有pending的Load Request等待处理
                if hasattr(self.core, 'las_server') and self.core.las_server:
                    las_server = self.core.las_server
                    pending_count = len(las_server.pending_requests.get(0, []))
                    if pending_count > 0:
                        self.logger.log_las(f"{config['name']}：检测到{pending_count}个pending的Load Request，立即处理")
                        # 获取第一个pending请求
                        pending_req = las_server.pending_requests[0][0]
                        # 设置为当前请求
                        self.current_request = {
                            'type': 'load',
                            'interface_position': 0,
                            'sample_id': pending_req.get('sample_id', ''),
                            'conn': pending_req['conn'],
                            'header': pending_req['header'],
                            'body': pending_req['body']
                        }
                        # 触发完成按钮
                        self._on_complete_button_click()
                        self.logger.log_las(f"{config['name']}：已自动发送Load Response")
                    else:
                        self.logger.log_las(f"{config['name']}：当前没有pending的Load Request")
                        self.logger.log_las(f"{config['name']}：等待LAS发送Load Request后将返回 0x{config['load_response']:02X}")
        
        # 在后台线程中执行，避免阻塞UI
        thread = threading.Thread(target=run_scenario, daemon=True)
        thread.start()
    
    def _trigger_scenario_9(self, caught=True):
        """场景9：IP0卡轨故障（机械手撞击/卡住在LAS侧）
        
        Args:
            caught: True=抓到了标本, False=没抓到标本
        """
        scenario_name = "场景9a" if caught else "场景9b"
        sample_result_desc = "标本已取走(0x00)" if caught else "标本还在(0x01)"
        sample_result_code = 0x00 if caught else 0x01
        
        self.logger.info(f"【按钮点击】{scenario_name} - 用户触发了此场景")
        self.logger.log_las(f"{scenario_name}：开始执行IP0卡轨故障场景（{sample_result_desc}）")
        
        # 记录当前场景
        scenario_key = '9a' if caught else '9b'
        self.core.active_scenario = scenario_key
        self.core.active_scenario_data = {
            'caught': caught,
            'sample_result_code': sample_result_code,
            'sample_result_desc': sample_result_desc
        }
        self.logger.log_las(f"{scenario_name}：已记录当前场景为 {scenario_key}，用于后续自动适配")
        
        import threading
        
        def run_scenario_9():
            self.logger.log_las(f"{scenario_name}：步骤1 - 设置Load失败（Lock Carrier in place）")
            # 设置Load失败原因
            self.load_failure_reason_combobox.set("Lock Carrier")
            self._update_load_failure_reason()
            
            self.logger.log_las(f"{scenario_name}：步骤2 - 设置机械手异常（Automation Status = Error）")
            # 设置机械手异常
            self.automation_recovery_status_combobox.set("Error")
            self._update_automation_recovery_status()
            
            self.logger.log_las(f"{scenario_name}：步骤3 - 设置分析仪不就绪（Analyzer Ready = Not Ready）")
            # 设置分析仪不就绪
            self.analyzer_ready_combobox.set("Not Ready")
            self._update_analyzer_ready_status()
            
            self.logger.log_las(f"{scenario_name}：步骤4 - 设置自动化接口状态为Critical（挡轨危险）")
            # 设置自动化接口状态为Critical
            self.automation_status_combobox.set("Critical")
            self._update_automation_status()
            
            self.logger.log_las(f"{scenario_name}：步骤5 - 设置Load Command Status = 2（锁住托盘）")
            # 无条件设置Load Command Status = 2，确保返回0x02给LAS
            self.core.load_command_status = 2  # Lock Carrier in place
            self.logger.log_las(f"{scenario_name}：已设置Load Command Status = 2 (Lock Carrier in place)")
            
            self.logger.log_las(f"{scenario_name}：IP0卡轨故障场景执行完成")
            self.logger.log_las(f"{scenario_name}：LAS应判定：机械手异常、挡轨、禁止动托盘、座子锁住、{sample_result_desc}")
            
            # 发送相关消息给LAS
            if hasattr(self.core, 'las_server') and self.core.las_server:
                self.logger.log_las("场景9：发送状态消息给LAS")
                
                # 发送Instrument Health Response（包含所有状态信息）
                try:
                    self.core.las_server.send_instrument_health_response()
                    self.logger.log_las("场景9：已发送Instrument Health Response消息")
                except Exception as e:
                    self.logger.error(f"场景9：发送Instrument Health消息失败: {str(e)}")
                
                # 注意：0x0002和0x0003消息类型在uRAP协议中不存在
                # 状态信息已通过Instrument Health Response (0x0202)传递
                # 注意：0x0004 Sample Result 在 uRAP 协议中不存在
                # 样本结果通过 Load/Unload Response 中的 Sample Processing Status 传递
                self.logger.log_las(f"{scenario_name}：跳过发送Sample Result (0x0004) - 该消息在uRAP协议中不存在")
            
            # 检查是否有正在处理的手动标本处理请求
            if hasattr(self, 'current_request'):
                self.logger.log_las("场景10：检测到正在处理的手动标本处理请求，自动触发完成按钮")
                # 自动触发完成按钮点击事件
                self._on_complete_button_click()   
        # 在后台线程中执行，避免阻塞UI
        thread = threading.Thread(target=run_scenario_9, daemon=True)
        thread.start()
    
    def _trigger_scenario_10(self):
        """场景10：机械手故障但不挡轨（立即放走空托）"""
        self.logger.info("【按钮点击】场景10 - 用户触发了此场景")
        self.logger.log_las("场景10：开始执行机械手故障但不挡轨场景")
        
        # 记录当前场景
        self.core.active_scenario = '10'
        self.core.active_scenario_data = {
            'description': '机械手故障放走空托',
            'load_response': 0x03,
            'sample_result': 0x00
        }
        self.logger.log_las("场景10：已记录当前场景为 10，用于后续自动适配")
        
        import threading
        
        def run_scenario_10():
            self.logger.log_las("场景10：步骤1 - 设置机械手异常（Automation Status = Error）")
            # 设置机械手异常
            self.automation_recovery_status_combobox.set("Error")
            self._update_automation_recovery_status()
            
            self.logger.log_las("场景10：步骤2 - 设置自动化接口状态为Red（不挡轨，机械手故障）")
            # 设置自动化接口状态为Red（机械手故障但不挡轨）
            self.automation_status_combobox.set("Red")
            self._update_automation_status()
            
            self.logger.log_las("场景10：步骤3 - 设置分析仪不就绪（关闭收样）")
            # 设置分析仪不就绪，关闭收样
            self.analyzer_ready_combobox.set("Not Ready")
            self._update_analyzer_ready_status()
            
            self.logger.log_las("场景10：步骤4 - 设置仪器处理状态为Red")
            # 设置仪器处理状态为Red
            self.instrument_status_combobox.set("Red")
            self._update_instrument_status()
            
            self.logger.log_las("场景10：步骤5 - 设置Load Response = 0x03（失败但解锁，直接放走）")
            # 设置Load失败原因为OK to Unlock Carrier，不锁座子
            self.load_failure_reason_combobox.set("OK to Unlock Carrier")
            self._update_load_failure_reason()
            
            # 关键：设置load_command_status为3，下次Load直接返回0x03
            self.core.load_command_status = 3  # Failed but Unlocked
            
            self.logger.log_las("场景10：机械手故障场景设置完成")
            self.logger.log_las("场景10：LAS应判定：机械手故障、不挡轨、可以动托盘、不锁座子")
            self.logger.log_las("场景10：【下次Load直接返回0x03，立即放走空托】")
            
            # 发送相关消息给LAS
            if hasattr(self.core, 'las_server') and self.core.las_server:
                self.logger.log_las("场景10：发送状态消息给LAS")
                
                # 发送Instrument Health Response（包含所有状态信息）
                try:
                    self.core.las_server.send_instrument_health_response()
                    self.logger.log_las("场景10：已发送Instrument Health Response消息")
                except Exception as e:
                    self.logger.error(f"场景10：发送Instrument Health消息失败: {str(e)}")
                
                # 注意：0x0002和0x0003消息类型在uRAP协议中不存在
                # 状态信息已通过Instrument Health Response (0x0202)传递
                
                self.logger.log_las("场景10：设置完成，下次Load请求将直接返回0x03（失败但解锁）")
                self.logger.log_las("场景10：LAS收到0x03后会立即放走空托，不锁座子")
                
                # 注意：0x0004 Sample Result 在 uRAP 协议中不存在
                # 样本结果通过 Load/Unload Response 中的 Sample Processing Status 传递
                self.logger.log_las("场景10：跳过发送Sample Result (0x0004) - 该消息在uRAP协议中不存在")
            
            # 检查是否有正在处理的手动标本处理请求
            if hasattr(self, 'current_request'):
                self.logger.log_las("场景10：检测到正在处理的手动标本处理请求，自动触发完成按钮")
                # 自动触发完成按钮点击事件
                self._on_complete_button_click()
        
        # 在后台线程中执行，避免阻塞UI
        thread = threading.Thread(target=run_scenario_10, daemon=True)
        thread.start()
    
    def _trigger_scenario_11(self):
        """场景11：机械手故障但标本还在轨道上（5分钟超时自动放行）"""
        self.logger.info("【按钮点击】场景11 - 用户触发了此场景")
        self.logger.log_las("场景11：开始执行机械手故障但标本还在轨道上场景")
        
        # 记录当前场景
        self.core.active_scenario = '11'
        self.core.active_scenario_data = {
            'description': '机械手故障5分钟解锁',
            'load_response_locked': 0x02,
            'load_response_unlock': 0x03,
            'sample_result': 0x01  # 标本还在
        }
        self.logger.log_las("场景11：已记录当前场景为 11，用于后续自动适配")
        
        import threading
        
        def run_scenario_11():
            self.logger.log_las("场景11：步骤1 - 设置机械手异常（Automation Status = Error）")
            # 设置机械手异常
            self.automation_recovery_status_combobox.set("Error")
            self._update_automation_recovery_status()
            
            self.logger.log_las("场景11：步骤2 - 设置自动化接口状态为Critical（挡轨，机械手故障）")
            # 设置自动化接口状态为Critical（机械手故障且挡轨，防止LAS移动托盘）
            self.automation_status_combobox.set("Critical")
            self._update_automation_status()
            
            # 手动设置 ready_to_load[0] = True，让LAS可以发送Load请求
            self.core.ready_to_load[0] = True
            self.logger.log_las("场景11：设置IP0就绪状态为True，允许LAS发送Load请求")
            
            self.logger.log_las("场景11：步骤3 - 设置分析仪就绪（允许收样，等待重试）")
            # 设置分析仪就绪，这样LAS会在机械手恢复后重试Load
            self.analyzer_ready_combobox.set("Ready")
            self._update_analyzer_ready_status()
            
            self.logger.log_las("场景11：步骤4 - 设置仪器处理状态为Yellow（警告状态）")
            # 设置仪器处理状态为Yellow（警告，但不是完全停止）
            self.instrument_status_combobox.set("Yellow")
            self._update_instrument_status()
            
            self.logger.log_las("场景11：步骤5 - 设置Load Response = 0x02（锁住托盘，等待修复）")
            # 设置Load失败原因为Lock Carrier，锁住托盘
            self.load_failure_reason_combobox.set("Lock Carrier")
            self._update_load_failure_reason()
            
            # 关键：设置load_command_status为2，下次Load返回0x02（锁住）
            self.core.load_command_status = 2  # Lock Carrier in place
            
            self.logger.log_las("场景11：机械手故障场景设置完成")
            self.logger.log_las("场景11：【提示】请手动修复机械手（点击场景8恢复）")
            self.logger.log_las("场景11：【警告】如果5分钟内未修复，将自动发送0x0304=0x03解锁，LAS移走托盘")
            
            # 发送相关消息给LAS
            if hasattr(self.core, 'las_server') and self.core.las_server:
                self.logger.log_las("场景11：发送状态消息给LAS")
                
                # 发送Instrument Health Response（包含所有状态信息）
                try:
                    self.core.las_server.send_instrument_health_response()
                    self.logger.log_las("场景11：已发送Instrument Health Response消息")
                except Exception as e:
                    self.logger.error(f"场景11：发送Instrument Health消息失败: {str(e)}")
                
                # 注意：0x0002和0x0003消息类型在uRAP协议中不存在
                # 状态信息已通过Instrument Health Response (0x0202)传递
            
            # 检查是否有正在处理的手动标本处理请求，自动触发完成发送0x02
            if hasattr(self, 'current_request'):
                self.logger.log_las("场景11：检测到正在处理的手动标本处理请求，自动触发完成按钮发送0x0304=0x02锁住")
                self._on_complete_button_click()
            
            # 等待5分钟，检查是否已恢复
            self.logger.log_las("场景11：开始5分钟倒计时，等待机械手恢复...")
            import time
            wait_time = 300  # 5分钟 = 300秒
            check_interval = 10  # 每10秒检查一次
            elapsed = 0
            
            # 定义统一的解锁处理函数（人工处理和超时都使用0x03）
            def handle_unlock(is_recovered=False, remaining_time=0):
                """统一处理解锁逻辑，都使用0x03"""
                try:
                    status_text = "已恢复" if is_recovered else "超时"
                    self.logger.log_las(f"场景11：【{status_text}】发送0x0304=0x03解锁")
                    
                    # 1. 发送0x0304 = 0x03（失败但解锁）
                    self.core.load_command_status = 3  # Failed but Unlocked
                    self.load_failure_reason_combobox.set("OK to Unlock Carrier")
                    self._update_load_failure_reason()
                    
                    # 2. 释放IP0锁定的carrier
                    self.core.clear_queue(0, force=True)
                    
                    # 3. 发送状态消息
                    if hasattr(self.core, 'las_server') and self.core.las_server:
                        # 发送Instrument Health（包含所有状态信息）
                        self.core.las_server.send_instrument_health_response()
                        self.logger.log_las("场景11：已发送Instrument Health Response消息")
                        # 注意：0x0002和0x0003消息类型在uRAP协议中不存在
                        # 状态信息已通过Instrument Health Response (0x0202)传递
                    
                    self.logger.log_las(f"场景11：【完成】已发送0x0304=0x03解锁，LAS将移走托盘")
                    
                    # 注意：0x0004 Sample Result 在 uRAP 协议中不存在
                    # 样本结果通过 Load/Unload Response 中的 Sample Processing Status 传递
                    #self.logger.log_las("场景11：跳过发送Sample Result (0x0004) - 该消息在uRAP协议中不存在")
                    
                except Exception as e:
                    self.logger.error(f"场景11：发送解锁消息失败: {str(e)}")
            
            while elapsed < wait_time:
                time.sleep(check_interval)
                elapsed += check_interval
                remaining = wait_time - elapsed
                
                # 检查机械手是否已恢复（Automation Status是否为Normal）
                if self.core.automation_status == 0x00:  # Normal
                    self.logger.log_las(f"场景11：机械手已恢复（倒计时{remaining}秒时）")
                    handle_unlock(is_recovered=True, remaining_time=remaining)
                    return  # 退出线程
                
                # 每30秒记录一次日志
                if elapsed % 30 == 0:
                    minutes = remaining // 60
                    seconds = remaining % 60
                    self.logger.log_las(f"场景11：等待机械手恢复... 还剩{minutes}分{seconds}秒")
            
            # 5分钟超时，自动解锁
            self.logger.log_las("场景11：【超时】5分钟未修复")
            handle_unlock(is_recovered=False)
            
            # 检查是否有正在处理的手动标本处理请求，自动触发完成发送0x03
            if hasattr(self, 'current_request'):
                self.logger.log_las("场景11：超时后自动触发完成按钮，发送0x0304=0x03解锁")
                self._on_complete_button_click()
        
        # 在后台线程中执行，避免阻塞UI
        thread = threading.Thread(target=run_scenario_11, daemon=True)
        thread.start()
    
    def _trigger_scenario_12(self):
        """场景12：Queue Flush（清空队列）- Load Response Status = 0x04"""
        self.logger.info("【按钮点击】场景12 - 用户触发了此场景")
        self.logger.log_las("场景12：开始执行Queue Flush场景（Load Response = 0x04）")
        
        import threading
        
        def run_scenario_12():
            self.logger.log_las("场景12：设置Load Response Status = 0x04 (Queue Flush)")
            # 设置Load失败原因为Queue Flush
            self.load_failure_reason_combobox.set("Queue Flush")
            self._update_load_failure_reason()
            
            # 设置load_command_status为4，下次Load返回0x04
            self.core.load_command_status = 4
            
            self.logger.log_las("场景12：Queue Flush场景设置完成")
            self.logger.log_las("场景12：LAS收到0x04后会清空队列，重新规划路径")
            
            # 发送相关消息给LAS
            if hasattr(self.core, 'las_server') and self.core.las_server:
                self.logger.log_las("场景12：发送Instrument Health消息给LAS")
                try:
                    self.core.las_server.send_instrument_health_response()
                    self.logger.log_las("场景12：已发送Instrument Health Response消息")
                except Exception as e:
                    self.logger.error(f"场景12：发送Instrument Health消息失败: {str(e)}")
        
        # 在后台线程中执行，避免阻塞UI
        thread = threading.Thread(target=run_scenario_12, daemon=True)
        thread.start()
    
    def _trigger_scenario_13(self):
        """场景13：Queue Rebuild（重建队列）- Load Response Status = 0x05"""
        self.logger.info("【按钮点击】场景13 - 用户触发了此场景")
        self.logger.log_las("场景13：开始执行Queue Rebuild场景（Load Response = 0x05）")
        
        import threading
        
        def run_scenario_13():
            self.logger.log_las("场景13：设置Load Response Status = 0x05 (Queue Rebuild)")
            # 设置Load失败原因为Queue Rebuild
            self.load_failure_reason_combobox.set("Queue Rebuild")
            self._update_load_failure_reason()
            
            # 设置load_command_status为5，下次Load返回0x05
            self.core.load_command_status = 5
            
            self.logger.log_las("场景13：Queue Rebuild场景设置完成")
            self.logger.log_las("场景13：LAS收到0x05后会重建队列，重新分配资源")
            
            # 发送相关消息给LAS
            if hasattr(self.core, 'las_server') and self.core.las_server:
                self.logger.log_las("场景13：发送Instrument Health消息给LAS")
                try:
                    self.core.las_server.send_instrument_health_response()
                    self.logger.log_las("场景13：已发送Instrument Health Response消息")
                except Exception as e:
                    self.logger.error(f"场景13：发送Instrument Health消息失败: {str(e)}")
        
        # 在后台线程中执行，避免阻塞UI
        thread = threading.Thread(target=run_scenario_13, daemon=True)
        thread.start()
    
    def _trigger_scenario_16(self):
        """场景16：人工修复完成（根据场景9/10/11自动适配）"""
        self.logger.info("【按钮点击】场景16 - 用户触发了此场景")
        self.logger.log_las("场景16：开始执行人工修复完成（自动适配）")
        
        import threading
        
        def run_scenario_16():
            # 检查当前激活的场景
            active_scenario = getattr(self.core, 'active_scenario', None)
            scenario_data = getattr(self.core, 'active_scenario_data', {})
            
            if active_scenario is None:
                self.logger.log_las("场景16：【警告】没有记录到之前触发的场景（9/10/11），将使用默认恢复")
                # 使用默认恢复（场景8的行为）
                self._trigger_scenario_8()
                return
            
            self.logger.log_las(f"场景16：检测到之前触发的场景是 {active_scenario}，开始自动适配恢复")
            
            # 获取当前样本ID
            sample_id = None
            if hasattr(self, 'current_request') and self.current_request:
                sample_id = self.current_request.get('sample_id', 'Unknown')
            elif hasattr(self.core, 'last_sample_id'):
                sample_id = self.core.last_sample_id
            else:
                sample_id = 'Unknown'
            
            # 根据场景自动适配
            if active_scenario == '9a':
                # 场景9a：卡轨-抓到标本
                # 需要发送：0x0304=0x03解锁，0x0004=0x00标本已取走
                self.logger.log_las("场景16：适配场景9a（卡轨-抓到标本）")
                self.logger.log_las("场景16：发送0x0304=0x03解锁，0x0004=0x00标本已取走")
                
                # 1. 发送0x0304=0x03
                self.core.load_command_status = 3
                self.load_failure_reason_combobox.set("OK to Unlock Carrier")
                self._update_load_failure_reason()
                
                # 2. 发送0x0004=0x00
                if hasattr(self.core, 'las_server') and self.core.las_server:
                    if hasattr(self.core.las_server, 'send_sample_result'):
                        self.core.las_server.send_sample_result(
                            sample_id=sample_id,
                            result_code=0x00,
                            interface_position=0
                        )
                
                # 3. 恢复状态
                self._restore_normal_status()
                
            elif active_scenario == '9b':
                # 场景9b：卡轨-没抓到
                # 需要发送：0x0304=0x03解锁，0x0004=0x01标本还在
                self.logger.log_las("场景16：适配场景9b（卡轨-没抓到）")
                self.logger.log_las("场景16：发送0x0304=0x03解锁，0x0004=0x01标本还在")
                
                # 1. 发送0x0304=0x03
                self.core.load_command_status = 3
                self.load_failure_reason_combobox.set("OK to Unlock Carrier")
                self._update_load_failure_reason()
                
                # 2. 发送0x0004=0x01
                if hasattr(self.core, 'las_server') and self.core.las_server:
                    if hasattr(self.core.las_server, 'send_sample_result'):
                        self.core.las_server.send_sample_result(
                            sample_id=sample_id,
                            result_code=0x01,
                            interface_position=0
                        )
                
                # 3. 恢复状态
                self._restore_normal_status()
                
            elif active_scenario == '10':
                # 场景10：机械手故障放走空托
                # 已经发送过0x0304=0x03和0x0004=0x00，只需要恢复状态
                self.logger.log_las("场景16：适配场景10（机械手故障放走空托）")
                self.logger.log_las("场景16：场景10已发送过解锁消息，直接恢复状态")
                
                # 直接恢复状态
                self._restore_normal_status()
                
            elif active_scenario == '11':
                # 场景11：机械手故障5分钟解锁
                # 已经发送过0x0304=0x03和0x0004=0x01，只需要恢复状态
                self.logger.log_las("场景16：适配场景11（机械手故障5分钟解锁）")
                self.logger.log_las("场景16：场景11已发送过解锁消息，直接恢复状态")
                
                # 直接恢复状态
                self._restore_normal_status()
            
            else:
                self.logger.log_las(f"场景16：【警告】未知的场景 {active_scenario}，使用默认恢复")
                self._restore_normal_status()
            
            # 清除场景记录
            self.core.active_scenario = None
            self.core.active_scenario_data = {}
            self.logger.log_las("场景16：人工修复完成，已清除场景记录")
        
        # 在后台线程中执行
        thread = threading.Thread(target=run_scenario_16, daemon=True)
        thread.start()
    
    def _restore_normal_status(self):
        """恢复系统到正常状态（供场景16使用）"""
        self.logger.log_las("场景16：恢复系统到正常状态")
        
        # 恢复所有状态
        self.automation_status_combobox.set("Green")
        self._update_automation_status()
        
        self.instrument_status_combobox.set("Green")
        self._update_instrument_status()
        
        self.automation_recovery_status_combobox.set("Normal")
        self._update_automation_recovery_status()
        
        self.analyzer_ready_combobox.set("Ready")
        self._update_analyzer_ready_status()
        
        self.load_failure_reason_combobox.set("Success")
        self._update_load_failure_reason()
        
        self.ip0_remote_status_combobox.set("Online Loading Only Mode")
        self.core.update_remote_control_status(0, 4)
        
        self.ip1_remote_status_combobox.set("Online Unloading Only Mode")
        self.core.update_remote_control_status(1, 5)
        
        # 发送恢复消息
        if hasattr(self.core, 'las_server') and self.core.las_server:
            try:
                # 发送Instrument Health（包含所有状态信息）
                self.core.las_server.send_instrument_health_response()
                self.logger.log_las("场景16：已发送Instrument Health")
                # 注意：0x0002和0x0003消息类型在uRAP协议中不存在
                # 状态信息已通过Instrument Health Response (0x0202)传递
                
            except Exception as e:
                self.logger.error(f"场景16：发送恢复消息失败: {str(e)}")
        
        self.logger.log_las("场景16：系统状态已恢复到正常")
    
    def _trigger_scenario_ip1(self, scenario_num):
        """IP1 UNLOAD场景触发器（场景17-23）
        
        Args:
            scenario_num: 场景编号（17-23）
        """
        scenario_names = {
            17: "场景17：IP1卡轨-成功装托",
            18: "场景18：IP1卡轨-未成功装托",
            19: "场景19：IP1故障放走托盘",
            20: "场景20：IP1故障5分钟解锁",
            21: "场景21：IP1 Queue Flush",
            22: "场景22：IP1 Queue Rebuild",
            23: "场景23：IP1失败解锁"
        }
        
        scenario_name = scenario_names.get(scenario_num, f"场景{scenario_num}")
        self.logger.info(f"【按钮点击】{scenario_name} - 用户触发了此场景")
        self.logger.log_las(f"{scenario_name}：开始执行IP1 UNLOAD场景")
        
        # 记录当前IP1场景
        self.core.active_scenario_ip1 = str(scenario_num)
        
        import threading
        
        def run_ip1_scenario():
            # 根据场景设置unload_command_status
            if scenario_num == 17:
                # 场景17：卡轨-标本已取走 -> 0x02锁住
                self.core.unload_command_status = 2
                sample_result = 0x00
                self.logger.log_las(f"{scenario_name}：设置Unload Response = 0x02 (Lock Carrier)")
                # 设置自动化接口状态为Critical（挡轨，防止LAS移动托盘）
                self.automation_status_combobox.set("Critical")
                self._update_automation_status()
                self.logger.log_las(f"{scenario_name}：设置自动化接口状态为Critical（挡轨）")
            elif scenario_num == 18:
                # 场景18：卡轨-标本还在 -> 0x02锁住
                self.core.unload_command_status = 2
                sample_result = 0x01
                self.logger.log_las(f"{scenario_name}：设置Unload Response = 0x02 (Lock Carrier)")
                # 设置自动化接口状态为Critical（挡轨，防止LAS移动托盘）
                self.automation_status_combobox.set("Critical")
                self._update_automation_status()
                self.logger.log_las(f"{scenario_name}：设置自动化接口状态为Critical（挡轨）")
            elif scenario_num == 19:
                # 场景19：故障放走托盘 -> 0x03解锁
                self.core.unload_command_status = 3
                sample_result = 0x00
                self.logger.log_las(f"{scenario_name}：设置Unload Response = 0x03 (Failed but Unlocked)")
                # 设置自动化接口状态为Red（机械手故障但不挡轨）
                self.automation_status_combobox.set("Red")
                self._update_automation_status()
                self.logger.log_las(f"{scenario_name}：设置自动化接口状态为Red（不挡轨，机械手故障）")
            elif scenario_num == 20:
                # 场景20：故障5分钟解锁 -> 0x02锁住（后续会变为0x03）
                self.core.unload_command_status = 2
                sample_result = 0x01
                self.logger.log_las(f"{scenario_name}：设置Unload Response = 0x02 (Lock Carrier)，5分钟后解锁")
                # 设置自动化接口状态为Red（机械手故障但不挡轨）
                self.automation_status_combobox.set("Red")
                self._update_automation_status()
                self.logger.log_las(f"{scenario_name}：设置自动化接口状态为Red（不挡轨，机械手故障）")
                # 启动5分钟定时器
                self._start_ip1_unlock_timer()
            elif scenario_num == 21:
                # 场景21：Queue Flush -> 0x04
                self.core.unload_command_status = 4
                self.logger.log_las(f"{scenario_name}：设置Unload Response = 0x04 (Queue Flush)")
            elif scenario_num == 22:
                # 场景22：Queue Rebuild -> 0x05
                self.core.unload_command_status = 5
                self.logger.log_las(f"{scenario_name}：设置Unload Response = 0x05 (Queue Rebuild)")
            elif scenario_num == 23:
                # 场景23：失败解锁 -> 0x03
                self.core.unload_command_status = 3
                self.logger.log_las(f"{scenario_name}：设置Unload Response = 0x03 (Failed but Unlocked)")
            
            # 发送Sample Result（对于场景17-20）
            if scenario_num in [17, 18, 19]:
                try:
                    sample_id = self._get_current_sample_id()
                    if hasattr(self.core, 'las_server') and self.core.las_server:
                        if hasattr(self.core.las_server, 'send_sample_result'):
                            # IP1使用operation_type=0x03
                            self.core.las_server.send_sample_result(
                                sample_id=sample_id,
                                result_code=sample_result,
                                interface_position=1,  # IP1
                                operation_type=0x03    # IP1 Unload
                            )
                            self.logger.log_las(f"{scenario_name}：已发送Sample Result = 0x{sample_result:02x}")
                except Exception as e:
                    self.logger.error(f"{scenario_name}：发送Sample Result失败: {str(e)}")
            
            # 设置IP1状态
            self.logger.log_las(f"{scenario_name}：IP1 UNLOAD场景设置完成")
            
            # 场景17-20：自动触发完成按钮（如果当前有UNLOAD请求）
            if scenario_num in [17, 18, 19, 20]:
                if hasattr(self, 'current_request'):
                    self.logger.log_las(f"{scenario_name}：检测到正在处理的手动标本处理请求，自动触发完成按钮")
                    self._on_complete_button_click()
        
        thread = threading.Thread(target=run_ip1_scenario, daemon=True)
        thread.start()

    def _trigger_ip1_unload_scenario(self, scenario_num):
        """IP1 UNLOAD反馈状态码场景触发器（场景1-8）

        Args:
            scenario_num: 场景编号（1-8）
        """
        scenario_config = {
            1: {
                'name': 'UNLOAD场景1：Success (0x01)',
                'desc': '卸载成功',
                'unload_response': 0x01,
                'automation_interface': 'Green',
                'automation_status': 'Normal',
                'analyzer_ready': 'Ready',
                'instrument_status': 'Green'
            },
            2: {
                'name': 'UNLOAD场景2：Lock Carrier (0x02)',
                'desc': '锁定载体',
                'unload_response': 0x02,
                'automation_interface': 'Critical',
                'automation_status': 'Normal',
                'analyzer_ready': 'Ready',
                'instrument_status': 'Green'
            },
            3: {
                'name': 'UNLOAD场景3：OK to Unlock (0x03)',
                'desc': '可解锁载体',
                'unload_response': 0x03,
                'automation_interface': 'Red',
                'automation_status': 'Error',
                'analyzer_ready': 'Not Ready',
                'instrument_status': 'Red'
            },
            4: {
                'name': 'UNLOAD场景4：Queue Flush (0x04)',
                'desc': '队列刷新',
                'unload_response': 0x04,
                'automation_interface': 'Green',
                'automation_status': 'Normal',
                'analyzer_ready': 'Ready',
                'instrument_status': 'Green'
            },
            5: {
                'name': 'UNLOAD场景5：Interface Offline (0x05)',
                'desc': 'Interface Offline',
                'unload_response': 0x05,
                'automation_interface': 'Green',
                'automation_status': 'Normal',
                'analyzer_ready': 'Ready',
                'instrument_status': 'Green'
            },
            6: {
                'name': 'UNLOAD场景6：Mode Error (0x06)',
                'desc': '模式错误',
                'unload_response': 0x06,
                'automation_interface': 'Critical',
                'automation_status': 'Error',
                'analyzer_ready': 'Not Ready',
                'instrument_status': 'Red'
            },
            7: {
                'name': 'UNLOAD场景7：Skipped Unloading (0x07)',
                'desc': '跳过卸载',
                'unload_response': 0x07,
                'automation_interface': 'Green',
                'automation_status': 'Normal',
                'analyzer_ready': 'Ready',
                'instrument_status': 'Green'
            },
            8: {
                'name': 'UNLOAD场景8：Release Next (0x08)',
                'desc': '释放下一个',
                'unload_response': 0x08,
                'automation_interface': 'Green',
                'automation_status': 'Normal',
                'analyzer_ready': 'Ready',
                'instrument_status': 'Green'
            }
        }

        config = scenario_config.get(scenario_num)
        if not config:
            self.logger.error(f"未知的场景编号: {scenario_num}")
            return

        self.logger.info(f"【按钮点击】{config['name']} - 用户触发了此场景")
        self.logger.log_las(f"{config['name']}：开始执行IP1 UNLOAD场景（{config['desc']}）")

        # 记录当前场景
        scenario_key = f'ip1_unload_{scenario_num}'
        self.core.active_scenario_ip1 = scenario_key
        self.core.active_scenario_ip1_data = {
            'scenario_num': scenario_num,
            'unload_response': config['unload_response'],
            'description': config['desc']
        }

        # 更新场景状态显示
        self.ip1_scenario_status_var.set(f"当前场景：{config['name']} - {config['desc']}")

        import threading

        def run_scenario():
            self.logger.log_las(f"{config['name']}：步骤1 - 设置设备状态参数")

            # 设置自动化接口状态（机械手状态）
            if config['automation_status'] == 'Normal':
                self.automation_recovery_status_combobox.set("Normal")
                self._update_automation_recovery_status()
            elif config['automation_status'] == 'Error':
                self.automation_recovery_status_combobox.set("Error")
                self._update_automation_recovery_status()
            self.logger.log_las(f"{config['name']}：设置Automation Status = {config['automation_status']}")

            # 设置分析仪就绪状态
            self.analyzer_ready_combobox.set(config['analyzer_ready'])
            self._update_analyzer_ready_status()
            self.logger.log_las(f"{config['name']}：设置Analyzer Ready = {config['analyzer_ready']}")

            # 设置仪器处理状态
            self.instrument_status_combobox.set(config['instrument_status'])
            self._update_instrument_status()
            self.logger.log_las(f"{config['name']}：设置Instrument Status = {config['instrument_status']}")

            # 设置自动化接口健康状态（不自动发送，稍后统一发送）
            self.automation_status_combobox.set(config['automation_interface'])
            self._update_automation_status(auto_send_health=False)
            self.logger.log_las(f"{config['name']}：设置Automation Interface Status = {config['automation_interface']}")

            # 设置Unload Response状态码
            self.logger.log_las(f"{config['name']}：步骤2 - 设置Unload Response = 0x{config['unload_response']:02X}")
            self.core.unload_command_status = config['unload_response']

            # 更新Unload失败原因下拉框（如果有对应项）
            response_map = {
                0x01: "Success",
                0x02: "Lock Carrier",
                0x03: "OK to Unlock Carrier",
                0x04: "Queue Flush",
                0x05: "Interface Offline",
                0x06: "Mode Error",
                0x07: "Skipped",
                0x08: "Release Next"
            }
            reason_text = response_map.get(config['unload_response'], "Success")
            # 注意：IP1可能没有unload_failure_reason_combobox，需要检查
            if hasattr(self, 'unload_failure_reason_combobox'):
                self.unload_failure_reason_combobox.set(reason_text)
                # 如果有对应的更新方法，调用它
                if hasattr(self, '_update_unload_failure_reason'):
                    self._update_unload_failure_reason()

            self.logger.log_las(f"{config['name']}：已设置Unload Command Status = 0x{config['unload_response']:02X}")

            # 发送相关消息给LAS
            if hasattr(self.core, 'las_server') and self.core.las_server:
                self.logger.log_las(f"{config['name']}：步骤3 - 发送状态消息给LAS")

                import time

                # 发送Instrument Health Response（包含所有状态信息）
                try:
                    self.core.las_server.send_instrument_health_response()
                    self.logger.log_las(f"{config['name']}：已发送Instrument Health Response")
                    time.sleep(0.2)
                except Exception as e:
                    self.logger.error(f"{config['name']}：发送Instrument Health失败: {str(e)}")

            self.logger.log_las(f"{config['name']}：场景执行完成")
            self.logger.log_las(f"{config['name']}：LAS收到Unload Response = 0x{config['unload_response']:02X}后将执行相应操作")

            # 检查是否有正在处理的手动标本处理请求
            if hasattr(self, 'current_request') and self.current_request:
                self.logger.log_las(f"{config['name']}：检测到正在处理的手动标本处理请求，自动触发完成按钮")
                self._on_complete_button_click()
            else:
                # 检查LAS是否有pending的Unload Request等待处理
                if hasattr(self.core, 'las_server') and self.core.las_server:
                    las_server = self.core.las_server
                    pending_count = len(las_server.pending_requests.get(1, []))
                    if pending_count > 0:
                        self.logger.log_las(f"{config['name']}：检测到{pending_count}个pending的Unload Request，立即处理")
                        # 获取第一个pending请求
                        pending_req = las_server.pending_requests[1][0]
                        # 设置为当前请求
                        self.current_request = {
                            'type': 'unload',
                            'interface_position': 1,
                            'sample_id': pending_req.get('sample_id', ''),
                            'conn': pending_req['conn'],
                            'header': pending_req['header'],
                            'body': pending_req['body']
                        }
                        # 触发完成按钮
                        self._on_complete_button_click()
                        self.logger.log_las(f"{config['name']}：已自动发送Unload Response")
                    else:
                        self.logger.log_las(f"{config['name']}：当前没有pending的Unload Request")
                        self.logger.log_las(f"{config['name']}：等待LAS发送Unload Request后将返回 0x{config['unload_response']:02X}")

        # 在后台线程中执行，避免阻塞UI
        thread = threading.Thread(target=run_scenario, daemon=True)
        thread.start()

    def _start_ip1_unlock_timer(self):
        """启动IP1 5分钟解锁定时器（场景20）"""
        def unlock_after_timeout():
            import time
            time.sleep(300)  # 5分钟
            self.logger.log_las("场景20：【超时】5分钟未修复，自动发送0x0304=0x03解锁IP1")
            self.core.unload_command_status = 3
            
            # 注意：0x0004 Sample Result 在 uRAP 协议中不存在
            # 样本结果通过 Load/Unload Response 中的 Sample Processing Status 传递
            self.logger.log_las("场景20：跳过发送Sample Result (0x0004) - 该消息在uRAP协议中不存在")
            
            # 超时后自动触发完成按钮发送0x03
            if hasattr(self, 'current_request'):
                self.logger.log_las("场景20：超时后自动触发完成按钮，发送0x0304=0x03解锁")
                self._on_complete_button_click()
        
        thread = threading.Thread(target=unlock_after_timeout, daemon=True)
        thread.start()
    
    def _trigger_scenario_ip1_24(self):
        """场景24：IP1人工修复完成（自动适配场景17-20）"""
        self.logger.info("【按钮点击】场景24 - 用户触发了此场景")
        self.logger.log_las("场景24：开始执行IP1人工修复完成（自动适配）")
        
        import threading
        
        def run_scenario_24():
            active_scenario = getattr(self.core, 'active_scenario_ip1', None)
            
            if active_scenario is None:
                self.logger.log_las("场景24：【警告】没有记录到之前触发的IP1场景，使用默认恢复")
                self._restore_ip1_normal_status()
                return
            
            self.logger.log_las(f"场景24：检测到之前触发的IP1场景是 {active_scenario}")
            
            sample_id = self._get_current_sample_id()
            
            if active_scenario == '17':
                # 场景17：卡轨-标本已取走
                self.logger.log_las("场景24：适配场景17，发送0x0304=0x03")
                self.core.unload_command_status = 3
                # 注意：0x0004 Sample Result 在 uRAP 协议中不存在
                self.logger.log_las("场景24：跳过发送Sample Result (0x0004) - 该消息在uRAP协议中不存在")
                self._restore_ip1_normal_status()
                
            elif active_scenario == '18':
                # 场景18：卡轨-标本还在
                self.logger.log_las("场景24：适配场景18，发送0x0304=0x03")
                self.core.unload_command_status = 3
                # 注意：0x0004 Sample Result 在 uRAP 协议中不存在
                self.logger.log_las("场景24：跳过发送Sample Result (0x0004) - 该消息在uRAP协议中不存在")
                self._restore_ip1_normal_status()
                
            elif active_scenario in ['19', '20']:
                # 场景19/20：已发送过消息，直接恢复状态
                self.logger.log_las(f"场景24：适配场景{active_scenario}，直接恢复状态")
                self._restore_ip1_normal_status()
            
            else:
                self.logger.log_las(f"场景24：【警告】未知的场景 {active_scenario}，使用默认恢复")
                self._restore_ip1_normal_status()
            
            # 清除场景记录
            self.core.active_scenario_ip1 = None
            self.logger.log_las("场景24：IP1人工修复完成，已清除场景记录")
        
        thread = threading.Thread(target=run_scenario_24, daemon=True)
        thread.start()
    
    def _restore_ip1_normal_status(self):
        """恢复IP1到正常状态"""
        self.logger.log_las("场景24：恢复IP1到正常状态")

        # 注意：不在这里设置 unload_command_status
        # unload_command_status 应该在调用此方法之前设置
        # 场景17/18 设置为 3（解锁），场景19/20 保持之前的状态

        # 恢复自动化接口状态为Green
        self.automation_status_combobox.set("Green")
        self._update_automation_status()
        self.logger.log_las("场景24：已恢复自动化接口状态为Green")

        # 恢复仪器处理状态为Green
        self.instrument_status_combobox.set("Green")
        self._update_instrument_status()
        self.logger.log_las("场景24：已恢复仪器处理状态为Green")

        # 恢复分析仪就绪状态为Ready
        self.analyzer_ready_combobox.set("Ready")
        self._update_analyzer_ready_status()
        self.logger.log_las("场景24：已恢复分析仪就绪状态为Ready")

        # 恢复IP1 REMOTE状态为Online Unloading Only Mode
        self.ip1_remote_status_combobox.set("Online Unloading Only Mode")
        self.core.update_remote_control_status(1, 5)
        self.logger.log_las("场景24：已恢复IP1 REMOTE状态为Online Unloading Only Mode")

        # 发送恢复消息
        if hasattr(self.core, 'las_server') and self.core.las_server:
            try:
                # 发送Instrument Health（包含所有状态信息）
                self.core.las_server.send_instrument_health_response()
                self.logger.log_las("场景24：已发送Instrument Health")
                # 注意：0x0002和0x0003消息类型在uRAP协议中不存在
                # 状态信息已通过Instrument Health Response (0x0202)传递
                
            except Exception as e:
                self.logger.error(f"场景24：发送恢复消息失败: {str(e)}")
        
        self.logger.log_las("场景24：IP1状态已恢复到正常")
    
    def _get_current_sample_id(self):
        """获取当前样本ID
        
        优先级：
        1. SAMPLE ID文本框中的值（用户手动输入的）
        2. current_request中的sample_id
        3. core.last_sample_id
        """
        # 优先从SAMPLE ID文本框获取（用户手动输入的条码）
        if hasattr(self, 'sample_id_entry'):
            sample_id = self.sample_id_entry.get().strip()
            if sample_id:
                return sample_id
        
        # 其次从current_request获取
        if hasattr(self, 'current_request') and self.current_request:
            return self.current_request.get('sample_id', 'Unknown')
        
        # 最后从core.last_sample_id获取
        if hasattr(self.core, 'last_sample_id'):
            return self.core.last_sample_id
        
        return 'Unknown'
    
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
                else:
                    # 样本ID不填写，设置为空字符串
                    request['sample_id'] = ''
                # 通知LAS服务器完成处理
                self.las_server.on_manual_operation_complete(request)
            else:
                # LOAD请求，直接通知LAS服务器完成处理
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
        """显示脱线标本列表"""
        # 创建弹窗窗口
        onboard_window = tk.Toplevel(self.root)
        onboard_window.title("脱线标本列表")
        onboard_window.geometry("800x400")
        onboard_window.transient(self.root)
        # 注意：不调用grab_set()，避免与手动操作提示的grab_set冲突
        
        # 创建主框架
        main_frame = ttk.Frame(onboard_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 获取脱线标本列表（包括脱线标本库中已离开轨道的标本）
        samples = self.core.get_all_samples()
        onboard_samples = [sample for sample_id, sample in samples.items() 
                          if sample['status'] not in ['unloaded', 'ejected']]
        
        # 获取已离开轨道的标本（从脱线标本库）
        offline_samples = list(self.core.offline_samples.values())
        
        # 合并标本列表
        all_samples = onboard_samples + offline_samples
        
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
        
        # 状态映射表
        status_map = {
            'loaded': '已装载',
            'processing': '处理中',
            'completed': '已完成',
            'load_failed': 'Load失败',
            'unloaded': '已卸载',
            'ejected': '已弹出',
            'left_track': '已离开轨道'
        }
        
        # 填充数据
        for sample in all_samples:
            load_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(sample['load_time']))
            status = status_map.get(sample['status'], sample['status'])
            tree.insert('', tk.END, iid=sample['sample_id'], 
                      values=(sample['sample_id'], status, load_time))
        
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
                # 获取已离开轨道的标本（从脱线标本库）
                offline_samples = list(self.core.offline_samples.values())
                # 合并标本列表
                all_samples = onboard_samples + offline_samples
                # 清空树
                for item in tree.get_children():
                    tree.delete(item)
                # 重新添加样本
                for sample in all_samples:
                    load_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(sample['load_time']))
                    status = status_map.get(sample['status'], sample['status'])
                    tree.insert('', tk.END, iid=sample['sample_id'], 
                              values=(sample['sample_id'], status, load_time))
        
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
