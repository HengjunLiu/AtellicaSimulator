#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LIS模块 - ASTM协议客户端实现
"""

import socket
import threading
import time
import random
from datetime import datetime


class LISClient:
    """LIS客户端，实现ASTM协议"""
    
    def __init__(self, config_manager, logger, core):
        """初始化LIS客户端
        
        Args:
            config_manager: 配置管理器实例
            logger: 日志管理器实例
            core: 核心模拟逻辑实例
        """
        self.config_manager = config_manager
        self.logger = logger
        self.core = core
        
        # 配置信息
        self.config = config_manager.get_lis_config()
        self.host = self.config.get('host', '127.0.0.1')
        self.port = self.config.get('port', 5000)
        self.result_delay = self.config.get('result_delay', 1800)  # 30分钟，单位秒
        self.reconnect_interval = self.config.get('reconnect_interval', 30)  # 重连间隔，单位秒
        
        # 客户端状态
        self.client_socket = None
        self.is_running = False
        self.is_connected = False
        self.receive_thread = None
        self.buffer = ''
        self.connection_lock = threading.Lock()
        
        # 响应缓存，用于存储LIS服务器的响应
        self.response_cache = {}
        self.response_cache_lock = threading.Lock()
        
        # 待发送结果缓存，用于LIS未连接时缓存结果
        self.pending_results = []
        self.pending_results_lock = threading.Lock()
        
        # ASTM协议常量
        self.RECORD_SEP = '\x0d'  # 记录分隔符（CR）
        self.FIELD_SEP = '|'       # 字段分隔符
        self.COMPONENT_SEP = '^'   # 组件分隔符
        self.REPEAT_SEP = '~'      # 重复分隔符
        self.ESCAPE_SEP = '\\'     # 转义分隔符
        
        # 记录类型常量
        self.RECORD_TYPE_HEADER = 'H'
        self.RECORD_TYPE_PATIENT = 'P'
        self.RECORD_TYPE_ORDER = 'O'
        self.RECORD_TYPE_RESULT = 'R'
        self.RECORD_TYPE_COMMENT = 'C'
        self.RECORD_TYPE_TERMINATOR = 'L'
        
        # 注册结果回调
        self.core.register_result_callback(self._send_result_callback)
        
        self.logger.info(f"LISClient initialized, will connect to {self.host}:{self.port}")
    
    def start(self):
        """启动LIS客户端"""
        if self.is_running:
            self.logger.warning("LISClient is already running")
            return
        
        self.is_running = True
        self.logger.info("LISClient started")
        
        # 启动连接线程
        connect_thread = threading.Thread(target=self._connect_loop, daemon=True)
        connect_thread.start()
    
    def stop(self):
        """停止LIS客户端"""
        self.is_running = False
        
        try:
            # 关闭连接
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None
            
            self.is_connected = False
            self.logger.info("LISClient stopped")
        except Exception as e:
            self.logger.error(f"Error stopping LISClient: {str(e)}")
    
    def _connect_loop(self):
        """连接循环，负责维护与LIS服务器的连接"""
        while self.is_running:
            if not self.is_connected:
                self.logger.info(f"Attempting to connect to LIS server at {self.host}:{self.port}...")
                self.logger.log_lis(f"Attempting to connect to LIS server at {self.host}:{self.port}...")
                if self._connect():
                    self.logger.info(f"Connected to LIS server at {self.host}:{self.port}")
                    self.logger.log_lis(f"Connected to LIS server at {self.host}:{self.port}")
                    # 启动接收线程
                    self.receive_thread = threading.Thread(target=self._receive_data, daemon=True)
                    self.receive_thread.start()
                else:
                    self.logger.error(f"Failed to connect to LIS server. Retrying in {self.reconnect_interval} seconds...")
                    self.logger.log_lis(f"Failed to connect to LIS server. Retrying in {self.reconnect_interval} seconds...")
                    time.sleep(self.reconnect_interval)
            time.sleep(1)
    
    def _connect(self):
        """连接到LIS服务器
        
        Returns:
            bool: 连接是否成功
        """
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 移除超时设置，避免因超时而断开连接
            # self.client_socket.settimeout(10)
            self.client_socket.connect((self.host, self.port))
            self.is_connected = True
            # 更新核心LIS连接状态为已连接
            self.core.update_lis_connection_status(1)  # 1: Connected
            # 记录连接成功到LIS通讯日志
            self.logger.log_lis(f"Connection established to {self.host}:{self.port}")
            
            # 发送缓存的结果
            self._send_pending_results()
            
            return True
        except Exception as e:
            self.logger.error(f"Connection error: {str(e)}")
            self.logger.log_lis(f"Connection error: {str(e)}")
            self.is_connected = False
            # 更新核心LIS连接状态为断开连接
            self.core.update_lis_connection_status(2)  # 2: Disconnected
            return False
    
    def _receive_data(self):
        """接收LIS服务器数据"""
        while self.is_running and self.is_connected:
            try:
                # 设置一个较短的超时，以便能够定期检查连接状态
                self.client_socket.settimeout(5)  # 5秒超时
                # 接收数据
                data = self.client_socket.recv(4096)
                if not data:
                    self.logger.info("Connection to LIS server closed")
                    self.logger.log_lis("Connection to LIS server closed")
                    self.is_connected = False
                    # 更新核心LIS连接状态为断开连接
                    self.core.update_lis_connection_status(2)  # 2: Disconnected
                    break
                
                # 立即显示收到的数据到日志
                self.logger.log_lis(f"Received data: {repr(data)}")
                
                # 转换为字符串并添加到缓冲区
                self.buffer += data.decode('ascii', errors='replace')
                
                # 收到消息后立即回复ACK
                self._send_ack()
                
                # 检查是否包含EOT字符(0x04)
                if '\x04' in self.buffer:
                    # 处理包含EOT的完整消息
                    self._process_buffer_with_eot()
                
            except socket.timeout:
                # 超时异常，不断开连接，继续等待数据
                # 这是正常的，因为我们设置了超时以便定期检查连接状态
                continue
            except socket.error as e:
                error_msg = f"Error receiving data from LIS server: {str(e)}"
                self.logger.error(error_msg)
                self.logger.log_lis(error_msg)
                self.is_connected = False
                # 更新核心LIS连接状态为断开连接
                self.core.update_lis_connection_status(2)  # 2: Disconnected
                break
            except Exception as e:
                error_msg = f"Unexpected error in LIS receive thread: {str(e)}"
                self.logger.error(error_msg)
                self.logger.log_lis(error_msg)
                self.is_connected = False
                # 更新核心LIS连接状态为断开连接
                self.core.update_lis_connection_status(2)  # 2: Disconnected
                break
    
    def _process_buffer_with_eot(self):
        """处理包含EOT字符的缓冲区数据"""
        while '\x04' in self.buffer:
            # 找到EOT字符位置
            eot_pos = self.buffer.find('\x04')
            if eot_pos == -1:
                break
            
            # 提取完整消息（从当前位置到EOT）
            full_message = self.buffer[:eot_pos]
            # 移除已处理的消息和EOT字符
            self.buffer = self.buffer[eot_pos + 1:]
            
            # 处理完整消息
            if full_message.strip():
                # 记录完整消息
                self.logger.log_lis(f"Processing complete message: {repr(full_message)}")
                # 处理ASTM消息
                self._process_message(full_message)
    
    def _process_message(self, message):
        """处理ASTM消息
        
        Args:
            message: ASTM消息
        """
        try:
            # 记录接收到的消息
            self.logger.log_lis(f"Received message from LIS server")
            self.logger.log_lis(f"Message content: {repr(message)}")
            
            # 解析消息
            records = message.split(self.RECORD_SEP)
            if not records:
                return
            
            # 处理每个记录
            patient_info = {}
            current_sample = None
            test_orders = []
            is_query_response = False
            
            for record in records:
                record = record.strip()
                if not record:
                    continue
                
                record_type = record[0]
                fields = record.split(self.FIELD_SEP)
                
                if record_type == self.RECORD_TYPE_HEADER:
                    # 处理头记录
                    self._handle_header_record(fields)
                    # 检查是否是查询响应（消息控制ID为Q）
                    if len(fields) >= 5 and fields[4] == 'Q':
                        is_query_response = True
                        
                elif record_type == self.RECORD_TYPE_PATIENT:
                    # 处理患者记录
                    patient_info = self._parse_patient_record(fields)
                    
                elif record_type == self.RECORD_TYPE_ORDER:
                    # 处理订单记录
                    order_info = self._parse_order_record(fields)
                    if order_info:
                        current_sample = order_info['sample_id']
                        test_orders = order_info['tests']
                        
                elif record_type == self.RECORD_TYPE_TERMINATOR:
                    # 处理终止记录
                    if current_sample and test_orders:
                        # 接收样本
                        self._receive_sample(current_sample, test_orders, patient_info)
                        
                        # 如果是查询响应，将结果存储到响应缓存
                        if is_query_response:
                            with self.response_cache_lock:
                                self.response_cache[current_sample] = test_orders
                            self.logger.log_lis(f"Stored query response for sample {current_sample}: {test_orders}")
            
            # 不再发送ACK，因为已经在收到数据时立即回复了
            # self._send_ack()
            
        except Exception as e:
            self.logger.error(f"Error processing LIS message: {str(e)}")
            self.logger.log_lis(f"Error processing message: {str(e)}")
    
    def _handle_header_record(self, fields):
        """处理ASTM头记录
        
        Args:
            fields: 记录字段列表
        """
        if len(fields) >= 4:
            sender = fields[1] if len(fields) > 1 else ''
            receiver = fields[2] if len(fields) > 2 else ''
            date_time = fields[3] if len(fields) > 3 else ''
            self.logger.log_lis(f"Header record - Sender: {sender}, Receiver: {receiver}, DateTime: {date_time}")
    
    def _parse_patient_record(self, fields):
        """解析患者记录
        
        Args:
            fields: 记录字段列表
            
        Returns:
            dict: 患者信息
        """
        patient_info = {}
        
        if len(fields) >= 2:
            patient_info['patient_id'] = fields[1] if fields[1] else ''
        
        if len(fields) >= 3:
            # 患者姓名字段（格式：LastName^FirstName^MiddleName^Suffix）
            name_components = fields[2].split(self.COMPONENT_SEP) if fields[2] else []
            if len(name_components) > 0:
                patient_info['last_name'] = name_components[0]
            if len(name_components) > 1:
                patient_info['first_name'] = name_components[1]
        
        if len(fields) >= 4:
            patient_info['dob'] = fields[3] if fields[3] else ''
        
        if len(fields) >= 5:
            patient_info['gender'] = fields[4] if fields[4] else ''
        
        self.logger.log_lis(f"Parsed patient record: {patient_info}")
        return patient_info
    
    def _parse_order_record(self, fields):
        """解析订单记录
        
        Args:
            fields: 记录字段列表
            
        Returns:
            dict: 订单信息
        """
        order_info = {
            'sample_id': '',
            'tests': []
        }
        
        if len(fields) >= 2:
            order_info['sample_id'] = fields[1] if fields[1] else ''
        
        if len(fields) >= 3:
            # 收集测试订单（重复字段）
            test_fields = fields[2].split(self.REPEAT_SEP) if fields[2] else []
            for test_field in test_fields:
                test_components = test_field.split(self.COMPONENT_SEP)
                if test_components and test_components[0]:
                    order_info['tests'].append(test_components[0])
        
        self.logger.log_lis(f"Parsed order record: {order_info}")
        return order_info
    
    def _receive_sample(self, sample_id, tests, patient_info):
        """接收样本
        
        Args:
            sample_id: 样本ID
            tests: 测试项目列表
            patient_info: 患者信息
        """
        # 调用核心模块接收样本
        success = self.core.receive_sample(sample_id, tests, patient_info)
        
        if success:
            self.logger.info(f"Sample {sample_id} received from LIS with tests {tests}")
            self.logger.log_lis(f"Sample received: {sample_id}, Tests: {tests}")
        else:
            self.logger.error(f"Failed to receive sample {sample_id} from LIS")
            self.logger.log_lis(f"Failed to receive sample: {sample_id}")
    
    def _send_ack(self):
        """发送确认消息"""
        # ASTM确认消息（简单ACK）
        with self.connection_lock:
            if self.is_connected and self.client_socket:
                try:
                    ack_msg = '\x06'  # ACK字符
                    self.client_socket.sendall(ack_msg.encode('ascii'))
                    self.logger.log_lis(f"Sent ACK to LIS server")
                except Exception as e:
                    self.logger.error(f"Error sending ACK: {str(e)}")
    
    def _send_result_callback(self, sample_id, results):
        """结果回调函数，用于发送结果回LIS
        Args:
            sample_id: 样本ID
            results: 测试结果
        """
        sample_info = self.core.get_sample_info(sample_id)
        if not sample_info or not sample_info['results']:
            return
        
        # 构建ASTM结果消息
        result_msg = self._build_result_message(sample_info)
        
        # 检查LIS连接状态
        if not self.is_connected:
            # LIS未连接，缓存结果待后续发送
            with self.pending_results_lock:
                self.pending_results.append({
                    'sample_id': sample_id,
                    'result_msg': result_msg,
                    'timestamp': time.time()
                })
            self.logger.warning(f"LIS not connected, result for sample {sample_id} cached. Pending results count: {len(self.pending_results)}")
            self.logger.log_lis(f"Result cached for sample {sample_id} - LIS not connected")
            return
        
        # 发送结果到LIS服务器
        self._send_message(result_msg)
    
    def _send_pending_results(self):
        """发送缓存的结果到LIS服务器"""
        with self.pending_results_lock:
            if not self.pending_results:
                return
            
            # 复制缓存列表并清空原列表
            results_to_send = self.pending_results.copy()
            self.pending_results = []
        
        self.logger.info(f"Sending {len(results_to_send)} pending results to LIS")
        self.logger.log_lis(f"Sending {len(results_to_send)} pending results to LIS")
        
        # 发送每个缓存的结果
        for result_info in results_to_send:
            try:
                sample_id = result_info['sample_id']
                result_msg = result_info['result_msg']
                
                self._send_message(result_msg)
                self.logger.info(f"Pending result for sample {sample_id} sent successfully")
                self.logger.log_lis(f"Pending result for sample {sample_id} sent successfully")
                
                # 添加短暂延迟，避免发送过快
                time.sleep(0.5)
            except Exception as e:
                self.logger.error(f"Error sending pending result for sample {result_info.get('sample_id', 'unknown')}: {str(e)}")
                self.logger.log_lis(f"Error sending pending result: {str(e)}")
    
    def get_apply(self, barcode):
        """获取申请项目
        Args:
            barcode: 样本条码
        Returns:
            list: 申请项目列表
        """
        if not barcode:
            return []
        
        # 记录获取申请项目请求
        self.logger.log_lis(f"Getting apply for barcode: {barcode}")
        
        # 检查响应缓存中是否已有结果
        with self.response_cache_lock:
            if barcode in self.response_cache:
                # 从缓存中获取结果
                test_orders = self.response_cache[barcode]
                # 从缓存中移除，避免重复使用
                del self.response_cache[barcode]
                self.logger.log_lis(f"Retrieved apply from cache for barcode: {barcode}")
                # 转换为显示格式
                return [f"{test} - {self._get_test_name(test)}" for test in test_orders]
        
        # 检查是否已连接到LIS服务器
        if not self.is_connected:
            self.logger.warning("Not connected to LIS server, using mock data")
            # 返回模拟的申请项目
            return ["TEST001 - 血常规", "TEST002 - 生化常规", "TEST003 - 肝功能", "TEST004 - 肾功能"]
        
        try:
            # 构建ASTM查询消息
            query_message = self._build_query_message(barcode)
            
            # 发送查询消息到LIS服务器
            self._send_message(query_message)
            
            # 等待并接收响应（这里简化处理，实际应该使用异步方式）
            # 注意：这只是一个示例，实际实现需要根据LIS服务器的响应格式进行调整
            self.logger.log_lis(f"Sent query for barcode: {barcode}")
            
            # 由于我们使用的是模拟实现，这里仍然返回模拟数据
            # 实际项目中应该解析LIS服务器的响应并返回真实的申请项目
            # 响应会通过_receive_data方法接收并由_process_message方法处理
            # 这里可以添加逻辑来等待响应或使用回调机制
            return ["TEST001 - 血常规", "TEST002 - 生化常规", "TEST003 - 肝功能", "TEST004 - 肾功能"]
        except Exception as e:
            self.logger.error(f"Error getting apply from LIS server: {str(e)}")
            # 出错时返回模拟数据
            return ["TEST001 - 血常规", "TEST002 - 生化常规", "TEST003 - 肝功能", "TEST004 - 肾功能"]
    
    def _send_message(self, message):
        """发送消息到LIS服务器
        
        Args:
            message: 要发送的ASTM消息
        """
        with self.connection_lock:
            if self.is_connected and self.client_socket:
                try:
                    self.client_socket.sendall(message.encode('ascii'))
                    self.logger.log_lis(f"Sent message to LIS server")
                    self.logger.log_lis(f"Message content: {repr(message)}")
                    
                    # 等待ACK
                    ack = self.client_socket.recv(1)
                    if ack == b'\x06':  # ACK
                        self.logger.log_lis("Received ACK from LIS server")
                    else:
                        self.logger.log_lis(f"Received unexpected response: {repr(ack)}")
                        
                except Exception as e:
                    self.logger.error(f"Error sending message to LIS server: {str(e)}")
                    self.is_connected = False
    
    def _build_result_message(self, sample_info):
        """构建ASTM结果消息
        Args:
            sample_info: 样本信息
        Returns:
            str: ASTM结果消息
        """
        # 获取当前时间
        now = datetime.now()
        date_time_str = now.strftime('%Y%m%d%H%M%S')
        date_str = now.strftime('%Y%m%d')
        
        # 构建消息
        message = []
        
        # 添加头记录
        header_record = [
            self.RECORD_TYPE_HEADER,
            'ATELLICA',                 # 发送方ID
            'LIS',                      # 接收方ID
            date_time_str,              # 消息日期时间
            '1',                        # 消息控制ID
            '1',                        # 版本号
            '1'                         # 字符集
        ]
        message.append(self.FIELD_SEP.join(header_record))
        
        # 添加患者记录
        patient_info = sample_info.get('patient_info', {})
        patient_record = [
            self.RECORD_TYPE_PATIENT,
            patient_info.get('patient_id', ''),  # 患者ID
            f"{patient_info.get('last_name', '')}^{patient_info.get('first_name', '')}",  # 患者姓名
            patient_info.get('dob', ''),  # 出生日期
            patient_info.get('gender', ''),  # 性别
            '',  # 可选字段
            '',  # 可选字段
            ''   # 可选字段
        ]
        message.append(self.FIELD_SEP.join(patient_record))
        
        # 添加订单记录
        order_record = [
            self.RECORD_TYPE_ORDER,
            sample_info['sample_id'],  # 样本ID
            '',  # 测试请求（在结果消息中不需要）
            date_str,  # 采集日期
            '',  # 采集时间
            '',  # 采集者ID
            '',  # 容器类型
            '',  # 容器状态
            'F',  # 样本状态（已完成）
            '',  # 优先级
            '',  # 医生ID
            ''   # 科室
        ]
        message.append(self.FIELD_SEP.join(order_record))
        
        # 添加结果记录
        results = sample_info['results']
        for test_code, result_info in results.items():
            result_record = [
                self.RECORD_TYPE_RESULT,
                test_code,  # 测试代码
                '',  # 结果值类型
                str(result_info['value']),  # 结果值
                result_info['unit'],  # 单位
                '',  # 参考范围
                result_info['flags'],  # 标志
                '',  # 异常标志
                date_str,  # 测试日期
                now.strftime('%H%M%S'),  # 测试时间
                'ATL',  # 操作者ID
                'F',  # 结果状态（已完成）
                '',  # 仪器ID
                ''   # 方法ID
            ]
            message.append(self.FIELD_SEP.join(result_record))
        
        # 添加终止记录
        terminator_record = [
            self.RECORD_TYPE_TERMINATOR,
            '1',  # 消息中的记录数
            '1'   # 校验和（简化处理）
        ]
        message.append(self.FIELD_SEP.join(terminator_record))
        
        # 组合消息，添加记录分隔符
        astm_message = self.RECORD_SEP.join(message) + self.RECORD_SEP
        
        self.logger.log_lis(f"Built result message for sample {sample_info['sample_id']}")
        self.logger.log_lis(f"Result message content: {repr(astm_message)}")
        
        return astm_message
    
    def _build_query_message(self, barcode):
        """构建查询申请项目的ASTM消息
        Args:
            barcode: 样本条码
        Returns:
            str: ASTM查询消息
        """
        # 获取当前时间
        now = datetime.now()
        date_time_str = now.strftime('%Y%m%d%H%M%S')
        
        # 构建消息
        message = []
        
        # 添加头记录
        header_record = [
            self.RECORD_TYPE_HEADER,
            'ATELLICA',                 # 发送方ID
            'LIS',                      # 接收方ID
            date_time_str,              # 消息日期时间
            'Q',                        # 消息控制ID（Q表示查询）
            '1',                        # 版本号
            '1'                         # 字符集
        ]
        message.append(self.FIELD_SEP.join(header_record))
        
        # 添加查询记录（使用订单记录类型，实际应该根据ASTM协议使用正确的记录类型）
        query_record = [
            self.RECORD_TYPE_ORDER,
            barcode,  # 样本ID/条码
            '',  # 测试请求
            '',  # 采集日期
            '',  # 采集时间
            '',  # 采集者ID
            '',  # 容器类型
            '',  # 容器状态
            '',  # 样本状态
            '',  # 优先级
            '',  # 医生ID
            ''   # 科室
        ]
        message.append(self.FIELD_SEP.join(query_record))
        
        # 添加终止记录
        terminator_record = [
            self.RECORD_TYPE_TERMINATOR,
            '1',  # 消息中的记录数
            '1'   # 校验和（简化处理）
        ]
        message.append(self.FIELD_SEP.join(terminator_record))
        
        # 组合消息，添加记录分隔符
        astm_message = self.RECORD_SEP.join(message) + self.RECORD_SEP
        
        self.logger.log_lis(f"Built query message for barcode: {barcode}")
        self.logger.log_lis(f"Query message content: {repr(astm_message)}")
        
        return astm_message
    
    def _get_test_name(self, test_code):
        """根据测试代码获取测试名称
        Args:
            test_code: 测试代码
        Returns:
            str: 测试名称
        """
        test_names = {
            'TEST001': '血常规',
            'TEST002': '生化常规',
            'TEST003': '肝功能',
            'TEST004': '肾功能'
        }
        return test_names.get(test_code, '未知测试')
