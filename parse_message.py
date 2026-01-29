#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析uRAP协议消息
"""

import struct
import binascii

def parse_urap_message(hex_message):
    """解析uRAP协议消息
    
    Args:
        hex_message: 十六进制消息字符串，空格分隔
    
    Returns:
        dict: 解析后的消息内容
    """
    # 将十六进制字符串转换为字节串
    hex_bytes = hex_message.replace(' ', '')
    message = binascii.unhexlify(hex_bytes)
    
    print(f"原始消息: {hex_message}")
    print(f"原始消息字节: {list(message)}")
    print(f"消息长度: {len(message)} 字节")
    
    # 验证STX和ETX
    if message[0] != 0x02 or message[-1] != 0x03:
        print("错误: 消息不是有效的uRAP消息，缺少STX或ETX")
        return None
    
    # 解析消息头
    msg_len = struct.unpack_from('!H', message, 1)[0]
    sequence_id = struct.unpack_from('!H', message, 3)[0]
    return_sequence_id = struct.unpack_from('!H', message, 5)[0]
    message_type = struct.unpack_from('!H', message, 7)[0]
    timestamp = message[9:17]
    instrument_id = message[17]
    
    # 消息类型映射
    msg_type_map = {
        0x0000: "ACK",
        0x0001: "HANDSHAKE",
        0x0005: "KEEPALIVE",
        0x0201: "INSTRUMENT_HEALTH_REQUEST",
        0x0202: "INSTRUMENT_HEALTH_RESPONSE",
        0x0203: "TEST_INVENTORY_REQUEST",
        0x0204: "TEST_INVENTORY_RESPONSE",
        0x0207: "ONBOARD_SAMPLE_INFO_REQUEST",
        0x0208: "ONBOARD_SAMPLE_INFO_RESPONSE",
        0x0209: "TRANSFER_STATUS_REQUEST",
        0x020A: "TRANSFER_STATUS_RESPONSE",
        0x020B: "CONSUMABLE_INVENTORY_REQUEST",
        0x020C: "CONSUMABLE_INVENTORY_RESPONSE",
        0x020D: "INITIALIZATION_COMPLETE",
        0x0303: "LOAD_UNLOAD_REQUEST",
        0x0304: "LOAD_UNLOAD_RESPONSE",
        0x0401: "ADD_QUEUE_REQUEST",
        0x0402: "ADD_QUEUE_RESPONSE",
        0x0403: "SKIP_QUEUE_REQUEST",
        0x0404: "SKIP_QUEUE_RESPONSE",
        0x0405: "CLEAR_QUEUE_REQUEST",
        0x0406: "CLEAR_QUEUE_RESPONSE"
    }
    
    msg_type_name = msg_type_map.get(message_type, f"UNKNOWN (0x{message_type:04X})")
    
    # 解析时间戳（简化版，避免解析错误）
    timestamp_str = f"原始: {binascii.hexlify(timestamp).decode('ascii')}"
    
    # 解析消息体和消息尾
    body_end = len(message) - 3  # 减去Checksum(2)和ETX(1)
    body = message[18:body_end]
    checksum = message[body_end:body_end+2]
    
    # 打印消息头信息
    print("\n=== 消息头信息 ===")
    print(f"STX: 0x02")
    print(f"消息长度: 0x{msg_len:04X} ({msg_len} 字节)")
    print(f"序列ID: 0x{sequence_id:04X} ({sequence_id})")
    print(f"返回序列ID: 0x{return_sequence_id:04X} ({return_sequence_id})")
    print(f"消息类型: 0x{message_type:04X} ({msg_type_name})")
    print(f"时间戳: {timestamp_str}")
    print(f"仪器ID: 0x{instrument_id:02X} ({instrument_id})")
    
    # 解析消息体
    print("\n=== 消息体信息 ===")
    if msg_type_name == "LOAD_UNLOAD_RESPONSE":
        parse_load_unload_response(body)
    elif msg_type_name == "LOAD_UNLOAD_REQUEST":
        parse_load_unload_request(body)
    else:
        print(f"未实现的消息类型解析: {msg_type_name}")
        print(f"消息体原始数据: {binascii.hexlify(body).decode('ascii')}")
    
    # 打印消息尾信息
    print("\n=== 消息尾信息 ===")
    print(f"校验和: 0x{checksum.hex().upper()}")
    print(f"ETX: 0x03")
    
    # 验证消息长度
    if msg_len != len(message):
        print("\n❌ 错误: 消息长度不匹配！")
        print(f"  消息头中指定的长度: {msg_len} 字节")
        print(f"  实际消息长度: {len(message)} 字节")
    else:
        print("\n✅ 消息长度匹配")
    
    # 计算并验证校验和
    calculated_checksum = calculate_checksum(message[0:body_end])
    if checksum != calculated_checksum:
        print("❌ 错误: 校验和不匹配！")
        print(f"  消息中的校验和: 0x{checksum.hex().upper()}")
        print(f"  计算得到的校验和: 0x{calculated_checksum.hex().upper()}")
    else:
        print("✅ 校验和匹配")
    
    return {
        "message_type": msg_type_name,
        "sequence_id": sequence_id,
        "return_sequence_id": return_sequence_id,
        "timestamp": timestamp_str,
        "instrument_id": instrument_id,
        "message_length": msg_len
    }

def calculate_checksum(data):
    """计算uRAP消息校验和
    
    Args:
        data: 要计算校验和的数据（包含STX和消息体，不包含校验和和ETX）
    
    Returns:
        bytes: 校验和（2字节ASCII十六进制）
    """
    # 计算二进制和，取模256，转换为2位十六进制ASCII字符串
    checksum = sum(data) % 256
    return f"{checksum:02X}".encode('ascii')

def parse_load_unload_response(body):
    """解析LOAD_UNLOAD_RESPONSE消息体
    
    Args:
        body: 消息体字节串
    """
    offset = 0
    
    print(f"消息体长度: {len(body)} 字节")
    print(f"消息体: {binascii.hexlify(body).decode('ascii')}")
    
    # 1. Interface Position Index (1字节)
    interface_position_index = body[offset]
    offset += 1
    print(f"1. 接口位置索引 (Interface Position Index): {interface_position_index} (IP{interface_position_index})")
    
    # 2. Load Sample ID Length (1字节)
    load_sample_id_len = body[offset]
    offset += 1
    print(f"2. 加载样本ID长度 (Load Sample ID Length): {load_sample_id_len} 字节")
    
    # 3. Load Sample ID (变长)
    load_sample_id = ""
    if load_sample_id_len > 0:
        load_sample_id = body[offset:offset+load_sample_id_len].decode('ascii')
    offset += load_sample_id_len
    print(f"3. 加载样本ID (Load Sample ID): '{load_sample_id}'")
    
    # 4. Load Command Status (1字节)
    load_status = body[offset]
    offset += 1
    load_status_map = {
        0x00: "Success",
        0x01: "Success",
        0x02: "No Sample Present",
        0x03: "Sample Not Accessible",
        0x04: "Sample Not Identified",
        0x05: "Sample Not Unloaded",
        0x06: "Sample Not Accepted",
        0x07: "Sample Rejected"
    }
    print(f"4. 加载命令状态 (Load Command Status): 0x{load_status:02X} ({load_status_map.get(load_status, f'Unknown (0x{load_status:02X})')})")
    
    # 5. Unload Sample ID Length (1字节)
    unload_sample_id_len = body[offset]
    offset += 1
    print(f"5. 卸载样本ID长度 (Unload Sample ID Length): {unload_sample_id_len} 字节")
    
    # 6. Unload Sample ID (变长)
    unload_sample_id = ""
    if unload_sample_id_len > 0:
        unload_sample_id = body[offset:offset+unload_sample_id_len].decode('ascii')
    offset += unload_sample_id_len
    print(f"6. 卸载样本ID (Unload Sample ID): '{unload_sample_id}'")
    
    # 7. Unload Command Status (1字节)
    unload_status = body[offset]
    offset += 1
    unload_status_map = {
        0x00: "Success",
        0x01: "Success",
        0x02: "No Sample Present",
        0x03: "Sample Not Accessible",
        0x04: "Sample Not Identified",
        0x05: "Sample Not Loaded",
        0x06: "Sample Not Accepted",
        0x07: "Sample Rejected"
    }
    print(f"7. 卸载命令状态 (Unload Command Status): 0x{unload_status:02X} ({unload_status_map.get(unload_status, f'Unknown (0x{unload_status:02X})')})")
    
    # 8. Sample Processing Status (1字节)
    sample_status = body[offset]
    offset += 1
    sample_status_map = {
        0x00: "No Tube Unloaded",
        0x01: "Sample Processed successfully",
        0x02: "Sample Processing Failed",
        0x03: "Sample Ejected",
        0x04: "Sample Retained",
        0x05: "Sample Aliquoted",
        0x06: "Sample Rerouted",
        0x07: "Sample Recapped",
        0x08: "Sample Decapped",
        0x09: "Sample Centrifuged",
        0x0A: "Sample Aliquoted and Rerouted",
        0x0B: "Sample Recapped and Rerouted",
        0x0C: "Sample Decapped and Rerouted",
        0x0D: "Sample Centrifuged and Rerouted",
        0x0E: "Sample Aliquoted and Retained",
        0x0F: "Sample Recapped and Retained",
        0x10: "Sample Decapped and Retained",
        0x11: "Sample Centrifuged and Retained",
        0x12: "Sample Aliquoted and Recapped",
        0x13: "Sample Aliquoted and Decapped",
        0x14: "Sample Aliquoted and Centrifuged",
        0x15: "Sample Recapped and Decapped",
        0x16: "Sample Recapped and Centrifuged",
        0x17: "Sample Decapped and Centrifuged",
        0x18: "Sample Aliquoted, Recapped and Rerouted",
        0x19: "Sample Aliquoted, Decapped and Rerouted",
        0x1A: "Sample Aliquoted, Centrifuged and Rerouted",
        0x1B: "Sample Aliquoted, Recapped and Retained",
        0x1C: "Sample Aliquoted, Decapped and Retained",
        0x1D: "Sample Aliquoted, Centrifuged and Retained",
        0x1E: "Sample Recapped, Decapped and Rerouted",
        0x1F: "Sample Recapped, Centrifuged and Rerouted",
        0x20: "Sample Decapped, Centrifuged and Rerouted",
        0x21: "Sample Recapped, Decapped and Retained",
        0x22: "Sample Recapped, Centrifuged and Retained",
        0x23: "Sample Decapped, Centrifuged and Retained",
        0x24: "Sample Aliquoted, Recapped, Decapped and Rerouted",
        0x25: "Sample Aliquoted, Recapped, Centrifuged and Rerouted",
        0x26: "Sample Aliquoted, Decapped, Centrifuged and Rerouted",
        0x27: "Sample Recapped, Decapped, Centrifuged and Rerouted",
        0x28: "Sample Aliquoted, Recapped, Decapped, Centrifuged and Rerouted"
    }
    print(f"8. 样本处理状态 (Sample Processing Status): 0x{sample_status:02X} ({sample_status_map.get(sample_status, f'Unknown (0x{sample_status:02X})')})")
    
    # 9. On Board Tube Count (2字节)
    onboard_count = struct.unpack_from('!H', body, offset)[0]
    offset += 2
    print(f"9. 在线试管数量 (On Board Tube Count): {onboard_count}")
    
    # 10. Completed Tube Count (2字节)
    completed_count = struct.unpack_from('!H', body, offset)[0]
    offset += 2
    print(f"10. 已完成试管数量 (Completed Tube Count): {completed_count}")
    
    # 11. Ready To Load (1字节)
    ready_to_load = body[offset]
    offset += 1
    ready_str = "Ready to Load" if ready_to_load == 1 else "Not Ready to Load"
    print(f"11. 就绪装载状态 (Ready To Load): {ready_to_load} ({ready_str})")
    
    # 12. Return Ready Tube Count (2字节)
    return_ready_count = struct.unpack_from('!H', body, offset)[0]
    offset += 2
    print(f"12. 可返回试管数量 (Return Ready Tube Count): {return_ready_count}")
    
    print(f"\n解析完成，剩余未解析字节: {len(body) - offset} 字节")
    
    # 检查是否所有字节都已解析
    if len(body) - offset != 0:
        print("❌ 错误: 消息体中还有未解析的字节！")
    else:
        print("✅ 消息体所有字节都已成功解析")
    
    # 验证字段值的合理性
    validate_load_unload_response_fields(
        interface_position_index,
        load_sample_id_len,
        load_status,
        unload_sample_id_len,
        unload_status,
        sample_status,
        onboard_count,
        completed_count,
        ready_to_load,
        return_ready_count
    )

def validate_load_unload_response_fields(
    interface_position_index,
    load_sample_id_len,
    load_status,
    unload_sample_id_len,
    unload_status,
    sample_status,
    onboard_count,
    completed_count,
    ready_to_load,
    return_ready_count
):
    """验证LOAD_UNLOAD_RESPONSE字段值的合理性
    
    Args:
        各个字段的值
    """
    print("\n=== 字段值验证 ===")
    
    # 验证Interface Position Index
    if interface_position_index not in [0, 1]:
        print(f"❌ 警告: 接口位置索引 {interface_position_index} 超出预期范围 [0, 1]")
    else:
        print(f"✅ 接口位置索引 {interface_position_index} 有效")
    
    # 验证Load Sample ID Length
    if load_sample_id_len > 24:
        print(f"❌ 警告: 加载样本ID长度 {load_sample_id_len} 超出最大允许值 24")
    else:
        print(f"✅ 加载样本ID长度 {load_sample_id_len} 有效")
    
    # 验证Load Command Status
    valid_load_statuses = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07]
    if load_status not in valid_load_statuses:
        print(f"❌ 警告: 加载命令状态 0x{load_status:02X} 不在有效范围内 {[hex(s) for s in valid_load_statuses]}")
    else:
        print(f"✅ 加载命令状态 0x{load_status:02X} 有效")
    
    # 验证Unload Sample ID Length
    if unload_sample_id_len > 24:
        print(f"❌ 警告: 卸载样本ID长度 {unload_sample_id_len} 超出最大允许值 24")
    else:
        print(f"✅ 卸载样本ID长度 {unload_sample_id_len} 有效")
    
    # 验证Unload Command Status
    valid_unload_statuses = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07]
    if unload_status not in valid_unload_statuses:
        print(f"❌ 警告: 卸载命令状态 0x{unload_status:02X} 不在有效范围内 {[hex(s) for s in valid_unload_statuses]}")
    else:
        print(f"✅ 卸载命令状态 0x{unload_status:02X} 有效")
    
    # 验证Sample Processing Status
    valid_sample_statuses = list(range(0x00, 0x29))  # 0x00-0x28
    if sample_status not in valid_sample_statuses:
        print(f"❌ 警告: 样本处理状态 0x{sample_status:02X} 不在有效范围内 0x00-0x28")
    else:
        print(f"✅ 样本处理状态 0x{sample_status:02X} 有效")
    
    # 验证Ready To Load
    if ready_to_load not in [0, 1]:
        print(f"❌ 警告: 就绪装载状态 {ready_to_load} 不在有效范围内 [0, 1]")
    else:
        print(f"✅ 就绪装载状态 {ready_to_load} 有效")
    
    # 验证计数字段
    if onboard_count < 0:
        print(f"❌ 警告: 在线试管数量 {onboard_count} 不能为负数")
    else:
        print(f"✅ 在线试管数量 {onboard_count} 有效")
    
    if completed_count < 0:
        print(f"❌ 警告: 已完成试管数量 {completed_count} 不能为负数")
    else:
        print(f"✅ 已完成试管数量 {completed_count} 有效")
    
    if return_ready_count < 0:
        print(f"❌ 警告: 可返回试管数量 {return_ready_count} 不能为负数")
    else:
        print(f"✅ 可返回试管数量 {return_ready_count} 有效")

def parse_load_unload_request(body):
    """解析LOAD_UNLOAD_REQUEST消息体
    
    Args:
        body: 消息体字节串
    """
    offset = 0
    
    print(f"消息体长度: {len(body)} 字节")
    print(f"消息体: {binascii.hexlify(body).decode('ascii')}")
    
    # 1. Interface Position Index (1字节)
    interface_position_index = body[offset]
    offset += 1
    print(f"1. 接口位置索引 (Interface Position Index): {interface_position_index} (IP{interface_position_index})")
    
    # 2. Carrier Occupancy (1字节)
    carrier_occupancy = body[offset]
    offset += 1
    occupancy_str = "Loaded" if carrier_occupancy == 1 else "Empty"
    print(f"2. 载体占用状态 (Carrier Occupancy): {carrier_occupancy} ({occupancy_str})")
    
    # 3. Sample ID Length (1字节)
    sample_id_len = body[offset]
    offset += 1
    print(f"3. 样本ID长度 (Sample ID Length): {sample_id_len} 字节")
    
    # 4. Sample ID (变长)
    sample_id = ""
    if sample_id_len > 0:
        sample_id = body[offset:offset+sample_id_len].decode('ascii')
    offset += sample_id_len
    print(f"4. 样本ID (Sample ID): '{sample_id}'")
    
    # 5. Tube Height (1字节)
    tube_height = body[offset]
    offset += 1
    print(f"5. 试管高度 (Tube Height): {tube_height}")
    
    # 6. Tube Diameter (1字节)
    tube_diameter = body[offset]
    offset += 1
    print(f"6. 试管直径 (Tube Diameter): {tube_diameter}")
    
    # 7. Elapsed Time (2字节)
    elapsed_time = struct.unpack_from('!H', body, offset)[0]
    offset += 2
    print(f"7. 经过时间 (Elapsed Time): {elapsed_time} 秒")
    
    print(f"\n解析完成，剩余未解析字节: {len(body) - offset} 字节")

if __name__ == "__main__":
    # 用户提供的消息
    hex_message = "02 00 22 00 17 00 16 03 04 00 1a 01 1a 11 22 2a 03 ff 00 00 01 00 01 01 00 01 00 00 01 00 00 46 31 03"
    parse_urap_message(hex_message)
