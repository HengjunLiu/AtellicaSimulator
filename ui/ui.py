#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI模块 - 图形用户界面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time


APP_VERSION = "v1.3.0"

class AtellicaUI:
    """Atellica模拟器图形用户界面"""
    
    def __init__(self, config_manager, logger, core, las_server, lis_server):
        """初始化UI
        
        Args:
            config_manager: 配置管理器实例
            logger: 日志管理器实例
            core: 核心模拟逻辑实例
            las_server: LAS服务器实例
            lis_server: LIS服务器实例
        """
        self.config_manager = config_manager
        self.logger = logger
        self.core = core
        self.las_server = las_server
        self.lis_server = lis_server
        
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
        
        # 设置日志回调函数
        self.logger.set_las_log_callback(self._on_las_log_received)
        self.logger.set_lis_log_callback(self._on_lis_log_received)
        
        # 创建UI组件
        self._create_widgets()
        
        # 启动服务器
        self.las_server.start()
        self.lis_server.start()
        
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
        status_frame = ttk.LabelFrame(main_frame, text="设备状态", padding="10")
        status_frame.pack(fill=tk.X, pady=10)
        
        # 状态指标网格
        status_grid = ttk.Frame(status_frame)
        status_grid.pack(fill=tk.X)
        
        # 自动化接口状态
        ttk.Label(status_grid, text="自动化接口状态:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.automation_status_var = tk.StringVar()
        self.automation_status_label = ttk.Label(status_grid, textvariable=self.automation_status_var, width=15)
        self.automation_status_label.grid(row=0, column=1, padx=5, pady=5)
        
        # 仪器处理状态
        ttk.Label(status_grid, text="仪器处理状态:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.instrument_status_var = tk.StringVar()
        self.instrument_status_label = ttk.Label(status_grid, textvariable=self.instrument_status_var, width=15)
        self.instrument_status_label.grid(row=0, column=3, padx=5, pady=5)
        
        # LIS连接状态
        ttk.Label(status_grid, text="LIS连接状态:").grid(row=0, column=4, sticky=tk.W, padx=5, pady=5)
        self.lis_status_var = tk.StringVar()
        self.lis_status_label = ttk.Label(status_grid, textvariable=self.lis_status_var, width=15)
        self.lis_status_label.grid(row=0, column=5, padx=5, pady=5)
        
        # 接口位置信息
        ttk.Label(status_grid, text="接口位置数量:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.interface_count_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.interface_count_var, width=15).grid(row=1, column=1, padx=5, pady=5)
        
        # 在线试管数量
        ttk.Label(status_grid, text="在线试管数量:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.onboard_tubes_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.onboard_tubes_var, width=15).grid(row=1, column=3, padx=5, pady=5)
        
        # 已完成试管数量
        ttk.Label(status_grid, text="已完成试管数量:").grid(row=1, column=4, sticky=tk.W, padx=5, pady=5)
        self.completed_tubes_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.completed_tubes_var, width=15).grid(row=1, column=5, padx=5, pady=5)
        
        # 队列状态（新增）
        ttk.Label(status_grid, text="就绪装载:", font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.ready_to_load_var = tk.StringVar()
        self.ready_to_load_label = ttk.Label(status_grid, textvariable=self.ready_to_load_var, width=15)
        self.ready_to_load_label.grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Label(status_grid, text="可返回样本数:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=5)
        self.return_ready_count_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.return_ready_count_var, width=15).grid(row=2, column=3, padx=5, pady=5)
        
        ttk.Label(status_grid, text="IP0队列长度:").grid(row=2, column=4, sticky=tk.W, padx=5, pady=5)
        self.ip0_queue_len_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.ip0_queue_len_var, width=15).grid(row=2, column=5, padx=5, pady=5)
        
        ttk.Label(status_grid, text="IP1队列长度:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.ip1_queue_len_var = tk.StringVar()
        ttk.Label(status_grid, textvariable=self.ip1_queue_len_var, width=15).grid(row=3, column=1, padx=5, pady=5)
        
        ttk.Label(status_grid, text="IP0锁定状态:").grid(row=3, column=2, sticky=tk.W, padx=5, pady=5)
        self.ip0_locked_var = tk.StringVar()
        self.ip0_locked_label = ttk.Label(status_grid, textvariable=self.ip0_locked_var, width=15)
        self.ip0_locked_label.grid(row=3, column=3, padx=5, pady=5)
        
        ttk.Label(status_grid, text="IP1锁定状态:").grid(row=3, column=4, sticky=tk.W, padx=5, pady=5)
        self.ip1_locked_var = tk.StringVar()
        self.ip1_locked_label = ttk.Label(status_grid, textvariable=self.ip1_locked_var, width=15)
        self.ip1_locked_label.grid(row=3, column=5, padx=5, pady=5)
        
        # 中间内容框架（分为左侧参数配置和右侧状态显示）
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.X, pady=10)
        
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
        self.automation_status_combobox = ttk.Combobox(device_config_frame, values=["Green", "Red"], width=15)
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
        
        # 右侧：详细状态显示
        detail_frame = ttk.LabelFrame(content_frame, text="详细状态", padding="10")
        detail_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 详细状态文本框
        self.detail_text = scrolledtext.ScrolledText(detail_frame, width=60, height=10, wrap=tk.WORD)
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        
        # 底部：日志显示
        logs_frame = ttk.LabelFrame(main_frame, text="通讯日志", padding="10")
        logs_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
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
        ttk.Button(left_button_frame, text="编辑库存", command=self._show_inventory_editor).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_button_frame, text="清空日志", command=self._clear_logs).pack(side=tk.LEFT, padx=5)
        
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
            ready_to_load = self.core.get_ready_to_load()
            if ready_to_load == 1:
                self.ready_to_load_var.set("是")
                self.ready_to_load_label.configure(foreground="green")
            else:
                self.ready_to_load_var.set("否")
                self.ready_to_load_label.configure(foreground="gray")
            
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
            
            # 更新详细状态文本
            detail_text = f"设备状态详细信息：\n"
            detail_text += f"自动化接口状态：{'Green' if automation_status == 1 else 'Red'}\n"
            detail_text += f"仪器处理状态：{'Green' if instrument_status == 1 else 'Yellow' if instrument_status == 2 else 'Red'}\n"
            detail_text += f"LIS连接状态：{'Connected' if lis_status == 1 else 'Disconnected'}\n"
            detail_text += f"接口位置数量：{health_status['interface_positions']}\n"
            
            for i in range(health_status['interface_positions']):
                remote_status = health_status['remote_control_status'][i] if i < len(health_status['remote_control_status']) else 1
                lock_ownership = health_status['lock_ownership'][i] if i < len(health_status['lock_ownership']) else 2
                detail_text += f"IP{i} - 远程控制状态：{remote_status}, 锁所有权：{'Locked' if lock_ownership == 1 else 'Not Locked'}\n"
            
            detail_text += f"处理积压：{health_status['processing_backlog']}\n"
            detail_text += f"样本获取延迟：{health_status['sample_acquisition_delay']}\n"
            detail_text += f"在线试管数量：{health_status['on_board_tube_count']}\n"
            detail_text += f"已完成试管数量：{health_status['completed_tube_count']}\n"
            
            # 获取队列详细信息
            detail_text += f"\n队列管理详细信息：\n"
            detail_text += f"就绪装载状态：{'是' if ready_to_load == 1 else '否'}\n"
            detail_text += f"可返回样本数：{return_ready_count}\n"
            
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
            
            self.detail_text.delete(1.0, tk.END)
            self.detail_text.insert(tk.END, detail_text)
            
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
        status_code = 1 if status == "Green" else 3
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
        self.las_log_text.delete(1.0, tk.END)
        self.lis_log_text.delete(1.0, tk.END)
    
    def _quit(self):
        """退出应用"""
        self.running = False
        
        # 停止服务器
        self.las_server.stop()
        self.lis_server.stop()
        
        # 关闭窗口
        self.root.quit()
    
    def run(self):
        """运行UI主循环"""
        try:
            self.root.mainloop()
        finally:
            self.running = False
