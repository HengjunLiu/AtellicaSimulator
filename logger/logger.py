#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logger模块 - 提供日志记录功能
"""

import logging
import os
import datetime
import time
import threading
import queue
import glob
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler


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
        
        # 日志回调函数，用于UI实时显示
        self.las_log_callback = None
        self.lis_log_callback = None
        
        # 异步日志队列和线程
        self.log_queue = queue.Queue(maxsize=10000)  # 日志队列，最大10000条
        self.log_thread = None
        self.log_thread_running = False
        self._start_log_thread()  # 启动异步日志线程
        
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
        
        # 自定义日志轮换命名器类
        class CustomNamer:
            def __call__(self, filename):
                """
                自定义日志文件名格式：
                - 当前日志：atellica_simulator.log
                - 轮换日志：atellica_simulator-2025-12-26.log
                """
                import os
                base_name = os.path.basename(filename)
                dir_name = os.path.dirname(filename)
                
                # 处理格式：atellica_simulator.log.2025-12-26
                if base_name.count('.') >= 2:
                    # 提取基本名称和日期部分
                    parts = base_name.split('.')
                    name = parts[0]
                    date_part = parts[-1]
                    # 构建新名称：name-date_part.log
                    return os.path.join(dir_name, f"{name}-{date_part}.log")
                return filename
        
        # 创建自定义命名器实例
        custom_namer = CustomNamer()
        
        # 添加文件处理器
        if self.config.get('file_output', True):
            # 主日志文件处理器 - 统一命名：atellica-simulator.log
            main_log_file = os.path.join(log_dir, 'atellica-simulator.log')
            file_handler = TimedRotatingFileHandler(
                main_log_file,
                when='midnight',  # 每天午夜轮换
                interval=1,        # 轮换间隔1天
                backupCount=self.config.get('backup_count', 7),  # 保留7天日志
                encoding='utf-8'
            )
            file_handler.suffix = '.%Y-%m-%d'  # 默认生成格式：atellica_simulator.log.2025-12-26
            file_handler.namer = custom_namer  # 应用自定义命名器
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # 初始化LAS通信日志记录器
        self.las_logger = logging.getLogger('LASCommunication')
        self.las_logger.setLevel(getattr(logging, self.config.get('level', 'INFO')))
        
        # 清除已存在的处理器
        for handler in self.las_logger.handlers[:]:
            self.las_logger.removeHandler(handler)
        
        # 添加LAS日志文件处理器 - 统一命名：las-communication.log
        las_log_file = os.path.join(log_dir, 'las-communication.log')
        las_file_handler = TimedRotatingFileHandler(
            las_log_file,
            when='midnight',
            interval=1,
            backupCount=self.config.get('backup_count', 7),
            encoding='utf-8'
        )
        las_file_handler.suffix = '.%Y-%m-%d'
        las_file_handler.namer = custom_namer
        las_file_handler.setFormatter(formatter)
        self.las_logger.addHandler(las_file_handler)
        
        # 初始化LIS通信日志记录器
        self.lis_logger = logging.getLogger('LISCommunication')
        self.lis_logger.setLevel(getattr(logging, self.config.get('level', 'INFO')))
        
        # 清除已存在的处理器
        for handler in self.lis_logger.handlers[:]:
            self.lis_logger.removeHandler(handler)
        
        # 添加LIS日志文件处理器 - 统一命名：lis-communication.log
        lis_log_file = os.path.join(log_dir, 'lis-communication.log')
        lis_file_handler = TimedRotatingFileHandler(
            lis_log_file,
            when='midnight',
            interval=1,
            backupCount=self.config.get('backup_count', 7),
            encoding='utf-8'
        )
        lis_file_handler.suffix = '.%Y-%m-%d'
        lis_file_handler.namer = custom_namer
        lis_file_handler.setFormatter(formatter)
        self.lis_logger.addHandler(lis_file_handler)
        
        # 初始化LAS原始数据日志记录器
        self.las_raw_logger = logging.getLogger('LASRawData')
        self.las_raw_logger.setLevel(logging.INFO)
        
        # 清除已存在的处理器
        for handler in self.las_raw_logger.handlers[:]:
            self.las_raw_logger.removeHandler(handler)
        
        # 添加LAS原始数据日志文件处理器
        # 按日轮转，单个文件最大100MB，保留30天
        las_raw_log_file = os.path.join(log_dir, 'las-rawdata')
        # 使用RotatingFileHandler配合TimedRotatingFileHandler的逻辑
        # 自定义Formatter，支持毫秒
        class MillisecondFormatter(logging.Formatter):
            def formatTime(self, record, datefmt=None):
                """自定义时间格式，支持毫秒"""
                if datefmt:
                    # 直接构建完整的时间字符串
                    dt = datetime.datetime.fromtimestamp(record.created)
                    milliseconds = f'{dt.microsecond // 1000:03d}'
                    # 使用strftime处理基本部分，手动添加毫秒
                    return dt.strftime(datefmt.split('.%3f')[0]) + f'.{milliseconds}'
                else:
                    # 使用默认格式
                    t = time.strftime(self.default_time_format, self.converter(record.created))
                    return self.default_msec_format % (t, record.msecs)
        
        # 使用简单的格式器，只输出消息内容，因为我们已经在log_las_raw中构建了完整的日志格式
        las_raw_formatter = logging.Formatter('%(message)s')
        
        # 每日创建新文件，使用自定义文件名格式
        class LASRawFileHandler(TimedRotatingFileHandler):
            def __init__(self, base_filename, when='midnight', interval=1, backupCount=30, encoding='utf-8'):
                self.base_filename = base_filename
                current_date = datetime.datetime.now().strftime('%Y%m%d')
                self.current_filename = f"{base_filename}{current_date}.log"
                super().__init__(
                    self.current_filename,
                    when=when,
                    interval=interval,
                    backupCount=backupCount,
                    encoding=encoding
                )
            
            def doRollover(self):
                """执行日志轮换"""
                if self.stream:
                    self.stream.close()
                    self.stream = None
                
                # 获取当前日期
                current_date = datetime.datetime.now().strftime('%Y%m%d')
                self.current_filename = f"{self.base_filename}{current_date}.log"
                
                # 设置新的文件名
                self.baseFilename = self.current_filename
                
                # 打开新文件
                self.stream = self._open()
                
                # 处理备份文件
                self.backupCount = self.config.get('las_raw_backup_count', 30)
                if self.backupCount > 0:
                    self._removeOldFiles()
        
        # 创建LAS原始数据日志处理器
        # 使用自定义的按日和按大小双重限制处理器
        class DualRotatingFileHandler(RotatingFileHandler):
            def __init__(self, base_filename, when='midnight', interval=1, 
                       backupCount=30, maxBytes=100*1024*1024, encoding='utf-8'):
                self.base_filename = base_filename
                self.when = when
                self.interval = interval
                self.backupCount = backupCount
                
                # 获取当前日期的文件名
                current_date = datetime.datetime.now().strftime('%Y%m%d')
                self.current_filename = f"{base_filename}{current_date}.log"
                
                super().__init__(
                    self.current_filename,
                    maxBytes=maxBytes,
                    backupCount=1,  # 每个日期只保留一个备份
                    encoding=encoding
                )
                
                # 设置日期轮转时间
                self.rolloverAt = self.computeRollover(time.time())
            
            def computeRollover(self, currentTime):
                """计算下一次轮转时间"""
                # 按日轮转计算
                now = datetime.datetime.fromtimestamp(currentTime)
                tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
                return tomorrow.timestamp()
            
            def shouldRollover(self, record):
                """检查是否需要轮转"""
                # 检查大小是否超过限制
                if super().shouldRollover(record):
                    return True
                
                # 检查是否需要按日轮转
                currentTime = time.time()
                return currentTime >= self.rolloverAt
            
            def doRollover(self):
                """执行日志轮转"""
                # 关闭当前文件
                if self.stream:
                    self.stream.close()
                    self.stream = None
                
                # 按大小轮转（RotatingFileHandler的默认行为）
                super().doRollover()
                
                # 检查是否需要按日轮转
                currentTime = time.time()
                if currentTime >= self.rolloverAt:
                    # 获取新的日期文件名
                    current_date = datetime.datetime.now().strftime('%Y%m%d')
                    self.current_filename = f"{self.base_filename}{current_date}.log"
                    self.baseFilename = self.current_filename
                    
                    # 重新打开新文件
                    self.stream = self._open()
                    
                    # 计算下一次轮转时间
                    self.rolloverAt = self.computeRollover(currentTime)
                    
                    # 清理旧文件
                    if self.backupCount > 0:
                        self._removeOldFiles()
            
            def _removeOldFiles(self):
                """移除旧日志文件"""
                import os
                import glob
                
                # 获取所有日志文件
                log_files = glob.glob(f"{self.base_filename}*.log")
                log_files.sort()
                
                # 如果文件数量超过备份数量，删除最旧的
                while len(log_files) > self.backupCount:
                    os.remove(log_files.pop(0))
        
        # 创建双重轮转日志处理器
        las_raw_file_handler = DualRotatingFileHandler(
            las_raw_log_file,
            when='midnight',
            interval=1,
            backupCount=30,
            maxBytes=100 * 1024 * 1024,  # 100MB
            encoding='utf-8'
        )
        las_raw_file_handler.setFormatter(las_raw_formatter)
        
        # 只添加一个处理器，避免日志重复
        self.las_raw_logger.addHandler(las_raw_file_handler)
    
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
    
    def set_las_log_callback(self, callback):
        """设置LAS日志回调函数
        
        Args:
            callback: 回调函数，接收日志消息和级别
        """
        self.las_log_callback = callback
    
    def set_lis_log_callback(self, callback):
        """设置LIS日志回调函数
        
        Args:
            callback: 回调函数，接收日志消息和级别
        """
        self.lis_log_callback = callback
    
    def log_las(self, message, level='INFO'):
        """记录LAS通信日志
        
        Args:
            message: 日志消息
            level: 日志级别
        """
        log_method = getattr(self.las_logger, level.lower())
        log_method(message)
        
        # 调用回调函数
        if self.las_log_callback and callable(self.las_log_callback):
            try:
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.las_log_callback(f"{timestamp} - LASCommunication - {level} - {message}")
            except Exception as e:
                self.logger.error(f"Error calling LAS log callback: {str(e)}")
    
    def log_lis(self, message, level='INFO'):
        """记录LIS通信日志
        
        Args:
            message: 日志消息
            level: 日志级别
        """
        log_method = getattr(self.lis_logger, level.lower())
        log_method(message)
        
        # 调用回调函数
        if self.lis_log_callback and callable(self.lis_log_callback):
            try:
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.lis_log_callback(f"{timestamp} - LISCommunication - {level} - {message}")
            except Exception as e:
                self.logger.error(f"Error calling LIS log callback: {str(e)}")
    
    def get_las_log_content(self, lines=100):
        """获取LAS日志内容
        
        Args:
            lines: 获取的行数
            
        Returns:
            str: LAS日志内容
        """# 获取LAS日志内容 - 使用新的统一命名
        log_dir = self.config.get('log_dir', 'logs')
        las_log_file = os.path.join(log_dir, 'las-communication.log')
        return self._get_log_content(las_log_file, lines)
    
    def get_lis_log_content(self, lines=100):
        """获取LIS日志内容
        
        Args:
            lines: 获取的行数
            
        Returns:
            str: LIS日志内容
        """# 获取LIS日志内容 - 使用新的统一命名
        log_dir = self.config.get('log_dir', 'logs')
        lis_log_file = os.path.join(log_dir, 'lis-communication.log')
        return self._get_log_content(lis_log_file, lines)
    
    def _start_log_thread(self):
        """启动异步日志线程"""
        if not self.log_thread_running:
            self.log_thread_running = True
            self.log_thread = threading.Thread(target=self._log_worker, daemon=True)
            self.log_thread.start()
    
    def _log_worker(self):
        """异步日志处理工作线程"""
        while self.log_thread_running:
            try:
                # 从队列中获取日志记录
                log_data = self.log_queue.get(block=True, timeout=1)
                if log_data is None:
                    break
                
                # 处理日志记录
                logger_name, message = log_data
                if logger_name == 'las_raw':
                    self.las_raw_logger.info(message)
                elif logger_name == 'las':
                    self.log_las(message)
                elif logger_name == 'lis':
                    self.log_lis(message)
                
                # 标记任务完成
                self.log_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in log worker: {str(e)}")
                continue
    
    def _async_log(self, logger_name, message):
        """异步记录日志
        
        Args:
            logger_name: 日志记录器名称
            message: 日志消息
        """
        try:
            self.log_queue.put((logger_name, message), block=False)
        except queue.Full:
            # 队列满时，尝试同步写入
            if logger_name == 'las_raw':
                self.las_raw_logger.info(message)
            elif logger_name == 'las':
                self.log_las(message)
            elif logger_name == 'lis':
                self.log_lis(message)
    
    def log_las_raw(self, message_type, data, extra_info=None):
        """记录LAS原始数据日志
        
        Args:
            message_type: 消息类型，'RECEIVED'或'SENT'
            data: 原始数据内容
            extra_info: 额外信息字典，包含解析后的信息或封装前的原始信息
        """
        import struct
        
        # 消息类型映射字典，包含所有指定的消息类型及其描述
        MESSAGE_TYPE_MAP = {
            0x0000: "ACK/NAK",
            0x0001: "Handshake message",
            0x0005: "Keep alive message",
            0x0201: "Instrument Health Request message",
            0x0202: "Instrument Health Response message",
            0x0203: "Test inventory request message",
            0x0204: "Reagent inventory response message",
            0x0207: "Onboard sample info request message",
            0x0208: "Onboard sample info response message",
            0x0209: "Transfer status request message",
            0x020A: "Transfer status response message",
            0x020B: "Consumable Inventory Request Message",
            0x020C: "Consumable Inventory response Message",
            0x020D: "Initialization Completed Message",
            0x0303: "Load_Unload Command request message",
            0x0304: "Load_Unload Command response message",
            0x0401: "Add queue request message",
            0x0402: "Add queue command response message",
            0x0403: "Skip queue command request message",
            0x0404: "Skip queue command response message",
            0x0405: "Clear queue request message",
            0x0406: "Clear queue response message"
        }
        
        # 将消息类型从完整的'SENT'/'RECEIVED'改为'S'/'R'
        msg_type_short = 'S' if message_type.upper() == 'SENT' else 'R'
        
        # 解析消息，提取消息类型和其他重要信息
        try:
            # 将十六进制字符串转换为二进制数据
            binary_data = bytes.fromhex(data)
            
            # 检查消息长度是否足够
            if len(binary_data) < 18:  # 最小消息长度
                message_desc = "Invalid message format - too short"
            else:
                # 解析消息头，提取消息类型
                message_type_hex = struct.unpack_from('!H', binary_data, 7)[0]
                message_type_str = f"0x{message_type_hex:04X}"
                
                # 获取消息类型描述
                message_description = MESSAGE_TYPE_MAP.get(message_type_hex, "Unknown message type")
                
                # 提取interface_position_index（如果需要）
                interface_position_index = None
                # 检查是否为需要提取IP索引的消息类型
                ip_required_msg_types = [
                    0x0209,  # Transfer Status Request
                    0x020A,  # Transfer Status Response
                    0x0303,  # Load/Unload Request
                    0x0304,  # Load/Unload Response
                    0x0401,  # Add Queue Request
                    0x0402,  # Add Queue Response
                    0x0403,  # Skip Queue Request
                    0x0404,  # Skip Queue Response
                    0x0405,  # Clear Queue Request
                    0x0406   # Clear Queue Response
                ]
                
                if message_type_hex in ip_required_msg_types:
                    # 消息体从第18字节开始
                    message_body = binary_data[18:]
                    if message_body:
                        # interface_position_index是消息体的第一个字节
                        interface_position_index = message_body[0]
                    else:
                        # 如果没有消息体，默认IP0
                        interface_position_index = 0
                
                # 根据消息类型构建描述，包含十六进制值、描述和IP索引（如果需要）
                if interface_position_index is not None:
                    message_desc = f"[{message_type_str}-{message_description}-IP{interface_position_index}]"
                else:
                    message_desc = f"[{message_type_str}-{message_description}]"
        except Exception as e:
            # 如果解析失败，使用基本描述
            message_desc = "[Invalid message format]"
        
        # 直接构建完整的日志消息，包括时间戳格式
        import datetime
        now = datetime.datetime.now()
        timestamp = now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # 精确到毫秒
        
        # 将连续的十六进制原始数据转换为带空格分隔的字节格式
        formatted_data = ' '.join(data[i:i+2] for i in range(0, len(data), 2))
        
        # 构建符合LOG.txt格式的日志消息：[S/R]:时间戳\t[消息类型-描述]\t格式化数据
        # 格式化额外信息（如果提供）
        formatted_extra_info = ""
        if extra_info is not None and isinstance(extra_info, dict):
            try:
                # 构建额外信息字符串，格式：[key1=value1, key2=value2, ...]
                extra_info_parts = []
                for key, value in extra_info.items():
                    # 安全格式化值，处理不同数据类型
                    if isinstance(value, (list, dict)):
                        # 对于复杂类型，使用简单字符串表示
                        value_str = f"{type(value).__name__}({len(value)})"
                    else:
                        # 对于基本类型，直接转换为字符串
                        value_str = str(value)
                    extra_info_parts.append(f"{key}={value_str}")
                
                if extra_info_parts:
                    formatted_extra_info = f"[{', '.join(extra_info_parts)}]"
            except Exception as e:
                # 如果格式化失败，记录错误但不影响日志记录
                self.logger.error(f"Error formatting extra_info: {str(e)}")
        
        # 构建符合LOG.txt格式的日志消息：[S/R]:时间戳	[消息类型-描述]	[额外信息]	格式化数据
        if formatted_extra_info:
            log_message = f"[{msg_type_short}]:{timestamp}\t{message_desc}\t{formatted_extra_info}\t{formatted_data}"
        else:
            log_message = f"[{msg_type_short}]:{timestamp}\t{message_desc}\t{formatted_data}"
        
        # 异步记录日志
        self._async_log('las_raw', log_message)
    
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
