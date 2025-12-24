#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI模块 - 图形用户界面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time


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
        self.root.title("Atellica Solution Simulator")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        # 设置主题
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # 状态更新标志
        self.running = False
        self.update_thread = None
        
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
        title_label.pack(pady=10)
        
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
        
        # 中间内容框架（分为左侧参数配置和右侧状态显示）
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
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
        self.detail_text = scrolledtext.ScrolledText(detail_frame, width=60, height=20, wrap=tk.WORD)
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
        self.las_log_text = scrolledtext.ScrolledText(las_log_frame, width=80, height=15, wrap=tk.WORD)
        self.las_log_text.pack(fill=tk.BOTH, expand=True)
        
        # LIS日志
        lis_log_frame = ttk.Frame(logs_notebook, padding="10")
        logs_notebook.add(lis_log_frame, text="LIS日志")
        self.lis_log_text = scrolledtext.ScrolledText(lis_log_frame, width=80, height=15, wrap=tk.WORD)
        self.lis_log_text.pack(fill=tk.BOTH, expand=True)
        
        # 底部按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="刷新状态", command=self._update_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="清空日志", command=self._clear_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="退出", command=self._quit).pack(side=tk.RIGHT, padx=5)
    
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
    
    def _update_logs(self):
        """更新日志显示"""
        try:
            # 更新LAS日志
            las_log_content = self.logger.get_las_log_content(50)  # 获取最后50行
            self.las_log_text.delete(1.0, tk.END)
            self.las_log_text.insert(tk.END, las_log_content)
            self.las_log_text.see(tk.END)  # 滚动到最后
            
            # 更新LIS日志
            lis_log_content = self.logger.get_lis_log_content(50)  # 获取最后50行
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
