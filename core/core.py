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
        
        # 队列管理
        self.queues = {
            0: [],  # IP0队列
            1: []   # IP1队列
        }
        self.locked_carriers = {
            0: None,  # IP0锁定的carrier
            1: None   # IP1锁定的carrier
        }
        self.ready_to_load = 0
        self.return_ready_count = 0
        
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
            
            # 更新就绪状态
            if carrier_occupancy in [2, 3]:  # 有样本的carrier
                self.ready_to_load = 1
            
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
    
    def get_ready_to_load(self):
        """获取就绪装载状态
        
        Returns:
            int: 0=未就绪, 1=就绪
        """
        with self.sample_lock:
            return self.ready_to_load
    
    def get_return_ready_count(self):
        """获取可返回样本数量
        
        Returns:
            int: 可返回样本数量
        """
        with self.sample_lock:
            return self.return_ready_count
    
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
                return load_result, unload_result, sample_status, self.on_board_tube_count, self.completed_tube_count, self.ready_to_load, self.return_ready_count
            
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
                        
                        # 更新在线试管数量
                        self.on_board_tube_count += 1
                        
                        # 检查样本是否存在
                        if sample_id in self.samples:
                            sample = self.samples[sample_id]
                            if sample['status'] == 'received':
                                sample['status'] = 'processing'
                                sample_status = 0x01  # Sample Processed successfully
                                load_result = {'sample_id': sample_id, 'status': 1}  # Success
                            else:
                                load_result = {'sample_id': sample_id, 'status': 7}  # Instrument Skipped Loading
                        else:
                            # 样本不存在，可能是新样本
                            load_result = {'sample_id': sample_id, 'status': 1}  # Success
                            sample_status = 0x14  # Sample not processed: No LIS orders
                    else:
                        # carrier已被锁定
                        load_result = {'sample_id': sample_id, 'status': 2}  # Error: Lock Carrier in place
                else:
                    # 远程控制状态不允许装载
                    load_result = {'sample_id': sample_id, 'status': 6}  # Load Skipped
            else:
                # 空carrier
                load_result = {'sample_id': '', 'status': 1}  # Success
                
                # 检查是否有样本需要卸载到空carrier
                if self.return_ready_count > 0:
                    # 查找已完成的样本
                    for sid, sample in self.samples.items():
                        if sample['status'] == 'completed' and 'unloaded' not in sample:
                            sample['unloaded'] = True
                            self.return_ready_count -= 1
                            self.completed_tube_count -= 1
                            unload_result = {'sample_id': sid, 'status': 1}  # Success
                            sample_status = 0x01  # Sample Processed successfully
                            break
            
            # 释放锁定的carrier
            if self.locked_carriers[interface_position_index] is not None:
                self.locked_carriers[interface_position_index] = None
            
            # 更新就绪状态
            if len(self.queues[interface_position_index]) > 0:
                self.ready_to_load = 1
            else:
                self.ready_to_load = 0
            
            return load_result, unload_result, sample_status, self.on_board_tube_count, self.completed_tube_count, self.ready_to_load, self.return_ready_count
