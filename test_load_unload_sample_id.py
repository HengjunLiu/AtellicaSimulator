#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试LOAD_UNLOAD_RESPONSE消息中Sample ID是否与请求消息一致
"""

import socket
import time
import struct
import binascii

# LAS服务器配置
LAS_SERVER_HOST = 'localhost'
LAS_SERVER_PORT = 10011

# 消息类型常量
MSG_TYPE_LOAD_UNLOAD_REQUEST = 0x0303
MSG_TYPE_LOAD_UNLOAD_RESPONSE = 0x0304

# 构建LOAD_UNLOAD_REQUEST消息

def build_load_unload_request(sample_id="TS01", carrier_occupancy=0x02):
    """构建LOAD_UNLOAD_REQUEST消息
    
    Args:
        sample_id: 样本ID
        carrier_occupancy: 载体占用状态
    
    Returns:
        bytes: 完整的uRAP消息
    """
    # 消息头部分
    stx = b'\x02'  # STX
    msg_len = 0x0020  # 消息总长度
    sequence_id = 0x0016  # 序列ID
    return_sequence_id = 0x0000  # 返回序列ID
    message_type = MSG_TYPE_LOAD_UNLOAD_REQUEST  # 消息类型
    timestamp = b'\x00\x00\x01\x9b\xf9\xa7\xac\x36'  # 时间戳
    instrument_id = b'\xff'  # 仪器ID
    
    # 消息体部分
    interface_position_index = 0x00  # IP0
    sample_id_bytes = sample_id.encode('ascii')
    sample_id_len = len(sample_id_bytes)
    tube_height = 0x00  # 试管高度
    tube_diameter = 0x82  # 试管直径
    elapsed_time = 0xffff  # 经过时间
    
    # 构建消息体
    body = struct.pack(
        f'!B B {sample_id_len}s B B H',
        interface_position_index,
        carrier_occupancy,
        sample_id_len,
        sample_id_bytes,
        tube_height,
        tube_diameter,
        elapsed_time
    )
    
    # 构建消息头
    header = struct.pack(
        '!H H H H 8sc',
        msg_len,
        sequence_id,
        return_sequence_id,
        message_type,
        timestamp,
        instrument_id
    )
    
    # 组合消息头和消息体
    message_without_checksum = stx + header + body
    
    # 计算校验和
    checksum = sum(message_without_checksum) % 256
    checksum_bytes = f"{checksum:02X}".encode('ascii')
    
    # 添加ETX
    etx = b'\x03'
    
    # 完整消息
    full_message = message_without_checksum + checksum_bytes + etx
    
    return full_message

# 解析LOAD_UNLOAD_RESPONSE消息
def parse_load_unload_response(message):
    """解析LOAD_UNLOAD_RESPONSE消息
    
    Args:
        message: 完整的uRAP消息
    
    Returns:
        dict: 解析后的消息内容
    """
    # 验证STX和ETX
    if message[0] != 0x02 or message[-1] != 0x03:
        print("错误: 消息不是有效的uRAP消息，缺少STX或ETX")
        return None
    
    # 解析消息头
    msg_len = struct.unpack_from('!H', message, 1)[0]
    sequence_id = struct.unpack_from('!H', message, 3)[0]
    return_sequence_id = struct.unpack_from('!H', message, 5)[0]
    message_type = struct.unpack_from('!H', message, 7)[0]
    
    if message_type != MSG_TYPE_LOAD_UNLOAD_RESPONSE:
        print(f"错误: 消息类型不是LOAD_UNLOAD_RESPONSE，而是0x{message_type:04X}")
        return None
    
    # 解析消息体
    offset = 18  # 消息头长度
    
    # 1. Interface Position Index (1字节)
    interface_position_index = message[offset]
    offset += 1
    
    # 2. Load Sample ID Length (1字节)
    load_sample_id_len = message[offset]
    offset += 1
    
    # 3. Load Sample ID (变长)
    load_sample_id = ""
    if load_sample_id_len > 0:
        load_sample_id = message[offset:offset+load_sample_id_len].decode('ascii')
    offset += load_sample_id_len
    
    # 4. Load Command Status (1字节)
    load_status = message[offset]
    offset += 1
    
    return {
        "interface_position_index": interface_position_index,
        "load_sample_id": load_sample_id,
        "load_status": load_status,
        "sequence_id": sequence_id,
        "return_sequence_id": return_sequence_id
    }

# 测试主函数
def test_load_unload_response_sample_id():
    """测试LOAD_UNLOAD_RESPONSE消息中的Sample ID是否与请求消息一致"""
    print("测试LOAD_UNLOAD_RESPONSE消息中的Sample ID是否与请求消息一致")
    print("=" * 60)
    
    try:
        # 连接到LAS服务器
        print(f"连接到LAS服务器 {LAS_SERVER_HOST}:{LAS_SERVER_PORT}...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((LAS_SERVER_HOST, LAS_SERVER_PORT))
            print("连接成功！")
            
            # 构建测试消息
            test_sample_id = "TS01"
            request_message = build_load_unload_request(sample_id=test_sample_id, carrier_occupancy=0x02)
            print(f"\n发送LOAD_UNLOAD_REQUEST消息，样本ID: '{test_sample_id}'")
            print(f"消息内容: {binascii.hexlify(request_message).decode('ascii')}")
            
            # 发送消息
            s.sendall(request_message)
            
            # 接收响应
            print("\n等待LOAD_UNLOAD_RESPONSE消息...")
            response = s.recv(1024)
            print(f"收到响应消息: {binascii.hexlify(response).decode('ascii')}")
            
            # 解析响应
            response_info = parse_load_unload_response(response)
            if response_info:
                print("\n响应消息解析结果:")
                print(f"  接口位置索引: {response_info['interface_position_index']} (IP{response_info['interface_position_index']})")
                print(f"  加载样本ID: '{response_info['load_sample_id']}'")
                print(f"  加载命令状态: 0x{response_info['load_status']:02X}")
                print(f"  序列ID: 0x{response_info['sequence_id']:04X}")
                print(f"  返回序列ID: 0x{response_info['return_sequence_id']:04X}")
                
                # 验证样本ID是否一致
                if response_info['load_sample_id'] == test_sample_id:
                    print(f"\n✅ 测试通过: 响应消息中的Sample ID '{response_info['load_sample_id']}'与请求消息中的Sample ID '{test_sample_id}'一致！")
                else:
                    print(f"\n❌ 测试失败: 响应消息中的Sample ID '{response_info['load_sample_id']}'与请求消息中的Sample ID '{test_sample_id}'不一致！")
            
    except ConnectionRefusedError:
        print(f"❌ 连接失败: 无法连接到LAS服务器 {LAS_SERVER_HOST}:{LAS_SERVER_PORT}")
        print("请确保LAS服务器已启动，或检查端口配置是否正确")
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
    
    print("\n" + "=" * 60)
    print("测试完成")

if __name__ == "__main__":
    test_load_unload_response_sample_id()
