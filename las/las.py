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
        
        # 连接状态跟踪
        self.connection_states = {}  # 记录连接的创建时间和状态
        
        # Keep-Alive机制
        self.keep_alive_interval = self.config.get('keep_alive_interval', 15)  # 秒
        self.keep_alive_inactivity_timeout = self.config.get('keep_alive_inactivity_timeout', 15)  # 秒
        self.last_message_time = time.time()
        self.last_keep_alive_time = 0
        self.keep_alive_thread = None
        
        # 超时和重试机制
        self.ack_timeout = self.config.get('ack_timeout', 1)  # ACK/NACK超时时间
        self.max_ack_retries = self.config.get('max_ack_retries', 5)  # 最大ACK重试次数
        self.max_nack_retries = self.config.get('max_nack_retries', 3)  # 最大NACK重试次数
        
        # 响应消息超时配置
        self.timeouts = {
            'instrument_health': self.config.get('instrument_health_timeout', 20),
            'test_inventory': self.config.get('test_inventory_timeout', 20),
            'onboard_sample_info': self.config.get('onboard_sample_info_timeout', 20),
            'transfer_status': self.config.get('transfer_status_timeout', 20),
            'add_queue': self.config.get('add_queue_timeout', 20),
            'skip_queue': self.config.get('skip_queue_timeout', 20),
            'clear_queue': self.config.get('clear_queue_timeout', 20),
            'load_unload': self.config.get('load_unload_timeout', 600),
            'consumable_inventory': self.config.get('consumable_inventory_timeout', 20)
        }
        
        # 握手和初始化超时
        self.handshake_retry_period = self.config.get('handshake_retry_period', 30)  # 秒
        self.handshake_response_timeout = self.config.get('handshake_response_timeout', 20)  # 秒
        self.handshake_timeout = self.config.get('handshake_timeout', 60)  # 秒 - LAS连接后未发送handshake消息的超时时间
        self.initialization_wait_period = self.config.get('initialization_wait_period', 30)  # 秒
        self.initialization_complete_timeout = self.config.get('initialization_complete_timeout', 30)  # 秒
        self.analyzer_shaking_timeout = self.config.get('analyzer_shaking_timeout', 480)  # 秒
        
        # 消息跟踪和超时管理
        self.pending_messages = {}  # 跟踪等待响应的消息
        self.message_lock = threading.Lock()
        
        # 重试计数器
        self.retry_counts = {}  # 跟踪消息重试次数
        
        # 连接重置状态
        self.connection_reset_time = 0
        self.reset_in_progress = False
        
        # 序列ID管理
        self.sequence_id = 1
        self.sequence_lock = threading.Lock()
        
        # 会话状态管理
        self.CONVERSATION_STATUS_LISTENING = 'listening'
        self.CONVERSATION_STATUS_INITIALIZATION = 'initialization'
        self.CONVERSATION_STATUS_CONNECTED = 'connected'
        self.conversation_status = self.CONVERSATION_STATUS_LISTENING
        
        # 初始化阶段已处理的请求类型集合
        self.initialized_requests = {
            'clear_queue': set(),  # 存储已处理的Interface Position Index
            'transfer_status': set(),  # 存储已处理的Interface Position Index
            'instrument_health': False,
            'test_inventory': False,
            'onboard_sample_info': False,
            'consumable_inventory': False
        }
        
        # 等待ACK标志
        self._awaiting_handshake_ack = False
        self._awaiting_init_complete_ack = False
        
        # 手动操作相关
        # 按接口位置分离的pending请求队列，避免IP0和IP1的请求互相影响
        self.pending_requests = {
            0: [],  # IP0的请求队列
            1: []   # IP1的请求队列
        }
        self.ui = None
        
        # 请求超时设置（秒）
        # 协议要求：Load/Unload Command Response Timeout = 600秒 (10分钟)
        self.request_timeout = 600  # 10分钟超时
        
        # 已移除标本管理
        self.removed_samples = []  # 存储已手工移除的标本ID
        self.removed_samples_lock = threading.Lock()
        
        # 超时检查线程
        self.timeout_check_thread = None
        self.timeout_check_interval = 0.5  # 秒
        
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

                # 检查是否有待处理的Keep-Alive消息（防止重复发送）
                has_pending_keepalive = False
                with self.message_lock:
                    for msg_info in self.pending_messages.values():
                        if msg_info['message_type'] == self.MSG_TYPE_KEEPALIVE:
                            has_pending_keepalive = True
                            break

                # 只有当conversation_status为"connected"、距离上次收到消息超过keep_alive_interval、
                # 且没有待处理的Keep-Alive消息时，才发送新的Keep-Alive消息
                if (self.conversation_status == self.CONVERSATION_STATUS_CONNECTED and
                    time_since_last_msg >= self.keep_alive_interval and
                    not has_pending_keepalive):
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
            
            # 构建完整消息，启用消息跟踪以便检测超时
            message, sequence_id = self._build_message(
                self.MSG_TYPE_KEEPALIVE,
                body,
                track_message=True  # 启用消息跟踪以检测Keep-Alive响应超时
            )
            
            # 记录发送的原始数据
            message_hex = binascii.hexlify(message).decode('ascii')
            extra_info = {
                'sequence_id': f"0x{sequence_id:04x}"}
            self.logger.log_las_raw('SENT', message_hex, extra_info)
        
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
            # 注意：Wait Period Prior to Initiating Handshake (LAS)是LAS端的等待时间，不是仪器端
            # 仪器端应该立即进入监听状态，准备接收LAS的Handshake消息
            accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            accept_thread.start()
            
            # 启动消息超时检查线程
            self.timeout_check_thread = threading.Thread(target=self._run_timeout_check, daemon=True)
            self.timeout_check_thread.start()
            
            # 启动pending请求超时检查线程
            self._start_pending_request_timeout_checker()
            
            # 启动等待期线程（后台执行，不阻塞UI）
            wait_thread = threading.Thread(target=self._wait_period, daemon=True)
            wait_thread.start()
            
        except Exception as e:
            self.logger.error(f"Failed to start LASServer: {str(e)}")
            self.is_running = False
    
    def _wait_period(self):
        """等待期执行方法"""
        # 1. Wait Period Prior to Entering Listening Mode - 15秒
        self.logger.info(f"Entering Wait Period Prior to Listening Mode: {self.keep_alive_inactivity_timeout} seconds")
        time.sleep(self.keep_alive_inactivity_timeout)
        self.logger.info("Wait Period completed, ready for connections")
    
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
                connection_id = f"{addr[0]}:{addr[1]}:{int(time.time())}"
                
                with self.connection_lock:
                    self.connections.append(conn)
                    # 记录连接状态
                    self.connection_states[connection_id] = {
                        'conn': conn,
                        'addr': addr,
                        'created_time': time.time(),
                        'status': 'connected',  # connected, handshake_received, initialized
                        'last_activity': time.time()
                    }
                
                self.logger.info(f"LAS connection established from {addr[0]}:{addr[1]}, ConnectionID={connection_id}")
                self.logger.log_las(f"Connection established: {addr[0]}:{addr[1]}, ConnectionID={connection_id}")
                
                # 为每个连接创建处理线程
                conn_thread = threading.Thread(
                    target=self._handle_connection,
                    args=(conn, addr, connection_id),
                    daemon=True
                )
                conn_thread.start()
                
            except socket.error as e:
                if self.is_running:
                    self.logger.error(f"Error accepting LAS connection: {str(e)}")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in LAS accept thread: {str(e)}")
    
    def _handle_connection(self, conn, addr, connection_id):
        """处理单个连接
        
        Args:
            conn: 连接 socket
            addr: 客户端地址
            connection_id: 连接ID
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
                    # LAS端因超时断连
                    self.logger.warning(f"LAS connection closed by LAS side (timeout), ConnectionID={connection_id}")
                    
                    # 2. 若LAS端因超时断连，仪器同步执行断连 + 重置 + 重启监听
                    self.logger.info("Step 1: LAS timeout detected, initiating TCP connection closure")
                    with self.connection_lock:
                        if conn in self.connections:
                            try:
                                conn.close()
                                self.logger.info(f"Disconnected LAS TCP connection due to LAS timeout")
                            except Exception as e:
                                self.logger.error(f"Error closing connection: {str(e)}")
                        # 清空连接列表
                        self.connections.clear()
                        # 清空连接状态
                        self.connection_states.clear()
                    
                    # 重置通信状态
                    self.logger.info("Step 2: Resetting communication state")
                    with self.message_lock:
                        self.pending_messages.clear()
                        self.retry_counts.clear()
                    # 重置会话状态
                    self.conversation_status = self.CONVERSATION_STATUS_LISTENING
                    # 重置等待标志
                    self._awaiting_handshake_ack = False
                    self._awaiting_init_complete_ack = False
                    # 重置初始化请求集合
                    self.initialized_requests = {
                        'clear_queue': set(),
                        'transfer_status': set(),
                        'instrument_health': False,
                        'test_inventory': False,
                        'onboard_sample_info': False,
                        'consumable_inventory': False
                    }
                    
                    # 执行15秒监听前等待
                    self.logger.info("Step 3: Entering 15-second wait period before restarting listening")
                    self.logger.info(f"Entering Wait Period Prior to Listening Mode: {self.keep_alive_inactivity_timeout} seconds")
                    time.sleep(self.keep_alive_inactivity_timeout)
                    
                    # 重启监听
                    self.logger.info("Step 4: Restarting TCP listening mode")
                    try:
                        if self.server_socket:
                            self.server_socket.close()
                        # 重新创建TCP服务器 socket
                        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        self.server_socket.bind((self.host, self.port))
                        self.server_socket.listen(5)
                        self.logger.info(f"LASServer restarted, listening on {self.host}:{self.port}")
                    except Exception as e:
                        self.logger.error(f"Failed to restart LASServer: {str(e)}")
                    
                    # 重新启动接受连接的线程
                    accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
                    accept_thread.start()
                    
                    self.logger.info("LAS timeout handling completed. Waiting for LAS to reconnect.")
                    break
                
                # 重置最后消息时间
                self.last_message_time = time.time()
                
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
                    # 检查是否有足够字节读取完整消息
                    if len(buffer) < stx_pos + message_length:
                        break
                    
                    # 提取完整消息
                    message = buffer[stx_pos:stx_pos + message_length]                    
                    # 验证最后一个字节是否为 ETX (0x03)
                    if message[-1:] != b'\x03':
                        # 无效消息，跳过
                        buffer = buffer[stx_pos + 1:]
                        continue
                    
                    # 更新缓冲区，移除已处理的消息
                    buffer = buffer[stx_pos + message_length:]
                    # 记录接收的原始数据
                    message_hex = binascii.hexlify(message).decode('ascii')
                    
                    try:
                        # 处理消息，传递原始十六进制数据用于日志记录
                        self._process_message(conn, addr, message, message_hex)
                    except Exception as e:
                        # 1. 若为仪器自身故障，标记业务执行失败
                        self.logger.error(f"Instrument internal error processing business message: {str(e)}")
                        self.logger.error(f"Marking business execution as failed due to internal error")
                        
                        # 发送NACK消息，表示消息处理失败
                        try:
                            # 解析消息头以获取sequence_id
                            msg_header, _, _ = self._parse_message(message)
                            if msg_header:
                                self._send_ack(conn, msg_header['sequence_id'], 0x01)  # 0x01 = NACK
                        except Exception as ack_error:
                            self.logger.error(f"Error sending NACK: {str(ack_error)}")
                    
        except socket.error as e:
            self.logger.error(f"LAS connection error with {addr[0]}:{addr[1]}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error handling LAS connection from {addr[0]}:{addr[1]}: {str(e)}")
        finally:
            # 清理连接
            with self.connection_lock:
                if conn in self.connections:
                    self.connections.remove(conn)
                
                # 从连接状态中移除
                for conn_id, state in list(self.connection_states.items()):
                    if state['conn'] == conn:
                        del self.connection_states[conn_id]
                        break
            
            try:
                conn.close()
            except:
                pass
            
            self.logger.info(f"LAS connection closed with {addr[0]}:{addr[1]}, ConnectionID={connection_id}")
            self.logger.log_las(f"Connection closed: {addr[0]}:{addr[1]}, ConnectionID={connection_id}")
    
    def _process_message(self, conn, addr, message, message_hex):
        """处理uRAP消息
        
        Args:
            conn: 连接 socket
            addr: 客户端地址
            message: uRAP消息
            message_hex: 消息的十六进制字符串表示
        """
        try:
            # 更新最后消息时间
            self.last_message_time = time.time()
            
            # 解析消息
            msg_header, msg_body, msg_footer = self._parse_message(message)
            
            if not msg_header:
                # 发送NACK
                self._send_ack(conn, 0, 0x01)  # 0x01 = Message Not Understood
                return
            
            # 记录接收到的原始消息
            extra_info = {
                'sequence_id': f"0x{msg_header['sequence_id']:04x}",
                'return_sequence_id': f"0x{msg_header['return_sequence_id']:04x}",
            }
            self.logger.log_las_raw('RECEIVED', message_hex, extra_info)
            
            # 记录接收到的消息
            self.logger.log_las(f"Received message from {addr[0]}:{addr[1]}: Type=0x{msg_header['message_type']:04x}, SeqID=0x{msg_header['sequence_id']:04x}, Content={message_hex}")
            
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
    
    def _run_timeout_check(self):
        """运行超时检查，处理消息超时和重试逻辑"""
        try:
            while self.is_running:
                try:
                    time.sleep(self.timeout_check_interval)
                    current_time = time.time()
                    
                    # 检查待处理消息的超时情况
                    with self.message_lock:
                        expired_messages = []
                        for seq_id, msg_info in list(self.pending_messages.items()):
                            # 根据消息类型确定超时时间
                            timeout = self.ack_timeout  # 默认使用ACK超时
                            
                            # 检查消息是否超时
                            if current_time - msg_info['send_time'] > timeout:
                                expired_messages.append(seq_id)
                        
                        # 处理超时消息
                        for seq_id in expired_messages:
                            if seq_id in self.pending_messages:
                                msg_info = self.pending_messages[seq_id]
                                self.logger.warning(f"Message timeout detected: SeqID=0x{seq_id:04x}, Type=0x{msg_info['message_type']:04x}")
                                
                                # 检查是否为Keep-Alive消息
                                if msg_info['message_type'] == self.MSG_TYPE_KEEPALIVE:
                                    # Keep-Alive消息的特殊处理
                                    self.logger.info(f"Keep-Alive message timeout detected: SeqID=0x{seq_id:04x}")
                                    
                                    # 检查重试次数
                                    if msg_info['retries'] < self.max_ack_retries:
                                        # 增加重试次数并重新发送消息
                                        msg_info['retries'] += 1
                                        msg_info['send_time'] = current_time
                                        self.logger.info(f"Retrying Keep-Alive message (attempt {msg_info['retries']}/{self.max_ack_retries}): SeqID=0x{seq_id:04x}")
                                        
                                        # 4. 重试期间暂停所有主动推送
                                        self.logger.info("Pausing all active message pushes during Keep-Alive retry period")
                                        
                                        # 重新发送消息到所有活跃连接
                                        try:
                                            with self.connection_lock:
                                                for conn in self.connections:
                                                    try:
                                                        conn.sendall(msg_info['message'])
                                                        self.logger.log_las(f"Retried Keep-Alive message sent: SeqID=0x{seq_id:04x}")
                                                    except Exception as e:
                                                        self.logger.error(f"Error resending Keep-Alive message: {str(e)}")
                                        except Exception as e:
                                            self.logger.error(f"Error in connection lock: {str(e)}")
                                    else:
                                        # 达到最大重试次数，判定链路永久失效
                                        self.logger.error(f"Max Keep-Alive retries reached: SeqID=0x{seq_id:04x}, link permanently failed")
                                        del self.pending_messages[seq_id]
                                        
                                        # 1) 无视 TCP 表面连通状态，直接判定链路永久失效
                                        self.logger.info("Step 1: Link permanently failed, ignoring TCP surface connectivity state")
                                        
                                        # 2) 主动断连，全量重置通信层状态
                                        self.logger.info("Step 2: Initiating TCP connection closure and resetting communication state")
                                        with self.connection_lock:
                                            for conn in self.connections:
                                                try:
                                                    conn.close()
                                                    self.logger.info(f"Disconnected LAS TCP connection due to Keep-Alive failure")
                                                except Exception as e:
                                                    self.logger.error(f"Error closing connection: {str(e)}")
                                            # 清空连接列表
                                            self.connections.clear()
                                            # 清空连接状态
                                            self.connection_states.clear()
                                        
                                        # 全量重置通信层状态
                                        self.logger.info("Step 2: Resetting communication layer state")
                                        with self.message_lock:
                                            self.pending_messages.clear()
                                            self.retry_counts.clear()
                                        # 重置会话状态
                                        self.conversation_status = self.CONVERSATION_STATUS_LISTENING
                                        # 重置等待标志
                                        self._awaiting_handshake_ack = False
                                        self._awaiting_init_complete_ack = False
                                        # 重置初始化请求集合
                                        self.initialized_requests = {
                                            'clear_queue': set(),
                                            'transfer_status': set(),
                                            'instrument_health': False,
                                            'test_inventory': False,
                                            'onboard_sample_info': False,
                                            'consumable_inventory': False
                                        }
                                        
                                        # 3) 执行 15 秒监听前等待，重启监听
                                        self.logger.info("Step 3: Entering 15-second wait period before restarting listening")
                                        self.logger.info(f"Entering Wait Period Prior to Listening Mode: {self.keep_alive_inactivity_timeout} seconds")
                                        time.sleep(self.keep_alive_inactivity_timeout)
                                        
                                        # 重启监听
                                        self.logger.info("Step 3: Restarting TCP listening mode")
                                        try:
                                            if self.server_socket:
                                                self.server_socket.close()
                                            # 重新创建TCP服务器 socket
                                            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                                            self.server_socket.bind((self.host, self.port))
                                            self.server_socket.listen(5)
                                            self.logger.info(f"LASServer restarted, listening on {self.host}:{self.port}")
                                        except Exception as e:
                                            self.logger.error(f"Failed to restart LASServer: {str(e)}")
                                        
                                        # 重新启动接受连接的线程
                                        accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
                                        accept_thread.start()
                                        
                                        self.logger.info("Keep-Alive failure handling completed. Waiting for LAS to reconnect.")
                                else:
                                    # 非Keep-Alive消息的常规处理
                                    # 检查重试次数
                                    if msg_info['retries'] < self.max_ack_retries:
                                        # 增加重试次数并重新发送消息
                                        msg_info['retries'] += 1
                                        msg_info['send_time'] = current_time
                                        self.logger.info(f"Retrying message (attempt {msg_info['retries']}/{self.max_ack_retries}): SeqID=0x{seq_id:04x}")
                                        
                                        # 重新发送消息到所有活跃连接
                                        try:
                                            with self.connection_lock:
                                                for conn in self.connections:
                                                    try:
                                                        conn.sendall(msg_info['message'])
                                                        self.logger.log_las(f"Retried message sent: SeqID=0x{seq_id:04x}")
                                                    except Exception as e:
                                                        self.logger.error(f"Error resending message: {str(e)}")
                                        except Exception as e:
                                            self.logger.error(f"Error in connection lock: {str(e)}")
                                    else:
                                        # 达到最大重试次数，判定握手失败
                                        self.logger.error(f"Max retries reached for message: SeqID=0x{seq_id:04x}, handshake failed")
                                        del self.pending_messages[seq_id]
                                        
                                        # 1. 判定握手失败，主动断连并重置通信状态
                                        self.logger.info("Step 1: Handshake failed, initiating TCP connection closure")
                                        with self.connection_lock:
                                            for conn in self.connections:
                                                try:
                                                    conn.close()
                                                    self.logger.info(f"Disconnected LAS TCP connection due to handshake failure")
                                                except Exception as e:
                                                    self.logger.error(f"Error closing connection: {str(e)}")
                                            # 清空连接列表
                                            self.connections.clear()
                                            # 清空连接状态
                                            self.connection_states.clear()
                                        
                                        # 重置通信状态
                                        self.logger.info("Step 1: Resetting communication state")
                                        with self.message_lock:
                                            self.pending_messages.clear()
                                            self.retry_counts.clear()
                                        # 重置会话状态
                                        self.conversation_status = self.CONVERSATION_STATUS_LISTENING
                                        # 重置等待标志
                                        self._awaiting_handshake_ack = False
                                        self._awaiting_init_complete_ack = False
                                        # 重置初始化请求集合
                                        self.initialized_requests = {
                                            'clear_queue': set(),
                                            'transfer_status': set(),
                                            'instrument_health': False,
                                            'test_inventory': False,
                                            'onboard_sample_info': False,
                                            'consumable_inventory': False
                                        }
                                        
                                        # 2. 执行 15 秒监听前等待，重启监听
                                        self.logger.info("Step 2: Entering 15-second wait period before restarting listening")
                                        self.logger.info(f"Entering Wait Period Prior to Listening Mode: {self.keep_alive_inactivity_timeout} seconds")
                                        time.sleep(self.keep_alive_inactivity_timeout)
                                        
                                        # 3. 重启监听
                                        self.logger.info("Step 3: Restarting TCP listening mode")
                                        try:
                                            if self.server_socket:
                                                self.server_socket.close()
                                            # 重新创建TCP服务器 socket
                                            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                                            self.server_socket.bind((self.host, self.port))
                                            self.server_socket.listen(5)
                                            self.logger.info(f"LASServer restarted, listening on {self.host}:{self.port}")
                                        except Exception as e:
                                            self.logger.error(f"Failed to restart LASServer: {str(e)}")
                                        
                                        # 重新启动接受连接的线程
                                        accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
                                        accept_thread.start()
                                        
                                        self.logger.info("Handshake failure handling completed. Waiting for LAS to reconnect and initiate handshake.")
                    
                    # 检查连接无活动超时
                    # 注意：Keep-Alive消息由_keep_alive_loop线程统一处理，这里只记录日志
                    try:
                        if self.conversation_status == self.CONVERSATION_STATUS_CONNECTED:
                            time_since_last_msg = current_time - self.last_message_time
                            if time_since_last_msg > self.keep_alive_inactivity_timeout * 3:  # 3倍无活动超时时间
                                self.logger.warning(f"Connection inactive for {time_since_last_msg:.1f} seconds, Keep-Alive will be handled by _keep_alive_loop")
                                # 不再在这里发送Keep-Alive，由_keep_alive_loop线程统一处理
                    except Exception as e:
                        self.logger.error(f"Error checking connection inactivity: {str(e)}")
                    
                    # 检查握手超时 - LAS连接后未发送handshake消息
                    try:
                        with self.connection_lock:
                            expired_connections = []
                            for conn_id, state in list(self.connection_states.items()):
                                # 只检查已连接但未收到handshake消息的连接
                                if state['status'] == 'connected':
                                    time_since_connection = current_time - state['created_time']
                                    if time_since_connection > self.handshake_timeout:
                                        expired_connections.append(conn_id)
                            
                            # 处理握手超时的连接
                            for conn_id in expired_connections:
                                if conn_id in self.connection_states:
                                    state = self.connection_states[conn_id]
                                    addr = state['addr']
                                    time_since_connection = current_time - state['created_time']
                                    
                                    # 记录超时事件的详细信息
                                    self.logger.error(f"Handshake timeout detected for connection {conn_id} from {addr[0]}:{addr[1]}")
                                    self.logger.error(f"Timeout details: Connection time={time.ctime(state['created_time'])}, "
                                                    f"Elapsed time={time_since_connection:.1f} seconds, "
                                                    f"Timeout threshold={self.handshake_timeout} seconds")
                                    
                                    # 主动断开连接
                                    try:
                                        state['conn'].close()
                                        self.logger.info(f"Disconnected LAS connection {conn_id} due to handshake timeout")
                                    except Exception as e:
                                        self.logger.error(f"Error closing connection {conn_id}: {str(e)}")
                                    
                                    # 从连接列表和状态中移除
                                    if state['conn'] in self.connections:
                                        self.connections.remove(state['conn'])
                                    del self.connection_states[conn_id]
                                    
                                    # 生成符合系统日志管理规范的日志信息
                                    self.logger.log_las(f"Handshake timeout: ConnectionID={conn_id}, "
                                                      f"Address={addr[0]}:{addr[1]}, "
                                                      f"ErrorType=HandshakeTimeout")
                    except Exception as e:
                        self.logger.error(f"Error checking handshake timeout: {str(e)}")
                    
                    # 检查初始化序列超时 - 握手后30秒内未完成初始化
                    try:
                        if self.conversation_status == self.CONVERSATION_STATUS_INITIALIZATION and hasattr(self, 'initialization_start_time'):
                            time_since_initialization = current_time - self.initialization_start_time
                            if time_since_initialization > self.initialization_complete_timeout:
                                # 检查初始化是否完成
                                is_initialized = (
                                    len(self.initialized_requests['clear_queue']) >= 2 and
                                    len(self.initialized_requests['transfer_status']) >= 2 and
                                    self.initialized_requests['instrument_health'] and
                                    self.initialized_requests['test_inventory'] and
                                    self.initialized_requests['onboard_sample_info'] and
                                    self.initialized_requests['consumable_inventory']
                                )
                                
                                if not is_initialized:
                                    # 初始化序列超时
                                    self.logger.error(f"Initialization sequence timeout detected")
                                    self.logger.error(f"Timeout details: Initialization start time={time.ctime(self.initialization_start_time)}, "
                                                    f"Elapsed time={time_since_initialization:.1f} seconds, "
                                                    f"Timeout threshold={self.initialization_complete_timeout} seconds")
                                    
                                    # 记录未完成的初始化请求
                                    missing_requests = []
                                    if len(self.initialized_requests['clear_queue']) < 2:
                                        missing_requests.append(f"clear_queue (need 2, got {len(self.initialized_requests['clear_queue'])})")
                                    if len(self.initialized_requests['transfer_status']) < 2:
                                        missing_requests.append(f"transfer_status (need 2, got {len(self.initialized_requests['transfer_status'])})")
                                    if not self.initialized_requests['instrument_health']:
                                        missing_requests.append("instrument_health")
                                    if not self.initialized_requests['test_inventory']:
                                        missing_requests.append("test_inventory")
                                    if not self.initialized_requests['onboard_sample_info']:
                                        missing_requests.append("onboard_sample_info")
                                    if not self.initialized_requests['consumable_inventory']:
                                        missing_requests.append("consumable_inventory")
                                    
                                    self.logger.error(f"Missing initialization requests: {', '.join(missing_requests)}")
                                    
                                    # 1. 主动发送 TCP 断开请求（FIN 包），强制关闭与 LAS 的连接
                                    self.logger.info("Step 1: Initiating TCP connection closure due to initialization sequence timeout")
                                    with self.connection_lock:
                                        for conn in self.connections:
                                            try:
                                                conn.close()
                                                self.logger.info(f"Disconnected LAS TCP connection due to initialization sequence timeout")
                                            except Exception as e:
                                                self.logger.error(f"Error closing connection: {str(e)}")
                                        # 清空连接列表
                                        self.connections.clear()
                                        # 清空连接状态
                                        self.connection_states.clear()
                                    
                                    # 2. 通信状态重置
                                    self.logger.info("Step 2: Resetting communication state")
                                    # 2.1 清空临时数据
                                    with self.message_lock:
                                        self.pending_messages.clear()
                                        self.retry_counts.clear()
                                    # 重置消息序列号计数器
                                    with self.sequence_lock:
                                        self.sequence_id = 1
                                    # 重置初始化请求缓存
                                    self.initialized_requests = {
                                        'clear_queue': set(),
                                        'transfer_status': set(),
                                        'instrument_health': False,
                                        'test_inventory': False,
                                        'onboard_sample_info': False,
                                        'consumable_inventory': False
                                    }
                                    # 重置握手状态
                                    self._awaiting_handshake_ack = False
                                    self._awaiting_init_complete_ack = False
                                    # 重置会话状态
                                    self.conversation_status = self.CONVERSATION_STATUS_LISTENING
                                    
                                    # 3. 重启监听等待
                                    self.logger.info("Step 3: Restarting listening wait period")
                                    # 3.1 启动 "进入监听模式前等待周期"（默认 15 秒）
                                    self.logger.info(f"Entering Wait Period Prior to Listening Mode: {self.keep_alive_inactivity_timeout} seconds")
                                    time.sleep(self.keep_alive_inactivity_timeout)
                                    
                                    # 3.2 重新初始化服务器套接字
                                    try:
                                        if self.server_socket:
                                            self.server_socket.close()
                                        # 重新创建TCP服务器 socket
                                        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                                        self.server_socket.bind((self.host, self.port))
                                        self.server_socket.listen(5)
                                        self.logger.info(f"LASServer restarted, listening on {self.host}:{self.port}")
                                    except Exception as e:
                                        self.logger.error(f"Failed to restart LASServer: {str(e)}")
                                    
                                    # 3.3 重新启动接受连接的线程
                                    accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
                                    accept_thread.start()
                                    
                                    self.logger.info("Initialization sequence timeout handling completed. Waiting for LAS to reconnect.")
                    except Exception as e:
                        self.logger.error(f"Error checking initialization sequence timeout: {str(e)}")
                except Exception as e:
                    if self.is_running:
                        self.logger.error(f"Error in timeout check: {str(e)}")
                    time.sleep(1)
        except Exception as e:
            self.logger.error(f"Critical error in timeout check thread: {str(e)}")
    
    def _handle_connection_reset(self):
        """处理连接重置逻辑"""
        if self.reset_in_progress:
            return
        
        self.reset_in_progress = True
        try:
            self.logger.info("Initiating connection reset due to communication failure")
            
            # 清理待处理消息
            with self.message_lock:
                self.pending_messages.clear()
                self.retry_counts.clear()
            
            # 重置会话状态
            self.conversation_status = self.CONVERSATION_STATUS_LISTENING
            self.initialized_requests = {
                'clear_queue': set(),
                'transfer_status': set(),
                'instrument_health': False,
                'test_inventory': False,
                'onboard_sample_info': False,
                'consumable_inventory': False
            }
            
            # 重置等待标志
            self._awaiting_handshake_ack = False
            self._awaiting_init_complete_ack = False
            
            # 记录重置时间
            self.connection_reset_time = time.time()
            
            self.logger.info("Connection reset completed")
            
        except Exception as e:
            self.logger.error(f"Error handling connection reset: {str(e)}")
        finally:
            self.reset_in_progress = False
    
    def _handle_ack(self, conn, header, body):
        """处理ACK消息
        
        Args:
            conn: 连接 socket
            header: 消息头
            body: 消息体
        """
        try:
            return_code = body[0] if body else 0x00
            return_seq_id = header['return_sequence_id']
            self.logger.log_las(f"Received ACK for SeqID=0x{return_seq_id:04x}, ReturnCode=0x{return_code:02x}")
            
            # 从待处理消息中移除已确认的消息
            with self.message_lock:
                if return_seq_id in self.pending_messages:
                    del self.pending_messages[return_seq_id]
                    self.logger.log_las(f"Removed completed message from pending list: SeqID=0x{return_seq_id:04x}")
            
            if return_code == 0x00:
                # 检查是否是对主动发送的握手消息的ACK
                if hasattr(self, '_awaiting_handshake_ack') and self._awaiting_handshake_ack:
                    # 记录初始化开始时间，用于检测初始化序列超时
                    self.initialization_start_time = time.time()
                    
                    # 收到对主动握手消息的ACK，切换到initialization状态
                    self.conversation_status = self.CONVERSATION_STATUS_INITIALIZATION
                    self._awaiting_handshake_ack = False
                    self.logger.info(f"Handshake completed, switching to {self.CONVERSATION_STATUS_INITIALIZATION} state")
                    self.logger.log_las(f"Handshake completed, switching to {self.CONVERSATION_STATUS_INITIALIZATION} state")
                    self.logger.info(f"Initialization sequence started. Must complete within {self.initialization_complete_timeout} seconds")
                    # 重置初始化请求集合
                    self.initialized_requests = {
                    'clear_queue': set(),
                    'transfer_status': set(),
                    'instrument_health': False,
                    'test_inventory': False,
                    'onboard_sample_info': False,
                    'consumable_inventory': False
                }
                
                # 检查是否是对初始化完成消息的ACK
                # 只有当我们发送了Initialization Completed Message后，收到的ACK才会切换到connected状态
                elif self.conversation_status == self.CONVERSATION_STATUS_INITIALIZATION and hasattr(self, '_awaiting_init_complete_ack') and self._awaiting_init_complete_ack:
                    # 收到初始化完成消息的ACK，切换到connected状态
                    self.conversation_status = self.CONVERSATION_STATUS_CONNECTED
                    self._awaiting_init_complete_ack = False
                    self.logger.info(f"Initialization completed, switching to {self.CONVERSATION_STATUS_CONNECTED} state")
                    self.logger.log_las(f"Initialization completed, switching to {self.CONVERSATION_STATUS_CONNECTED} state")
            else:
                # NACK处理
                self.logger.warning(f"Received NACK for message: SeqID=0x{return_seq_id:04x}, ReturnCode=0x{return_code:02x}")
                # 检查NACK重试次数
                nack_count = self.retry_counts.get(return_seq_id, 0)
                if nack_count < self.max_nack_retries:
                    self.retry_counts[return_seq_id] = nack_count + 1
                    self.logger.info(f"NACK received, will retry (attempt {nack_count + 1}/{self.max_nack_retries})")
                else:
                    # 达到最大NACK重试次数，触发连接重置
                    self.logger.error(f"Max NACK retries reached for message: SeqID=0x{return_seq_id:04x}, initiating connection reset")
                    self._handle_connection_reset()
                
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
                self._handle_transfer_status_request(conn, header, body)
            elif message_type == self.MSG_TYPE_CLEAR_QUEUE_REQUEST:
                self._handle_clear_queue_request(conn, header, body)
            
            # 记录已处理的请求
            if message_type == self.MSG_TYPE_CLEAR_QUEUE_REQUEST:
                # 解析Interface Position Index
                ip_index = body[0] if body else 0
                self.initialized_requests['clear_queue'].add(ip_index)
            elif message_type == self.MSG_TYPE_TRANSFER_STATUS_REQUEST:
                # 解析Interface Position Index
                ip_index = body[0] if body else 0
                self.initialized_requests['transfer_status'].add(ip_index)
            elif message_type == self.MSG_TYPE_INSTRUMENT_HEALTH_REQUEST:
                self.initialized_requests['instrument_health'] = True
            elif message_type == self.MSG_TYPE_TEST_INVENTORY_REQUEST:
                self.initialized_requests['test_inventory'] = True
            elif message_type == self.MSG_TYPE_ONBOARD_SAMPLE_INFO_REQUEST:
                self.initialized_requests['onboard_sample_info'] = True
            elif message_type == self.MSG_TYPE_CONSUMABLE_INVENTORY_REQUEST:
                self.initialized_requests['consumable_inventory'] = True
            
            # 检查是否所有初始化请求都已处理完成
            if (len(self.initialized_requests['clear_queue']) >= 2 and 
                len(self.initialized_requests['transfer_status']) >= 2 and 
                self.initialized_requests['instrument_health'] and 
                self.initialized_requests['test_inventory'] and 
                self.initialized_requests['onboard_sample_info'] and 
                self.initialized_requests['consumable_inventory']):
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
                self._handle_clear_queue_request(conn, header, body)
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
            
            # 检查是否有IP处于locked状态
            if health_status['lock_ownership']:
                # 遍历所有接口位置，发送LOAD_UNLOAD_RESPONSE
                for i in range(health_status['interface_positions']):
                    lock_status = health_status['lock_ownership'][i] if i < len(health_status['lock_ownership']) else 2
                    # lock_ownership为1表示Locked by Instrument，需要发送LOAD_UNLOAD_RESPONSE
                    if lock_status == 1:
                        # 获取该IP上实际的样本ID
                        actual_sample_id = ""
                        # 检查core模块中是否有锁定的carrier信息
                        if hasattr(self.core, 'locked_carriers') and self.core.locked_carriers and i in self.core.locked_carriers:
                            carrier_info = self.core.locked_carriers[i]
                            if carrier_info and 'sample_id' in carrier_info:
                                actual_sample_id = carrier_info['sample_id']
                        # 发送响应消息，包含实际样本ID
                        self._send_load_unload_response(conn, i, actual_sample_id)
            
            # 发送初始化完成消息
            self._send_initialization_complete(conn)
            
            # 收到ACK后会切换到connected状态
            
        except Exception as e:
            self.logger.error(f"Error handling initialization complete: {str(e)}")
            self.logger.log_las(f"Error handling initialization complete: {str(e)}")
    
    def _send_load_unload_response(self, conn, interface_position_index=0, actual_sample_id=""):
        """发送LOAD_UNLOAD_RESPONSE消息
        
        Args:
            conn: 连接 socket
            interface_position_index: 接口位置索引，默认IP0
            actual_sample_id: 实际的样本ID，用于填充到响应消息中
        """
        try:
            # 获取相关状态
            health_status = self.core.get_instrument_health()
            ready_to_load = self.core.get_ready_to_load(interface_position_index)
            return_ready_count = self.core.get_return_ready_count()
            
            # 构建响应消息体 - 根据实际情况动态填充
            load_sample_id = actual_sample_id  # 使用传入的实际样本ID
            unload_sample_id = ""  # 暂时为空，可根据实际情况获取
            
            load_sample_id_len = len(load_sample_id)
            load_sample_id_bytes = load_sample_id.encode('ascii')
            load_status = 2  # 2=error performing Load command(Lock Carrier in place)
            
            unload_sample_id_len = len(unload_sample_id)
            unload_sample_id_bytes = unload_sample_id.encode('ascii')
            unload_status = 2  # 2=error performing Unload command(Lock Carrier in place)
            
            sample_status = 0  # 0=No Sample Present
            onboard_count = health_status['on_board_tube_count']
            completed_count = health_status['completed_tube_count']
            
            body = struct.pack(
                f'!B B {load_sample_id_len}s B B {unload_sample_id_len}s B B H H B H',
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
            
            # 记录发送的原始数据
            message_hex = binascii.hexlify(message).decode('ascii')
            extra_info = {
                'sequence_id': f"0x{sequence_id:04x}",
                'interface_position': interface_position_index,
                'load_sample_id': load_sample_id_bytes.hex(),
                'load_status': load_status,
                'unload_sample_id': unload_sample_id_bytes.hex(),
                'unload_status': unload_status,
                'sample_status': sample_status,
                'onboard_count': onboard_count,
                'completed_count': completed_count,
                'ready_to_load': ready_to_load,
                'return_ready_count': return_ready_count
            }
            self.logger.log_las_raw('SENT', message_hex, extra_info)
            
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
    
    def _build_message(self, message_type, body, return_sequence_id=0, track_message=False):
        """构建uRAP消息
        
        Args:
            message_type: 消息类型
            body: 消息体
            return_sequence_id: 返回序列ID
            track_message: 是否跟踪此消息以进行超时检查
            
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
        checksum_data = header + body  # 包含STX
        checksum = self._calculate_checksum(checksum_data)
        
        # 构建完整消息
        message = header + body + checksum + b'\x03'  # ETX
        
        # 跟踪消息以进行超时检查
        if track_message:
            with self.message_lock:
                self.pending_messages[sequence_id] = {
                    'message_type': message_type,
                    'message': message,
                    'send_time': time.time(),
                    'retries': 0
                }
        
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
            
            # 记录发送的原始数据
            message_hex = binascii.hexlify(message).decode('ascii')
            ack_type = "ACK" if return_code == 0x00 else "NACK"
            extra_info = {
                'sequence_id': f"0x{sequence_id:04x}",
                'return_sequence_id': f"0x{sequence_id:04x}",
                'return_code': f"0x{return_code:02x}"
            }
            self.logger.log_las_raw('SENT', message_hex, extra_info)
            
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
            
            # 更新连接状态为handshake_received
            for conn_id, state in list(self.connection_states.items()):
                if state['conn'] == conn:
                    state['status'] = 'handshake_received'
                    state['last_activity'] = time.time()
                    break
            
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
                return_sequence_id=return_sequence_id,
                track_message=True
            )
            
            # 记录发送的原始数据
            message_hex = binascii.hexlify(message).decode('ascii')
            extra_info = {
                'sequence_id': f"0x{sequence_id:04x}",
                'return_sequence_id': f"0x{return_sequence_id:04x}",
            }
            self.logger.log_las_raw('SENT', message_hex, extra_info)
            
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
                body,
                track_message=True
            )
            
            # 记录发送的原始数据
            message_hex = binascii.hexlify(message).decode('ascii')
            extra_info = {
                'sequence_id': f"0x{sequence_id:04x}"}
            self.logger.log_las_raw('SENT', message_hex, extra_info)
            
            # 设置等待ACK标志
            self._awaiting_init_complete_ack = True
            
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
                return_sequence_id=header['sequence_id'],
                track_message=True
            )
            
            # 记录发送的原始数据
            message_hex = binascii.hexlify(message).decode('ascii')
            extra_info = {
                'sequence_id': f"0x{sequence_id:04x}",
                'return_sequence_id': f"0x{header['sequence_id']:04x}",
                'automation_interface_status': f"0x{health_status['automation_interface_status']:04x}",
                'instrument_process_status': f"0x{health_status['instrument_process_status']:04x}",
                'lis_connection_status': f"0x{health_status['lis_connection_status']:04x}",
                'interface_positions': health_status['interface_positions'],
                'on_board_tube_count': health_status['on_board_tube_count'],
                'completed_tube_count': health_status['completed_tube_count']
            }
            self.logger.log_las_raw('SENT', message_hex, extra_info)
            
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
                return_sequence_id=header['sequence_id'],
                track_message=True
            )
            
            # 记录发送的原始数据
            message_hex = binascii.hexlify(message).decode('ascii')
            extra_info = {
                'sequence_id': f"0x{sequence_id:04x}",
                'return_sequence_id': f"0x{header['sequence_id']:04x}"
            }
            self.logger.log_las_raw('SENT', message_hex, extra_info)
            
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
            # 获取所有样本信息
            samples = self.core.get_all_samples()
            onboard_samples = [sample for sample in samples.values() if sample['status'] not in ['ejected', 'unloaded']]
            onboard_count = len(onboard_samples)
            
            # 构建响应消息体
            body = struct.pack('!H', onboard_count)
            
            # 添加每个在线样本
            for sample in onboard_samples:
                sample_id = sample['sample_id'].encode('ascii')
                body += struct.pack(f'!B {len(sample_id)}s',
                                  len(sample_id),
                                  sample_id)
            
            # 添加已移除样本数量和ID
            with self.removed_samples_lock:
                removed_count = len(self.removed_samples)
                body += struct.pack('!H', removed_count)
                
                # 添加每个已移除样本
                for removed_sample_id in self.removed_samples:
                    sample_id_bytes = removed_sample_id.encode('ascii')
                    body += struct.pack(f'!B {len(sample_id_bytes)}s',
                                      len(sample_id_bytes),
                                      sample_id_bytes)
            
            # 构建完整消息
            message, sequence_id = self._build_message(
                self.MSG_TYPE_ONBOARD_SAMPLE_INFO_RESPONSE,
                body,
                return_sequence_id=header['sequence_id'],
                track_message=True
            )
            
            # 记录发送的原始数据
            message_hex = binascii.hexlify(message).decode('ascii')
            extra_info = {
                'sequence_id': f"0x{sequence_id:04x}",
                'return_sequence_id': f"0x{header['sequence_id']:04x}", 
                'onboard_count': onboard_count
            }
            self.logger.log_las_raw('SENT', message_hex, extra_info)
            
            # 发送消息
            conn.sendall(message)
            
            self.logger.info(f"LAS onboard sample info response sent, SeqID=0x{sequence_id:04x}, Samples={onboard_count}")
            self.logger.log_las(f"Onboard sample info response sent, SeqID=0x{sequence_id:04x}, Samples={onboard_count}")
            
        except Exception as e:
            self.logger.error(f"Error handling LAS onboard sample info request: {str(e)}")
            self.logger.log_las(f"Error handling onboard sample info request: {str(e)}")
    
    def send_onboard_sample_info_message(self, conn=None, header=None, include_removed=False, track_message=False):
        """发送Onboard Sample Info消息（统一方法）
        
        该方法合并了响应发送和通知发送的功能，支持以下模式：
        1. 请求响应模式：传入conn和header，回复特定请求
        2. 广播通知模式：不传入conn，向所有连接发送通知
        3. 包含已移除样本：设置include_removed=True，包含removed_samples列表
        
        Args:
            conn: 目标连接socket，为None时发送到所有连接
            header: 请求消息头，用于设置return_sequence_id
            include_removed: 是否包含已移除样本信息
            track_message: 是否跟踪消息状态
            
        Returns:
            bool: 发送成功返回True，失败返回False
        """
        try:
            # 检查连接状态，仅在connected状态下发送
            if self.conversation_status != self.CONVERSATION_STATUS_CONNECTED:
                self.logger.warning(f"Cannot send onboard sample info message: not in connected state (current state: {self.conversation_status})")
                return False
            
            with self.connection_lock:
                # 确定目标连接列表
                if conn is not None:
                    target_connections = [conn]
                else:
                    target_connections = self.connections
                
                if not target_connections:
                    self.logger.warning("No LAS connections available, cannot send onboard sample info message")
                    return False
                
                # 获取所有样本
                samples = self.core.get_all_samples()
                onboard_samples = [sample for sample in samples.values() if sample['status'] not in ['unloaded', 'ejected']]
                onboard_count = len(onboard_samples)
                
                # 构建响应消息体
                body = struct.pack('!H', onboard_count)
                
                # 添加每个在线样本
                for sample in onboard_samples:
                    sample_id = sample['sample_id'].encode('ascii')
                    body += struct.pack(f'!B {len(sample_id)}s',
                                      len(sample_id),
                                      sample_id)
                
                # 添加已移除样本信息（如果启用）
                removed_count = 0
                if include_removed:
                    with self.removed_samples_lock:
                        removed_count = len(self.removed_samples)
                        body += struct.pack('!H', removed_count)
                        
                        # 添加每个已移除样本
                        for removed_sample_id in self.removed_samples:
                            sample_id_bytes = removed_sample_id.encode('ascii')
                            body += struct.pack(f'!B {len(sample_id_bytes)}s',
                                              len(sample_id_bytes),
                                              sample_id_bytes)
                else:
                    # 不包含已移除样本，只添加数量0
                    body += struct.pack('!H', 0)
                
                # 发送到目标连接
                for target_conn in target_connections:
                    # 构建完整消息
                    if header is not None:
                        # 请求响应模式，设置return_sequence_id
                        message, sequence_id = self._build_message(
                            self.MSG_TYPE_ONBOARD_SAMPLE_INFO_RESPONSE,
                            body,
                            return_sequence_id=header['sequence_id'],
                            track_message=track_message
                        )
                        
                        # 记录发送的原始数据
                        message_hex = binascii.hexlify(message).decode('ascii')
                        extra_info = {
                            'sequence_id': f"0x{sequence_id:04x}",
                            'return_sequence_id': f"0x{header['sequence_id']:04x}",
                            'onboard_count': onboard_count
                        }                       
                    else:
                        # 广播通知模式，不设置return_sequence_id
                        message, sequence_id = self._build_message(
                            self.MSG_TYPE_ONBOARD_SAMPLE_INFO_RESPONSE,
                            body,
                            track_message=track_message
                        )
                       
                        # 记录发送的原始数据
                        message_hex = binascii.hexlify(message).decode('ascii')
                        extra_info = {
                            'sequence_id': f"0x{sequence_id:04x}",
                            'onboard_count': onboard_count
                        }
                    
                    self.logger.log_las_raw('SENT', message_hex, extra_info)
                    # 发送消息
                    target_conn.sendall(message)
                    
                    # 记录日志
                    if include_removed:
                        self.logger.info(f"LAS onboard sample info message sent, SeqID=0x{sequence_id:04x}, Samples={onboard_count}, Removed={removed_count}")
                        self.logger.log_las(f"Onboard sample info message sent, SeqID=0x{sequence_id:04x}, Samples={onboard_count}, Removed={removed_count}")
                    else:
                        self.logger.info(f"LAS onboard sample info message sent, SeqID=0x{sequence_id:04x}, Samples={onboard_count}")
                        self.logger.log_las(f"Onboard sample info message sent, SeqID=0x{sequence_id:04x}, Samples={onboard_count}")
                
                return True
                    
        except Exception as e:
            self.logger.error(f"Error sending onboard sample info message: {str(e)}")
            self.logger.log_las(f"Error sending onboard sample info message: {str(e)}")
            return False
    
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
                return_sequence_id=header['sequence_id'],
                track_message=True
            )
            
            # 记录发送的原始数据
            message_hex = binascii.hexlify(message).decode('ascii')
            extra_info = {
                'sequence_id': f"0x{sequence_id:04x}",
                'return_sequence_id': f"0x{header['sequence_id']:04x}"
            }
            self.logger.log_las_raw('SENT', message_hex, extra_info)
            
            # 发送消息
            conn.sendall(message)
            
            self.logger.info(f"LAS consumable inventory response sent, SeqID=0x{sequence_id:04x}, Modules={module_count}")
            self.logger.log_las(f"Consumable inventory response sent, SeqID=0x{sequence_id:04x}, Modules={module_count}")
            
        except Exception as e:
            self.logger.error(f"Error handling LAS consumable inventory request: {str(e)}")
            self.logger.log_las(f"Error handling consumable inventory request: {str(e)}")
    
    def _handle_transfer_status_request(self, conn, header, body):
        """处理传输状态请求
        
        Args:
            conn: 连接 socket
            header: 消息头
            body: 消息体
        """
        try:
            # 获取传输状态
            health_status = self.core.get_instrument_health()
            
            # 从请求消息体中获取Interface Position Index字段
            interface_position_index = body[0] if body else 0
            
            # 获取核心模块的队列信息
            ready_to_load = self.core.get_ready_to_load(interface_position_index)
            return_ready_count = self.core.get_return_ready_count()
            
            # 构建响应消息体（针对请求中的接口位置）
            # 消息类型：0x020A - Transfer status response message
            # 注意：当前实现的消息格式与协议文档有差异
            # 协议定义：Interface Position Index + Ready to Load + Return Ready Tube Count
            # 当前实现：Interface Position Index + Status + Interface Idle + Error Code + Sample ID
            # TODO: 需要根据实际LAS系统要求调整消息格式
            sample_status = 0x03  # 样本状态（自定义实现，协议未定义此字段）
            interface_idle = 0x01  # 接口空闲标识
            error_code = 0x00      # 故障码
            
            # 获取待卸载的样本ID
            next_sample_id = self.core.get_next_sample_to_unload()
            sample_id_bytes = next_sample_id.encode('ascii') if next_sample_id else b''
            sample_id_len = len(sample_id_bytes)
            
            # 构建符合协议的消息体
            body = struct.pack(
                f'!BBBB{sample_id_len}s',
                interface_position_index,
                sample_status,       # 样本状态：0x03 = 检测完成，等待卸载
                interface_idle,      # 接口空闲标识：0x01 = 空闲
                error_code,          # 故障码：0x00 = 无故障
                sample_id_bytes      # 样本ID
            )
            
            # 构建完整消息
            message, sequence_id = self._build_message(
                self.MSG_TYPE_TRANSFER_STATUS_RESPONSE,
                body,
                return_sequence_id=header['sequence_id'],
                track_message=True
            )
            
            # 记录发送的原始数据
            message_hex = binascii.hexlify(message).decode('ascii')
            extra_info = {
                'sequence_id': f"0x{sequence_id:04x}",
                'return_sequence_id': f"0x{header['sequence_id']:04x}",
                'interface_position_index': interface_position_index,
                'ready_to_load': ready_to_load,
                'return_ready_count': return_ready_count
            }
            self.logger.log_las_raw('SENT', message_hex, extra_info)
            
            # 发送消息
            conn.sendall(message)
            
            self.logger.info(f"LAS transfer status response sent, SeqID=0x{sequence_id:04x}, Status=0x{sample_status:02x}, InterfaceIdle=0x{interface_idle:02x}, ErrorCode=0x{error_code:02x}, SampleID={next_sample_id}")
            self.logger.log_las(f"Transfer status response sent, SeqID=0x{sequence_id:04x}, Status=0x{sample_status:02x}, SampleID={next_sample_id}")
            
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
                return_sequence_id=header['sequence_id'],
                track_message=True
            )
            
            # 记录发送的原始数据
            message_hex = binascii.hexlify(message).decode('ascii')
            extra_info = {
                'sequence_id': f"0x{sequence_id:04x}",
                'return_sequence_id': f"0x{header['sequence_id']:04x}",
                'interface_position_index': interface_position_index,
                'carrier_occupancy': carrier_occupancy,
                'sample_id': sample_id,
                'success': success
            }
            self.logger.log_las_raw('SENT', message_hex, extra_info)
            
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
                return_sequence_id=header['sequence_id'],
                track_message=True
            )
            
            # 记录发送的原始数据
            message_hex = binascii.hexlify(message).decode('ascii')
            extra_info = {
                'sequence_id': f"0x{sequence_id:04x}",
                'return_sequence_id': f"0x{header['sequence_id']:04x}",
                'interface_position_index': interface_position_index,
                'carrier_occupancy': carrier_occupancy,
                'sample_id': sample_id,
                'in_queue': in_queue,
                'success': success
            }
            self.logger.log_las_raw('SENT', message_hex, extra_info)
            
            # 发送消息
            conn.sendall(message)
            
            self.logger.info(f"LAS skip queue response sent, SeqID=0x{sequence_id:04x}, SampleID={sample_id}, Status={'Success' if success else 'Failed'}")
            self.logger.log_las(f"Skip queue response sent, SeqID=0x{sequence_id:04x}")
            
        except Exception as e:
            self.logger.error(f"Error handling LAS skip queue request: {str(e)}")
            self.logger.log_las(f"Error handling skip queue request: {str(e)}")
    
    def _handle_clear_queue_request(self, conn, header, body):
        """处理清除队列请求
        
        Args:
            conn: 连接 socket
            header: 消息头
            body: 消息体
        """
        try:
            # 解析请求消息体中的Interface Position Index
            interface_position_index = body[0] if body else 0
            
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
                return_sequence_id=header['sequence_id'],
                track_message=True
            )
            
            # 记录发送的原始数据
            message_hex = binascii.hexlify(message).decode('ascii')
            extra_info = {
                'sequence_id': f"0x{sequence_id:04x}",
                'return_sequence_id': f"0x{header['sequence_id']:04x}",
                'interface_position_index': interface_position_index,
                'success': success
            }
            self.logger.log_las_raw('SENT', message_hex, extra_info)
            
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
            
            # 协议要求：样本ID最大长度为20个字符
            if len(sample_id) > 20:
                self.logger.warning(f"{request_type.upper()}请求被拒绝：样本ID长度超过20个字符")
                self.logger.log_las(f"{request_type.upper()} request rejected: Sample ID too long (max 20 chars)")
                # 发送错误响应 - 状态码 0x08 (Unsupported Sample ID)
                self._send_load_unload_error_response(
                    conn, header, interface_position_index,
                    status=8  # Unable to perform command: Unsupported Sample ID
                )
                return
            
            tube_height = body[offset]
            offset += 1
            
            tube_diameter = body[offset]
            offset += 1
            
            elapsed_time = struct.unpack_from('!H', body, offset)[0]
            
            # 确定请求类型
            # 根据接口索引判断：
            # - 0x00 (IP0) → Load请求（从LAS装载样本到Atellica）
            # - 0x01 (IP1) → Unload请求（从Atellica卸载样本到LAS）
            request_type = 'load' if interface_position_index == 0x00 else 'unload'
            
            # 检查carrier是否已被锁定（根据uRAP协议，同一接口位置同一时间只能处理一个请求）
            if self.core.locked_carriers[interface_position_index] is not None:
                self.logger.warning(f"{request_type.upper()}请求被拒绝：IP{interface_position_index}的carrier已被锁定")
                self.logger.log_las(f"{request_type.upper()} request rejected: Carrier locked for IP{interface_position_index}")
                # 发送错误响应
                self._send_load_unload_error_response(
                    conn, header, interface_position_index,
                    status=2  # Error: Lock Carrier in place
                )
                return
            
            # 检查该接口位置是否已有待处理请求
            if self.pending_requests[interface_position_index]:
                self.logger.warning(f"{request_type.upper()}请求被拒绝：IP{interface_position_index}已有待处理请求")
                self.logger.log_las(f"{request_type.upper()} request rejected: Pending request exists for IP{interface_position_index}")
                # 发送错误响应
                self._send_load_unload_error_response(
                    conn, header, interface_position_index,
                    status=2  # Error: Lock Carrier in place
                )
                return
            
            # 检查是否重复请求（相同序列号）
            seq_id = header['sequence_id']
            for req in self.pending_requests[interface_position_index]:
                if req['header']['sequence_id'] == seq_id:
                    self.logger.warning(f"{request_type.upper()}请求重复：SeqID=0x{seq_id:04x}")
                    return
            
            # UNLOAD请求验证：业务逻辑检查
            # 检查是否有待卸载的样本（业务规则，非协议要求）
            if request_type == 'unload':
                # 验证：使用请求中的sample_id或获取下一个待卸载样本
                # 优先使用请求中传递的sample_id（用户输入的）
                target_sample_id = sample_id if sample_id else self.core.get_next_sample_to_unload()
                if not target_sample_id:
                    self.logger.warning(f"UNLOAD请求被拒绝：无待卸载样本")
                    self.logger.log_las(f"UNLOAD request rejected: No sample ready for unload")
                    # 发送拒绝响应
                    self._send_load_unload_error_response(
                        conn, header, interface_position_index,
                        status=6  # Unload Skipped
                    )
                    return
            
            # 获取要显示的样本ID
            display_sample_id = sample_id
            if request_type == 'unload':
                # 对于UNLOAD请求，获取下一个要卸载的样本ID
                display_sample_id = self.core.get_next_sample_to_unload()
            
            # 打印调试日志
            self.logger.info(f"DEBUG - manual_complete: {manual_complete}, self.ui: {self.ui is not None}")
            self.logger.info(f"DEBUG - Request type: {request_type}, IP: {interface_position_index}, SampleID: {display_sample_id}")
            
            # 对于LOAD请求，总是等待手动操作完成
            # 对于UNLOAD请求，总是等待手动操作完成
            if not manual_complete and self.ui:
                # 显示UI提示，等待用户操作
                prompt_shown = self.ui._show_manual_prompt(request_type, interface_position_index, display_sample_id)
                
                if not prompt_shown:
                    # UI正在显示其他请求，将当前请求加入等待队列
                    self.logger.warning(f"UI busy, queuing {request_type} request for IP{interface_position_index}")
                    self.pending_requests[interface_position_index].append({
                        'conn': conn,
                        'header': header,
                        'body': body,
                        'timestamp': time.time(),  # 添加时间戳用于超时检查
                        'waiting_for_ui': True  # 标记为等待UI可用
                    })
                    return
                
                # 保存请求信息，等待手动完成（按接口位置分离存储）
                self.pending_requests[interface_position_index].append({
                    'conn': conn,
                    'header': header,
                    'body': body,
                    'timestamp': time.time()  # 添加时间戳用于超时检查
                })
                
                self.logger.info(f"LAS manual operation requested: {request_type} for IP{interface_position_index}, SampleID={display_sample_id}")
                self.logger.log_las(f"Manual operation requested: {request_type} for IP{interface_position_index}, SampleID={display_sample_id}")
                return
            
            # 处理装载/卸载请求
            self.logger.info(f"调用process_load_unload: IP={interface_position_index}, sample_id={sample_id}")
            load_result, unload_result, sample_status, onboard_count, completed_count, ready_to_load, return_ready_count = self.core.process_load_unload(
                interface_position_index,
                carrier_occupancy,
                sample_id,
                tube_height,
                tube_diameter,
                elapsed_time
            )
            self.logger.info(f"process_load_unload返回: load_result={load_result}, unload_result={unload_result}")
            
            # 确保load_result和unload_result被正确初始化
            if load_result is None:
                load_result = {'sample_id': sample_id, 'status': 1}  # 默认使用请求中的样本ID
            if unload_result is None:
                unload_result = {'sample_id': '', 'status': 1}
            
            # 转换ready_to_load为整数（struct.pack需要整数）
            if isinstance(ready_to_load, dict):
                # 如果 ready_to_load 是字典，则检查指定接口位置是否就绪（1 表示就绪，0 表示未就绪）
                ready_to_load = 1 if ready_to_load[interface_position_index] else 0
            
            # 确保load_result包含sample_id，如果没有则使用请求中的样本ID
            if 'sample_id' not in load_result or not load_result['sample_id']:
                load_result['sample_id'] = sample_id
            
            # 构建响应消息体
            # Load Sample ID
            load_sample_id_bytes = load_result.get('sample_id', '').encode('ascii') if load_result else b''
            load_sample_id_len = len(load_sample_id_bytes)
            
            # Unload Sample ID
            unload_sample_id_bytes = unload_result.get('sample_id', '').encode('ascii') if unload_result else b''
            unload_sample_id_len = len(unload_sample_id_bytes)
            
            body = struct.pack(
                f'!B B {load_sample_id_len}s B B {unload_sample_id_len}s B B H H B H',
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
                return_sequence_id=header['sequence_id'],
                track_message=True
            )
            
            # 记录发送的原始数据
            message_hex = binascii.hexlify(message).decode('ascii')
            extra_info = {
                'sequence_id': f"0x{sequence_id:04x}",
                'return_sequence_id': f"0x{header['sequence_id']:04x}",
                'interface_position_index': interface_position_index,
                'load_sample': load_result.get('sample_id', 'N/A'),
                'load_status': load_result.get('status', 1) if load_result else 1,
                'unload_sample': unload_result.get('sample_id', 'N/A'),
                'unload_status': unload_result.get('status', 1) if unload_result else 1,
                'sample_status': sample_status,
                'onboard_count': onboard_count,
                'completed_count': completed_count,
                'ready_to_load': ready_to_load,
                'return_ready_count': return_ready_count
            }
            self.logger.log_las_raw('SENT', message_hex, extra_info)
            
            # 发送消息
            self.logger.info(f"准备发送响应: conn={conn}, message_len={len(message)}")
            conn.sendall(message)
            self.logger.info(f"响应已发送")
            
            self.logger.info(f"LAS load/unload response sent, SeqID=0x{sequence_id:04x}, SampleID={sample_id}, LoadStatus={load_result.get('status') if load_result else 'N/A'}, UnloadStatus={unload_result.get('status') if unload_result else 'N/A'}")
            self.logger.log_las(f"Load/Unload response sent, SeqID=0x{sequence_id:04x}")
            
        except Exception as e:
            self.logger.error(f"Error handling LAS load/unload request: {str(e)}")
            self.logger.log_las(f"Error handling load/unload request: {str(e)}")
            
            # 1. 暂停当前机械动作，保留载具锁定状态
            self.logger.info("Step 1: Pausing current mechanical action, preserving carrier lock state")
            # 注意：载具锁定状态由core模块管理，异常处理时会自动保留
            # 这里不需要额外操作，因为core模块会维护载具锁定状态
    
    def _send_load_unload_error_response(self, conn, header, interface_position_index, status=2):
        """发送LOAD/UNLOAD错误响应
        
        Args:
            conn: 连接socket
            header: 请求消息头
            interface_position_index: 接口位置索引
            status: 错误状态码（默认2=Error: Lock Carrier in place）
        """
        try:
            # 构建错误响应体
            body = struct.pack(
                '!B B B B B B B H H B H',
                interface_position_index,
                0,  # load_sample_id_len = 0
                status if interface_position_index == 0 else 1,  # Load Status
                0,  # unload_sample_id_len = 0
                status if interface_position_index == 1 else 1,  # Unload Status
                0x00,  # Sample Status: No Tube Unloaded
                self.core.get_instrument_health()['on_board_tube_count'],
                self.core.get_instrument_health()['completed_tube_count'],
                self.core.get_ready_to_load(),
                self.core.get_return_ready_count()
            )
            
            # 构建完整消息
            message, sequence_id = self._build_message(
                self.MSG_TYPE_LOAD_UNLOAD_RESPONSE,
                body,
                return_sequence_id=header['sequence_id']
            )
            
            # 发送消息
            conn.sendall(message)
            
            self.logger.info(f"LAS load/unload error response sent, SeqID=0x{sequence_id:04x}, IP={interface_position_index}, Status={status}")
            self.logger.log_las(f"Load/Unload error response sent, SeqID=0x{sequence_id:04x}, Status={status}")
            
        except Exception as e:
            self.logger.error(f"Error sending load/unload error response: {str(e)}")
    
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
        interface_position = request['interface_position']
        
        self.logger.info(f"on_manual_operation_complete called for IP{interface_position}, pending_requests count: {len(self.pending_requests[interface_position])}")
        
        # 检查该接口位置是否有待处理请求
        if not self.pending_requests[interface_position]:
            self.logger.warning(f"No pending request for IP{interface_position}")
            return
        
        # 获取该接口位置的第一个待处理请求（FIFO）
        pending_request = self.pending_requests[interface_position].pop(0)
        conn = pending_request['conn']
        header = pending_request['header']
        body = pending_request['body']
        
        # 对于UNLOAD请求，更新pending_request的body中的样本ID
        # 解析原始body
        offset = 0
        interface_position_index = body[offset]
        offset += 1
        
        carrier_occupancy = body[offset]
        offset += 1
        
        sample_id_len = body[offset]
        offset += 1
        
        original_sample_id = ''
        if sample_id_len > 0:
            original_sample_id = body[offset:offset+sample_id_len].decode('ascii')
            offset += sample_id_len
        
        tube_height = body[offset]
        offset += 1
        
        tube_diameter = body[offset]
        offset += 1
        
        elapsed_time = struct.unpack_from('!H', body, offset)[0]
        
        # 确定请求类型
        # 根据接口索引判断：
        # - 0x00 (IP0) → Load请求（从LAS装载样本到Atellica）
        # - 0x01 (IP1) → Unload请求（从Atellica卸载样本到LAS）
        request_type = 'load' if interface_position_index == 0x00 else 'unload'
        
        # 根据请求类型处理样本ID
        if request_type == 'unload':
            # 对于UNLOAD请求，使用UI传递的样本ID（用户输入的要卸载的样本ID）
            new_sample_id = request['sample_id']
            new_sample_id_bytes = new_sample_id.encode('ascii')
            new_sample_id_len = len(new_sample_id_bytes)
            
            # 重新构建body，使用UI传递的样本ID
            body = struct.pack(
                f'!BBB{new_sample_id_len}sBBH',
                interface_position_index,
                carrier_occupancy,
                new_sample_id_len,
                new_sample_id_bytes,
                tube_height,
                tube_diameter,
                elapsed_time
            )
            self.logger.info(f"UNLOAD请求：使用UI传递的样本ID: {new_sample_id}")
        else:
            # 对于LOAD请求，使用原始请求中的样本ID（来自LAS）
            # 不需要重新构建body，使用原始body
            self.logger.info(f"LOAD请求：使用原始请求中的样本ID: {original_sample_id}")
        
        # 在后台线程中等待并发送响应，避免阻塞UI
        self.logger.info(f"{request_type.upper()}请求：手工操作完成，将在10秒后发送RESPONSE")
        threading.Thread(
            target=self._send_load_unload_response_after_delay,
            args=(conn, header, body, request_type),
            daemon=True
        ).start()
    
    def _send_load_unload_response_after_delay(self, conn, header, body, request_type):
        """在延迟后发送LOAD/UNLOAD响应（在后台线程中执行）
        
        Args:
            conn: 连接socket
            header: 消息头
            body: 消息体
            request_type: 请求类型('load'或'unload')
        """
        try:
            # 等待10秒
            self.logger.info(f"{request_type.upper()}请求：后台线程开始等待10秒...")
            time.sleep(10)
            self.logger.info(f"{request_type.upper()}请求：等待10秒完成，准备发送RESPONSE")
            
            # 检查连接是否仍然有效
            with self.connection_lock:
                if conn not in self.connections:
                    self.logger.warning(f"{request_type.upper()}请求：连接已断开，无法发送响应")
                    return
                
                # 测试连接是否有效
                try:
                    # 设置非阻塞模式测试连接
                    conn.setblocking(0)
                    # 尝试接收数据（不实际接收）
                    import select
                    ready = select.select([conn], [], [], 0)
                    conn.setblocking(1)
                    
                    if ready[0]:
                        # 有数据可读，可能是连接断开
                        data = conn.recv(1, socket.MSG_PEEK)
                        if not data:
                            self.logger.warning(f"{request_type.upper()}请求：连接已关闭")
                            return
                except Exception as conn_err:
                    self.logger.warning(f"{request_type.upper()}请求：连接测试失败: {str(conn_err)}")
                    return
            
            self.logger.info(f"{request_type.upper()}请求：连接有效，开始处理请求")
            
            # 继续处理原始请求
            try:
                self._handle_load_unload_request(conn, header, body, manual_complete=True)
                self.logger.info(f"{request_type.upper()}请求：_handle_load_unload_request执行完成")
            except Exception as e:
                self.logger.error(f"{request_type.upper()}请求：_handle_load_unload_request执行失败: {str(e)}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
            
            self.logger.info(f"{request_type.upper()}请求：响应发送完成")
        except Exception as e:
            self.logger.error(f"Error sending delayed load/unload response: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _start_pending_request_timeout_checker(self):
        """启动pending请求超时检查线程"""
        if self.timeout_check_thread is None or not self.timeout_check_thread.is_alive():
            self.timeout_check_thread = threading.Thread(
                target=self._check_pending_request_timeout_loop,
                daemon=True
            )
            self.timeout_check_thread.start()
            self.logger.info("Pending request timeout checker started")
    
    def _check_pending_request_timeout_loop(self):
        """检查pending请求超时的循环"""
        while self.is_running:
            try:
                self._check_pending_request_timeout()
                time.sleep(self.timeout_check_interval)
            except Exception as e:
                self.logger.error(f"Error in pending request timeout check: {str(e)}")
    
    def _check_pending_request_timeout(self):
        """检查并处理超时的pending请求"""
        current_time = time.time()
        
        for ip in [0, 1]:
            for request in self.pending_requests[ip][:]:  # 使用切片复制列表
                if current_time - request.get('timestamp', 0) > self.request_timeout:
                    # 请求超时，发送错误响应
                    self.logger.warning(f"Pending request timeout for IP{ip}, SeqID=0x{request['header']['sequence_id']:04x}")
                    try:
                        conn = request['conn']
                        header = request['header']
                        body = request['body']
                        interface_position_index = body[0]
                        
                        # 发送超时错误响应
                        self._send_load_unload_error_response(
                            conn, header, interface_position_index,
                            status=6  # Skipped
                        )
                        
                        # 从队列中移除
                        self.pending_requests[ip].remove(request)
                        self.logger.info(f"Removed timed out request for IP{ip}")
                    except Exception as e:
                        self.logger.error(f"Error handling timed out request: {str(e)}")
    
    def manual_eject_sample(self, sample_id, interface_position=0):
        """手动弹出样本并通知LAS

        Args:
            sample_id: 要弹出的样本ID
            interface_position: 接口位置（默认为IP0）

        Returns:
            bool: 是否成功
        """
        success = False
        try:
            # 1. 查询核心模块中的样本信息
            sample_info = self.core.get_sample_info(sample_id)
            if sample_info is None:
                self.logger.error(f"Sample {sample_id} not found in core module samples")
                return False

            # 2. 更新样本状态为 "ejected"
            with self.core.sample_lock:
                if sample_id in self.core.samples:
                    self.core.samples[sample_id]['statusII'] = self.core.samples[sample_id]['status']
                    self.core.samples[sample_id]['status'] = 'ejected'
                    self.logger.info(f"Updated sample {sample_id} status to 'ejected'")
                else:
                    self.logger.error(f"Sample {sample_id} disappeared during status update")
                    return False

            # 3. 记录已移除的标本并发送通知
            with self.removed_samples_lock:
                if sample_id not in self.removed_samples:
                    self.removed_samples.append(sample_id)
                    self.logger.info(f"Sample {sample_id} added to removed samples list")

            # 发送 Onboard Sample Info 消息通知 LAS 标本已被移除
            notification_success = self.send_onboard_sample_info_message(include_removed=True, track_message=True)
            if notification_success:
                self.logger.info(f"Sent Onboard Sample Info notification with removed sample {sample_id}")
            else:
                self.logger.warning(f"Failed to send Onboard Sample Info notification for removed sample {sample_id}")

            # 4. 如果通知发送成功，执行更新核心样本状态
            if notification_success:
                success = self.core.manual_eject_sample(sample_id)
                if not success:
                    self.logger.error(f"Failed to manually eject sample {sample_id}: Sample not found or already completed")
            else:
                self.logger.warning(f"Failed to send notification for sample {sample_id}, skipping core status update")
                success = False

            return success
        except Exception as e:
            self.logger.error(f"Error in manual_eject_sample: {str(e)}")
            self.logger.log_las(f"Error in manual eject: {str(e)}")
            return False
    
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
                    extra_info = {
                        'sequence_id': f"0x{sequence_id:04x}",
                        'interface_position_index': interface_position_index,
                        'ready_to_load': ready_to_load,
                        'return_ready_count': return_ready_count
                    }
                    self.logger.log_las_raw('SENT', message_hex, extra_info)
                    # 发送消息
                    conn.sendall(message)
                    
                    self.logger.info(f"LAS transfer status response sent, SeqID=0x{sequence_id:04x}, ReadyToLoad={ready_to_load}, ReturnReady={return_ready_count}")
                    self.logger.log_las(f"Transfer status response sent, SeqID=0x{sequence_id:04x}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending transfer status response: {str(e)}")
            self.logger.log_las(f"Error sending transfer status response: {str(e)}")
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
                    extra_info = {
                        'sequence_id': f"0x{sequence_id:04x}",
                        'automation_interface_status': f"0x{health_status['automation_interface_status']:04x}",
                        'instrument_process_status': f"0x{health_status['instrument_process_status']:04x}",
                        'lis_connection_status': f"0x{health_status['lis_connection_status']:04x}",
                        'interface_positions': f"0x{health_status['interface_positions']:04x}",
                        'on_board_tube_count': health_status['on_board_tube_count'],
                        'completed_tube_count': health_status['completed_tube_count']
                    }
                    self.logger.log_las_raw('SENT', message_hex, extra_info)
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
                    extra_info = {
                        'sequence_id': f"0x{sequence_id:04x}"
                    }
                    self.logger.log_las_raw('SENT', message_hex, extra_info)
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
                    extra_info = {
                        'sequence_id': f"0x{sequence_id:04x}"
                    }
                    self.logger.log_las_raw('SENT', message_hex, extra_info)
                    # 发送消息
                    conn.sendall(message)
                    
                    self.logger.info(f"LAS consumable inventory response sent, SeqID=0x{sequence_id:04x}, Modules={module_count}")
                    self.logger.log_las(f"Consumable inventory response sent, SeqID=0x{sequence_id:04x}, Modules={module_count}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending consumable inventory response: {str(e)}")
            self.logger.log_las(f"Error sending consumable inventory response: {str(e)}")
            return False
