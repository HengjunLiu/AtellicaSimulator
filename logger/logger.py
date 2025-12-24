#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logger模块 - 提供日志记录功能
"""

import logging
import os
from logging.handlers import RotatingFileHandler


class Logger:
    """日志管理器"""
    
    def __init__(self, config_manager):
        """初始化日志管理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.config = config_manager.get_logger_config()
        
        # 创建日志目录
        log_dir = self.config.get('log_dir', 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 初始化主日志记录器
        self.logger = logging.getLogger('AtellicaSimulator')
        self.logger.setLevel(getattr(logging, self.config.get('level', 'INFO')))
        
        # 清除已存在的处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 初始化格式器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 添加控制台处理器
        if self.config.get('console_output', True):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # 添加文件处理器
        if self.config.get('file_output', True):
            main_log_file = os.path.join(log_dir, 'atellica_simulator.log')
            file_handler = RotatingFileHandler(
                main_log_file,
                maxBytes=self.config.get('max_bytes', 10*1024*1024),  # 10MB
                backupCount=self.config.get('backup_count', 5)
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # 初始化LAS通信日志记录器
        self.las_logger = logging.getLogger('LASCommunication')
        self.las_logger.setLevel(getattr(logging, self.config.get('level', 'INFO')))
        
        # 清除已存在的处理器
        for handler in self.las_logger.handlers[:]:
            self.las_logger.removeHandler(handler)
        
        # 添加LAS日志文件处理器
        las_log_file = os.path.join(log_dir, 'las_communication.log')
        las_file_handler = RotatingFileHandler(
            las_log_file,
            maxBytes=self.config.get('max_bytes', 10*1024*1024),
            backupCount=self.config.get('backup_count', 5)
        )
        las_file_handler.setFormatter(formatter)
        self.las_logger.addHandler(las_file_handler)
        
        # 初始化LIS通信日志记录器
        self.lis_logger = logging.getLogger('LISCommunication')
        self.lis_logger.setLevel(getattr(logging, self.config.get('level', 'INFO')))
        
        # 清除已存在的处理器
        for handler in self.lis_logger.handlers[:]:
            self.lis_logger.removeHandler(handler)
        
        # 添加LIS日志文件处理器
        lis_log_file = os.path.join(log_dir, 'lis_communication.log')
        lis_file_handler = RotatingFileHandler(
            lis_log_file,
            maxBytes=self.config.get('max_bytes', 10*1024*1024),
            backupCount=self.config.get('backup_count', 5)
        )
        lis_file_handler.setFormatter(formatter)
        self.lis_logger.addHandler(lis_file_handler)
    
    def debug(self, message):
        """记录调试信息
        
        Args:
            message: 日志消息
        """
        self.logger.debug(message)
    
    def info(self, message):
        """记录普通信息
        
        Args:
            message: 日志消息
        """
        self.logger.info(message)
    
    def warning(self, message):
        """记录警告信息
        
        Args:
            message: 日志消息
        """
        self.logger.warning(message)
    
    def error(self, message):
        """记录错误信息
        
        Args:
            message: 日志消息
        """
        self.logger.error(message)
    
    def critical(self, message):
        """记录严重错误信息
        
        Args:
            message: 日志消息
        """
        self.logger.critical(message)
    
    def log_las(self, message, level='INFO'):
        """记录LAS通信日志
        
        Args:
            message: 日志消息
            level: 日志级别
        """
        log_method = getattr(self.las_logger, level.lower())
        log_method(message)
    
    def log_lis(self, message, level='INFO'):
        """记录LIS通信日志
        
        Args:
            message: 日志消息
            level: 日志级别
        """
        log_method = getattr(self.lis_logger, level.lower())
        log_method(message)
    
    def get_las_log_content(self, lines=100):
        """获取LAS日志内容
        
        Args:
            lines: 获取的行数
            
        Returns:
            str: LAS日志内容
        """
        log_dir = self.config.get('log_dir', 'logs')
        las_log_file = os.path.join(log_dir, 'las_communication.log')
        return self._get_log_content(las_log_file, lines)
    
    def get_lis_log_content(self, lines=100):
        """获取LIS日志内容
        
        Args:
            lines: 获取的行数
            
        Returns:
            str: LIS日志内容
        """
        log_dir = self.config.get('log_dir', 'logs')
        lis_log_file = os.path.join(log_dir, 'lis_communication.log')
        return self._get_log_content(lis_log_file, lines)
    
    def _get_log_content(self, log_file, lines=100):
        """获取日志文件内容
        
        Args:
            log_file: 日志文件路径
            lines: 获取的行数
            
        Returns:
            str: 日志内容
        """
        if not os.path.exists(log_file):
            return "Log file not found"
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.readlines()
            
            # 获取最后N行
            if len(content) > lines:
                content = content[-lines:]
            
            return ''.join(content)
        except Exception as e:
            return f"Error reading log file: {str(e)}"
