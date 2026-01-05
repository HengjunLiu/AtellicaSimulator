#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
URAP指令实现测试脚本
"""

import sys
import os
import time
import threading

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core import AtellicaCore
from config import ConfigManager
from logger import Logger


def test_queue_management():
    """测试队列管理功能"""
    print("\n=== 测试队列管理功能 ===")
    
    config_manager = ConfigManager('config.json')
    logger = Logger(config_manager)
    core = AtellicaCore(config_manager, logger)
    
    # 测试1: 添加到队列
    print("\n1. 测试添加到队列:")
    success = core.add_to_queue(
        interface_position_index=0,
        carrier_occupancy=2,  # Uncapped Tube
        sample_id="QUEUE_TEST_001",
        sample_priority=1,  # Routine
        tube_height=75,
        tube_diameter=0x96  # 15mm
    )
    print(f"   添加样本到IP0队列: {'成功' if success else '失败'}")
    
    # 添加更多样本
    core.add_to_queue(0, 2, "QUEUE_TEST_002", 1, 75, 0x96)
    core.add_to_queue(0, 3, "QUEUE_TEST_003", 2, 75, 0x96)  # STAT样本
    print(f"   添加更多样本后队列长度: {len(core.queues[0])}")
    
    # 测试2: 获取队列信息
    print("\n2. 测试获取队列信息:")
    queue_info = core.get_queue_info(0)
    print(f"   IP0队列长度: {len(queue_info)}")
    for carrier in queue_info:
        print(f"   - SampleID: {carrier['sample_id']}, Occupancy: {carrier['carrier_occupancy']}, Priority: {carrier['sample_priority']}")
    
    # 测试3: 获取就绪状态
    print("\n3. 测试就绪状态:")
    ready = core.get_ready_to_load()
    print(f"   Ready To Load: {'是' if ready == 1 else '否'}")
    
    # 测试4: 跳过队列
    print("\n4. 测试跳过队列:")
    skip_success = core.skip_from_queue(0, 2, "QUEUE_TEST_001", 0)
    print(f"   跳过QUEUE_TEST_001: {'成功' if skip_success else '失败'}")
    print(f"   跳过后的队列长度: {len(core.queues[0])}")
    
    # 测试5: 清除队列
    print("\n5. 测试清除队列:")
    clear_success = core.clear_queue(0)
    print(f"   清除IP0队列: {'成功' if clear_success else '失败'}")
    print(f"   清除后的队列长度: {len(core.queues[0])}")
    
    print("\n=== 队列管理测试完成 ===")


def test_load_unload():
    """测试装载/卸载功能"""
    print("\n=== 测试装载/卸载功能 ===")
    
    config_manager = ConfigManager('config.json')
    logger = Logger(config_manager)
    core = AtellicaCore(config_manager, logger)
    
    # 准备样本
    core.receive_sample("LU_TEST_001", ['TEST001'], {})
    core.receive_sample("LU_TEST_002", ['TEST002'], {})
    
    print(f"   当前在线试管数量: {core.on_board_tube_count}")
    print(f"   当前已完成试管数量: {core.completed_tube_count}")
    
    # 测试1: 装载操作
    print("\n1. 测试装载操作:")
    load_result, unload_result, sample_status, onboard, completed, ready, return_ready = core.process_load_unload(
        interface_position_index=0,
        carrier_occupancy=2,  # Uncapped Tube
        sample_id="LU_TEST_001",
        tube_height=75,
        tube_diameter=0x96,
        elapsed_time=100
    )
    
    print(f"   Load结果:")
    print(f"   - SampleID: {load_result['sample_id']}")
    print(f"   - Status: {load_result['status']} (1=Success, 2=Lock Error, 6=Skipped, 7=Instrument Skipped)")
    print(f"   Sample Processing Status: {sample_status} (0x01=Success, 0x14=No Orders)")
    print(f"   操作后在线试管数量: {onboard}")
    print(f"   操作后就绪状态: {'是' if ready == 1 else '否'}")
    
    # 测试2: 空Carrier卸载
    print("\n2. 测试空Carrier卸载:")
    # 标记样本为完成
    core.samples["LU_TEST_001"]['status'] = 'completed'
    core.completed_tube_count += 1
    core.return_ready_count += 1
    
    print(f"   设置返回就绪样本数: {core.return_ready_count}")
    
    load_result, unload_result, sample_status, onboard, completed, ready, return_ready = core.process_load_unload(
        interface_position_index=1,
        carrier_occupancy=1,  # Empty Carrier
        sample_id="",
        tube_height=75,
        tube_diameter=0x96,
        elapsed_time=0
    )
    
    print(f"   Unload结果:")
    if unload_result:
        print(f"   - SampleID: {unload_result['sample_id']}")
        print(f"   - Status: {unload_result['status']}")
    else:
        print(f"   - 无卸载操作")
    print(f"   Sample Processing Status: {sample_status}")
    
    print("\n=== 装载/卸载测试完成 ===")


def test_transfer_status():
    """测试传输状态功能"""
    print("\n=== 测试传输状态功能 ===")
    
    config_manager = ConfigManager('config.json')
    logger = Logger(config_manager)
    core = AtellicaCore(config_manager, logger)
    
    # 测试获取传输状态
    print("\n1. 测试获取传输状态:")
    ready_to_load = core.get_ready_to_load()
    return_ready_count = core.get_return_ready_count()
    
    print(f"   Ready To Load: {ready_to_load}")
    print(f"   Return Ready Tube Count: {return_ready_count}")
    
    # 添加样本到队列
    core.add_to_queue(0, 2, "TS_TEST_001", 1, 75, 0x96)
    
    ready_to_load = core.get_ready_to_load()
    print(f"   添加样本后 Ready To Load: {ready_to_load}")
    
    print("\n=== 传输状态测试完成 ===")


def test_message_types():
    """测试消息类型常量"""
    print("\n=== 测试消息类型常量 ===")
    
    from las import LASServer
    
    config_manager = ConfigManager('config.json')
    logger = Logger(config_manager)
    core = AtellicaCore(config_manager, logger)
    
    server = LASServer(config_manager, logger, core)
    
    print("\n已实现的消息类型常量:")
    print(f"  HANDSHAKE:        0x{server.MSG_TYPE_HANDSHAKE:04x}")
    print(f"  ACK:              0x{server.MSG_TYPE_ACK:04x}")
    print(f"  KEEPALIVE:        0x{server.MSG_TYPE_KEEPALIVE:04x}")
    print(f"  INSTRUMENT_HEALTH_REQUEST:  0x{server.MSG_TYPE_INSTRUMENT_HEALTH_REQUEST:04x}")
    print(f"  INSTRUMENT_HEALTH_RESPONSE: 0x{server.MSG_TYPE_INSTRUMENT_HEALTH_RESPONSE:04x}")
    print(f"  TEST_INVENTORY_REQUEST:     0x{server.MSG_TYPE_TEST_INVENTORY_REQUEST:04x}")
    print(f"  TEST_INVENTORY_RESPONSE:    0x{server.MSG_TYPE_TEST_INVENTORY_RESPONSE:04x}")
    print(f"  ONBOARD_SAMPLE_INFO_REQUEST:  0x{server.MSG_TYPE_ONBOARD_SAMPLE_INFO_REQUEST:04x}")
    print(f"  ONBOARD_SAMPLE_INFO_RESPONSE: 0x{server.MSG_TYPE_ONBOARD_SAMPLE_INFO_RESPONSE:04x}")
    print(f"  TRANSFER_STATUS_REQUEST:  0x{server.MSG_TYPE_TRANSFER_STATUS_REQUEST:04x}")
    print(f"  TRANSFER_STATUS_RESPONSE: 0x{server.MSG_TYPE_TRANSFER_STATUS_RESPONSE:04x}")
    print(f"  CONSUMABLE_INVENTORY_REQUEST:  0x{server.MSG_TYPE_CONSUMABLE_INVENTORY_REQUEST:04x}")
    print(f"  CONSUMABLE_INVENTORY_RESPONSE: 0x{server.MSG_TYPE_CONSUMABLE_INVENTORY_RESPONSE:04x}")
    print(f"  INITIALIZATION_COMPLETE: 0x{server.MSG_TYPE_INITIALIZATION_COMPLETE:04x}")
    print(f"  LOAD_UNLOAD_REQUEST:  0x{server.MSG_TYPE_LOAD_UNLOAD_REQUEST:04x}")
    print(f"  LOAD_UNLOAD_RESPONSE: 0x{server.MSG_TYPE_LOAD_UNLOAD_RESPONSE:04x}")
    print(f"  ADD_QUEUE_REQUEST:    0x{server.MSG_TYPE_ADD_QUEUE_REQUEST:04x}")
    print(f"  ADD_QUEUE_RESPONSE:   0x{server.MSG_TYPE_ADD_QUEUE_RESPONSE:04x}")
    print(f"  SKIP_QUEUE_REQUEST:   0x{server.MSG_TYPE_SKIP_QUEUE_REQUEST:04x}")
    print(f"  SKIP_QUEUE_RESPONSE:  0x{server.MSG_TYPE_SKIP_QUEUE_RESPONSE:04x}")
    print(f"  CLEAR_QUEUE_REQUEST:  0x{server.MSG_TYPE_CLEAR_QUEUE_REQUEST:04x}")
    print(f"  CLEAR_QUEUE_RESPONSE: 0x{server.MSG_TYPE_CLEAR_QUEUE_RESPONSE:04x}")
    
    print("\n=== 消息类型常量测试完成 ===")


def test_keepalive_config():
    """测试Keep-Alive配置"""
    print("\n=== 测试Keep-Alive配置 ===")
    
    from las import LASServer
    
    config_manager = ConfigManager('config.json')
    logger = Logger(config_manager)
    core = AtellicaCore(config_manager, logger)
    
    server = LASServer(config_manager, logger, core)
    
    print(f"\nKeep-Alive配置:")
    print(f"  Keep-Alive间隔: {server.keep_alive_interval}秒")
    print(f"  超时阈值: {server.keep_alive_interval * 3}秒 (3倍间隔)")
    
    print("\n=== Keep-Alive配置测试完成 ===")


if __name__ == "__main__":
    print("=" * 60)
    print("URAP指令实现测试")
    print("=" * 60)
    
    try:
        test_message_types()
        test_keepalive_config()
        test_queue_management()
        test_load_unload()
        test_transfer_status()
        
        print("\n" + "=" * 60)
        print("所有URAP指令测试完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
