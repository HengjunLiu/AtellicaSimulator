#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LIS模块 - ASTM协议服务端实现
"""

import socket
import threading
import time
import random
from datetime import datetime


class LISServer:
    """LIS服务器，实现ASTM协议"""
    
    def __init__(self, config_manager, logger, core):
        """初始化LIS服务器
        
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
        self.host = self.config.get('host', '0.0.0.0')
        self.port = self.config.get('port', 10002)
        self.result_delay = self.config.get('result_delay', 1800)  # 30分钟，单位秒
        self.max_connections = self.config.get('max_connections', 10)
        
        # 服务器状态
        self.server_socket = None
        self.is_running = False
        self.connections = []
        self.connection_lock = threading.Lock()
        
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
        
        self.logger.info(f"LISServer initialized, listening on {self.host}:{self.port}")
    
    def start(self):
        """启动LIS服务器"""
        if self.is_running:
            self.logger.warning("LISServer is already running")
            return
        
        try:
            # 创建TCP服务器 socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(self.max_connections)
            
            self.is_running = True
            self.logger.info(f"LISServer started, listening on {self.host}:{self.port}")
            
            # 启动接受连接的线程
            accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            accept_thread.start()
            
        except Exception as e:
            self.logger.error(f"Failed to start LISServer: {str(e)}")
            self.is_running = False
    
    def stop(self):
        """停止LIS服务器"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        try:
            # 关闭所有连接
            with self.connection_lock:
                for conn in self.connections:
                    conn.close()
                self.connections.clear()
            
            # 关闭服务器 socket
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
            
            self.logger.info("LISServer stopped")
        except Exception as e:
            self.logger.error(f"Error stopping LISServer: {str(e)}")
    
    def _accept_connections(self):
        """接受客户端连接"""
        while self.is_running:
            try:
                conn, addr = self.server_socket.accept()
                with self.connection_lock:
                    if len(self.connections) >= self.max_connections:
                        conn.close()
                        self.logger.warning(f"LIS connection rejected from {addr[0]}:{addr[1]} - max connections reached")
                        continue
                    self.connections.append(conn)
                
                self.logger.info(f"LIS connection established from {addr[0]}:{addr[1]}")
                self.logger.log_lis(f"Connection established: {addr[0]}:{addr[1]}")
                
                # 为每个连接创建处理线程
                conn_thread = threading.Thread(
                    target=self._handle_connection,
                    args=(conn, addr),
                    daemon=True
                )
                conn_thread.start()
                
            except socket.error as e:
                if self.is_running:
                    self.logger.error(f"Error accepting LIS connection: {str(e)}")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in LIS accept thread: {str(e)}")
    
    def _handle_connection(self, conn, addr):
        """处理单个连接
        
        Args:
            conn: 连接 socket
            addr: 客户端地址
        """
        buffer = ''
        
        try:
            while self.is_running:
                # 接收数据
                data = conn.recv(4096)
                if not data:
                    break
                
                # 转换为字符串
                buffer += data.decode('ascii', errors='replace')
                
                # 处理缓冲区中的ASTM消息
                while True:
                    # 查找完整消息（以L记录结尾）
                    msg_end = buffer.find(f"L{self.FIELD_SEP}")
                    if msg_end == -1:
                        break
                    
                    # 提取完整消息
                    # 找到消息的起始位置（H记录）
                    msg_start = buffer.find(f"H{self.FIELD_SEP}")
                    if msg_start == -1:
                        # 没有找到H记录，清空缓冲区
                        buffer = ''
                        break
                    
                    # 提取完整消息
                    message = buffer[msg_start:msg_end + buffer[msg_end:].find(self.RECORD_SEP) + 1]
                    buffer = buffer[msg_end + buffer[msg_end:].find(self.RECORD_SEP) + 1:]
                    
                    # 处理消息
                    self._process_message(conn, addr, message)
                    
        except socket.error as e:
            self.logger.error(f"LIS connection error with {addr[0]}:{addr[1]}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error handling LIS connection from {addr[0]}:{addr[1]}: {str(e)}")
        finally:
            # 清理连接
            with self.connection_lock:
                if conn in self.connections:
                    self.connections.remove(conn)
            
            try:
                conn.close()
            except:
                pass
            
            self.logger.info(f"LIS connection closed with {addr[0]}:{addr[1]}")
            self.logger.log_lis(f"Connection closed: {addr[0]}:{addr[1]}")
    
    def _process_message(self, conn, addr, message):
        """处理ASTM消息
        
        Args:
            conn: 连接 socket
            addr: 客户端地址
            message: ASTM消息
        """
        try:
            # 记录接收到的消息
            self.logger.log_lis(f"Received message from {addr[0]}:{addr[1]}")
            self.logger.log_lis(f"Message content: {repr(message)}")
            
            # 解析消息
            records = message.split(self.RECORD_SEP)
            if not records:
                return
            
            # 处理每个记录
            patient_info = {}
            current_sample = None
            test_orders = []
            
            for record in records:
                record = record.strip()
                if not record:
                    continue
                
                record_type = record[0]
                fields = record.split(self.FIELD_SEP)
                
                if record_type == self.RECORD_TYPE_HEADER:
                    # 处理头记录
                    self._handle_header_record(fields)
                    
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
                        self._receive_sample(conn, current_sample, test_orders, patient_info)
                    
            # 发送确认消息
            self._send_ack(conn)
            
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
    
    def _receive_sample(self, conn, sample_id, tests, patient_info):
        """接收样本
        
        Args:
            conn: 连接 socket
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
    
    def _send_ack(self, conn):
        """发送确认消息
        
        Args:
            conn: 连接 socket
        """
        # ASTM确认消息（简单ACK）
        ack_msg = '\x06'  # ACK字符
        conn.sendall(ack_msg.encode('ascii'))
        self.logger.log_lis(f"Sent ACK to client")
    
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
        
        # 发送结果到所有连接的客户端
        with self.connection_lock:
            for conn in self.connections:
                try:
                    conn.sendall(result_msg.encode('ascii'))
                    self.logger.log_lis(f"Sent results for sample {sample_id} to client")
                except Exception as e:
                    self.logger.error(f"Error sending results to client: {str(e)}")
    
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
            'LIS',                      # 发送方ID
            'ATELLICA',                 # 接收方ID
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
    
    def _send_result_message(self, conn, astm_message):
        """发送ASTM结果消息
        
        Args:
            conn: 连接 socket
            astm_message: ASTM结果消息
        """
        try:
            # 发送消息
            conn.sendall(astm_message.encode('ascii'))
            
            # 等待ACK
            ack = conn.recv(1)
            if ack == b'\x06':  # ACK
                self.logger.log_lis("Received ACK for result message")
            else:
                self.logger.log_lis(f"Received unexpected response: {repr(ack)}")
                
        except Exception as e:
            self.logger.error(f"Error sending result message: {str(e)}")
            self.logger.log_lis(f"Error sending result message: {str(e)}")
