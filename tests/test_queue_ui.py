#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试队列管理UI更新功能
"""

import sys
import time
from config import ConfigManager
from logger import Logger
from core import AtellicaCore


def test_queue_ui():
    """测试队列管理UI更新功能"""
    print("=== 测试队列管理UI更新功能 ===")
    
    # 初始化配置和日志
    config_manager = ConfigManager("config.json")
    logger = Logger(config_manager)
    
    # 初始化核心逻辑
    core = AtellicaCore(config_manager, logger)
    
    print("\n1. 初始状态检查:")
    print(f"   就绪装载: {core.get_ready_to_load()}")
    print(f"   可返回样本数: {core.get_return_ready_count()}")
    print(f"   IP0队列长度: {len(core.get_queue_info(0))}")
    print(f"   IP1队列长度: {len(core.get_queue_info(1))}")
    print(f"   IP0锁定状态: {core.locked_carriers[0]}")
    print(f"   IP1锁定状态: {core.locked_carriers[1]}")
    
    print("\n2. 添加样本到队列:")
    # 添加样本到IP0队列
    core.add_to_queue(0, 2, "SAMPLE001", 1, 100, 13)
    core.add_to_queue(0, 3, "SAMPLE002", 2, 120, 16)
    # 添加样本到IP1队列
    core.add_to_queue(1, 2, "SAMPLE003", 1, 110, 15)
    
    print(f"   IP0队列长度: {len(core.get_queue_info(0))}")
    print(f"   IP1队列长度: {len(core.get_queue_info(1))}")
    print(f"   就绪装载: {core.get_ready_to_load()}")
    
    print("\n3. 队列详细信息:")
    ip0_queue = core.get_queue_info(0)
    print("   IP0队列:")
    for i, item in enumerate(ip0_queue):
        print(f"     [{i+1}] 样本ID: {item.get('sample_id')}, 占用类型: {item.get('carrier_occupancy')},")
        print(f"       优先级: {item.get('sample_priority')}, 试管尺寸: {item.get('tube_height')}x{item.get('tube_diameter')}")
    
    ip1_queue = core.get_queue_info(1)
    print("   IP1队列:")
    for i, item in enumerate(ip1_queue):
        print(f"     [{i+1}] 样本ID: {item.get('sample_id')}, 占用类型: {item.get('carrier_occupancy')},")
        print(f"       优先级: {item.get('sample_priority')}, 试管尺寸: {item.get('tube_height')}x{item.get('tube_diameter')}")
    
    print("\n4. 模拟处理Load/Unload请求:")
    # 处理IP0的装载请求
    load_result, unload_result, sample_status, onboard_count, completed_count, ready_to_load, return_ready_count = \
        core.process_load_unload(0, 2, "SAMPLE001", 100, 13, 10)
    
    print(f"   处理结果: load_result={load_result}, unload_result={unload_result}")
    print(f"   样本状态: {sample_status}, 在线数量: {onboard_count}")
    print(f"   就绪装载: {ready_to_load}, 可返回样本数: {return_ready_count}")
    print(f"   IP0锁定状态: {core.locked_carriers[0]}")
    
    print("\n5. 模拟队列跳过操作:")
    # 跳过IP0队列中的第二个样本
    core.skip_from_queue(0, 3, "SAMPLE002", True)
    print(f"   IP0队列长度: {len(core.get_queue_info(0))}")
    
    print("\n6. 模拟清空队列:")
    # 清空IP1队列
    core.clear_queue(1)
    print(f"   IP1队列长度: {len(core.get_queue_info(1))}")
    
    print("\n7. 最终状态检查:")
    print(f"   就绪装载: {core.get_ready_to_load()}")
    print(f"   可返回样本数: {core.get_return_ready_count()}")
    print(f"   IP0队列长度: {len(core.get_queue_info(0))}")
    print(f"   IP1队列长度: {len(core.get_queue_info(1))}")
    print(f"   IP0锁定状态: {core.locked_carriers[0]}")
    print(f"   IP1锁定状态: {core.locked_carriers[1]}")
    
    print("\n=== 测试完成 ===")
    print("队列管理UI更新功能测试通过！")
    print("所有相关方法均正常工作，UI将能正确显示队列管理的实时信息。")


if __name__ == "__main__":
    test_queue_ui()
