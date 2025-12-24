#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AtellicaSimulator 测试脚本
"""

import time
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core import AtellicaCore
from config import ConfigManager
from logger import Logger


def test_core_functionality():
    """测试核心功能"""
    print("=== 测试 AtellicaCore 功能 ===")
    
    # 初始化配置管理器
    config_manager = ConfigManager('config.json')
    
    # 初始化日志管理器
    logger = Logger(config_manager)
    logger.info("测试脚本启动...")
    
    # 初始化核心模拟逻辑
    core = AtellicaCore(config_manager, logger)
    
    # 测试1: 获取仪器健康状态
    print("\n1. 测试获取仪器健康状态:")
    health_status = core.get_instrument_health()
    print(f"   自动化接口状态: {'Green' if health_status['automation_interface_status'] == 1 else 'Red'}")
    print(f"   仪器处理状态: {'Green' if health_status['instrument_process_status'] == 1 else 'Yellow' if health_status['instrument_process_status'] == 2 else 'Red'}")
    print(f"   LIS连接状态: {'Connected' if health_status['lis_connection_status'] == 1 else 'Disconnected'}")
    print(f"   接口位置数量: {health_status['interface_positions']}")
    print(f"   在线试管数量: {health_status['on_board_tube_count']}")
    print(f"   已完成试管数量: {health_status['completed_tube_count']}")
    
    # 测试2: 获取测试库存
    print("\n2. 测试获取测试库存:")
    test_inventory = core.get_test_inventory()
    print(f"   测试项目数量: {len(test_inventory['tests'])}")
    for test in test_inventory['tests']:
        print(f"   - {test['name']}: 可用数量={test['count']}, 状态={'Green' if test['status'] == 1 else 'Yellow' if test['status'] == 2 else 'Red'}")
    
    # 测试3: 获取耗材库存
    print("\n3. 测试获取耗材库存:")
    consumable_inventory = core.get_consumable_inventory()
    print(f"   模块数量: {len(consumable_inventory['modules'])}")
    for module in consumable_inventory['modules']:
        print(f"   - 模块 {module['id']}: 耗材数量={len(module['consumables'])}")
    
    # 测试4: 接收样本
    print("\n4. 测试接收样本:")
    sample_id = f"TEST{int(time.time())}"
    tests = ['TEST001', 'TEST002', 'TEST003']
    patient_info = {
        'patient_id': 'PAT123',
        'last_name': 'Test',
        'first_name': 'Patient',
        'dob': '19900101',
        'gender': 'M'
    }
    
    success = core.receive_sample(sample_id, tests, patient_info)
    print(f"   接收样本 {sample_id}: {'成功' if success else '失败'}")
    
    if success:
        # 测试5: 获取样本信息
        print(f"\n5. 测试获取样本信息:")
        sample_info = core.get_sample_info(sample_id)
        if sample_info:
            print(f"   样本ID: {sample_info['sample_id']}")
            print(f"   测试项目: {sample_info['tests']}")
            print(f"   状态: {sample_info['status']}")
        
        # 测试6: 获取所有样本
        print(f"\n6. 测试获取所有样本:")
        all_samples = core.get_all_samples()
        print(f"   样本总数: {len(all_samples)}")
        for sid, sinfo in all_samples.items():
            print(f"   - {sid}: 状态={sinfo['status']}, 测试数={len(sinfo['tests'])}")
    
    # 测试7: 更新设备状态
    print(f"\n7. 测试更新设备状态:")
    print("   更新自动化接口状态为Red...")
    core.update_automation_interface_status(3)
    health_status = core.get_instrument_health()
    print(f"   新的自动化接口状态: {'Green' if health_status['automation_interface_status'] == 1 else 'Red'}")
    
    print(f"   更新仪器处理状态为Yellow...")
    core.update_instrument_process_status(2)
    health_status = core.get_instrument_health()
    print(f"   新的仪器处理状态: {'Green' if health_status['instrument_process_status'] == 1 else 'Yellow' if health_status['instrument_process_status'] == 2 else 'Red'}")
    
    # 测试8: 更新测试库存
    print(f"\n8. 测试更新测试库存:")
    print("   更新TEST001的可用数量为200...")
    core.update_test_inventory('TEST001', count=200)
    test_inventory = core.get_test_inventory()
    for test in test_inventory['tests']:
        if test['name'] == 'TEST001':
            print(f"   TEST001: 可用数量={test['count']}, 状态={'Green' if test['status'] == 1 else 'Yellow' if test['status'] == 2 else 'Red'}")
            break
    
    print("\n=== 所有测试完成 ===")
    logger.info("测试脚本完成")


if __name__ == "__main__":
    test_core_functionality()
