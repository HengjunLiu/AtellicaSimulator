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
        self.reconnect_interval = self.config.get(
            'reconnect_interval', 30)  # 重连间隔，单位秒

        # 客户端状态
        self.client_socket = None
        self.is_running = False
        self.is_connected = False
        self.receive_thread = None
        self.buffer = ''
        self.connection_lock = threading.Lock()
        # 状态管理
        self.state = 'idle'  # 状态：idle（空闲）, sending（发送）, receiving（接收）
        self.last_activity_time = time.time()  # 最后一次操作的时间
        self.state_check_thread = None  # 状态检查线程
        # 记录发送的查询条码
        self.current_query_barcode = None
        # 错误回调函数，用于通知UI条码不一致等错误
        self.error_callback = None

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

        self.logger.info(
            f"LISClient initialized, will connect to {self.host}:{self.port}")

    def start(self):
        """启动LIS客户端"""
        if self.is_running:
            self.logger.warning("LISClient is already running")
            return

        self.is_running = True
        self.logger.info("LISClient started")

        # 启动连接线程
        connect_thread = threading.Thread(
            target=self._connect_loop, daemon=True)
        connect_thread.start()

        # 启动状态检查线程
        self.state_check_thread = threading.Thread(
            target=self._state_check_loop, daemon=True)
        self.state_check_thread.start()

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
                self.logger.info(
                    f"Attempting to connect to LIS server at {self.host}:{self.port}...")
                self.logger.log_lis(
                    f"Attempting to connect to LIS server at {self.host}:{self.port}...")
                if self._connect():
                    self.logger.info(
                        f"Connected to LIS server at {self.host}:{self.port}")
                    self.logger.log_lis(
                        f"Connected to LIS server at {self.host}:{self.port}")
                    # 启动接收线程
                    self.receive_thread = threading.Thread(
                        target=self._receive_data, daemon=True)
                    self.receive_thread.start()
                else:
                    self.logger.error(
                        f"Failed to connect to LIS server. Retrying in {self.reconnect_interval} seconds...")
                    self.logger.log_lis(
                        f"Failed to connect to LIS server. Retrying in {self.reconnect_interval} seconds...")
                    time.sleep(self.reconnect_interval)
            time.sleep(1)

    def _connect(self):
        """连接到LIS服务器

        Returns:
            bool: 连接是否成功
        """
        try:
            self.client_socket = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            # 移除超时设置，避免因超时而断开连接
            # self.client_socket.settimeout(10)
            self.client_socket.connect((self.host, self.port))
            self.is_connected = True
            # 更新核心LIS连接状态为已连接
            self.core.update_lis_connection_status(1)  # 1: Connected
            # 记录连接成功到LIS通讯日志
            self.logger.log_lis(
                f"Connection established to {self.host}:{self.port}")

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
            # 检查套接字是否有效
            if not self.client_socket:
                self.is_connected = False
                break

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
                    self.core.update_lis_connection_status(
                        2)  # 2: Disconnected
                    # 关闭套接字
                    if self.client_socket:
                        try:
                            self.client_socket.close()
                        except:
                            pass
                        self.client_socket = None
                    break

                # 更新最后操作时间
                self.last_activity_time = time.time()

                # 立即显示收到的数据到日志
                self.logger.log_lis(f"R: {repr(data)}")

                # 转换为字符串并添加到缓冲区
                data_str = data.decode('ascii', errors='replace')
                self.buffer += data_str

                # 检查是否包含EOT字符(0x04)
                if '\x04' in data_str:
                    # 收到EOT，不回消息
                    self.logger.log_lis("R: " + '\x04')
                    # 结束接收状态，进入空闲状态
                    if self.state == 'receiving':
                        self.state = 'idle'
                        self.logger.log_lis(
                            "Exited receiving state, entered idle state")
                    # 处理包含EOT的完整消息
                    self._process_buffer_with_eot()

                elif '\x05' in data_str:
                    # 收到ENQ，回ACK
                    self.logger.log_lis("R: ENQ")
                    # 进入接收状态
                    self.state = 'receiving'
                    self.logger.log_lis("Entered receiving state")
                    self._send_ack()
                else:
                    # 如果在接收状态，回复ACK
                    # 发送状态时不回复ACK，避免在发送EOT后又发送ACK
                    if self.state == 'receiving':
                        self._send_ack()

            except socket.timeout:
                # 超时异常，不断开连接，继续等待数据
                # 这是正常的，因为我们设置了超时以便定期检查连接状态
                continue
            except socket.error as e:
                error_msg = f"Error receiving data from LIS server: {str(e)}"
                # 只记录错误，不显示在日志中，避免干扰用户
                # self.logger.error(error_msg)
                # self.logger.log_lis(error_msg)
                self.is_connected = False
                # 更新核心LIS连接状态为断开连接
                self.core.update_lis_connection_status(2)  # 2: Disconnected
                # 关闭套接字
                if self.client_socket:
                    try:
                        self.client_socket.close()
                    except:
                        pass
                    self.client_socket = None
                break
            except Exception as e:
                error_msg = f"Unexpected error in LIS receive thread: {str(e)}"
                # 只记录错误，不显示在日志中，避免干扰用户
                # self.logger.error(error_msg)
                # self.logger.log_lis(error_msg)
                self.is_connected = False
                # 更新核心LIS连接状态为断开连接
                self.core.update_lis_connection_status(2)  # 2: Disconnected
                # 关闭套接字
                if self.client_socket:
                    try:
                        self.client_socket.close()
                    except:
                        pass
                    self.client_socket = None
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
                # 处理ASTM消息
                self._process_message(full_message)

    def _process_message(self, message):
        """处理ASTM消息

        Args:
            message: ASTM消息
        """
        try:
            # 忽略功能字符：EOT(0x04), ENQ(0x05), ACK(0x06), CR(0x0d), LF(0x0a)
            # 以及校验和部分（通常在ETX之后）
            functional_chars = ['\x04', '\x05', '\x06', '\x0d', '\x0a']
            filtered_message = message

            # 移除功能字符
            for char in functional_chars:
                filtered_message = filtered_message.replace(char, '')

            # 移除ETX之后的校验和部分
            etx_pos = filtered_message.find('\x03')
            if etx_pos != -1:
                filtered_message = filtered_message[:etx_pos]

            # 如果过滤后消息为空，直接返回
            if not filtered_message.strip():
                return

            # 解析消息（使用原始消息进行记录分离，因为过滤可能会影响记录边界）
            records = message.split(self.RECORD_SEP)
            if not records:
                return

            # 处理每个记录
            patient_info = {}
            current_sample = None
            test_orders = []
            is_query_response = False

            for i, record in enumerate(records):
                # 对每个记录也进行过滤
                filtered_record = record
                for char in functional_chars:
                    filtered_record = filtered_record.replace(char, '')

                # 移除ETX之后的校验和部分
                etx_pos = filtered_record.find('\x03')
                if etx_pos != -1:
                    filtered_record = filtered_record[:etx_pos]

                filtered_record = filtered_record.replace('\x02', '')
                filtered_record = filtered_record.strip()
                if not filtered_record:
                    continue

                # 提取记录类型，处理可能的数字前缀
                record_type = filtered_record[0]
                # 如果第一个字符是数字，找到第一个非数字字符作为记录类型
                if record_type.isdigit():
                    for char in filtered_record:
                        if not char.isdigit():
                            record_type = char
                            break

                fields = filtered_record.split(self.FIELD_SEP)

                # 处理第一个字段（可能包含记录类型和数字前缀）
                if fields:
                    # 去掉第一个字段中的数字前缀，保留记录类型
                    first_field = fields[0]
                    if first_field:
                        # 找到第一个非数字字符
                        non_digit_start = 0
                        while non_digit_start < len(first_field) and first_field[non_digit_start].isdigit():
                            non_digit_start += 1
                        # 如果有非数字字符，提取出来作为新的第一个字段
                        if non_digit_start < len(first_field):
                            fields[0] = first_field[non_digit_start:]
                        else:
                            # 如果全是数字，保持原样
                            pass

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

                        # 检查收到的样本ID是否与发送的查询条码一致
                        barcode_match = True
                        if self.current_query_barcode and current_sample:
                            if self.current_query_barcode != current_sample:
                                # 条码不一致，提示报错
                                error_msg = f"条码不一致: 发送查询 {self.current_query_barcode}, 收到订单 {current_sample}"
                                self.logger.error(error_msg)
                                self.logger.log_lis(f"ERROR: {error_msg}")
                                # 调用错误回调函数通知UI
                                if self.error_callback:
                                    self.error_callback(error_msg)
                                # 恢复到空闲状态
                                self.state = 'idle'
                                # 清空当前查询条码
                                self.current_query_barcode = None
                                # 标记条码不匹配
                                barcode_match = False
                                # 跳过后续处理
                                continue

                        # 只有条码匹配时才继续处理
                        if not barcode_match:
                            continue

                elif record_type == self.RECORD_TYPE_TERMINATOR:
                    # 处理终止记录
                    if current_sample:
                        if test_orders:
                            # 检查条码一致性
                            barcode_match = True
                            if self.current_query_barcode:
                                if self.current_query_barcode != current_sample:
                                    # 条码不一致，提示报错
                                    error_msg = f"条码不一致: 发送查询 {self.current_query_barcode}, 收到订单 {current_sample}"
                                    self.logger.error(error_msg)
                                    self.logger.log_lis(f"ERROR: {error_msg}")
                                    # 调用错误回调函数通知UI
                                    if self.error_callback:
                                        self.error_callback(error_msg)
                                    # 恢复到空闲状态
                                    self.state = 'idle'
                                    # 标记条码不匹配
                                    barcode_match = False

                            # 只有条码匹配时才处理
                            if barcode_match:
                                # 接收样本
                                self._receive_sample(
                                    current_sample, test_orders, patient_info)

                                # 如果是查询响应，将结果存储到响应缓存
                                if is_query_response:
                                    with self.response_cache_lock:
                                        self.response_cache[self.current_query_barcode] = test_orders
                                else:
                                    # 即使不是查询响应，也存储到缓存，以便get_apply方法可以获取
                                    with self.response_cache_lock:
                                        self.response_cache[self.current_query_barcode] = test_orders

                            # 处理完成后清空当前查询条码
                            if self.current_query_barcode:
                                self.current_query_barcode = None
                                # 恢复到空闲状态
                                self.state = 'idle'

        except Exception as e:
            self.logger.error(f"Error processing LIS message: {str(e)}")

    def _handle_header_record(self, fields):
        """处理ASTM头记录

        Args:
            fields: 记录字段列表
        """
        pass

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
            name_components = fields[2].split(
                self.COMPONENT_SEP) if fields[2] else []
            if len(name_components) > 0:
                patient_info['last_name'] = name_components[0]
            if len(name_components) > 1:
                patient_info['first_name'] = name_components[1]

        if len(fields) >= 4:
            patient_info['dob'] = fields[3] if fields[3] else ''

        if len(fields) >= 5:
            patient_info['gender'] = fields[4] if fields[4] else ''

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

        if len(fields) >= 3:
            # 提取样本ID (SampleIdentifier)
            sample_id = fields[2].strip()
            if sample_id:
                order_info['sample_id'] = sample_id

        if len(fields) >= 5:
            # 提取测试请求 (Request)
            request_field = fields[4].strip()
            if request_field:
                # 处理重复的测试请求（使用反斜杠分隔）
                if '\\' in request_field:
                    requests = request_field.split('\\')
                    for req in requests:
                        req = req.strip()
                        if req:
                            # 处理组件分隔符
                            if self.COMPONENT_SEP in req:
                                parts = req.split(self.COMPONENT_SEP)
                                # 测试代码通常在第四部分 (^ ^ ^ Test ^ ...)
                                if len(parts) >= 4:
                                    test_code = parts[3].strip()
                                    if test_code:
                                        order_info['tests'].append(test_code)
                            else:
                                order_info['tests'].append(req)
                else:
                    # 单个测试请求
                    if self.COMPONENT_SEP in request_field:
                        parts = request_field.split(self.COMPONENT_SEP)
                        # 测试代码通常在第四部分 (^ ^ ^ Test ^ ...)
                        if len(parts) >= 4:
                            test_code = parts[3].strip()
                            if test_code:
                                order_info['tests'].append(test_code)
                    else:
                        order_info['tests'].append(request_field)

        # 额外检查：如果没有找到样本ID，尝试其他字段
        if not order_info['sample_id']:
            for i, field in enumerate(fields):
                field = field.strip()
                if field and field.isdigit() and len(field) >= 5:
                    order_info['sample_id'] = field
                    break

        return order_info

    def _receive_sample(self, sample_id, tests, patient_info):
        """接收样本

        Args:
            sample_id: 样本ID
            tests: 测试项目列表
            patient_info: 患者信息
        """
        try:
            # 调用核心模块接收样本
            success = self.core.receive_sample(sample_id, tests, patient_info)

            if success:
                self.logger.info(
                    f"Sample {sample_id} received from LIS with tests {tests}")
                self.logger.log_lis(
                    f"Sample received: {sample_id}, Tests: {tests}")
            else:
                self.logger.error(f"Failed to receive sample {sample_id} from LIS - sample may already exist or no valid tests")
                self.logger.log_lis(f"Failed to receive sample: {sample_id} (already exists or invalid tests)")
        except Exception as e:
            self.logger.error(f"Exception receiving sample {sample_id}: {str(e)}")
            self.logger.log_lis(f"Exception receiving sample {sample_id}: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")

    def _send_ack(self):
        """发送确认消息"""
        # ASTM确认消息（简单ACK）
        with self.connection_lock:
            if self.is_connected and self.client_socket:
                try:
                    ack_msg = '\x06'  # ACK字符
                    self.client_socket.sendall(ack_msg.encode('ascii'))
                    self.logger.log_lis(f"S: ACK")
                except Exception as e:
                    self.logger.error(f"Error sending ACK: {str(e)}")

    def _send_pending_results(self):
        """发送缓存的结果到LIS服务器"""
        with self.pending_results_lock:
            if not self.pending_results:
                return

            # 复制缓存列表并清空原列表
            results_to_send = self.pending_results.copy()
            self.pending_results = []

        self.logger.info(
            f"Sending {len(results_to_send)} pending results to LIS")
        self.logger.log_lis(
            f"Sending {len(results_to_send)} pending results to LIS")

        # 发送每个缓存的结果
        for result_info in results_to_send:
            try:
                sample_id = result_info['sample_id']
                result_msg = result_info['result_msg']

                self._send_message(result_msg)
                self.logger.info(
                    f"Pending result for sample {sample_id} sent successfully")
                self.logger.log_lis(
                    f"Pending result for sample {sample_id} sent successfully")

                # 添加短暂延迟，避免发送过快
                time.sleep(0.5)
            except Exception as e:
                self.logger.error(
                    f"Error sending pending result for sample {result_info.get('sample_id', 'unknown')}: {str(e)}")
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

        # 清空响应缓存中的内容
        with self.response_cache_lock:
            if self.response_cache:
                self.logger.log_lis(
                    f"Clearing response cache before getting apply, current cache size: {len(self.response_cache)}")
                self.response_cache.clear()

        # 检查是否已连接到LIS服务器
        if not self.is_connected:
            self.logger.warning("Not connected to LIS server")
            return []

        try:
            # 发送查询消息到LIS服务器（传入barcode以便在发送过程中构建查询消息）
            self._send_message(barcode)

            # 等待并接收响应（添加简单的等待机制）
            self.logger.log_lis(
                f"Sent query for barcode: {barcode}, waiting for response...")

            # 等待响应，最多等待5秒
            start_time = time.time()
            while time.time() - start_time < 5:
                with self.response_cache_lock:
                    if barcode in self.response_cache:
                        # 从缓存中获取结果
                        test_orders = self.response_cache[barcode]
                        # 从缓存中移除，避免重复使用
                        del self.response_cache[barcode]
                        self.logger.log_lis(
                            f"Retrieved apply from cache for barcode: {barcode}")
                        # 转换为显示格式
                        return [f"{test} - {self._get_test_name(test)}" for test in test_orders]
                # 短暂延迟，避免CPU占用过高
                time.sleep(0.1)

            # 超时，返回空列表
            self.logger.warning(
                f"Timeout waiting for apply response for barcode: {barcode}")
            return []
        except Exception as e:
            self.logger.error(f"Error getting apply from LIS server: {str(e)}")
            return []

    def _state_check_loop(self):
        """状态检查循环，用于检查无操作时间并自动回到空闲状态"""
        while self.is_running:
            try:
                current_time = time.time()
                # 检查是否超过100秒无操作
                if current_time - self.last_activity_time > 100:
                    # 如果当前状态不是空闲，设置为空闲
                    if self.state != 'idle':
                        self.logger.log_lis(
                            f"Auto reset to idle state after 100s of inactivity")
                        self.state = 'idle'
                # 每10秒检查一次
                time.sleep(10)
            except Exception as e:
                self.logger.error(f"Error in state check loop: {str(e)}")
                time.sleep(10)

    def _send_message(self, message_or_barcode):
        """发送消息到LIS服务器

        Args:
            message_or_barcode: 要发送的ASTM消息或样本条码
        """
        # 更新最后操作时间
        self.last_activity_time = time.time()

        # 只在空闲状态时处理发送请求
        if self.state != 'idle':
            self.logger.log_lis(
                f"Cannot send message: current state is {self.state}, expected idle")
            return

        with self.connection_lock:
            if self.is_connected and self.client_socket:
                try:
                    # 确定要发送的消息
                    if '|' not in message_or_barcode or '\x0d' not in message_or_barcode:
                        # 如果传入的是条码，构建查询消息
                        barcode = message_or_barcode
                        self.logger.log_lis(
                            f"Building query message for barcode: {barcode}")
                        # 记录当前查询的条码
                        self.current_query_barcode = barcode
                        message = self._build_query_message(barcode)
                    else:
                        # 否则直接使用传入的消息
                        message = message_or_barcode

                    # 先发送ENQ字符(0x05)
                    enq_char = '\x05'
                    self.client_socket.sendall(enq_char.encode('ascii'))
                    self.logger.log_lis(f"S: ENQ")
                    # 进入发送状态
                    self.state = 'sending'
                    self.logger.log_lis("Entered sending state")
                    
                    # 发送实际的ASTM消息
                    self.logger.log_lis(
                        f"Preparing to send message, length: {len(message)} bytes")
                    self.logger.log_lis(
                        f"Message preview: {repr(message[:100])}...")  # 只显示前100个字符

                    encoded_message = message.encode('ascii')
                    # 一次性发送整个消息
                    self.client_socket.sendall(encoded_message)
                    self.logger.log_lis(f"S: {repr(message)}")
                    self.logger.log_lis(
                        f"S: Sent {len(encoded_message)} bytes at once")
                    self.logger.log_lis("Message sent successfully")

                    # 发送EOT
                    eot_char = '\x04'
                    self.client_socket.sendall(
                        eot_char.encode('ascii'))
                    self.logger.log_lis(f"S: EOT")
                    # 结束发送状态，进入空闲状态
                    self.state = 'idle'
                    self.logger.log_lis(
                        "Exited sending state, entered idle state")
                except Exception as e:
                    self.logger.error(
                        f"Error sending message to LIS server: {str(e)}")
                    # 尝试发送EOT，确保连接状态正确
                    try:
                        eot_char = '\x04'
                        self.client_socket.sendall(eot_char.encode('ascii'))
                        self.logger.log_lis(f"S: EOT (error recovery)")
                    except:
                        # 发送EOT失败，忽略错误
                        pass
                    # 结束发送状态，进入空闲状态
                    self.state = 'idle'
                    self.logger.log_lis(
                        "Exited sending state due to error, entered idle state")
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
        time_str = now.strftime('%H%M%S')

        # 构建消息
        message = []

        # 添加头记录（按照示例格式）
        header_record = [
            '1' + self.RECORD_TYPE_HEADER,  # 在H前面加数字1
            '\^&',                      # 字段分隔符定义
            '',                          # 保留字段
            '',                          # 保留字段
            'UIW_LIS',                   # 发送方ID（按照示例）
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            'LIS_ID',                    # 消息控制ID（按照示例）
            '',                          # 保留字段
            'P',                         # 处理标志（按照示例）
            '',                          # 保留字段
            date_time_str                # 消息日期时间
        ]
        message.append(self.FIELD_SEP.join(header_record))

        # 添加患者记录（按照示例格式）
        patient_record = [
            self.RECORD_TYPE_PATIENT,
            '1'                          # 序列号
        ]
        message.append(self.FIELD_SEP.join(patient_record))

        # 添加订单记录（按照示例格式）
        sample_id = sample_info['sample_id']
        tests = list(sample_info['results'].keys())
        test_code = tests[0] if tests else ''

        order_record = [
            self.RECORD_TYPE_ORDER,
            '1',                        # 序列号
            sample_id,                  # 样本ID
            '',                          # 保留字段
            f"^^^{test_code}^^^1",       # 测试请求
            'R',                         # 优先级（按照示例）
            '',                          # 保留字段
            date_time_str,               # 样本采集时间
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            'Serum',                     # 样本类型（按照示例）
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            'F'                          # 样本状态（已完成）
        ]
        message.append(self.FIELD_SEP.join(order_record))

        # 添加制造商信息记录（按照示例格式）
        manufacturer_record = [
            'M',                        # 记录类型
            '1',                        # 序列号
            'SHD^CEN:NG^V1^O',           # 制造商信息（按照示例）
            'RD',                        # 参考数据（按照示例）
            '1379UN'                     # 单位（按照示例）
        ]
        message.append(self.FIELD_SEP.join(manufacturer_record))

        # 添加结果记录和注释记录（按照示例格式）
        results = sample_info['results']
        for i, (test_code, result_info) in enumerate(results.items(), 1):
            # 添加结果记录
            result_record = [
                self.RECORD_TYPE_RESULT,
                str(i),                    # 序列号
                f"^^^{test_code}^^^1^RLU^{test_code}#0",  # 测试信息（按照示例格式）
                str(result_info['value']),  # 结果值
                result_info['unit'],  # 单位
                '',  # 参考范围
                '',  # 标志
                '',  # 异常标志
                'F',  # 结果状态（已完成）
                '',  # 保留字段
                '1234^No Review',  # 审核信息（按照示例）
                '',  # 保留字段
                '',  # 保留字段
                date_time_str,  # 测试时间
                'SP01066^CM01256'  # 操作者信息（按照示例）
            ]
            message.append(self.FIELD_SEP.join(result_record))

            # 添加注释记录
            comment_record = [
                'C',                        # 记录类型
                '1',                        # 序列号
                '',                          # 保留字段
                'PREAG^200801',              # 注释内容（按照示例）
                'G'                          # 注释类型（按照示例）
            ]
            message.append(self.FIELD_SEP.join(comment_record))

        # 添加终止记录（按照示例格式）
        terminator_record = [
            self.RECORD_TYPE_TERMINATOR,
            '1',  # 消息中的记录数
            'N'   # 校验和标志（按照示例）
        ]
        message.append(self.FIELD_SEP.join(terminator_record))

        # 组合消息，添加记录分隔符
        astm_message = self.RECORD_SEP.join(message) + self.RECORD_SEP

        # 添加STX、ETX和校验和
        stx = '\x02'  # 开始传输字符
        etx = '\x03'  # 结束传输字符
        lf = '\x0a'   # 换行符

        # 计算校验和（Atellica Solution二进制和算法）
        # 校验和覆盖范围：从头部的第二个字符到校验和本身之前的尾部最后一个字符
        # 使用二进制和算法，取模256
        checksum = 0

        # 计算消息内容和ETX的校验和
        message_plus_etx = astm_message + etx

        # 计算拼接后整个字符串的校验和（二进制和，取模256）
        for char in message_plus_etx:
            checksum += ord(char)
        checksum %= 256  # 取模256

        # 确保校验和是两位十六进制格式
        checksum_hex = f'{checksum:02X}'

        # 验证校验和计算
        self.logger.log_lis(
            f"Checksum calculation: message='{repr(astm_message)}', checksum={checksum_hex}")

        # 构建最终消息（按照示例格式：STX + 消息 + ETX + 校验和 + CR + LF）
        final_message = stx + astm_message + etx + checksum_hex + self.RECORD_SEP + lf

        # 验证校验和计算是否正确
        self.logger.log_lis(
            f"Checksum calculation: message length={len(astm_message)}, checksum={checksum_hex}")

        self.logger.log_lis(
            f"Built result message for sample {sample_info['sample_id']}")
        self.logger.log_lis(f"Result message content: {repr(final_message)}")

        return final_message

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

        # 添加头记录（按照示例格式）
        header_record = [
            '1' + self.RECORD_TYPE_HEADER,  # 在H前面加数字1
            '\^&',                      # 字段分隔符定义
            '',                          # 保留字段
            '',                          # 保留字段
            'UIW_LIS',                   # 发送方ID（按照示例）
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            'LIS_ID',                    # 消息控制ID（按照示例）
            '',                          # 保留字段
            'P',                         # 处理标志（按照示例）
            '',                          # 保留字段
            date_time_str                # 消息日期时间
        ]
        message.append(self.FIELD_SEP.join(header_record))

        # 添加查询记录（按照示例格式）
        query_record = [
            'Q',                        # 查询记录类型
            '1',                        # 记录序号
            '^' + barcode,              # 样本ID/条码（前面加^）
            '^' + barcode,              # 重复条码（按照示例）
            'ALL',                      # 测试请求（按照示例）
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            '',                          # 保留字段
            'O'                          # 订单标志（按照示例）
        ]
        message.append(self.FIELD_SEP.join(query_record))

        # 添加终止记录（按照示例格式）
        terminator_record = [
            self.RECORD_TYPE_TERMINATOR,
            '1',  # 消息中的记录数
            'N'   # 校验和标志（按照示例）
        ]
        message.append(self.FIELD_SEP.join(terminator_record))

        # 组合消息，添加记录分隔符
        astm_message = self.RECORD_SEP.join(message) + self.RECORD_SEP

        # 在1前面加stx，最后加校验
        stx = '\x02'  # 开始传输字符
        etx = '\x03'  # 结束传输字符
        lf = '\x0a'   # 换行符（按照示例）

        # 计算校验和（Atellica Solution二进制和算法）
        # 校验和覆盖范围：从头部的第二个字符到校验和本身之前的尾部最后一个字符
        # 使用二进制和算法，取模256
        checksum = 0

        # 计算消息内容和ETX的校验和
        message_plus_etx = astm_message + etx

        # 计算拼接后整个字符串的校验和（二进制和，取模256）
        for char in message_plus_etx:
            checksum += ord(char)
        checksum %= 256  # 取模256

        # 确保校验和是两位十六进制格式
        checksum_hex = f'{checksum:02X}'

        # 记录校验和计算结果
        self.logger.log_lis(
            f"Checksum calculation for barcode {barcode}: message+etx length={len(message_plus_etx)}, checksum={checksum_hex}")

        # 构建最终消息（按照示例格式：STX + 消息 + ETX + 校验和 + CR + LF）
        final_message = stx + astm_message + etx + checksum_hex + self.RECORD_SEP + lf

        self.logger.log_lis(f"Built query message for barcode: {barcode}")
        self.logger.log_lis(f"Query message content: {repr(final_message)}")

        return final_message

    def _get_test_name(self, test_code):
        """根据测试代码获取测试名称
        Args:
            test_code: 测试代码
        Returns:
            str: 测试名称
        """
        test_names = {
            'C3': 'C3',
            'TEST002': '生化常规',
            'TEST003': '肝功能',
            'TEST004': '肾功能'
        }
        # return test_names.get(test_code, test_code)
        return test_names.get(test_code, "未知项目")

    def set_error_callback(self, callback):
        """设置错误回调函数

        Args:
            callback: 错误回调函数，接收错误信息作为参数
        """
        self.error_callback = callback

    def send_result(self, barcode, test_items):
        """发送结果到LIS服务器

        Args:
            barcode: 样本条码
            test_items: 项目列表，每个项目格式为 "测试代码 - 测试名称" 或 "测试代码"

        Returns:
            tuple: (success, message) 成功状态和消息
        """
        import time
        import random

        if not barcode:
            return False, "请输入条码"

        if not test_items:
            return False, "请输入测试项目"

        # 解析测试项目并生成随机结果
        results = {}
        for item in test_items:
            item = item.strip()
            if item and not item.startswith('错误:'):
                # 提取测试代码（假设格式为 "测试代码 - 测试名称"）
                if ' - ' in item:
                    test_code = item.split(' - ')[0]
                else:
                    test_code = item
                # 为每个测试项目生成随机结果
                results[test_code] = {
                    'value': round(random.uniform(10, 100), 2),
                    'unit': '',
                    'flags': '',
                    'status': 'completed',
                    'timestamp': time.time()
                }

        if not results:
            return False, "未找到测试项目"

        # 检查LIS连接状态
        if not self.is_connected:
            return False, "LIS服务器未连接，无法发送结果"

        # 检查LIS客户端状态
        if self.state != 'idle':
            return False, f"LIS客户端当前状态为 {self.state}，无法发送结果"

        # 构建样本信息
        sample_info = {
            'sample_id': barcode,
            'results': results,
            'patient_info': {}
        }

        try:
            # 构建ASTM结果消息
            result_message = self._build_result_message(sample_info)

            # 发送结果到LIS服务器
            self._send_message(result_message)

            # 构建结果数据字符串用于日志
            result_data = f"条码: {barcode}\n"
            for test_code, result in results.items():
                result_data += f"{test_code}: {result['value']}\n"

            # 记录发送结果
            self.logger.log_lis(f"发送LIS结果: {result_data}")
            self.logger.info(f"发送LIS结果: {result_data}")

            return True, "结果发送成功"
        except Exception as e:
            # 记录发送失败
            error_msg = f"发送结果失败: {str(e)}"
            self.logger.error(error_msg)
            self.logger.log_lis(error_msg)
            return False, error_msg

    def generate_results(self, apply_items, barcode):
        """生成测试结果

        Args:
            apply_items: 申请项目列表，每个项目格式为 "测试代码 - 测试名称" 或 "测试代码"
            barcode: 样本条码

        Returns:
            str: 生成的结果数据字符串，格式为：
                条码: 1234567890
                TEST1: 123.45
                TEST2: 678.90
        """
        import random
        import time

        if not apply_items:
            return ""

        # 解析测试项目
        test_items = []
        for item in apply_items:
            item = item.strip()
            if item and not item.startswith('错误:'):
                # 提取测试代码（假设格式为 "测试代码 - 测试名称"）
                if ' - ' in item:
                    test_code = item.split(' - ')[0]
                else:
                    test_code = item
                test_items.append(test_code)

        if not test_items:
            return ""

        # 为每个测试项目生成随机结果
        results = {}
        for test in test_items:
            results[test] = {
                'value': round(random.uniform(10, 100), 2),
                'status': 'completed',
                'timestamp': time.time(),
                'unit': '',
                'flags': ''
            }

        # 构建结果消息
        result_data = f"条码: {barcode}\n"
        for test, result in results.items():
            result_data += f"{test}: {result['value']}\n"

        return result_data
