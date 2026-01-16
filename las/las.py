#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAS模块 - uRAP协议服务端实现
"""

import socket
import threading
import struct
import time
import binascii


class LASServer:
    """LAS服务器，实现uRAP协议"""
    
    def __init__(self, config_manager, logger, core):
        """初始化LAS服务器
        
        Args:
            config_manager: 配置管理器实例
            logger: 日志管理器实例
            core: 核心模拟逻辑实例
        """
        self.config_manager = config_manager
        self.logger = logger
        self.core = core
        
        # 配置信息
        self.config = config_manager.get_las_config()
        self.host = self.config.get('host', '0.0.0.0')
        self.port = self.config.get('port', 10001)
        
        # 服务器状态
        self.server_socket = None
        self.is_running = False
        self.connections = []
        self.connection_lock = threading.Lock()
        
        # Keep-Alive机制
        self.keep_alive_interval = self.config.get('keep_alive_interval', 15)  # 秒
        self.last_message_time = time.time()
        self.last_keep_alive_time = 0
        self.keep_alive_thread = None
        
        # 序列ID管理
        self.sequence_id = 1
        self.sequence_lock = threading.Lock()
        
        # 会话状态管理
        self.CONVERSATION_STATUS_LISTENING = 'listening'
        self.CONVERSATION_STATUS_INITIALIZATION = 'initialization'
        self.CONVERSATION_STATUS_CONNECTED = 'connected'
        self.conversation_status = self.CONVERSATION_STATUS_LISTENING
        
        # 初始化阶段已处理的请求类型集合
        self.initialized_requests = set()
        
        # 手动操作相关
        self.pending_requests = []
        self.ui = None
        
        # 核心模块引用
        self.core = core
        
        # 消息类型常量
        self.MSG_TYPE_HANDSHAKE = 0x0001
        self.MSG_TYPE_ACK = 0x0000
        self.MSG_TYPE_KEEPALIVE = 0x0005
        self.MSG_TYPE_INSTRUMENT_HEALTH_REQUEST = 0x0201
        self.MSG_TYPE_INSTRUMENT_HEALTH_RESPONSE = 0x0202
        self.MSG_TYPE_TEST_INVENTORY_REQUEST = 0x0203
        self.MSG_TYPE_TEST_INVENTORY_RESPONSE = 0x0204
        self.MSG_TYPE_ONBOARD_SAMPLE_INFO_REQUEST = 0x0207
        self.MSG_TYPE_ONBOARD_SAMPLE_INFO_RESPONSE = 0x0208
        self.MSG_TYPE_TRANSFER_STATUS_REQUEST = 0x0209
        self.MSG_TYPE_TRANSFER_STATUS_RESPONSE = 0x020A
        self.MSG_TYPE_CONSUMABLE_INVENTORY_REQUEST = 0x020B
        self.MSG_TYPE_CONSUMABLE_INVENTORY_RESPONSE = 0x020C
        self.MSG_TYPE_INITIALIZATION_COMPLETE = 0x020D
        self.MSG_TYPE_LOAD_UNLOAD_REQUEST = 0x0303
        self.MSG_TYPE_LOAD_UNLOAD_RESPONSE = 0x0304
        self.MSG_TYPE_ADD_QUEUE_REQUEST = 0x0401
        self.MSG_TYPE_ADD_QUEUE_RESPONSE = 0x0402
        self.MSG_TYPE_SKIP_QUEUE_REQUEST = 0x0403
        self.MSG_TYPE_SKIP_QUEUE_RESPONSE = 0x0404
        self.MSG_TYPE_CLEAR_QUEUE_REQUEST = 0x0405
        self.MSG_TYPE_CLEAR_QUEUE_RESPONSE = 0x0406
        
        # 状态常量
        self.STATUS_GREEN = 1
        self.STATUS_YELLOW = 2
        self.STATUS_RED = 3
        
        self.logger.info(f"LASServer initialized, listening on {self.host}:{self.port}")
    
    def _keep_alive_loop(self, conn):
        """Keep-Alive循环
        
        Args:
            conn: 连接 socket
        """
        while self.is_running:
            try:
                time.sleep(1)
                
                current_time = time.time()
                time_since_last_msg = current_time - self.last_message_time
                time_since_keepalive = current_time - self.last_keep_alive_time
                
                # 如果超过keep_alive_interval没有发送Keep-Alive消息，则发送一个
                if time_since_keepalive >= self.keep_alive_interval:
                    # 检查连接是否仍然活跃（超过3倍keep_alive_interval没有消息则断开）
                    if time_since_last_msg >= self.keep_alive_interval * 3:
                        self.logger.warning("Keep-Alive timeout, closing connection")
                        self.logger.log_las("Keep-Alive timeout, closing connection")
                        try:
                            conn.close()
                        except:
                            pass
                        break
                    
                    # 发送Keep-Alive消息
                    self._send_keepalive(conn)
                    self.last_keep_alive_time = current_time
                    
            except Exception as e:
                if self.is_running:
                    self.logger.error(f"Error in Keep-Alive loop: {str(e)}")
                break
    
    def _send_keepalive(self, conn):
        """发送Keep-Alive消息
        
        Args:
            conn: 连接 socket
        """
        try:
            # Keep-Alive消息体为空
            body = b''
            
            # 构建完整消息
            message, sequence_id = self._build_message(
                self.MSG_TYPE_KEEPALIVE,
                body
            )
            
            # 记录发送的原始数据
            message_hex = binascii.hexlify(message).decode('ascii')
            self.logger.log_las_raw('SENT', message_hex)
            # 发送消息
            conn.sendall(message)
            
            self.logger.info(f"LAS Keep-Alive message sent, SeqID=0x{sequence_id:04x}")
            self.logger.log_las(f"Keep-Alive sent, SeqID=0x{sequence_id:04x}")
            
        except Exception as e:
            self.logger.error(f"Error sending LAS Keep-Alive: {str(e)}")
            self.logger.log_las(f"Error sending Keep-Alive: {str(e)}")
    
    def _handle_keepalive(self, conn, header):
        """处理Keep-Alive消息
        
        Args:
            conn: 连接 socket
            header: 消息头
        """
        self.logger.info(f"LAS Keep-Alive received, SeqID=0x{header['sequence_id']:04x}")
        self.logger.log_las(f"Keep-Alive received, SeqID=0x{header['sequence_id']:04x}")
    
    def start(self):
        """启动LAS服务器"""
        if self.is_running:
            self.logger.warning("LASServer is already running")
            return
        
        try:
            # 创建TCP服务器 socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.is_running = True
            self.logger.info(f"LASServer started, listening on {self.host}:{self.port}")
            
            # 启动接受连接的线程
            accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            accept_thread.start()
            
        except Exception as e:
            self.logger.error(f"Failed to start LASServer: {str(e)}")
            self.is_running = False
    
    def stop(self):
        """停止LAS服务器"""
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
            
            self.logger.info("LASServer stopped")
        except Exception as e:
            self.logger.error(f"Error stopping LASServer: {str(e)}")
    
    def _accept_connections(self):
        """接受客户端连接"""
        while self.is_running:
            try:
                conn, addr = self.server_socket.accept()
                with self.connection_lock:
                    self.connections.append(conn)
                
                self.logger.info(f"LAS connection established from {addr[0]}:{addr[1]}")
                self.logger.log_las(f"Connection established: {addr[0]}:{addr[1]}")
                
                # 为每个连接创建处理线程
                conn_thread = threading.Thread(
                    target=self._handle_connection,
                    args=(conn, addr),
                    daemon=True
                )
                conn_thread.start()
                
            except socket.error as e:
                if self.is_running:
                    self.logger.error(f"Error accepting LAS connection: {str(e)}")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in LAS accept thread: {str(e)}")
    
    def _handle_connection(self, conn, addr):
        """处理单个连接
        
        Args:
            conn: 连接 socket
            addr: 客户端地址
        """
        buffer = b''
        
        try:
            # 重置最后消息时间
            self.last_message_time = time.time()
            self.last_keep_alive_time = 0
            
            # 启动Keep-Alive线程
            self.keep_alive_thread = threading.Thread(target=self._keep_alive_loop, args=(conn,), daemon=True)
            self.keep_alive_thread.start()
            
            while self.is_running:
                # 接收数据
                data = conn.recv(4096)
                if not data:
                    break
                
                buffer += data
                
                # 处理缓冲区中的消息
                while True:
                    # 查找消息起始标志 STX (0x02)
                    stx_pos = buffer.find(b'\x02')
                    if stx_pos == -1:
                        break
                    
                    # 检查是否有足够字节读取消息长度 (STX + 2 bytes length)
                    if len(buffer) < stx_pos + 3:
                        break
                    
                    # 读取消息长度 (2 bytes after STX, total bytes including STX)
                    message_length = struct.unpack_from('!H', buffer, stx_pos + 1)[0]
                    print(f"Message length: {message_length}")
                    
                    # 检查是否有足够字节读取完整消息
                    if len(buffer) < stx_pos + message_length:
                        break
                    
                    # 提取完整消息
                    message = buffer[stx_pos:stx_pos + message_length]
                    print(f"Received message: {message}")
                    
                    # 验证最后一个字节是否为 ETX (0x03)
                    if message[-1:] != b'\x03':
                        # 无效消息，跳过
                        buffer = buffer[stx_pos + 1:]
                        continue
                    
                    # 更新缓冲区，移除已处理的消息
                    buffer = buffer[stx_pos + message_length:]
                    # 记录接收的原始数据
                    message_hex = binascii.hexlify(message).decode('ascii')
                    print(f"Received message hex: {message_hex}")
                    self.logger.log_las_raw('RECEIVED', message_hex)
                    
                    # 处理消息
                    self._process_message(conn, addr, message)
                    
        except socket.error as e:
            self.logger.error(f"LAS connection error with {addr[0]}:{addr[1]}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error handling LAS connection from {addr[0]}:{addr[1]}: {str(e)}")
        finally:
            # 清理连接
            with self.connection_lock:
                if conn in self.connections:
                    self.connections.remove(conn)
            
            try:
                conn.close()
            except:
                pass
            
            self.logger.info(f"LAS connection closed with {addr[0]}:{addr[1]}")
            self.logger.log_las(f"Connection closed: {addr[0]}:{addr[1]}")
    
    def _process_message(self, conn, addr, message):
        """处理uRAP消息
        
        Args:
            conn: 连接 socket
            addr: 客户端地址
            message: uRAP消息
        """
        try:
            # 更新最后消息时间
            self.last_message_time = time.time()
            
            # 解析消息
            msg_header, msg_body, msg_footer = self._parse_message(message)
            
            if not msg_header:
                # 发送NACK
                self._send_ack(conn, msg_header.get('sequence_id', 0), 0x01)  # 0x01 = Message Not Understood
                return
            
            # 记录接收到的消息
            msg_hex = binascii.hexlify(message).decode('ascii')
            self.logger.log_las(f"Received message from {addr[0]}:{addr[1]}: Type=0x{msg_header['message_type']:04x}, SeqID=0x{msg_header['sequence_id']:04x}, Content={msg_hex}")
            
            # 处理ACK消息（任何状态下都必须能接收）
            message_type = msg_header['message_type']
            if message_type == self.MSG_TYPE_ACK:
                self._handle_ack(conn, msg_header, msg_body)
                return
            
            # 根据会话状态处理消息
            if self.conversation_status == self.CONVERSATION_STATUS_LISTENING:
                self._process_listening_state(conn, msg_header, msg_body, addr)
            elif self.conversation_status == self.CONVERSATION_STATUS_INITIALIZATION:
                self._process_initialization_state(conn, msg_header, msg_body, addr)
            elif self.conversation_status == self.CONVERSATION_STATUS_CONNECTED:
                self._process_connected_state(conn, msg_header, msg_body, addr)
                
        except Exception as e:
            self.logger.error(f"Error processing LAS message: {str(e)}")
            self.logger.log_las(f"Error processing message: {str(e)}")
    
    def _handle_ack(self, conn, header, body):
        """处理ACK消息
        
        Args:
            conn: 连接 socket
            header: 消息头
            body: 消息体
        """
        try:
            return_code = body[0] if body else 0x00
            self.logger.log_las(f"Received ACK for SeqID=0x{header['return_sequence_id']:04x}, ReturnCode=0x{return_code:02x}")
            
            if return_code == 0x00:
                # 检查是否是对主动发送的握手消息的ACK
                if hasattr(self, '_awaiting_handshake_ack') and self._awaiting_handshake_ack:
                    # 收到对主动握手消息的ACK，切换到initialization状态
                    self.conversation_status = self.CONVERSATION_STATUS_INITIALIZATION
                    self._awaiting_handshake_ack = False
                    self.logger.info(f"Handshake completed, switching to {self.CONVERSATION_STATUS_INITIALIZATION} state")
                    self.logger.log_las(f"Handshake completed, switching to {self.CONVERSATION_STATUS_INITIALIZATION} state")
                    # 重置初始化请求集合
                    self.initialized_requests.clear()
                
                # 检查是否是对初始化完成消息的ACK
                # 这里需要通过sequence_id来判断，暂时简化处理
                # 假设收到ACK后就切换到connected状态
                elif self.conversation_status == self.CONVERSATION_STATUS_INITIALIZATION:
                    # 收到初始化完成消息的ACK，切换到connected状态
                    self.conversation_status = self.CONVERSATION_STATUS_CONNECTED
                    self.logger.info(f"Initialization completed, switching to {self.CONVERSATION_STATUS_CONNECTED} state")
                    self.logger.log_las(f"Initialization completed, switching to {self.CONVERSATION_STATUS_CONNECTED} state")
                
        except Exception as e:
            self.logger.error(f"Error handling LAS ACK: {str(e)}")
            self.logger.log_las(f"Error handling ACK: {str(e)}")
    
    def _process_listening_state(self, conn, header, body, addr):
        """处理监听状态下的消息
        
        Args:
            conn: 连接 socket
            header: 消息头
            body: 消息体
            addr: 客户端地址
        """
        message_type = header['message_type']
        
        # 只有握手消息是合法的
        if message_type == self.MSG_TYPE_HANDSHAKE:
            # 发送ACK
            self._send_ack(conn, header['sequence_id'], 0x00)  # 0x00 = ACK
            # 处理握手
            self._handle_handshake(conn, header, body)
        else:
            # 发送0x03 ACK，不处理其他消息
            self.logger.warning(f"Invalid message type {message_type} in listening state")
            self.logger.log_las(f"Invalid message type {message_type} in listening state")
            self._send_ack(conn, header['sequence_id'], 0x03)  # 0x03 = Message Type Not Supported
    
    def _process_initialization_state(self, conn, header, body, addr):
        """处理初始化状态下的消息
        
        Args:
            conn: 连接 socket
            header: 消息头
            body: 消息体
            addr: 客户端地址
        """
        message_type = header['message_type']
        
        # 检查是否为合法的初始化请求消息
        valid_init_messages = {
            self.MSG_TYPE_CLEAR_QUEUE_REQUEST,
            self.MSG_TYPE_INSTRUMENT_HEALTH_REQUEST,
            self.MSG_TYPE_TEST_INVENTORY_REQUEST,
            self.MSG_TYPE_ONBOARD_SAMPLE_INFO_REQUEST,
            self.MSG_TYPE_TRANSFER_STATUS_REQUEST,
            self.MSG_TYPE_CONSUMABLE_INVENTORY_REQUEST
        }
        
        if message_type in valid_init_messages:
            # 发送ACK
            self._send_ack(conn, header['sequence_id'], 0x00)  # 0x00 = ACK
            
            # 处理消息
            if message_type == self.MSG_TYPE_INSTRUMENT_HEALTH_REQUEST:
                self._handle_instrument_health_request(conn, header)
            elif message_type == self.MSG_TYPE_TEST_INVENTORY_REQUEST:
                self._handle_test_inventory_request(conn, header)
            elif message_type == self.MSG_TYPE_ONBOARD_SAMPLE_INFO_REQUEST:
                self._handle_onboard_sample_info_request(conn, header)
            elif message_type == self.MSG_TYPE_CONSUMABLE_INVENTORY_REQUEST:
                self._handle_consumable_inventory_request(conn, header)
            elif message_type == self.MSG_TYPE_TRANSFER_STATUS_REQUEST:
                self._handle_transfer_status_request(conn, header)
            elif message_type == self.MSG_TYPE_CLEAR_QUEUE_REQUEST:
                self._handle_clear_queue_request(conn, header)
            
            # 记录已处理的请求类型
            self.initialized_requests.add(message_type)
            
            # 检查是否所有初始化请求都已处理完成
            if self.initialized_requests.issuperset(valid_init_messages):
                self._handle_initialization_complete(conn)
        else:
            # 发送0x03 ACK，不处理其他消息
            self.logger.warning(f"Invalid message type {message_type} in initialization state")
            self.logger.log_las(f"Invalid message type {message_type} in initialization state")
            self._send_ack(conn, header['sequence_id'], 0x03)  # 0x03 = Message Type Not Supported
    
    def _process_connected_state(self, conn, header, body, addr):
        """处理连接状态下的消息
        
        Args:
            conn: 连接 socket
            header: 消息头
            body: 消息体
            addr: 客户端地址
        """
        message_type = header['message_type']
        
        # 检查是否为合法的连接状态消息
        valid_connected_messages = {
            self.MSG_TYPE_KEEPALIVE,
            self.MSG_TYPE_ADD_QUEUE_REQUEST,
            self.MSG_TYPE_SKIP_QUEUE_REQUEST,
            self.MSG_TYPE_CLEAR_QUEUE_REQUEST,
            self.MSG_TYPE_LOAD_UNLOAD_REQUEST
        }
        
        if message_type in valid_connected_messages:
            # 发送ACK
            self._send_ack(conn, header['sequence_id'], 0x00)  # 0x00 = ACK
            
            # 处理消息
            if message_type == self.MSG_TYPE_KEEPALIVE:
                self._handle_keepalive(conn, header)
            elif message_type == self.MSG_TYPE_LOAD_UNLOAD_REQUEST:
                self._handle_load_unload_request(conn, header, body)
            elif message_type == self.MSG_TYPE_ADD_QUEUE_REQUEST:
                self._handle_add_queue_request(conn, header, body)
            elif message_type == self.MSG_TYPE_SKIP_QUEUE_REQUEST:
                self._handle_skip_queue_request(conn, header, body)
            elif message_type == self.MSG_TYPE_CLEAR_QUEUE_REQUEST:
                self._handle_clear_queue_request(conn, header)
        else:
            # 发送0x03 ACK，不处理其他消息
            self.logger.warning(f"Invalid message type {message_type} in connected state")
            self.logger.log_las(f"Invalid message type {message_type} in connected state")
            self._send_ack(conn, header['sequence_id'], 0x03)  # 0x03 = Message Type Not Supported
    
    def _handle_initialization_complete(self, conn):
        """处理初始化完成逻辑
        
        Args:
            conn: 连接 socket
        """
        try:
            # 检查IP0和IP1的锁定状态
            health_status = self.core.get_instrument_health()
            # 默认IP0和IP1都是unlocked状态
            ip0_locked = False
            ip1_locked = False
            
            # 检查是否有IP处于locked状态
            if health_status['lock_ownership']:
                # lock_ownership[0] 是 IP0 的状态，2表示locked
                ip0_locked = len(health_status['lock_ownership']) > 0 and health_status['lock_ownership'][0] == 2
                ip1_locked = len(health_status['lock_ownership']) > 1 and health_status['lock_ownership'][1] == 2
            
            # 如果有任意一个IP为locked状态，先发送LOAD_UNLOAD_RESPONSE
            if ip0_locked or ip1_locked:
                self._send_load_unload_response(conn)
            
            # 发送初始化完成消息
            self._send_initialization_complete(conn)
            
            # 收到ACK后会切换到connected状态
            
        except Exception as e:
            self.logger.error(f"Error handling initialization complete: {str(e)}")
            self.logger.log_las(f"Error handling initialization complete: {str(e)}")
    
    def _send_load_unload_response(self, conn):
        """发送LOAD_UNLOAD_RESPONSE消息
        
        Args:
            conn: 连接 socket
        """
        try:
            # 获取相关状态
            health_status = self.core.get_instrument_health()
            ready_to_load = self.core.get_ready_to_load()
            return_ready_count = self.core.get_return_ready_count()
            
            # 构建空的响应消息体
            interface_position_index = 0  # 默认IP0
            load_sample_id_len = 0
            load_sample_id_bytes = b''
            load_status = 1  # 1=成功
            unload_sample_id_len = 0
            unload_sample_id_bytes = b''
            unload_status = 1  # 1=成功
            sample_status = 0  # 0=无样本
            onboard_count = health_status['on_board_tube_count']
            completed_count = health_status['completed_tube_count']
            
            body = struct.pack(
                f'!B B {load_sample_id_len}s B B {unload_sample_id_len}s B B B H H B H',
                interface_position_index,
                load_sample_id_len,
                load_sample_id_bytes,
                load_status,
                unload_sample_id_len,
                unload_sample_id_bytes,
                unload_status,
                sample_status,
                onboard_count,
                completed_count,
                ready_to_load,
                return_ready_count
            )
            
            # 构建完整消息
            message, sequence_id = self._build_message(
                self.MSG_TYPE_LOAD_UNLOAD_RESPONSE,
                body
            )
            
            # 发送消息
            conn.sendall(message)
            
            self.logger.info(f"LAS load/unload response sent, SeqID=0x{sequence_id:04x}")
            self.logger.log_las(f"Load/Unload response sent, SeqID=0x{sequence_id:04x}")
            
        except Exception as e:
            self.logger.error(f"Error sending LAS load/unload response: {str(e)}")
            self.logger.log_las(f"Error sending load/unload response: {str(e)}")
    
    def _parse_message(self, message):
        """解析uRAP消息
        
        Args:
            message: uRAP消息
            
        Returns:
            tuple: (header, body, footer) 或 (None, None, None) 如果解析失败
        """
        try:
            # 消息格式：STX + Header + Body + Footer + ETX
            # Header: STX (1) + Message Length (2) + Sequence ID (2) + Return Sequence ID (2) + 
            #         Message Type (2) + Time Stamp (8) + Instrument ID (1)
            # Footer: Checksum (2) + ETX (1)
            
            if len(message) < 18:  # 最小消息长度
                return None, None, None
            
            # 解析消息头
            msg_len = struct.unpack_from('!H', message, 1)[0]
            sequence_id = struct.unpack_from('!H', message, 3)[0]
            return_sequence_id = struct.unpack_from('!H', message, 5)[0]
            message_type = struct.unpack_from('!H', message, 7)[0]
            timestamp = message[9:17]
            instrument_id = message[17]
            
            header = {
                'message_length': msg_len,
                'sequence_id': sequence_id,
                'return_sequence_id': return_sequence_id,
                'message_type': message_type,
                'timestamp': timestamp,
                'instrument_id': instrument_id
            }
            
            # 解析消息体和消息尾
            body_end = len(message) - 3  # 减去Checksum(2)和ETX(1)
            body = message[18:body_end]
            checksum = message[body_end:body_end+2]
            
            footer = {
                'checksum': checksum
            }
            
            # 验证消息长度
            if msg_len != len(message):
                self.logger.warning(f"LAS message length mismatch: expected {msg_len}, got {len(message)}")
                return None, None, None
            
            # 验证校验和
            calculated_checksum = self._calculate_checksum(message[0:body_end])
            if checksum != calculated_checksum:
                self.logger.warning(f"LAS message checksum mismatch: expected {checksum.hex()}, got {calculated_checksum.hex()}")
                return None, None, None
            
            return header, body, footer
            
        except Exception as e:
            self.logger.error(f"Error parsing LAS message: {str(e)}")
            return None, None, None
    
    def _calculate_checksum(self, data):
        """计算校验和
        
        Args:
            data: 要计算校验和的数据
            
        Returns:
            bytes: 校验和（2字节）
        """
        # 计算二进制和，取模256，转换为2位十六进制ASCII字符串
        checksum = sum(data) % 256
        return f"{checksum:02X}".encode('ascii')
    
    def _build_message(self, message_type, body, return_sequence_id=0):
        """构建uRAP消息
        
        Args:
            message_type: 消息类型
            body: 消息体
            return_sequence_id: 返回序列ID
            
        Returns:
            bytes: 完整的uRAP消息
        """
        # 获取序列ID
        with self.sequence_lock:
            sequence_id = self.sequence_id
            self.sequence_id = (self.sequence_id % 0xFFFF) + 1
        
        # 构建消息头
        current_time = self._get_current_timestamp()
        instrument_id = int(self.config.get('instrument_id', '0xFF'), 16)
        
        # 计算消息长度（STX + Header + Body + Footer + ETX）
        header_len = 1 + 2 + 2 + 2 + 2 + 8 + 1  # STX(1) + Header fields
        footer_len = 2 + 1  # Checksum(2) + ETX(1)
        msg_len = header_len + len(body) + footer_len
        
        # 构建消息头
        header = struct.pack(
            '!cH HHH 8sc',
            b'\x02',  # STX
            msg_len,
            sequence_id,
            return_sequence_id,
            message_type,
            current_time,
            bytes([instrument_id])
        )
        
        # 计算校验和（包含头和体，不包含尾）
        checksum_data = header[1:] + body  # 去掉STX
        checksum = self._calculate_checksum(checksum_data)
        
        # 构建完整消息
        message = header + body + checksum + b'\x03'  # ETX
        
        return message, sequence_id
    
    def _get_current_timestamp(self):
        """获取当前时间戳（8字节）
        
        Returns:
            bytes: 8字节时间戳，格式：年(2字节)+月(1)+日(1)+时(1)+分(1)+秒(1)+毫秒(2)
        """
        # 获取当前时间
        current = time.localtime()
        milliseconds = int((time.time() % 1) * 1000)
        
        # 构建时间戳各字段
        year = current.tm_year - 2000  # 从2000年开始计算
        month = current.tm_mon
        day = current.tm_mday
        hour = current.tm_hour
        minute = current.tm_min
        second = current.tm_sec
        
        # 按照uRAP协议格式打包：年(2字节)+月(1)+日(1)+时(1)+分(1)+秒(1)+毫秒(2)
        timestamp = struct.pack('!HBBBBBH', 
                               year, month, day, hour, minute, second, milliseconds)
        return timestamp
    
    def _send_ack(self, conn, sequence_id, return_code):
        """发送ACK/NACK消息
        
        Args:
            conn: 连接 socket
            sequence_id: 要确认的消息序列ID
            return_code: 0x00=ACK, 0x01=NACK, 0x03=Message Type Not Supported
        """
        try:
            # 构建ACK消息体
            body = bytes([return_code])
            
            # 构建完整消息
            message, _ = self._build_message(
                self.MSG_TYPE_ACK,
                body,
                return_sequence_id=sequence_id
            )
            
            # 发送消息
            conn.sendall(message)
            
            # 记录日志
            ack_type = "ACK" if return_code == 0x00 else "NACK"
            self.logger.log_las(f"Sent {ack_type} for SeqID=0x{sequence_id:04x}, ReturnCode=0x{return_code:02x}")
            
        except Exception as e:
            self.logger.error(f"Error sending LAS ACK: {str(e)}")
            self.logger.log_las(f"Error sending ACK: {str(e)}")
    
    def _handle_handshake(self, conn, header, body):
        """处理握手消息
        
        Args:
            conn: 连接 socket
            header: 消息头
            body: 消息体
        """
        try:
            # 解析握手消息体
            # 格式：Protocol Version (2) + Instrument Type (2) + Capability Version (2) + 
            #       Software Version (2) + Instrument ID (1) + FL + Instrument Serial # (n)
            if len(body) < 10:  # 最小握手消息体长度
                return
            
            protocol_version = struct.unpack_from('!H', body, 0)[0]
            instrument_type = struct.unpack_from('!H', body, 2)[0]
            capability_version = struct.unpack_from('!H', body, 4)[0]
            software_version = struct.unpack_from('!H', body, 6)[0]
            instrument_id = body[8]
            serial_len = body[9]
            
            if len(body) < 10 + serial_len:
                return
            
            instrument_serial = body[10:10+serial_len].decode('ascii')
            
            self.logger.info(f"LAS handshake received: ProtocolVersion=0x{protocol_version:04x}, "
                           f"InstrumentType=0x{instrument_type:04x}, Serial={instrument_serial}")
            self.logger.log_las(f"Handshake received: Protocol=0x{protocol_version:04x}, "
                               f"Type=0x{instrument_type:04x}, Serial={instrument_serial}")
            
            # 发送握手响应（注意：这里是响应LAS的握手请求，不是主动发送）
            # 第一步：向LAS回复正常的ACK应答消息
            # 注意：ACK已经在_process_listening_state中发送了
            
            # 第二步：模拟器主动向LAS发送一条HANDSHAKE消息
            self._send_handshake_response(conn, 0)  # return_sequence_id=0表示主动发送
            
            # 等待LAS的ACK，收到后会在_handle_ack中切换到initialization状态
            # 这里设置一个标志，用于在收到ACK时识别这是对我们主动发送的握手消息的响应
            self._awaiting_handshake_ack = True
            
        except Exception as e:
            self.logger.error(f"Error handling LAS handshake: {str(e)}")
            self.logger.log_las(f"Error handling handshake: {str(e)}")
    
    def _send_handshake_response(self, conn, return_sequence_id):
        """发送握手响应
        
        Args:
            conn: 连接 socket
            return_sequence_id: 返回序列ID
        """
        try:
            # 构建握手响应消息体
            protocol_version = int(self.config.get('protocol_version', '0x0330'), 16)
            instrument_type = int(self.config.get('instrument_type', '0x0001'), 16)
            capability_version = int(self.config.get('capability_version', '0x0104'), 16)
            software_version = int(self.config.get('software_version', '0x0100'), 16)
            instrument_id = int(self.config.get('instrument_id', '0xFF'), 16)
            instrument_serial = self.config.get('instrument_serial', 'ATELLICA')
            serial_len = len(instrument_serial)
            
            body = struct.pack(
                f'!H H H H c B {serial_len}s',
                protocol_version,
                instrument_type,
                capability_version,
                software_version,
                bytes([instrument_id]),
                serial_len,
                instrument_serial.encode('ascii')
            )
            
            # 构建完整消息
            message, sequence_id = self._build_message(
                self.MSG_TYPE_HANDSHAKE,
                body,
                return_sequence_id=return_sequence_id
            )
            
            # 发送消息
            conn.sendall(message)
            
            # 记录发送的消息内容
            msg_hex = binascii.hexlify(message).decode('ascii')
            self.logger.info(f"LAS handshake response sent, SeqID=0x{sequence_id:04x}")
            self.logger.log_las(f"Handshake response sent, SeqID=0x{sequence_id:04x}, Content={msg_hex}")
            
        except Exception as e:
            self.logger.error(f"Error sending LAS handshake response: {str(e)}")
            self.logger.log_las(f"Error sending handshake response: {str(e)}")
    
    def _send_initialization_complete(self, conn):
        """发送初始化完成消息
        
        Args:
            conn: 连接 socket
        """
        try:
            # 初始化完成消息体为空
            body = b''
            
            # 构建完整消息
            message, sequence_id = self._build_message(
                self.MSG_TYPE_INITIALIZATION_COMPLETE,
                body
            )
            
            # 发送消息
            conn.sendall(message)
            
            # 记录发送的消息内容
            msg_hex = binascii.hexlify(message).decode('ascii')
            self.logger.info(f"LAS initialization complete message sent, SeqID=0x{sequence_id:04x}")
            self.logger.log_las(f"Initialization complete sent, SeqID=0x{sequence_id:04x}, Content={msg_hex}")
            
        except Exception as e:
            self.logger.error(f"Error sending LAS initialization complete message: {str(e)}")
            self.logger.log_las(f"Error sending initialization complete: {str(e)}")
    
    def _handle_instrument_health_request(self, conn, header):
        """处理仪器健康请求
        
        Args:
            conn: 连接 socket
            header: 消息头
        """
        try:
            # 获取仪器健康状态
            health_status = self.core.get_instrument_health()
            
            # 构建响应消息体
            body = struct.pack(
                '!BBB B',
                health_status['automation_interface_status'],
                health_status['instrument_process_status'],
                health_status['lis_connection_status'],
                health_status['interface_positions']
            )
            
            # 添加接口位置状态
            for i in range(health_status['interface_positions']):
                remote_status = health_status['remote_control_status'][i] if i < len(health_status['remote_control_status']) else 1
                lock_ownership = health_status['lock_ownership'][i] if i < len(health_status['lock_ownership']) else 2
                body += struct.pack('!BB', remote_status, lock_ownership)
            
            # 添加处理积压、样本获取延迟、在线试管数量、已完成试管数量
            body += struct.pack(
                '!HHHH',
                health_status['processing_backlog'],
                health_status['sample_acquisition_delay'],
                health_status['on_board_tube_count'],
                health_status['completed_tube_count']
            )
            
            # 构建完整消息
            message, sequence_id = self._build_message(
                self.MSG_TYPE_INSTRUMENT_HEALTH_RESPONSE,
                body,
                return_sequence_id=header['sequence_id']
            )
            
            # 发送消息
            conn.sendall(message)
            
            self.logger.info(f"LAS instrument health response sent, SeqID=0x{sequence_id:04x}")
            self.logger.log_las(f"Instrument health response sent, SeqID=0x{sequence_id:04x}")
            
        except Exception as e:
            self.logger.error(f"Error handling LAS instrument health request: {str(e)}")
            self.logger.log_las(f"Error handling instrument health request: {str(e)}")
    
    def _handle_test_inventory_request(self, conn, header):
        """处理测试库存请求
        
        Args:
            conn: 连接 socket
            header: 消息头
        """
        try:
            # 获取测试库存
            test_inventory = self.core.get_test_inventory()
            tests = test_inventory['tests']
            test_count = len(tests)
            
            # 构建响应消息体
            body = struct.pack('!H', test_count)
            
            # 添加每个测试项目
            for test in tests:
                test_name = test['name'].encode('ascii')
                body += struct.pack(f'!B {len(test_name)}s HH',
                                  len(test_name),
                                  test_name,
                                  test['count'],
                                  test['status'])
            
            # 构建完整消息
            message, sequence_id = self._build_message(
                self.MSG_TYPE_TEST_INVENTORY_RESPONSE,
                body,
                return_sequence_id=header['sequence_id']
            )
            
            # 发送消息
            conn.sendall(message)
            
            self.logger.info(f"LAS test inventory response sent, SeqID=0x{sequence_id:04x}, Tests={test_count}")
            self.logger.log_las(f"Test inventory response sent, SeqID=0x{sequence_id:04x}, Tests={test_count}")
            
        except Exception as e:
            self.logger.error(f"Error handling LAS test inventory request: {str(e)}")
            self.logger.log_las(f"Error handling test inventory request: {str(e)}")
    
    def _handle_onboard_sample_info_request(self, conn, header):
        """处理在线样本信息请求
        
        Args:
            conn: 连接 socket
            header: 消息头
        """
        try:
            # 获取所有样本
            samples = self.core.get_all_samples()
            onboard_samples = [sample for sample in samples.values() if sample['status'] != 'completed']
            onboard_count = len(onboard_samples)
            
            # 构建响应消息体
            body = struct.pack('!H', onboard_count)
            
            # 添加每个在线样本
            for sample in onboard_samples:
                sample_id = sample['sample_id'].encode('ascii')
                body += struct.pack(f'!B {len(sample_id)}s',
                                  len(sample_id),
                                  sample_id)
            
            # 添加已移除样本数量（这里简化处理，返回0）
            body += struct.pack('!H', 0)
            
            # 构建完整消息
            message, sequence_id = self._build_message(
                self.MSG_TYPE_ONBOARD_SAMPLE_INFO_RESPONSE,
                body,
                return_sequence_id=header['sequence_id']
            )
            
            # 发送消息
            conn.sendall(message)
            
            self.logger.info(f"LAS onboard sample info response sent, SeqID=0x{sequence_id:04x}, Samples={onboard_count}")
            self.logger.log_las(f"Onboard sample info response sent, SeqID=0x{sequence_id:04x}, Samples={onboard_count}")
            
        except Exception as e:
            self.logger.error(f"Error handling LAS onboard sample info request: {str(e)}")
            self.logger.log_las(f"Error handling onboard sample info request: {str(e)}")
    
    def _handle_consumable_inventory_request(self, conn, header):
        """处理耗材库存请求
        
        Args:
            conn: 连接 socket
            header: 消息头
        """
        try:
            # 获取耗材库存
            consumable_inventory = self.core.get_consumable_inventory()
            modules = consumable_inventory['modules']
            module_count = len(modules)
            
            # 构建响应消息体
            body = struct.pack('!B', module_count)
            
            # 添加每个模块的耗材信息
            for module in modules:
                module_id = module['id'].encode('ascii')
                consumables = module['consumables']
                consumable_count = len(consumables)
                
                body += struct.pack(f'!B {len(module_id)}s B',
                                  len(module_id),
                                  module_id,
                                  consumable_count)
                
                # 添加每个耗材
                for consumable in consumables:
                    body += struct.pack('!BB',
                                      consumable['id'],
                                      consumable['status'])
            
            # 构建完整消息
            message, sequence_id = self._build_message(
                self.MSG_TYPE_CONSUMABLE_INVENTORY_RESPONSE,
                body,
                return_sequence_id=header['sequence_id']
            )
            
            # 发送消息
            conn.sendall(message)
            
            self.logger.info(f"LAS consumable inventory response sent, SeqID=0x{sequence_id:04x}, Modules={module_count}")
            self.logger.log_las(f"Consumable inventory response sent, SeqID=0x{sequence_id:04x}, Modules={module_count}")
            
        except Exception as e:
            self.logger.error(f"Error handling LAS consumable inventory request: {str(e)}")
            self.logger.log_las(f"Error handling consumable inventory request: {str(e)}")
    
    def _handle_transfer_status_request(self, conn, header):
        """处理传输状态请求
        
        Args:
            conn: 连接 socket
            header: 消息头
        """
        try:
            # 获取传输状态
            health_status = self.core.get_instrument_health()
            
            # 获取核心模块的队列信息
            ready_to_load = self.core.get_ready_to_load()
            return_ready_count = self.core.get_return_ready_count()
            
            # 构建响应消息体（针对指定接口位置）
            # 简化处理：只支持IP0
            interface_position_index = 0
            
            body = struct.pack(
                '!BBH',
                interface_position_index,
                ready_to_load,
                return_ready_count
            )
            
            # 构建完整消息
            message, sequence_id = self._build_message(
                self.MSG_TYPE_TRANSFER_STATUS_RESPONSE,
                body,
                return_sequence_id=header['sequence_id']
            )
            
            # 发送消息
            conn.sendall(message)
            
            self.logger.info(f"LAS transfer status response sent, SeqID=0x{sequence_id:04x}, ReadyToLoad={ready_to_load}, ReturnReady={return_ready_count}")
            self.logger.log_las(f"Transfer status response sent, SeqID=0x{sequence_id:04x}")
            
        except Exception as e:
            self.logger.error(f"Error handling LAS transfer status request: {str(e)}")
            self.logger.log_las(f"Error handling transfer status request: {str(e)}")
    
    def _handle_add_queue_request(self, conn, header, body):
        """处理添加队列请求
        
        Args:
            conn: 连接 socket
            header: 消息头
            body: 消息体
        """
        try:
            # 解析请求消息体
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
            
            sample_priority = body[offset]
            offset += 1
            
            tube_height = body[offset]
            offset += 1
            
            tube_diameter = body[offset]
            
            # 添加到核心队列
            success = self.core.add_to_queue(
                interface_position_index,
                carrier_occupancy,
                sample_id,
                sample_priority,
                tube_height,
                tube_diameter
            )
            
            # 构建响应消息体
            response_body = struct.pack(
                f'!B B {len(sample_id)}s B',
                interface_position_index,
                sample_id_len,
                sample_id.encode('ascii'),
                1 if success else 0  # Command Status: 0x01=成功
            )
            
            # 构建完整消息
            message, sequence_id = self._build_message(
                self.MSG_TYPE_ADD_QUEUE_RESPONSE,
                response_body,
                return_sequence_id=header['sequence_id']
            )
            
            # 发送消息
            conn.sendall(message)
            
            self.logger.info(f"LAS add queue response sent, SeqID=0x{sequence_id:04x}, SampleID={sample_id}, Status={'Success' if success else 'Failed'}")
            self.logger.log_las(f"Add queue response sent, SeqID=0x{sequence_id:04x}")
            
        except Exception as e:
            self.logger.error(f"Error handling LAS add queue request: {str(e)}")
            self.logger.log_las(f"Error handling add queue request: {str(e)}")
    
    def _handle_skip_queue_request(self, conn, header, body):
        """处理跳过队列请求
        
        Args:
            conn: 连接 socket
            header: 消息头
            body: 消息体
        """
        try:
            # 解析请求消息体
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
            
            in_queue = body[offset]
            offset += 1
            
            tube_height = body[offset]
            offset += 1
            
            tube_diameter = body[offset]
            
            # 从队列中跳过
            success = self.core.skip_from_queue(
                interface_position_index,
                carrier_occupancy,
                sample_id,
                in_queue
            )
            
            # 构建响应消息体
            response_body = struct.pack(
                f'!B B {len(sample_id)}s B',
                interface_position_index,
                sample_id_len,
                sample_id.encode('ascii'),
                1 if success else 0  # Command Status: 0x01=成功
            )
            
            # 构建完整消息
            message, sequence_id = self._build_message(
                self.MSG_TYPE_SKIP_QUEUE_RESPONSE,
                response_body,
                return_sequence_id=header['sequence_id']
            )
            
            # 发送消息
            conn.sendall(message)
            
            self.logger.info(f"LAS skip queue response sent, SeqID=0x{sequence_id:04x}, SampleID={sample_id}, Status={'Success' if success else 'Failed'}")
            self.logger.log_las(f"Skip queue response sent, SeqID=0x{sequence_id:04x}")
            
        except Exception as e:
            self.logger.error(f"Error handling LAS skip queue request: {str(e)}")
            self.logger.log_las(f"Error handling skip queue request: {str(e)}")
    
    def _handle_clear_queue_request(self, conn, header):
        """处理清除队列请求
        
        Args:
            conn: 连接 socket
            header: 消息头
        """
        try:
            # 解析请求消息体
            interface_position_index = header.get('message_body', b'\x00')[0] if header.get('message_body') else 0
            
            # 清除队列
            success = self.core.clear_queue(interface_position_index)
            
            # 构建响应消息体
            body = struct.pack(
                '!BB',
                interface_position_index,
                1 if success else 0  # Command Status: 0x01=成功
            )
            
            # 构建完整消息
            message, sequence_id = self._build_message(
                self.MSG_TYPE_CLEAR_QUEUE_RESPONSE,
                body,
                return_sequence_id=header['sequence_id']
            )
            
            # 发送消息
            conn.sendall(message)
            
            self.logger.info(f"LAS clear queue response sent, SeqID=0x{sequence_id:04x}, IP={interface_position_index}, Status={'Success' if success else 'Failed'}")
            self.logger.log_las(f"Clear queue response sent, SeqID=0x{sequence_id:04x}")
            
        except Exception as e:
            self.logger.error(f"Error handling LAS clear queue request: {str(e)}")
            self.logger.log_las(f"Error handling clear queue request: {str(e)}")
    
    def _handle_load_unload_request(self, conn, header, body, manual_complete=False):
        """处理装载/卸载请求
        
        Args:
            conn: 连接 socket
            header: 消息头
            body: 消息体
            manual_complete: 是否已通过手动操作完成
        """
        try:
            # 解析请求消息体
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
            
            tube_height = body[offset]
            offset += 1
            
            tube_diameter = body[offset]
            offset += 1
            
            elapsed_time = struct.unpack_from('!H', body, offset)[0]
            
            # 确定请求类型
            # 0x01表示有样本需要卸载 (LOAD request)
            # 0x00表示需要装载样本 (UNLOAD request)
            request_type = 'load' if carrier_occupancy == 0x01 else 'unload'
            
            # 获取要显示的样本ID
            display_sample_id = sample_id
            if request_type == 'unload':
                # 对于UNLOAD请求，获取下一个要卸载的样本ID
                display_sample_id = self.core.get_next_sample_to_unload()
            
            if not manual_complete and self.ui:
                # 显示UI提示，等待用户操作
                self.ui._show_manual_prompt(request_type, interface_position_index, display_sample_id)
                
                # 保存请求信息，等待手动完成
                self.pending_requests.append({
                    'conn': conn,
                    'header': header,
                    'body': body
                })
                
                self.logger.info(f"LAS manual operation requested: {request_type} for IP{interface_position_index}, SampleID={display_sample_id}")
                self.logger.log_las(f"Manual operation requested: {request_type} for IP{interface_position_index}, SampleID={display_sample_id}")
                return
            
            # 处理装载/卸载请求
            load_result, unload_result, sample_status, onboard_count, completed_count, ready_to_load, return_ready_count = self.core.process_load_unload(
                interface_position_index,
                carrier_occupancy,
                sample_id,
                tube_height,
                tube_diameter,
                elapsed_time
            )
            
            # 构建响应消息体
            # Load Sample ID
            load_sample_id_bytes = load_result.get('sample_id', '').encode('ascii') if load_result else b''
            load_sample_id_len = len(load_sample_id_bytes)
            
            # Unload Sample ID
            unload_sample_id_bytes = unload_result.get('sample_id', '').encode('ascii') if unload_result else b''
            unload_sample_id_len = len(unload_sample_id_bytes)
            
            body = struct.pack(
                f'!B B {load_sample_id_len}s B B {unload_sample_id_len}s B B B H H B H',
                interface_position_index,
                load_sample_id_len,
                load_sample_id_bytes,
                load_result.get('status', 1) if load_result else 1,  # Load Command Status
                unload_sample_id_len,
                unload_sample_id_bytes,
                unload_result.get('status', 1) if unload_result else 1,  # Unload Command Status
                sample_status,  # Sample Processing Status
                onboard_count,
                completed_count,
                ready_to_load,
                return_ready_count
            )
            
            # 构建完整消息
            message, sequence_id = self._build_message(
                self.MSG_TYPE_LOAD_UNLOAD_RESPONSE,
                body,
                return_sequence_id=header['sequence_id']
            )
            
            # 发送消息
            conn.sendall(message)
            
            self.logger.info(f"LAS load/unload response sent, SeqID=0x{sequence_id:04x}, SampleID={sample_id}, LoadStatus={load_result.get('status') if load_result else 'N/A'}, UnloadStatus={unload_result.get('status') if unload_result else 'N/A'}")
            self.logger.log_las(f"Load/Unload response sent, SeqID=0x{sequence_id:04x}")
            
        except Exception as e:
            self.logger.error(f"Error handling LAS load/unload request: {str(e)}")
            self.logger.log_las(f"Error handling load/unload request: {str(e)}")
    
    # ========== 主动消息发送方法（供core模块调用） ==========
    
    def set_ui(self, ui):
        """设置UI引用
        
        Args:
            ui: UI实例
        """
        self.ui = ui
    
    def on_manual_operation_complete(self, request):
        """手动操作完成回调
        
        Args:
            request: 请求信息，包含type、interface_position、sample_id
        """
        if self.pending_requests:
            # 获取第一个待处理请求
            pending_request = self.pending_requests.pop(0)
            conn = pending_request['conn']
            header = pending_request['header']
            body = pending_request['body']
            
            # 继续处理原始请求
            self._process_load_unload_request(conn, header, body, manual_complete=True)
    
    def send_transfer_status_response(self, interface_position_index=0, ready_to_load=0, return_ready_count=0):
        """发送传输状态响应消息
        
        Args:
            interface_position_index: 接口位置索引
            ready_to_load: 准备装载数量
            return_ready_count: 返回准备数量
        """
        try:
            # 只在connected状态下发送
            if self.conversation_status != self.CONVERSATION_STATUS_CONNECTED:
                self.logger.warning(f"Cannot send transfer status response in {self.conversation_status} state")
                return False
            
            # 构建消息体
            body = struct.pack(
                '!BBH',
                interface_position_index,
                ready_to_load,
                return_ready_count
            )
            
            # 遍历所有连接并发送消息
            with self.connection_lock:
                for conn in self.connections:
                    # 构建完整消息
                    message, sequence_id = self._build_message(
                        self.MSG_TYPE_TRANSFER_STATUS_RESPONSE,
                        body
                    )
                    
                    # 记录发送的原始数据
                    message_hex = binascii.hexlify(message).decode('ascii')
                    self.logger.log_las_raw('SENT', message_hex)
                    # 发送消息
                    conn.sendall(message)
                    
                    self.logger.info(f"LAS transfer status response sent, SeqID=0x{sequence_id:04x}, ReadyToLoad={ready_to_load}, ReturnReady={return_ready_count}")
                    self.logger.log_las(f"Transfer status response sent, SeqID=0x{sequence_id:04x}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending transfer status response: {str(e)}")
            self.logger.log_las(f"Error sending transfer status response: {str(e)}")
            return False
    
    def send_onboard_sample_info_response(self):
        """发送在线样本信息响应消息
        """
        try:
            # 只在connected状态下发送
            if self.conversation_status != self.CONVERSATION_STATUS_CONNECTED:
                self.logger.warning(f"Cannot send onboard sample info response in {self.conversation_status} state")
                return False
            
            # 获取所有样本
            samples = self.core.get_all_samples()
            onboard_samples = [sample for sample in samples.values() if sample['status'] != 'completed']
            onboard_count = len(onboard_samples)
            
            # 构建响应消息体
            body = struct.pack('!H', onboard_count)
            
            # 添加每个在线样本
            for sample in onboard_samples:
                sample_id = sample['sample_id'].encode('ascii')
                body += struct.pack(f'!B {len(sample_id)}s',
                                  len(sample_id),
                                  sample_id)
            
            # 添加已移除样本数量（这里简化处理，返回0）
            body += struct.pack('!H', 0)
            
            # 遍历所有连接并发送消息
            with self.connection_lock:
                for conn in self.connections:
                    # 构建完整消息
                    message, sequence_id = self._build_message(
                        self.MSG_TYPE_ONBOARD_SAMPLE_INFO_RESPONSE,
                        body
                    )
                    
                    # 记录发送的原始数据
                    message_hex = binascii.hexlify(message).decode('ascii')
                    self.logger.log_las_raw('SENT', message_hex)
                    # 发送消息
                    conn.sendall(message)
                    
                    self.logger.info(f"LAS onboard sample info response sent, SeqID=0x{sequence_id:04x}, Samples={onboard_count}")
                    self.logger.log_las(f"Onboard sample info response sent, SeqID=0x{sequence_id:04x}, Samples={onboard_count}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending onboard sample info response: {str(e)}")
            self.logger.log_las(f"Error sending onboard sample info response: {str(e)}")
            return False
    
    def send_instrument_health_response(self):
        """发送仪器健康响应消息
        """
        try:
            # 只在connected状态下发送
            if self.conversation_status != self.CONVERSATION_STATUS_CONNECTED:
                self.logger.warning(f"Cannot send instrument health response in {self.conversation_status} state")
                return False
            
            # 获取仪器健康状态
            health_status = self.core.get_instrument_health()
            
            # 构建响应消息体
            body = struct.pack(
                '!BBB B',
                health_status['automation_interface_status'],
                health_status['instrument_process_status'],
                health_status['lis_connection_status'],
                health_status['interface_positions']
            )
            
            # 添加接口位置状态
            for i in range(health_status['interface_positions']):
                remote_status = health_status['remote_control_status'][i] if i < len(health_status['remote_control_status']) else 1
                lock_ownership = health_status['lock_ownership'][i] if i < len(health_status['lock_ownership']) else 2
                body += struct.pack('!BB', remote_status, lock_ownership)
            
            # 添加处理积压、样本获取延迟、在线试管数量、已完成试管数量
            body += struct.pack(
                '!HHHH',
                health_status['processing_backlog'],
                health_status['sample_acquisition_delay'],
                health_status['on_board_tube_count'],
                health_status['completed_tube_count']
            )
            
            # 遍历所有连接并发送消息
            with self.connection_lock:
                for conn in self.connections:
                    # 构建完整消息
                    message, sequence_id = self._build_message(
                        self.MSG_TYPE_INSTRUMENT_HEALTH_RESPONSE,
                        body
                    )
                    
                    # 记录发送的原始数据
                    message_hex = binascii.hexlify(message).decode('ascii')
                    self.logger.log_las_raw('SENT', message_hex)
                    # 发送消息
                    conn.sendall(message)
                    
                    self.logger.info(f"LAS instrument health response sent, SeqID=0x{sequence_id:04x}")
                    self.logger.log_las(f"Instrument health response sent, SeqID=0x{sequence_id:04x}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending instrument health response: {str(e)}")
            self.logger.log_las(f"Error sending instrument health response: {str(e)}")
            return False
    
    def send_test_inventory_response(self):
        """发送测试库存响应消息
        """
        try:
            # 只在connected状态下发送
            if self.conversation_status != self.CONVERSATION_STATUS_CONNECTED:
                self.logger.warning(f"Cannot send test inventory response in {self.conversation_status} state")
                return False
            
            # 获取测试库存
            test_inventory = self.core.get_test_inventory()
            tests = test_inventory['tests']
            test_count = len(tests)
            
            # 构建响应消息体
            body = struct.pack('!H', test_count)
            
            # 添加每个测试项目
            for test in tests:
                test_name = test['name'].encode('ascii')
                body += struct.pack(f'!B {len(test_name)}s HH',
                                  len(test_name),
                                  test_name,
                                  test['count'],
                                  test['status'])
            
            # 遍历所有连接并发送消息
            with self.connection_lock:
                for conn in self.connections:
                    # 构建完整消息
                    message, sequence_id = self._build_message(
                        self.MSG_TYPE_TEST_INVENTORY_RESPONSE,
                        body
                    )
                    
                    # 记录发送的原始数据
                    message_hex = binascii.hexlify(message).decode('ascii')
                    self.logger.log_las_raw('SENT', message_hex)
                    # 发送消息
                    conn.sendall(message)
                    
                    self.logger.info(f"LAS test inventory response sent, SeqID=0x{sequence_id:04x}, Tests={test_count}")
                    self.logger.log_las(f"Test inventory response sent, SeqID=0x{sequence_id:04x}, Tests={test_count}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending test inventory response: {str(e)}")
            self.logger.log_las(f"Error sending test inventory response: {str(e)}")
            return False
    
    def send_consumable_inventory_response(self):
        """发送耗材库存响应消息
        """
        try:
            # 只在connected状态下发送
            if self.conversation_status != self.CONVERSATION_STATUS_CONNECTED:
                self.logger.warning(f"Cannot send consumable inventory response in {self.conversation_status} state")
                return False
            
            # 获取耗材库存
            consumable_inventory = self.core.get_consumable_inventory()
            modules = consumable_inventory['modules']
            module_count = len(modules)
            
            # 构建响应消息体
            body = struct.pack('!B', module_count)
            
            # 添加每个模块的耗材信息
            for module in modules:
                module_id = module['id'].encode('ascii')
                consumables = module['consumables']
                consumable_count = len(consumables)
                
                body += struct.pack(f'!B {len(module_id)}s B',
                                  len(module_id),
                                  module_id,
                                  consumable_count)
                
                # 添加每个耗材
                for consumable in consumables:
                    body += struct.pack('!BB',
                                      consumable['id'],
                                      consumable['status'])
            
            # 遍历所有连接并发送消息
            with self.connection_lock:
                for conn in self.connections:
                    # 构建完整消息
                    message, sequence_id = self._build_message(
                        self.MSG_TYPE_CONSUMABLE_INVENTORY_RESPONSE,
                        body
                    )
                    
                    # 记录发送的原始数据
                    message_hex = binascii.hexlify(message).decode('ascii')
                    self.logger.log_las_raw('SENT', message_hex)
                    # 发送消息
                    conn.sendall(message)
                    
                    self.logger.info(f"LAS consumable inventory response sent, SeqID=0x{sequence_id:04x}, Modules={module_count}")
                    self.logger.log_las(f"Consumable inventory response sent, SeqID=0x{sequence_id:04x}, Modules={module_count}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending consumable inventory response: {str(e)}")
            self.logger.log_las(f"Error sending consumable inventory response: {str(e)}")
            return False
