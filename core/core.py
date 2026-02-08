#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core模块 - 核心模拟逻辑
"""

import threading
import time
import random
from collections import defaultdict
import sqlite3
import os
import datetime


class AtellicaCore:
    """Atellica核心模拟逻辑"""
    
    def __init__(self, config_manager, logger):
        """初始化核心模拟逻辑
        
        Args:
            config_manager: 配置管理器实例
            logger: 日志管理器实例
        """
        self.config_manager = config_manager
        self.logger = logger
        self.lis_client = None  # LIS客户端实例，稍后设置
        
        # 设备状态
        self.automation_interface_status = config_manager.get_core_config().get('automation_interface_status', 1)
        self.instrument_process_status = config_manager.get_core_config().get('instrument_process_status', 1)
        self.lis_connection_status = config_manager.get_core_config().get('lis_connection_status', 1)
        self.interface_positions = config_manager.get_core_config().get('interface_positions', 2)
        self.remote_control_status = config_manager.get_core_config().get('remote_control_status', [4, 5])
        self.lock_ownership = config_manager.get_core_config().get('lock_ownership', [2, 2])
        self.processing_backlog = config_manager.get_core_config().get('processing_backlog', 0)
        self.sample_acquisition_delay = config_manager.get_core_config().get('sample_acquisition_delay', 0)
        self.on_board_tube_count = config_manager.get_core_config().get('on_board_tube_count', 0)
        self.completed_tube_count = config_manager.get_core_config().get('completed_tube_count', 0)
        
        # 测试项目 inventory
        self.test_inventory = config_manager.get_test_inventory_config().copy()
        
        # 耗材 inventory
        self.consumable_inventory = config_manager.get_consumable_inventory_config().copy()
        
        # 样本管理
        self.samples = {}
        self.pending_results = {}
        
        # 队列管理
        self.queues = {
            0: [],  # IP0队列
            1: []   # IP1队列
        }
        self.locked_carriers = {
            0: None,  # IP0锁定的carrier
            1: None   # IP1锁定的carrier
        }
        self.ready_to_load = {
            0: True,  # IP0是否就绪装载
            1: True   # IP1是否就绪装载
        }
        self.return_ready_count = 0
        
        # 线程锁
        self.status_lock = threading.Lock()
        self.sample_lock = threading.Lock()
        self.inventory_lock = threading.Lock()
        
        # 样本工作流队列 - 用于优化线程使用
        self.sample_workflow_queue = []
        self.sample_workflow_lock = threading.Lock()
        self.sample_workflow_event = threading.Event()
        
        # 样本工作流处理线程 - 单个线程处理所有样本的工作流
        self.sample_workflow_thread = threading.Thread(target=self._process_sample_workflow_loop, daemon=True)
        self.sample_workflow_thread.start()
        
        # 样本工作流定时器管理 - 避免使用time.sleep阻塞线程
        self.sample_timers = {}
        self.sample_timers_lock = threading.Lock()
        
        # 结果生成线程
        self.result_thread = threading.Thread(target=self._generate_results_loop, daemon=True)
        self.result_thread.start()
        
        # 初始化SQLite数据库
        self._init_database()
        
        # 从数据库初始化样本数据
        self._initialize_from_database()
        
        self.logger.info("AtellicaCore initialized successfully")
    
    def _init_database(self):
        """初始化SQLite数据库，创建on_board_samples表
        """
        try:
            # 创建数据库目录（如果不存在）
            db_dir = 'data'
            if not os.path.exists(db_dir):
                os.makedirs(db_dir)
            
            # 数据库文件路径
            db_path = os.path.join(db_dir, 'atellica.db')
            
            # 创建数据库连接
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 创建on_board_samples表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS on_board_samples (
                    sample_id TEXT PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    load_time DATETIME NOT NULL
                )
            ''')
            
            # 创建locked_carrier_info表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS locked_carrier_info (
                    interface_positions TEXT PRIMARY KEY,
                    sample_id TEXT,
                    carrier_occupancy INTEGER
                )
            ''')
            
            # 提交事务并关闭连接
            conn.commit()
            conn.close()
            
            self.logger.info(f"Database initialized successfully at {db_path}")
            
        except sqlite3.Error as e:
            self.logger.error(f"Error initializing database: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error initializing database: {str(e)}")
    
    def _initialize_from_database(self):
        """从数据库初始化样本数据
        
        应用启动时，查询on_board_samples表，初始化样本数据和相关变量
        """
        try:
            self.logger.info("开始从数据库初始化样本数据...")
            
            # 建立数据库连接
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 查询on_board_samples表
            cursor.execute("SELECT sample_id, load_time FROM on_board_samples")
            records = cursor.fetchall()
            
            # 处理查询结果
            if records:
                self.logger.info(f"发现 {len(records)} 条样本记录")
                
                # 提取所有sample_id并存储到self.samples
                for record in records:
                    sample_id = record[0]
                    load_time = record[1]
                    
                    # 尝试将load_time转换为时间戳
                    try:
                        if isinstance(load_time, str):
                            # 解析时间字符串
                            load_time_obj = datetime.datetime.strptime(load_time, '%Y-%m-%d %H:%M:%S')
                            load_time_timestamp = load_time_obj.timestamp()
                        else:
                            load_time_timestamp = load_time
                    except Exception as e:
                        self.logger.warning(f"解析load_time失败: {e}，使用当前时间")
                        load_time_timestamp = time.time()
                    
                    # 存储样本信息
                    self.samples[sample_id] = {
                        'sample_id': sample_id,
                        'status': 'completed',
                        'ready_for_unload': True,
                        'load_time': load_time_timestamp,
                        'timestamp': load_time_timestamp
                    }
                
                # 初始化变量
                total_records = len(records)
                self.on_board_tube_count = total_records
                self.completed_tube_count = total_records
                self.return_ready_count = total_records
                
                self.logger.info(f"初始化完成: on_board_tube_count={self.on_board_tube_count}, completed_tube_count={self.completed_tube_count}, return_ready_count={self.return_ready_count}")
            else:
                self.logger.info("on_board_samples表中无记录")
                # 确保变量初始化为0
                self.on_board_tube_count = 0
                self.completed_tube_count = 0
            
            # 查询locked_carrier_info表，初始化lock_ownership
            self.logger.info("开始初始化lock_ownership...")
            
            try:
                # 查询locked_carrier_info表
                cursor.execute("SELECT interface_positions FROM locked_carrier_info")
                locked_records = cursor.fetchall()
                
                # 提取所有锁定的接口位置
                locked_positions = []
                for record in locked_records:
                    # 从interface_positions中提取数字部分，如"IP0" -> 0
                    try:
                        position_str = record[0]
                        if position_str.startswith('IP'):
                            position_idx = int(position_str[2:])
                            locked_positions.append(position_idx)
                    except (ValueError, IndexError) as e:
                        self.logger.warning(f"解析接口位置失败: {e}")
                
                # 初始化lock_ownership
                interface_count = self.interface_positions
                new_lock_ownership = []
                
                for i in range(interface_count):
                    if i in locked_positions:
                        new_lock_ownership.append(1)
                    else:
                        new_lock_ownership.append(2)
                
                self.lock_ownership = new_lock_ownership
                self.logger.info(f"初始化lock_ownership完成: {self.lock_ownership}")
                
            except Exception as e:
                self.logger.warning(f"初始化lock_ownership失败: {e}，使用默认值")
                # 保持默认值不变
            
            # 关闭连接
            conn.close()
            
            self.logger.info("从数据库初始化样本数据完成")
            
        except sqlite3.Error as e:
            self.logger.error(f"数据库初始化错误: {str(e)}")
            # 确保变量初始化为默认值
            self.on_board_tube_count = 0
            self.completed_tube_count = 0
        except Exception as e:
            self.logger.error(f"初始化过程中的意外错误: {str(e)}")
            # 确保变量初始化为默认值
            self.on_board_tube_count = 0
            self.completed_tube_count = 0
    
    def set_lis_client(self, lis_client):
        """设置LIS客户端实例
        
        Args:
            lis_client: LISClient实例
        """
        self.lis_client = lis_client
        self.logger.info("LIS client instance set in core")
    
    def set_las_server(self, las_server):
        """设置LAS服务器实例
        
        Args:
            las_server: LASServer实例
        """
        self.las_server = las_server
        self.logger.info("LAS server instance set in core")
    
    def _generate_results_loop(self):
        """结果生成循环，定期检查并生成样本结果"""
        while True:
            time.sleep(60)  # 每分钟检查一次
            current_time = time.time()
            
            with self.sample_lock:
                # 检查所有待生成结果的样本
                samples_to_process = []
                for sample_id, result_info in self.pending_results.items():
                    if current_time >= result_info['result_time']:
                        samples_to_process.append(sample_id)
                
                # 生成结果
                for sample_id in samples_to_process:
                    self._generate_sample_result(sample_id)
    
    def _generate_sample_result(self, sample_id):
        """生成样本结果
        
        Args:
            sample_id: 样本ID
        """
        with self.sample_lock:
            if sample_id not in self.pending_results:
                return
            
            sample_info = self.pending_results.pop(sample_id)
            sample = self.samples.get(sample_id)
            
            if not sample:
                return
            
        # 生成随机结果
        results = {}
        for test_code in sample['tests']:
            # 根据测试项目生成不同范围的随机结果
            if test_code.startswith('TEST'):
                # 模拟不同类型的测试结果
                if int(test_code[4:]) % 2 == 0:
                    # 整数结果
                    results[test_code] = {
                        'value': random.randint(10, 100),
                        'unit': 'mg/dL',
                        'flags': ''
                    }
                else:
                    # 小数结果
                    results[test_code] = {
                        'value': round(random.uniform(1.0, 10.0), 2),
                        'unit': 'mmol/L',
                        'flags': ''
                    }
            else:
                # 默认结果
                results[test_code] = {
                    'value': round(random.uniform(0.0, 100.0), 2),
                    'unit': 'U/L',
                    'flags': ''
                }
        
        # 更新样本状态
        with self.sample_lock:
            sample['status'] = 'completed'
            sample['results'] = results
            sample['completed_time'] = time.time()
            
            # 更新完成试管数量
            with self.status_lock:
                self.completed_tube_count += 1
        
        self.logger.info(f"Generated results for sample {sample_id}: {results}")
        
        # 通知LIS模块发送结果
        # 通过回调机制实现，由LIS模块注册回调函数
        if hasattr(self, 'result_callback') and callable(self.result_callback):
            try:
                self.result_callback(sample_id, results)
            except Exception as e:
                self.logger.error(f"Error calling result callback: {str(e)}")
    
    def register_result_callback(self, callback):
        """注册结果生成回调函数
        
        Args:
            callback: 回调函数，接受sample_id和results作为参数
        """
        self.result_callback = callback
    
    def receive_sample(self, sample_id, tests, patient_info=None):
        """接收样本
        
        Args:
            sample_id: 样本ID
            tests: 测试项目列表
            patient_info: 患者信息（可选）
            
        Returns:
            bool: 是否成功接收
        """
        self.logger.info(f"receive_sample called: sample_id={sample_id}, tests={tests}")
        
        with self.sample_lock:
            if sample_id in self.samples:
                self.logger.warning(f"Sample {sample_id} already exists")
                return False
            
            # 检查测试项目是否存在
            with self.inventory_lock:
                valid_tests = []
                self.logger.debug(f"Checking tests against inventory: {self.test_inventory.get('tests', [])}")
                for test_code in tests:
                    test_exists = any(test['name'] == test_code for test in self.test_inventory['tests'])
                    self.logger.debug(f"Test {test_code} exists: {test_exists}")
                    if test_exists:
                        valid_tests.append(test_code)
                    else:
                        self.logger.warning(f"Test {test_code} not found in inventory")
            
            if not valid_tests:
                self.logger.error(f"No valid tests for sample {sample_id}")
                return False
            
            # 创建样本记录
            sample = {
                'sample_id': sample_id,
                'tests': valid_tests,
                'patient_info': patient_info or {},
                'received_time': time.time(),
                'status': 'received',
                'results': None,
                'completed_time': None
            }
            
            self.samples[sample_id] = sample
            
            # 计算结果生成时间（5分钟后）
            result_delay = self.config_manager.get_lis_config().get('result_delay', 300)
            result_time = time.time() + result_delay
            
            self.pending_results[sample_id] = {
                'result_time': result_time,
                'sample_info': sample
            }
            
        self.logger.info(f"Received sample {sample_id} with tests {valid_tests}, results will be available at {time.ctime(result_time)}")
        return True
    
    def get_sample_info(self, sample_id):
        """获取样本信息
        
        Args:
            sample_id: 样本ID
            
        Returns:
            dict: 样本信息，不存在则返回None
        """
        with self.sample_lock:
            return self.samples.get(sample_id)
    
    def manual_eject_sample(self, sample_id):
        """手动弹出样本 - 标本已离开ATS，且不在LAS上
        
        Args:
            sample_id: 要弹出的样本ID
            
        Returns:
            bool: 是否成功弹出
        """
        with self.sample_lock:
            if sample_id not in self.samples:
                return False
            
            sample = self.samples[sample_id]
            
            # 检查样本状态
            if sample['status'] == 'unloaded':
                return False
            
            with self.status_lock:
                # 减少在管计数
                self.on_board_tube_count -= 1
                
                # 根据样本状态减少相应计数器
                if sample['statusII'] == 'completed':
                    self.completed_tube_count -= 1
                
                if sample.get('ready_for_unload', False):
                    self.return_ready_count -= 1
            
            # 从self.samples列表中移除样本
            del self.samples[sample_id]
            
            # 从数据库中删除样本记录
            self._delete_sample_from_db(sample_id)
            
            return True
    
    def get_all_samples(self):
        """获取所有样本信息（从内存中的self.samples返回）

        Returns:
            dict: 所有样本信息
        """
        with self.sample_lock:
            return self.samples.copy()
    
    def update_automation_interface_status(self, status):
        """更新自动化接口状态
        
        Args:
            status: 状态值（1: Green, 3: Red，4: Critical）
        """
        with self.status_lock:
            if self.automation_interface_status == status:
                return
            self.automation_interface_status = status
            self.logger.info(f"Updated automation interface status to {status}")
        
        # 调用LAS服务器的send_instrument_health_response方法
        if hasattr(self, 'las_server') and self.las_server:
            self.las_server.send_instrument_health_response()
    
    def update_instrument_process_status(self, status):
        """更新仪器处理状态
        
        Args:
            status: 状态值（1: Green, 2: Yellow, 3: Red）
        """
        with self.status_lock:
            if self.instrument_process_status == status:
                return
            self.instrument_process_status = status
            self.logger.info(f"Updated instrument process status to {status}")
    
    def update_lis_connection_status(self, status):
        """更新LIS连接状态
        
        Args:
            status: 状态值（1: Connected, 2: Disconnected）
        """
        with self.status_lock:
            if self.lis_connection_status == status:
                return
            self.lis_connection_status = status
            self.logger.info(f"Updated LIS connection status to {status}")

        # 调用LAS服务器的send_instrument_health_response方法
        if hasattr(self, 'las_server') and self.las_server:
            self.las_server.send_instrument_health_response()
    
    def update_remote_control_status(self, ip_index, status):
        """更新远程控制状态
        
        Args:
            ip_index: 接口位置索引（0或1）
            status: 状态值
        """
        with self.status_lock:
            if 0 <= ip_index < len(self.remote_control_status):
                if self.remote_control_status[ip_index] == status:
                    return
                self.remote_control_status[ip_index] = status
                self.logger.info(f"Updated remote control status for IP{ip_index} to {status}")

        # 调用LAS服务器的send_instrument_health_response方法
        if hasattr(self, 'las_server') and self.las_server:
            self.las_server.send_instrument_health_response()
    
    def update_lock_ownership(self, ip_index, ownership):
        """更新锁所有权
        
        Args:
            ip_index: 接口位置索引（0或1）
            ownership: 所有权值（1: Locked by Instrument, 2: Not Locked by Instrument）
        """
        with self.status_lock:
            if 0 <= ip_index < len(self.lock_ownership):
                self.lock_ownership[ip_index] = ownership
                self.logger.info(f"Updated lock ownership for IP{ip_index} to {ownership}")
    
    def get_load_unload_command_status(self, interface_positions):
        """获取装载/卸载命令状态
        
        Args:
            interface_positions: 接口位置（0或1）
            
        Returns:
            int: 命令状态码（1、2、3或5）
        """
        with self.status_lock:
            if self.automation_interface_status == 4:
                return 2
            elif self.automation_interface_status == 3:
                return 3
            elif self.remote_control_status[interface_positions] == 1:
                return 5
            else:
                return 1
    
    def get_instrument_health(self):
        """获取仪器健康状态
        
        Returns:
            dict: 仪器健康状态
        """
        with self.status_lock:
            return {
                'automation_interface_status': self.automation_interface_status,
                'instrument_process_status': self.instrument_process_status,
                'lis_connection_status': self.lis_connection_status,
                'interface_positions': self.interface_positions,
                'remote_control_status': self.remote_control_status.copy(),
                'lock_ownership': self.lock_ownership.copy(),
                'processing_backlog': self.processing_backlog,
                'sample_acquisition_delay': self.sample_acquisition_delay,
                'on_board_tube_count': self.on_board_tube_count,
                'completed_tube_count': self.completed_tube_count
            }
    
    def update_test_inventory(self, test_name, count=None, status=None):
        """更新测试项目库存
        
        Args:
            test_name: 测试项目名称
            count: 可用测试数量（可选）
            status: 状态（可选）
            
        Returns:
            bool: 是否成功更新
        """
        with self.inventory_lock:
            for test in self.test_inventory['tests']:
                if test['name'] == test_name:
                    if count is not None:
                        test['count'] = count
                        # 根据数量自动更新状态
                        threshold = self.test_inventory['threshold']
                        if count == 0:
                            test['status'] = 3  # Red
                        elif count < threshold:
                            test['status'] = 2  # Yellow
                        else:
                            test['status'] = 1  # Green
                    
                    if status is not None:
                        test['status'] = status
                    
                    self.logger.info(f"Updated test inventory: {test_name} - count: {test['count']}, status: {test['status']}")
                    return True
            
            self.logger.error(f"Test {test_name} not found in inventory")
            return False
    
    def add_test_inventory(self, test_name, count, status):
        """添加测试项目库存
        
        Args:
            test_name: 测试项目名称
            count: 可用测试数量
            status: 状态（1: Green, 2: Yellow, 3: Red）
            
        Returns:
            bool: 是否成功添加
        """
        with self.inventory_lock:
            for test in self.test_inventory['tests']:
                if test['name'] == test_name:
                    self.logger.error(f"Test {test_name} already exists in inventory")
                    return False
            
            new_test = {
                'name': test_name,
                'count': count,
                'status': status
            }
            self.test_inventory['tests'].append(new_test)
            self.logger.info(f"Added test inventory: {test_name} - count: {count}, status: {status}")
            return True
    
    def delete_test_inventory(self, test_name):
        """删除测试项目库存
        
        Args:
            test_name: 测试项目名称
            
        Returns:
            bool: 是否成功删除
        """
        with self.inventory_lock:
            for i, test in enumerate(self.test_inventory['tests']):
                if test['name'] == test_name:
                    del self.test_inventory['tests'][i]
                    self.logger.info(f"Deleted test inventory: {test_name}")
                    return True
            
            self.logger.error(f"Test {test_name} not found in inventory")
            return False
    
    def get_test_inventory(self):
        """获取测试项目库存
        
        Returns:
            dict: 测试项目库存
        """
        with self.inventory_lock:
            return self.test_inventory.copy()
    
    def update_consumable_inventory(self, module_id, consumable_id, status):
        """更新耗材库存
        
        Args:
            module_id: 模块ID
            consumable_id: 耗材ID
            status: 状态（1: Green, 2: Yellow, 3: Red）
            
        Returns:
            bool: 是否成功更新
        """
        with self.inventory_lock:
            for module in self.consumable_inventory['modules']:
                if module['id'] == module_id:
                    for consumable in module['consumables']:
                        if consumable['id'] == consumable_id:
                            consumable['status'] = status
                            self.logger.info(f"Updated consumable inventory: Module {module_id}, Consumable {consumable_id} - status: {status}")
                            return True
                    break
            
            self.logger.error(f"Consumable {consumable_id} not found in module {module_id}")
            return False
    
    def add_consumable_inventory(self, module_id, consumable_id, status):
        """添加耗材库存
        
        Args:
            module_id: 模块ID
            consumable_id: 耗材ID
            status: 状态（1: Green, 2: Yellow, 3: Red）
            
        Returns:
            bool: 是否成功添加
        """
        with self.inventory_lock:
            for module in self.consumable_inventory['modules']:
                if module['id'] == module_id:
                    for cons in module['consumables']:
                        if cons['id'] == consumable_id:
                            self.logger.error(f"Consumable {consumable_id} already exists in module {module_id}")
                            return False
                    
                    new_consumable = {
                        'id': consumable_id,
                        'status': status
                    }
                    module['consumables'].append(new_consumable)
                    self.logger.info(f"Added consumable inventory: Module {module_id}, Consumable {consumable_id} - status: {status}")
                    return True
            
            new_module = {
                'id': module_id,
                'consumables': [{'id': consumable_id, 'status': status}]
            }
            self.consumable_inventory['modules'].append(new_module)
            self.logger.info(f"Added new module with consumable: Module {module_id}, Consumable {consumable_id} - status: {status}")
            return True
    
    def delete_consumable_inventory(self, module_id, consumable_id):
        """删除耗材库存
        
        Args:
            module_id: 模块ID
            consumable_id: 耗材ID
            
        Returns:
            bool: 是否成功删除
        """
        with self.inventory_lock:
            for i, module in enumerate(self.consumable_inventory['modules']):
                if module['id'] == module_id:
                    for j, cons in enumerate(module['consumables']):
                        if cons['id'] == consumable_id:
                            del module['consumables'][j]
                            self.logger.info(f"Deleted consumable: Module {module_id}, Consumable {consumable_id}")
                            
                            if len(module['consumables']) == 0:
                                del self.consumable_inventory['modules'][i]
                                self.logger.info(f"Deleted empty module: {module_id}")
                            return True
            
            self.logger.error(f"Consumable {consumable_id} not found in module {module_id}")
            return False
    
    def get_consumable_inventory(self):
        """获取耗材库存
        
        Returns:
            dict: 耗材库存
        """
        with self.inventory_lock:
            return self.consumable_inventory.copy()
    
    def get_status_summary(self):
        """获取状态摘要
        
        Returns:
            dict: 状态摘要
        """
        with self.status_lock:
            return {
                'automation_interface_status': self.automation_interface_status,
                'instrument_process_status': self.instrument_process_status,
                'lis_connection_status': self.lis_connection_status,
                'on_board_tube_count': self.on_board_tube_count,
                'completed_tube_count': self.completed_tube_count
            }
    
    def add_to_queue(self, interface_position_index, carrier_occupancy, sample_id, sample_priority, tube_height, tube_diameter):
        """添加样本到队列
        
        Args:
            interface_position_index: 接口位置索引
            carrier_occupancy: carrier占用类型
            sample_id: 样本ID
            sample_priority: 样本优先级
            tube_height: 试管高度
            tube_diameter: 试管直径
            
        Returns:
            bool: 是否成功添加
        """
        with self.sample_lock:
            if interface_position_index not in self.queues:
                return False
            
            carrier_info = {
                'carrier_occupancy': carrier_occupancy,
                'sample_id': sample_id,
                'sample_priority': sample_priority,
                'tube_height': tube_height,
                'tube_diameter': tube_diameter
            }
            
            self.queues[interface_position_index].append(carrier_info)
            
            self.logger.info(f"Added to queue IP{interface_position_index}: SampleID={sample_id}, Occupancy={carrier_occupancy}")
            return True
    
    def skip_from_queue(self, interface_position_index, carrier_occupancy, sample_id, in_queue):
        """从队列中跳过样本
        
        Args:
            interface_position_index: 接口位置索引
            carrier_occupancy: carrier占用类型
            sample_id: 样本ID
            in_queue: 是否在队列中
            
        Returns:
            bool: 是否成功跳过
        """
        with self.sample_lock:
            if interface_position_index not in self.queues:
                return False
            
            # 查找匹配的carrier并移除
            for i, carrier in enumerate(self.queues[interface_position_index]):
                if (carrier['sample_id'] == sample_id and 
                    carrier['carrier_occupancy'] == carrier_occupancy):
                    self.queues[interface_position_index].pop(i)
                    self.logger.info(f"Skipped from queue IP{interface_position_index}: SampleID={sample_id}")
                    return True
            
            return False
    
    def clear_queue(self, interface_position_index):
        """清除队列
        
        Args:
            interface_position_index: 接口位置索引
            
        Returns:
            bool: 是否成功清除
        """
        with self.sample_lock:
            if interface_position_index not in self.queues:
                return False
            
            # 不清除锁定的carrier
            if self.locked_carriers[interface_position_index] is not None:
                self.logger.warning(f"Cannot clear queue IP{interface_position_index}: carrier is locked")
                return False
            
            count = len(self.queues[interface_position_index])
            self.queues[interface_position_index] = []
            
            self.logger.info(f"Cleared queue IP{interface_position_index}: {count} carriers removed")
            return True
    
    def get_queue_info(self, interface_position_index):
        """获取队列信息
        
        Args:
            interface_position_index: 接口位置索引
            
        Returns:
            list: 队列中的carrier列表
        """
        with self.sample_lock:
            return self.queues.get(interface_position_index, []).copy()
    
    def get_ready_to_load(self, interface_position_index=None):
        """获取就绪装载状态
        
        Args:
            interface_position_index: 接口位置索引（可选），0=IP0, 1=IP1
            
        Returns:
            int: 0=未就绪, 1=就绪
        """
        with self.sample_lock:
            if interface_position_index is not None:
                # 根据接口位置索引返回对应预设值
                if interface_position_index == 0:
                    return 1 if self.ready_to_load[0] else 0
                elif interface_position_index == 1:
                    return 1 if self.ready_to_load[1] else 0
                else:
                    return 0  # 无效索引返回未就绪
            else:
                # 保持向后兼容，返回整体就绪状态
                return 1 if any(self.ready_to_load.values()) else 0
    
    def get_return_ready_count(self):
        """获取可返回样本数量
        
        Returns:
            int: 可返回样本数量
        """
        with self.sample_lock:
            return self.return_ready_count
    
    def get_next_sample_to_unload(self):
        """获取下一个要卸载的样本
        
        Returns:
            str: 样本ID，如果没有则返回空字符串
        """
        with self.sample_lock:
            if self.return_ready_count > 0:
                # 查找已完成且准备好UNLOAD的样本
                for sid, sample in self.samples.items():
                    if sample['status'] == 'completed' and 'unloaded' not in sample and sample.get('ready_for_unload', False):
                        return sid
            return ""
    
    def _process_sample_workflow_loop(self):
        """样本工作流处理循环 - 单个线程处理所有样本的工作流
        
        从队列中获取样本ID，依次处理每个样本的工作流
        避免为每个样本创建单独的线程
        """
        self.logger.info("样本工作流处理线程已启动")
        
        while True:
            try:
                # 等待队列中有样本
                self.sample_workflow_event.wait(timeout=1.0)
                
                with self.sample_workflow_lock:
                    if not self.sample_workflow_queue:
                        self.sample_workflow_event.clear()
                        continue
                    # 获取队列中的第一个样本
                    sample_id = self.sample_workflow_queue.pop(0)
                
                # 处理样本工作流
                self.logger.info(f"工作流线程开始处理样本: {sample_id}")
                self._process_sample_workflow(sample_id)
                
            except Exception as e:
                self.logger.error(f"样本工作流处理循环出错: {str(e)}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _add_sample_to_workflow_queue(self, sample_id):
        """将样本添加到工作流队列
        
        Args:
            sample_id: 样本ID
        """
        with self.sample_workflow_lock:
            # 检查样本是否已在队列中
            if sample_id not in self.sample_workflow_queue:
                self.sample_workflow_queue.append(sample_id)
                self.sample_workflow_event.set()
                self.logger.info(f"样本 {sample_id} 已添加到工作流队列，当前队列长度: {len(self.sample_workflow_queue)}")
            else:
                self.logger.warning(f"样本 {sample_id} 已在工作流队列中，跳过")
    
    def _schedule_workflow_step(self, sample_id, step_name, delay_seconds, step_func):
        """调度工作流步骤 - 使用定时器替代time.sleep
        
        Args:
            sample_id: 样本ID
            step_name: 步骤名称
            delay_seconds: 延迟秒数
            step_func: 步骤执行函数
        """
        def timer_callback():
            try:
                # 清除定时器记录
                with self.sample_timers_lock:
                    if sample_id in self.sample_timers and step_name in self.sample_timers[sample_id]:
                        del self.sample_timers[sample_id][step_name]
                # 执行步骤
                step_func()
            except Exception as e:
                self.logger.error(f"Sample {sample_id}: 工作流步骤 {step_name} 执行出错: {str(e)}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # 创建定时器
        timer = threading.Timer(delay_seconds, timer_callback)
        timer.daemon = True
        
        # 记录定时器
        with self.sample_timers_lock:
            if sample_id not in self.sample_timers:
                self.sample_timers[sample_id] = {}
            self.sample_timers[sample_id][step_name] = timer
        
        # 启动定时器
        timer.start()
        self.logger.info(f"Sample {sample_id}: 已调度工作流步骤 {step_name}，延迟 {delay_seconds} 秒")
    
    def _cancel_sample_timers(self, sample_id):
        """取消样本的所有定时器
        
        Args:
            sample_id: 样本ID
        """
        with self.sample_timers_lock:
            if sample_id in self.sample_timers:
                for step_name, timer in self.sample_timers[sample_id].items():
                    timer.cancel()
                    self.logger.info(f"Sample {sample_id}: 已取消工作流步骤 {step_name} 的定时器")
                del self.sample_timers[sample_id]
    
    def _workflow_step_lis_query(self, sample_id):
        """工作流步骤1: 询问LIS工单
        
        Args:
            sample_id: 样本ID
        """
        try:
            self.logger.info(f"Sample {sample_id}: 开始执行LIS工单查询步骤")
            
            with self.sample_lock:
                if sample_id not in self.samples:
                    self.logger.warning(f"Sample {sample_id}: 样本不存在，跳过LIS查询")
                    return
                
                selected_tests = []
                
                # 检查是否有LIS客户端实例
                if hasattr(self, 'lis_client') and self.lis_client:
                    # 调用LIS客户端的query_worklist方法查询工单
                    self.logger.info(f"Sample {sample_id}: 使用真实ASTM协议询问LIS工单")
                    
                    # 调用get_apply方法获取测试订单
                    selected_tests = self.lis_client.get_apply(sample_id)
                    
                    if selected_tests:
                        self.logger.info(f"Sample {sample_id}: 收到LIS真实工单，测试项目: {selected_tests}")
                    else:
                        self.logger.warning(f"Sample {sample_id}: 未收到LIS工单，使用模拟数据")
                        # 使用模拟数据 - test_inventory['tests']是列表，不是字典
                        test_items = [test['name'] for test in self.test_inventory['tests']][:10]
                        selected_tests = random.sample(test_items, min(random.randint(3, 5), len(test_items)))
                else:
                    # 没有LIS客户端实例，使用模拟数据
                    self.logger.info(f"Sample {sample_id}: 没有LIS客户端实例，使用模拟工单")
                    # test_inventory['tests']是列表，不是字典
                    test_items = [test['name'] for test in self.test_inventory['tests']][:10]
                    selected_tests = random.sample(test_items, min(random.randint(3, 5), len(test_items)))
                
                # 检查测试项目是否可以开展
                valid_tests = []
                invalid_tests = []
                
                # 将test_inventory['tests']列表转换为字典，便于查找
                test_inventory_dict = {test['name']: test for test in self.test_inventory['tests']}
                
                for test in selected_tests:
                    # 检查项目是否定义
                    test_info = test_inventory_dict.get(test)
                    if not test_info:
                        invalid_tests.append((test, '未定义的测试项目'))
                        continue
                    
                    # 检查试剂是否充足
                    if test_info['count'] <= 0:
                        invalid_tests.append((test, '试剂不足'))
                        continue
                    
                    # 检查项目状态
                    if test_info['status'] != 1:  # 状态不是Green
                        invalid_tests.append((test, '项目状态异常'))
                        continue
                    
                    # 项目可以开展
                    valid_tests.append(test)
                
                # 更新样本的测试项目
                self.samples[sample_id]['tests'] = valid_tests
                self.samples[sample_id]['invalid_tests'] = invalid_tests
                self.samples[sample_id]['lis_asked'] = True
                
                if valid_tests:
                    self.logger.info(f"Sample {sample_id}: 有效测试项目: {valid_tests}")
                
                if invalid_tests:
                    self.logger.warning(f"Sample {sample_id}: 无效测试项目: {invalid_tests}")
                    
                    # 对于无效项目，立即生成ERROR结果
                    error_results = {}
                    for test, reason in invalid_tests:
                        error_results[test] = {
                            'value': 'ERROR',
                            'status': 'error',
                            'timestamp': time.time(),
                            'error_reason': reason,
                            'unit': '',
                            'flags': 'E'
                        }
                    
                    # 更新样本结果
                    self.samples[sample_id]['results'] = error_results
                    self.samples[sample_id]['status'] = 'completed'
                    
                    # 标记样本为已完成
                    self.samples[sample_id]['completed_time'] = time.time()
                    
                    # 通知LIS结果已生成
                    if hasattr(self, 'result_callback') and callable(self.result_callback):
                        try:
                            self.result_callback(sample_id, error_results)
                            self.logger.info(f"Sample {sample_id}: 已发送无效项目的ERROR结果给LIS")
                        except Exception as e:
                            self.logger.error(f"Error calling result callback: {str(e)}")
                
                # 记录最终的测试项目
                self.logger.info(f"Sample {sample_id}: 最终测试项目: {valid_tests}")
                
                # 保存valid_tests和invalid_tests供下一步使用
                has_valid_tests = len(valid_tests) > 0
            
            # 可选：如果有有效测试项目，异步生成结果（不影响UNLOAD流程）
            # 注意：准备UNLOAD步骤已在 _process_sample_workflow 中调度（3分钟后）
            if has_valid_tests:
                self._schedule_workflow_step(
                    sample_id,
                    'generate_results',
                    120,  # 2分钟后生成结果（在UNLOAD之后）
                    lambda: self._workflow_step_generate_results(sample_id, valid_tests, invalid_tests)
                )
                
        except Exception as e:
            self.logger.error(f"Sample {sample_id}: LIS查询步骤出错: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _workflow_step_generate_results(self, sample_id, valid_tests, invalid_tests):
        """工作流步骤2: 生成测试结果
        
        Args:
            sample_id: 样本ID
            valid_tests: 有效测试项目列表
            invalid_tests: 无效测试项目列表
        """
        try:
            self.logger.info(f"Sample {sample_id}: 开始执行结果生成步骤")
            
            with self.sample_lock:
                if sample_id not in self.samples:
                    self.logger.warning(f"Sample {sample_id}: 样本不存在，跳过结果生成")
                    return
                
                # 生成随机测试结果
                results = {}
                
                # 使用之前创建的字典来查找测试项目信息
                for test in valid_tests:
                    # 为每个测试项目生成随机结果
                    test_info = test_inventory_dict.get(test, {})
                    results[test] = {
                        'value': round(random.uniform(10, 100), 2),
                        'status': 'completed',
                        'timestamp': time.time(),
                        'unit': test_info.get('unit', ''),
                        'flags': ''
                    }
                
                # 更新样本结果，合并之前的ERROR结果
                if invalid_tests:
                    # 如果之前有无效项目的ERROR结果，合并它们
                    existing_results = self.samples[sample_id].get('results', {})
                    results.update(existing_results)
                    self.samples[sample_id]['status'] = 'completed'
                else:
                    self.samples[sample_id]['status'] = 'completed'
                
                self.samples[sample_id]['results'] = results
                
                # 注意：completed_tube_count 和 return_ready_count 已在 _workflow_step_ready_for_unload 中增加
                # 这里不再重复增加，只更新样本状态和结果
                
                # 标记样本为已完成
                self.samples[sample_id]['completed_time'] = time.time()
                
                self.logger.info(f"Sample {sample_id}: 生成测试结果成功，结果: {results}")
                
                # 通知LIS结果已生成
                if hasattr(self, 'lis_client') and self.lis_client:
                    try:
                        # 从results中提取测试项目列表
                        test_items = list(results.keys())
                        success, message = self.lis_client.send_result(sample_id, test_items)
                        self.logger.info(f"Sample {sample_id}: 已发送有效项目的结果给LIS, 状态: {success}, 消息: {message}")
                    except Exception as e:
                        self.logger.error(f"Error sending result to LIS: {str(e)}")
            
            # 结果生成完成，清理定时器记录
            with self.sample_timers_lock:
                if sample_id in self.sample_timers:
                    del self.sample_timers[sample_id]
                    
        except Exception as e:
            self.logger.error(f"Sample {sample_id}: 结果生成步骤出错: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _workflow_step_ready_for_unload(self, sample_id):
        """工作流步骤: 准备UNLOAD
        
        根据协议，LOAD之后3分钟即可准备UNLOAD，不依赖于LIS问询状态和结果。
        
        Args:
            sample_id: 样本ID
        """
        try:
            self.logger.info(f"Sample {sample_id}: 开始执行准备UNLOAD步骤（LOAD后3分钟）")
            
            with self.sample_lock:
                if sample_id not in self.samples:
                    self.logger.warning(f"Sample {sample_id}: 样本不存在，跳过准备UNLOAD")
                    return
                
                # 更新样本状态为准备UNLOAD
                self.samples[sample_id]['ready_for_unload'] = True
                
                # 增加已完成试管数量和可返回样本数量
                # 注意：这里假设样本在3分钟后即视为完成，不等待实际结果生成
                self.completed_tube_count += 1
                self.return_ready_count += 1
                
                self.logger.info(f"Sample {sample_id}: 已准备好UNLOAD（不依赖LIS结果），completed_tube_count={self.completed_tube_count}, return_ready_count={self.return_ready_count}")
            
            # 发送Transfer Status Response通知LAS
            if hasattr(self, 'las_server') and self.las_server:
                try:
                    # 发送IP0的状态
                    self.las_server.send_transfer_status_response(
                        interface_position_index=0,
                        ready_to_load=self.get_ready_to_load(0),
                        return_ready_count=self.return_ready_count
                    )
                    # 发送IP1的状态
                    self.las_server.send_transfer_status_response(
                        interface_position_index=1,
                        ready_to_load=self.get_ready_to_load(1),
                        return_ready_count=self.return_ready_count
                    )
                    self.logger.info(f"Sample {sample_id}: 已发送Transfer Status Response，return_ready_count={self.return_ready_count}")
                except Exception as e:
                    self.logger.error(f"Sample {sample_id}: 发送Transfer Status Response失败: {str(e)}")
            
            # 注意：不清理定时器记录，因为结果生成可能还在进行中
            # 结果生成步骤会自己清理定时器
                    
        except Exception as e:
            self.logger.error(f"Sample {sample_id}: 准备UNLOAD步骤出错: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _process_sample_workflow(self, sample_id):
        """处理标本完整工作流 - 使用定时器调度，避免阻塞线程
        
        流程（根据协议，UNLOAD不依赖于LIS结果）：
        1. 标本LOAD后5秒，询问LIS工单（可选，异步执行，失败不影响后续步骤）
        2. 标本LOAD后1分钟，准备UNLOAD（必须执行，不依赖LIS结果）
        3. 标本LOAD后2分钟，生成测试结果（可选，异步执行）
        
        Args:
            sample_id: 样本ID
        """
        try:
            self.logger.info(f"Sample {sample_id}: 开始工作流处理（使用定时器调度，UNLOAD不依赖LIS结果）")
            
            # 步骤1: 调度5秒后询问LIS工单（可选，失败不影响UNLOAD）
            self._schedule_workflow_step(
                sample_id, 
                'lis_query', 
                5, 
                lambda: self._workflow_step_lis_query(sample_id)
            )
            
            # 步骤2: 调度1分钟后准备UNLOAD（必须执行，独立于LIS查询）
            # 无论LIS查询成功或失败，1分钟后都必须准备UNLOAD
            self._schedule_workflow_step(
                sample_id,
                'ready_for_unload',
                60,  # 1分钟 = 60秒
                lambda: self._workflow_step_ready_for_unload(sample_id)
            )
            
        except Exception as e:
            self.logger.error(f"Error processing sample workflow for {sample_id}: {str(e)}")
    
    def _get_db_connection(self):
        """获取数据库连接
        
        Returns:
            sqlite3.Connection: 数据库连接对象
        """
        db_dir = 'data'
        db_path = os.path.join(db_dir, 'atellica.db')
        return sqlite3.connect(db_path)
    
    def _insert_sample_to_db(self, sample_id, load_time):
        """将样本插入数据库
        
        Args:
            sample_id: 样本ID
            load_time: 装载时间
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 转换load_time为ISO格式
            load_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(load_time))
            
            # 插入样本记录
            cursor.execute('''
                INSERT OR REPLACE INTO on_board_samples 
                (sample_id, load_time)
                VALUES (?, ?)
            ''', (sample_id, load_time_str))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Inserted sample {sample_id} into database")
            
        except sqlite3.Error as e:
            self.logger.error(f"Error inserting sample {sample_id} into database: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error inserting sample {sample_id} into database: {str(e)}")
    
    def _delete_sample_from_db(self, sample_id):
        """从数据库中删除样本
        
        Args:
            sample_id: 样本ID
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 删除样本记录
            cursor.execute('''
                DELETE FROM on_board_samples WHERE sample_id = ?
            ''', (sample_id,))
            
            if cursor.rowcount > 0:
                self.logger.info(f"Deleted sample {sample_id} from database")
            
            conn.commit()
            conn.close()
            
        except sqlite3.Error as e:
            self.logger.error(f"Error deleting sample {sample_id} from database: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error deleting sample {sample_id} from database: {str(e)}")
    
    def _save_locked_carrier(self, interface_positions, sample_id, carrier_occupancy):
        """持久化存储锁定状态到数据库
        
        Args:
            interface_positions: 接口位置，格式为"IP0/IP1"
            sample_id: 样本ID
            carrier_occupancy: carrier状态
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 检查记录是否存在
            cursor.execute('SELECT interface_positions FROM locked_carrier_info WHERE interface_positions = ?', (interface_positions,))
            existing_record = cursor.fetchone()
            
            if existing_record:
                # 记录存在，执行更新操作
                cursor.execute('''
                    UPDATE locked_carrier_info 
                    SET sample_id = ?, carrier_occupancy = ? 
                    WHERE interface_positions = ?
                ''', (sample_id, carrier_occupancy, interface_positions))
            else:
                # 记录不存在，执行插入操作
                cursor.execute('''
                    INSERT INTO locked_carrier_info (interface_positions, sample_id, carrier_occupancy)
                    VALUES (?, ?, ?)
                ''', (interface_positions, sample_id, carrier_occupancy))
            
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            self.logger.error(f"Error saving locked carrier to database: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error saving locked carrier to database: {str(e)}")
    
    def _delete_locked_carrier(self, interface_positions):
        """从数据库中删除锁定状态记录
        
        Args:
            interface_positions: 接口位置，格式为"IP0/IP1"
        """
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 基于主键执行删除操作
            cursor.execute('DELETE FROM locked_carrier_info WHERE interface_positions = ?', (interface_positions,))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            self.logger.error(f"Error deleting locked carrier from database: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error deleting locked carrier from database: {str(e)}")
    
    def process_load_unload(self, interface_position_index, carrier_occupancy, sample_id, tube_height, tube_diameter, elapsed_time):
        """处理装载/卸载请求
        
        Args:
            interface_position_index: 接口位置索引
            carrier_occupancy: carrier占用类型
            sample_id: 样本ID
            tube_height: 试管高度
            tube_diameter: 试管直径
            elapsed_time: 经过时间
            
        Returns:
            tuple: (load_result, unload_result, sample_status, onboard_count, completed_count, ready_to_load, return_ready_count)
        """
        with self.sample_lock:
            # 初始化结果
            load_result = None
            unload_result = None
            sample_status = 0x00  # No Tube Unloaded
            
            # 检查接口位置状态
            health_status = self.get_instrument_health()
            if interface_position_index >= health_status['interface_positions']:
                # 接口位置不存在
                load_result = {'sample_id': '', 'status': 5}  # Interface position is offline
                return load_result, unload_result, sample_status, self.on_board_tube_count, self.completed_tube_count, self.get_ready_to_load(interface_position_index), self.return_ready_count
            
            # 检查远程控制状态
            remote_status = health_status['remote_control_status'][interface_position_index]
            
            # 处理Load操作
            if carrier_occupancy in [2, 3]:  # 有样本
                if remote_status in [4, 3]:  # Loading Only or Exchange mode
                    # 执行装载操作
                    if self.locked_carriers[interface_position_index] is None:
                        # 锁定carrier
                        self.locked_carriers[interface_position_index] = {
                            'sample_id': sample_id,
                            'carrier_occupancy': carrier_occupancy
                        }
                        
                        # 持久化存储锁定状态到数据库
                        interface_positions = f"IP{interface_position_index}"
                        self._save_locked_carrier(interface_positions, sample_id, carrier_occupancy)
                        
                        # 从队列中获取并删除第一项数据
                        queue_sample_id = None
                        try:
                            if self.queues.get(interface_position_index):
                                # 取出队列第一项数据
                                queue_item = self.queues[interface_position_index].pop(0)
                                queue_sample_id = queue_item.get('sample_id')
                        except (IndexError, KeyError, AttributeError) as e:
                            self.logger.error(f"Error processing queue: {e}")
                            queue_sample_id = None
                        
                        # 检查样本是否存在
                        if sample_id in self.samples:
                            sample = self.samples[sample_id]
                            if sample['status'] == 'received':
                                sample['status'] = 'processing'
                                sample_status = 0x01  # Sample Processed successfully
                                
                                # 确定load_result['status']的值
                                load_result_status = self.get_load_unload_command_status(interface_position_index)
                                if queue_sample_id and queue_sample_id != sample_id:
                                    load_result_status = 4
                                
                                load_result = {'sample_id': sample_id, 'status': load_result_status}
                                
                                # 根据status执行相应操作
                                if load_result_status == 1:
                                    self.on_board_tube_count += 1
                                
                                # 将样本信息插入数据库
                                load_time = sample.get('load_time', time.time())
                                self._insert_sample_to_db(sample_id, load_time)
                            else:
                                load_result = {'sample_id': sample_id, 'status': 7}  # Instrument Skipped Loading
                                
                                # 确保其他状态值也有处理逻辑
                                if load_result['status'] == 7:
                                    self.logger.info(f"Instrument skipped loading for sample {sample_id}")
                        else:
                            # 样本不存在，创建新样本记录
                            current_time = time.time()
                            self.samples[sample_id] = {
                                'sample_id': sample_id,
                                'status': 'processing',
                                'tests': [],
                                'results': {},
                                'timestamp': current_time,
                                'load_time': current_time,
                                'interface_position': interface_position_index
                            }
                            
                            # 确定load_result['status']的值
                            load_result_status = self.get_load_unload_command_status(interface_position_index)
                            if queue_sample_id and queue_sample_id != sample_id:
                                load_result_status = 4
                            
                            load_result = {'sample_id': sample_id, 'status': load_result_status}
                            sample_status = 0x01  # Sample Processed successfully
                            
                            # 根据status执行相应操作
                            if load_result_status == 1:
                                self.on_board_tube_count += 1
                            
                            # 将样本信息插入数据库
                            self._insert_sample_to_db(sample_id, current_time)
                            
                            # 将样本添加到工作流队列（使用单个工作线程处理，避免创建大量线程）
                            self._add_sample_to_workflow_queue(sample_id)
                    else:
                        # carrier已被锁定
                        load_result = {'sample_id': sample_id, 'status': 2}  # Error: Lock Carrier in place
                else:
                    # 远程控制状态不允许装载
                    load_result = {'sample_id': sample_id, 'status': 6}  # Load Skipped
            else:
                # 空carrier
                load_result = {'sample_id': '', 'status': 1}  # Success
                
                # 处理Unload操作
                if remote_status in [5, 3]:  # Unloading Only or Exchange mode
                    # 执行卸载操作
                    if self.locked_carriers[interface_position_index] is None:
                        # 锁定carrier用于卸载
                        self.locked_carriers[interface_position_index] = {
                            'sample_id': '',
                            'carrier_occupancy': carrier_occupancy
                        }
                        
                        # 持久化存储锁定状态到数据库
                        interface_positions = f"IP{interface_position_index}"
                        self._save_locked_carrier(interface_positions, '', carrier_occupancy)
                        
                        # 检查是否有样本需要卸载到空carrier
                        if self.return_ready_count > 0:
                            # 优先使用传入的sample_id查找样本
                            if sample_id and sample_id in self.samples:
                                sample = self.samples[sample_id]
                                if sample['status'] == 'completed' and 'unloaded' not in sample and sample.get('ready_for_unload', False):
                                    # 确定unload_result['status']的值
                                    unload_result_status = self.get_load_unload_command_status(interface_position_index)
                                    
                                    # 标记样本为已卸载
                                    sample['unloaded'] = True
                                    sample_status = 0x01  # Sample Processed successfully
                                    
                                    unload_result = {'sample_id': sample_id, 'status': unload_result_status}
                                    
                                    # 根据status执行相应操作
                                    if unload_result_status in [1, 2, 3]:
                                        self.return_ready_count -= 1
                                        self.completed_tube_count -= 1
                                        self.on_board_tube_count -= 1
                                        
                                        # 从内存中删除样本信息
                                        if sample_id in self.samples:
                                            del self.samples[sample_id]
                                            self.logger.info(f"Sample {sample_id}: 已从内存中删除")
                                        
                                        # 从数据库中删除样本
                                        self._delete_sample_from_db(sample_id)
                                    
                                    self.logger.info(f"Sample {sample_id}: 已成功UNLOAD")
                                else:
                                    # 样本不存在或不符合条件，遍历查找
                                    for sid, sample in self.samples.items():
                                        if sample['status'] == 'completed' and 'unloaded' not in sample and sample.get('ready_for_unload', False):
                                            # 确定unload_result['status']的值
                                            unload_result_status = self.get_load_unload_command_status(interface_position_index)
                                            
                                            # 标记样本为已卸载
                                            sample['unloaded'] = True
                                            sample_status = 0x01  # Sample Processed successfully
                                            
                                            unload_result = {'sample_id': sid, 'status': unload_result_status}
                                            
                                            # 根据status执行相应操作
                                            if unload_result_status in [1, 2, 3]:
                                                self.return_ready_count -= 1
                                                self.completed_tube_count -= 1
                                                self.on_board_tube_count -= 1
                                                
                                                # 从内存中删除样本信息
                                                if sid in self.samples:
                                                    del self.samples[sid]
                                                    self.logger.info(f"Sample {sid}: 已从内存中删除")
                                                
                                                # 从数据库中删除样本
                                                self._delete_sample_from_db(sid)
                                            
                                            self.logger.info(f"Sample {sid}: 已成功UNLOAD")
                                            break
                            else:
                                # 没有传入sample_id或样本不存在，遍历查找
                                for sid, sample in self.samples.items():
                                    if sample['status'] == 'completed' and 'unloaded' not in sample and sample.get('ready_for_unload', False):
                                        # 确定unload_result['status']的值
                                        unload_result_status = self.get_load_unload_command_status(interface_position_index)
                                        
                                        # 标记样本为已卸载
                                        sample['unloaded'] = True
                                        sample_status = 0x01  # Sample Processed successfully
                                        
                                        unload_result = {'sample_id': sid, 'status': unload_result_status}
                                        
                                        # 根据status执行相应操作
                                        if unload_result_status in [1, 2, 3]:
                                            self.return_ready_count -= 1
                                            self.completed_tube_count -= 1
                                            self.on_board_tube_count -= 1
                                            
                                            # 从内存中删除样本信息
                                            if sid in self.samples:
                                                del self.samples[sid]
                                                self.logger.info(f"Sample {sid}: 已从内存中删除")
                                            
                                            # 从数据库中删除样本
                                            self._delete_sample_from_db(sid)
                                        
                                        self.logger.info(f"Sample {sid}: 已成功UNLOAD")
                                        break
                        else:
                            # 没有样本需要卸载
                            unload_result = {'sample_id': '', 'status': 6}  # Unload Skipped
                    else:
                        # carrier已被锁定
                        unload_result = {'sample_id': '', 'status': 2}  # Error: Lock Carrier in place
                else:
                    # 远程控制状态不允许卸载
                    unload_result = {'sample_id': '', 'status': 6}  # Unload Skipped
            
            # 释放锁定的carrier
            if self.locked_carriers[interface_position_index] is not None:
                # 从数据库中删除锁定状态记录
                interface_positions = f"IP{interface_position_index}"
                self._delete_locked_carrier(interface_positions)
                # 释放锁定
                self.locked_carriers[interface_position_index] = None
            
            # 在锁内部直接获取ready_to_load值，避免调用get_ready_to_load导致死锁
            ready_to_load_value = 1 if self.ready_to_load.get(interface_position_index, False) else 0
            
            return load_result, unload_result, sample_status, self.on_board_tube_count, self.completed_tube_count, ready_to_load_value, self.return_ready_count
