#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Config模块 - 处理参数配置和持久化
"""

import json
import os


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file='config.json'):
        """初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self):
        """加载配置文件
        
        Returns:
            dict: 配置字典
        """
        # 默认配置
        default_config = {
            'logger': {
                'level': 'INFO',
                'console_output': True,
                'file_output': True,
                'log_dir': 'logs',
                'max_bytes': 10*1024*1024,  # 10MB
                'backup_count': 5
            },
            'las': {
                'host': '0.0.0.0',
                'port': 10001,
                'protocol_version': '0x0330',
                'instrument_type': '0x0001',
                'capability_version': '0x0104',
                'software_version': '0x0100',
                'instrument_id': '0xFF',
                'instrument_serial': 'ATELLICA',
                'keep_alive_interval': 30,  # 秒
                'ack_timeout': 20,  # 秒
                'response_timeout': 20  # 秒
            },
            'lis': {
                'host': '0.0.0.0',
                'port': 10002,
                'result_delay': 1800,  # 30分钟，单位秒
                'max_connections': 10
            },
            'core': {
                'automation_interface_status': 1,  # 1: Green, 3: Red
                'instrument_process_status': 1,  # 1: Green, 2: Yellow, 3: Red
                'lis_connection_status': 1,  # 1: Connected, 2: Disconnected
                'interface_positions': 2,
                'remote_control_status': [4, 5],  # IP0: Loading Only, IP1: Unloading Only
                'lock_ownership': [2, 2],  # 2: Not Locked by Instrument
                'processing_backlog': 0,
                'sample_acquisition_delay': 0,
                'on_board_tube_count': 0,
                'completed_tube_count': 0
            },
            'test_inventory': {
                'threshold': 10,
                'tests': [
                    {'name': 'TEST001', 'count': 100, 'status': 1},  # 1: Green, 2: Yellow, 3: Red
                    {'name': 'TEST002', 'count': 50, 'status': 1},
                    {'name': 'TEST003', 'count': 5, 'status': 2},
                    {'name': 'TEST004', 'count': 0, 'status': 3}
                ]
            },
            'consumable_inventory': {
                'modules': [
                    {
                        'id': 'MODULE001',
                        'consumables': [
                            {'id': 1, 'status': 1},  # CH Cleaner
                            {'id': 2, 'status': 1},  # CH Conditioner
                            {'id': 3, 'status': 1},  # CH Wash
                            {'id': 4, 'status': 1},  # CH Diluent
                            {'id': 5, 'status': 2},  # Pretreatment
                            {'id': 25, 'status': 1},  # Tips
                            {'id': 26, 'status': 1},  # Cuvettes
                            {'id': 27, 'status': 1}   # Water
                        ]
                    }
                ]
            }
        }
        
        # 如果配置文件存在，加载配置
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # 合并配置，使用默认配置填充缺失的字段
                self._merge_config(default_config, loaded_config)
                return default_config
            except Exception as e:
                print(f"Error loading config file: {str(e)}. Using default config.")
                return default_config
        else:
            # 保存默认配置
            self._save_config(default_config)
            return default_config
    
    def _merge_config(self, default, loaded):
        """合并配置，使用默认配置填充缺失的字段
        
        Args:
            default: 默认配置
            loaded: 从文件加载的配置
        """
        for key, value in loaded.items():
            if key in default:
                if isinstance(value, dict) and isinstance(default[key], dict):
                    self._merge_config(default[key], value)
                elif isinstance(value, list) and isinstance(default[key], list):
                    # 对于列表，直接替换
                    default[key] = value
                else:
                    default[key] = value
    
    def _save_config(self, config):
        """保存配置到文件
        
        Args:
            config: 配置字典
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config file: {str(e)}")
    
    def save(self):
        """保存当前配置到文件"""
        self._save_config(self.config)
    
    def get(self, key, default=None):
        """获取配置值
        
        Args:
            key: 配置键，支持点分隔符，如 'las.host'
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key, value):
        """设置配置值
        
        Args:
            key: 配置键，支持点分隔符，如 'las.host'
            value: 配置值
        """
        keys = key.split('.')
        config = self.config
        
        # 遍历到最后一个键的父节点
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置值
        config[keys[-1]] = value
        
        # 保存配置
        self.save()
    
    def get_logger_config(self):
        """获取日志配置
        
        Returns:
            dict: 日志配置
        """
        return self.config.get('logger', {})
    
    def get_las_config(self):
        """获取LAS配置
        
        Returns:
            dict: LAS配置
        """
        return self.config.get('las', {})
    
    def get_lis_config(self):
        """获取LIS配置
        
        Returns:
            dict: LIS配置
        """
        return self.config.get('lis', {})
    
    def get_core_config(self):
        """获取核心配置
        
        Returns:
            dict: 核心配置
        """
        return self.config.get('core', {})
    
    def get_test_inventory_config(self):
        """获取测试项目配置
        
        Returns:
            dict: 测试项目配置
        """
        return self.config.get('test_inventory', {})
    
    def get_consumable_inventory_config(self):
        """获取耗材配置
        
        Returns:
            dict: 耗材配置
        """
        return self.config.get('consumable_inventory', {})
