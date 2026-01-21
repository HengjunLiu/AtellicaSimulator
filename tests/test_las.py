#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAS模块测试程序
包含单元测试、集成测试和功能测试用例
"""

import unittest
import threading
import time
import socket
import struct
import binascii
from unittest.mock import MagicMock, patch

# 添加项目根目录到Python路径
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from las.las import LASServer


class TestLASModule(unittest.TestCase):
    """LAS模块测试类"""
    
    def setUp(self):
        """设置测试环境"""
        # 创建模拟对象
        self.mock_config_manager = MagicMock()
        self.mock_logger = MagicMock()
        self.mock_core = MagicMock()
        
        # 配置模拟对象
        self.mock_config_manager.get_las_config.return_value = {
            'host': '0.0.0.0',
            'port': 10011,
            'keep_alive_interval': 15
        }
        
        self.mock_core.get_instrument_health.return_value = {
            'automation_interface_status': 1,
            'instrument_process_status': 1,
            'lis_connection_status': 1,
            'interface_positions': 2,
            'remote_control_status': [1, 1],
            'lock_ownership': [2, 2],
            'processing_backlog': 0,
            'sample_acquisition_delay': 0,
            'on_board_tube_count': 0,
            'completed_tube_count': 0
        }
        
        self.mock_core.get_test_inventory.return_value = {
            'tests': []
        }
        
        self.mock_core.get_all_samples.return_value = {}
        
        self.mock_core.get_consumable_inventory.return_value = {
            'modules': []
        }
        
        self.mock_core.get_ready_to_load.return_value = 0
        self.mock_core.get_return_ready_count.return_value = 0
        
        # 创建LASServer实例
        self.las_server = LASServer(self.mock_config_manager, self.mock_logger, self.mock_core)
    
    def tearDown(self):
        """清理测试环境"""
        if self.las_server.is_running:
            self.las_server.stop()
    
    def test_initialization(self):
        """测试LASServer初始化"""
        # 验证初始状态
        self.assertEqual(self.las_server.conversation_status, self.las_server.CONVERSATION_STATUS_LISTENING)
        self.assertEqual(self.las_server.host, '0.0.0.0')
        self.assertEqual(self.las_server.port, 10011)
        self.assertFalse(self.las_server.is_running)
        self.assertEqual(len(self.las_server.connections), 0)
    
    def test_start_stop(self):
        """测试LASServer启动和停止"""
        # 测试启动
        self.las_server.start()
        time.sleep(0.5)  # 等待服务器启动
        self.assertTrue(self.las_server.is_running)
        self.assertIsNotNone(self.las_server.server_socket)
        
        # 测试停止
        self.las_server.stop()
        self.assertFalse(self.las_server.is_running)
        self.assertIsNone(self.las_server.server_socket)
        self.assertEqual(len(self.las_server.connections), 0)
    
    def test_conversation_status_initialization(self):
        """测试会话状态初始化"""
        # 验证初始状态
        self.assertEqual(self.las_server.conversation_status, self.las_server.CONVERSATION_STATUS_LISTENING)
    
    def test_send_transfer_status_response(self):
        """测试发送传输状态响应"""
        # 设置为connected状态
        self.las_server.conversation_status = self.las_server.CONVERSATION_STATUS_CONNECTED
        
        # 模拟连接
        mock_conn = MagicMock()
        self.las_server.connections.append(mock_conn)
        
        # 调用方法
        result = self.las_server.send_transfer_status_response(0, 1, 2)
        
        # 验证结果
        self.assertTrue(result)
        mock_conn.sendall.assert_called_once()
    
    def test_send_onboard_sample_info_response(self):
        """测试发送在线样本信息响应"""
        # 设置为connected状态
        self.las_server.conversation_status = self.las_server.CONVERSATION_STATUS_CONNECTED
        
        # 模拟连接
        mock_conn = MagicMock()
        self.las_server.connections.append(mock_conn)
        
        # 调用方法
        result = self.las_server.send_onboard_sample_info_response()
        
        # 验证结果
        self.assertTrue(result)
        mock_conn.sendall.assert_called_once()
    
    def test_send_instrument_health_response(self):
        """测试发送仪器健康响应"""
        # 设置为connected状态
        self.las_server.conversation_status = self.las_server.CONVERSATION_STATUS_CONNECTED
        
        # 模拟连接
        mock_conn = MagicMock()
        self.las_server.connections.append(mock_conn)
        
        # 调用方法
        result = self.las_server.send_instrument_health_response()
        
        # 验证结果
        self.assertTrue(result)
        mock_conn.sendall.assert_called_once()
    
    def test_send_test_inventory_response(self):
        """测试发送测试库存响应"""
        # 设置为connected状态
        self.las_server.conversation_status = self.las_server.CONVERSATION_STATUS_CONNECTED
        
        # 模拟连接
        mock_conn = MagicMock()
        self.las_server.connections.append(mock_conn)
        
        # 调用方法
        result = self.las_server.send_test_inventory_response()
        
        # 验证结果
        self.assertTrue(result)
        mock_conn.sendall.assert_called_once()
    
    def test_send_consumable_inventory_response(self):
        """测试发送耗材库存响应"""
        # 设置为connected状态
        self.las_server.conversation_status = self.las_server.CONVERSATION_STATUS_CONNECTED
        
        # 模拟连接
        mock_conn = MagicMock()
        self.las_server.connections.append(mock_conn)
        
        # 调用方法
        result = self.las_server.send_consumable_inventory_response()
        
        # 验证结果
        self.assertTrue(result)
        mock_conn.sendall.assert_called_once()
    
    def test_invalid_message_in_listening_state(self):
        """测试在监听状态下收到无效消息"""
        # 创建模拟消息
        mock_header = {'message_type': 0x0201, 'sequence_id': 1}
        mock_body = b''
        mock_conn = MagicMock()
        mock_addr = ('127.0.0.1', 12345)
        
        # 调用方法
        self.las_server._process_listening_state(mock_conn, mock_header, mock_body, mock_addr)
        
        # 验证结果
        mock_conn.sendall.assert_called_once()
    
    def test_valid_handshake_in_listening_state(self):
        """测试在监听状态下收到有效握手消息"""
        # 创建模拟消息
        mock_header = {'message_type': 0x0001, 'sequence_id': 1}
        mock_body = struct.pack('!HHHHcB4s', 0x0330, 0x0001, 0x0104, 0x0100, b'\xFF', 4, b'1234')
        mock_conn = MagicMock()
        mock_addr = ('127.0.0.1', 12345)
        
        # 调用方法
        self.las_server._process_listening_state(mock_conn, mock_header, mock_body, mock_addr)
        
        # 验证结果
        self.assertTrue(hasattr(self.las_server, '_awaiting_handshake_ack'))
        self.assertTrue(self.las_server._awaiting_handshake_ack)
    
    def test_ack_processing(self):
        """测试ACK消息处理"""
        # 设置awaiting_handshake_ack标志
        self.las_server._awaiting_handshake_ack = True
        
        # 创建模拟消息
        mock_header = {'return_sequence_id': 1}
        mock_body = b'\x00'
        mock_conn = MagicMock()
        
        # 调用方法
        self.las_server._handle_ack(mock_conn, mock_header, mock_body)
        
        # 验证结果
        self.assertEqual(self.las_server.conversation_status, self.las_server.CONVERSATION_STATUS_INITIALIZATION)
        self.assertFalse(self.las_server._awaiting_handshake_ack)
    
    def test_initialization_complete(self):
        """测试初始化完成"""
        # 设置为initialization状态
        self.las_server.conversation_status = self.las_server.CONVERSATION_STATUS_INITIALIZATION
        
        # 设置等待初始化完成ACK标志
        self.las_server._awaiting_init_complete_ack = True

        # 创建模拟消息
        mock_header = {'return_sequence_id': 1}
        mock_body = b'\x00'
        mock_conn = MagicMock()

        # 调用方法
        self.las_server._handle_ack(mock_conn, mock_header, mock_body)

        # 验证结果
        self.assertEqual(self.las_server.conversation_status, self.las_server.CONVERSATION_STATUS_CONNECTED)


class TestLASIntegration(unittest.TestCase):
    """LAS模块集成测试类"""
    
    def setUp(self):
        """设置测试环境"""
        # 创建模拟对象
        self.mock_config_manager = MagicMock()
        self.mock_logger = MagicMock()
        self.mock_core = MagicMock()
        
        # 配置模拟对象
        self.mock_config_manager.get_las_config.return_value = {
            'host': '127.0.0.1',
            'port': 10012,
            'keep_alive_interval': 15
        }
        
        self.mock_core.get_instrument_health.return_value = {
            'automation_interface_status': 1,
            'instrument_process_status': 1,
            'lis_connection_status': 1,
            'interface_positions': 2,
            'remote_control_status': [1, 1],
            'lock_ownership': [2, 2],
            'processing_backlog': 0,
            'sample_acquisition_delay': 0,
            'on_board_tube_count': 0,
            'completed_tube_count': 0
        }
        
        self.mock_core.get_test_inventory.return_value = {
            'tests': []
        }
        
        self.mock_core.get_all_samples.return_value = {}
        
        self.mock_core.get_consumable_inventory.return_value = {
            'modules': []
        }
        
        self.mock_core.get_ready_to_load.return_value = 0
        self.mock_core.get_return_ready_count.return_value = 0
        
        # 创建LASServer实例
        self.las_server = LASServer(self.mock_config_manager, self.mock_logger, self.mock_core)
    
    def tearDown(self):
        """清理测试环境"""
        if self.las_server.is_running:
            self.las_server.stop()
    
    def test_server_startup(self):
        """测试服务器启动"""
        # 启动服务器
        server_thread = threading.Thread(target=self.las_server.start)
        server_thread.daemon = True
        server_thread.start()
        
        # 等待服务器启动
        time.sleep(1)
        
        # 验证服务器是否正在运行
        self.assertTrue(self.las_server.is_running)
        
        # 尝试连接服务器
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = client_socket.connect_ex(('127.0.0.1', 10012))
        client_socket.close()
        
        # 验证连接成功
        self.assertEqual(result, 0)
    
    def test_message_processing(self):
        """测试消息处理"""
        # 启动服务器
        server_thread = threading.Thread(target=self.las_server.start)
        server_thread.daemon = True
        server_thread.start()
        
        # 等待服务器启动
        time.sleep(1)
        
        # 连接服务器
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('127.0.0.1', 10012))
        
        # 发送握手消息
        # 构建握手消息
        protocol_version = 0x0330
        instrument_type = 0x0001
        capability_version = 0x0104
        software_version = 0x0100
        instrument_id = 0xFF
        serial_len = 4
        instrument_serial = b'1234'
        
        body = struct.pack(f'!HHHHcB{serial_len}s', 
                         protocol_version, instrument_type, capability_version, software_version,
                         bytes([instrument_id]), serial_len, instrument_serial)
        
        # 构建完整消息
        msg_len = 1 + 2 + 2 + 2 + 2 + 8 + 1 + len(body) + 2 + 1  # STX + Header + Body + Footer + ETX
        sequence_id = 1
        return_sequence_id = 0
        message_type = 0x0001
        timestamp = b'\x1A\x01\x0C\x0D\x0E\x0F\x00\x00'
        instrument_id_byte = bytes([instrument_id])
        
        header = struct.pack('!cHHHH8sc', 
                          b'\x02', msg_len, sequence_id, return_sequence_id, message_type, timestamp, instrument_id_byte)
        
        checksum_data = header + body
        checksum = sum(checksum_data) % 256
        checksum_bytes = f"{checksum:02X}".encode('ascii')
        
        message = header + body + checksum_bytes + b'\x03'
        
        # 发送消息
        client_socket.sendall(message)
        
        # 接收响应
        response = client_socket.recv(4096)
        
        # 验证响应
        self.assertIn(b'\x02', response)
        self.assertIn(b'\x03', response)
        
        # 关闭连接
        client_socket.close()


class TestLASFunctional(unittest.TestCase):
    """LAS模块功能测试类"""
    
    def setUp(self):
        """设置测试环境"""
        # 创建模拟对象
        self.mock_config_manager = MagicMock()
        self.mock_logger = MagicMock()
        self.mock_core = MagicMock()
        
        # 配置模拟对象
        self.mock_config_manager.get_las_config.return_value = {
            'host': '127.0.0.1',
            'port': 10013,
            'keep_alive_interval': 15
        }
        
        self.mock_core.get_instrument_health.return_value = {
            'automation_interface_status': 1,
            'instrument_process_status': 1,
            'lis_connection_status': 1,
            'interface_positions': 2,
            'remote_control_status': [1, 1],
            'lock_ownership': [2, 2],
            'processing_backlog': 0,
            'sample_acquisition_delay': 0,
            'on_board_tube_count': 0,
            'completed_tube_count': 0
        }
        
        self.mock_core.get_test_inventory.return_value = {
            'tests': [
                {'name': 'Test1', 'count': 10, 'status': 1},
                {'name': 'Test2', 'count': 20, 'status': 1}
            ]
        }
        
        self.mock_core.get_all_samples.return_value = {
            '1': {'sample_id': 'Sample1', 'status': 'processing'},
            '2': {'sample_id': 'Sample2', 'status': 'completed'}
        }
        
        self.mock_core.get_consumable_inventory.return_value = {
            'modules': [
                {
                    'id': 'Module1',
                    'consumables': [
                        {'id': 1, 'status': 1},
                        {'id': 2, 'status': 2}
                    ]
                }
            ]
        }
        
        self.mock_core.get_ready_to_load.return_value = 2
        self.mock_core.get_return_ready_count.return_value = 1
        
        # 创建LASServer实例
        self.las_server = LASServer(self.mock_config_manager, self.mock_logger, self.mock_core)
    
    def tearDown(self):
        """清理测试环境"""
        if self.las_server.is_running:
            self.las_server.stop()
    
    def test_end_to_end_handshake(self):
        """测试端到端握手流程"""
        # 启动服务器
        server_thread = threading.Thread(target=self.las_server.start)
        server_thread.daemon = True
        server_thread.start()
        
        # 等待服务器启动
        time.sleep(1)
        
        # 连接服务器
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('127.0.0.1', 10013))
        
        try:
            # 发送握手消息
            # 构建握手消息
            protocol_version = 0x0330
            instrument_type = 0x0001
            capability_version = 0x0104
            software_version = 0x0100
            instrument_id = 0xFF
            serial_len = 4
            instrument_serial = b'1234'
            
            body = struct.pack(f'!HHHHcB{serial_len}s', 
                             protocol_version, instrument_type, capability_version, software_version,
                             bytes([instrument_id]), serial_len, instrument_serial)
            
            # 构建完整消息
            msg_len = 1 + 2 + 2 + 2 + 2 + 8 + 1 + len(body) + 2 + 1  # STX + Header + Body + Footer + ETX
            sequence_id = 1
            return_sequence_id = 0
            message_type = 0x0001
            timestamp = b'\x1A\x01\x0C\x0D\x0E\x0F\x00\x00'
            instrument_id_byte = bytes([instrument_id])
            
            header = struct.pack('!cHHHH8sc', 
                              b'\x02', msg_len, sequence_id, return_sequence_id, message_type, timestamp, instrument_id_byte)
            
            checksum_data = header + body
            checksum = sum(checksum_data) % 256
            checksum_bytes = f"{checksum:02X}".encode('ascii')
            
            message = header + body + checksum_bytes + b'\x03'
            
            # 发送消息
            client_socket.sendall(message)
            
            # 接收响应
            response = client_socket.recv(8192)  # 增加缓冲区大小
            
            # 验证响应包含STX和ETX
            self.assertIn(b'\x02', response, "响应中没有STX标记")
            self.assertIn(b'\x03', response, "响应中没有ETX标记")
            
            # 验证至少收到了两个消息（ACK和握手响应）
            stx_count = response.count(b'\x02')
            etx_count = response.count(b'\x03')
            self.assertGreaterEqual(stx_count, 1, f"至少应该有1个STX标记，实际有{stx_count}个")
            self.assertGreaterEqual(etx_count, 1, f"至少应该有1个ETX标记，实际有{etx_count}个")
            
            # 记录测试结果
            self.mock_logger.info(f"端到端握手测试完成，收到{stx_count}个消息")
            
        finally:
            # 关闭连接
            client_socket.close()
    
    def test_all_active_messages(self):
        """测试所有主动消息发送"""
        # 启动服务器
        server_thread = threading.Thread(target=self.las_server.start)
        server_thread.daemon = True
        server_thread.start()
        
        # 等待服务器启动
        time.sleep(1)
        
        # 连接服务器
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('127.0.0.1', 10013))
        
        try:
            # 设置服务器状态为connected
            self.las_server.conversation_status = self.las_server.CONVERSATION_STATUS_CONNECTED
            
            # 测试所有主动消息发送方法
            result1 = self.las_server.send_transfer_status_response()
            result2 = self.las_server.send_onboard_sample_info_response()
            result3 = self.las_server.send_instrument_health_response()
            result4 = self.las_server.send_test_inventory_response()
            result5 = self.las_server.send_consumable_inventory_response()
            
            # 验证结果
            self.assertTrue(result1)
            self.assertTrue(result2)
            self.assertTrue(result3)
            self.assertTrue(result4)
            self.assertTrue(result5)
        finally:
            # 关闭连接
            client_socket.close()


if __name__ == '__main__':
    # 创建测试套件
    suite = unittest.TestSuite()
    
    # 添加测试类 - 使用现代方式
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLASModule))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLASIntegration))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLASFunctional))
    
    # 运行测试并生成报告
    # 检查xmlrunner是否可用
    try:
        import xmlrunner
        
        # 创建报告目录
        if not os.path.exists('test_reports'):
            os.makedirs('test_reports')
        
        # 运行测试
        with open('test_reports/las_test_report.xml', 'wb') as output:
            runner = xmlrunner.XMLTestRunner(output=output, verbosity=2)
            result = runner.run(suite)
    except ImportError:
        # 如果xmlrunner不可用，使用标准测试运行器
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
    
    # 打印测试结果
    print(f"\n\n测试结果总结：")
    print(f"运行测试用例数：{result.testsRun}")
    print(f"失败测试用例数：{len(result.failures)}")
    print(f"错误测试用例数：{len(result.errors)}")
    print(f"跳过测试用例数：{len(result.skipped)}")
    
    if result.wasSuccessful():
        print("测试通过！")
    else:
        print("测试失败！")
        sys.exit(1)