#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core模块 - 核心模拟逻辑
"""

import threading
import time
import random
from collections import defaultdict


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
        
        # 线程锁
        self.status_lock = threading.Lock()
        self.sample_lock = threading.Lock()
        self.inventory_lock = threading.Lock()
        
        # 结果生成线程
        self.result_thread = threading.Thread(target=self._generate_results_loop, daemon=True)
        self.result_thread.start()
        
        self.logger.info("AtellicaCore initialized successfully")
    
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
        with self.sample_lock:
            if sample_id in self.samples:
                self.logger.warning(f"Sample {sample_id} already exists")
                return False
            
            # 检查测试项目是否存在
            with self.inventory_lock:
                valid_tests = []
                for test_code in tests:
                    test_exists = any(test['name'] == test_code for test in self.test_inventory['tests'])
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
            
            # 更新在线试管数量
            with self.status_lock:
                self.on_board_tube_count += 1
            
            # 计算结果生成时间（30分钟后）
            result_delay = self.config_manager.get_lis_config().get('result_delay', 1800)
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
    
    def get_all_samples(self):
        """获取所有样本信息
        
        Returns:
            dict: 所有样本信息
        """
        with self.sample_lock:
            return self.samples.copy()
    
    def update_automation_interface_status(self, status):
        """更新自动化接口状态
        
        Args:
            status: 状态值（1: Green, 3: Red）
        """
        with self.status_lock:
            self.automation_interface_status = status
            self.logger.info(f"Updated automation interface status to {status}")
    
    def update_instrument_process_status(self, status):
        """更新仪器处理状态
        
        Args:
            status: 状态值（1: Green, 2: Yellow, 3: Red）
        """
        with self.status_lock:
            self.instrument_process_status = status
            self.logger.info(f"Updated instrument process status to {status}")
    
    def update_lis_connection_status(self, status):
        """更新LIS连接状态
        
        Args:
            status: 状态值（1: Connected, 2: Disconnected）
        """
        with self.status_lock:
            self.lis_connection_status = status
            self.logger.info(f"Updated LIS connection status to {status}")
    
    def update_remote_control_status(self, ip_index, status):
        """更新远程控制状态
        
        Args:
            ip_index: 接口位置索引（0或1）
            status: 状态值
        """
        with self.status_lock:
            if 0 <= ip_index < len(self.remote_control_status):
                self.remote_control_status[ip_index] = status
                self.logger.info(f"Updated remote control status for IP{ip_index} to {status}")
    
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
