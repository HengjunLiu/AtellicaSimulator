#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AtellicaSimulator - 西门子医疗检验设备模拟器
主程序入口
"""

import sys
import time
import argparse
from core import AtellicaCore
from las import LASServer
from lis import LISServer
from ui import AtellicaUI
from config import ConfigManager
from logger import Logger


def main():
    """主程序入口"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Atellica Solution Simulator')
    parser.add_argument('--no-ui', action='store_true', help='Run without UI (headless mode)')
    parser.add_argument('--config', type=str, default='config.json', help='Configuration file path')
    args = parser.parse_args()
    
    try:
        # 初始化配置管理器
        print("Initializing ConfigManager...")
        config_manager = ConfigManager(args.config)
        print("ConfigManager initialized successfully")
        
        # 初始化日志管理器
        print("Initializing Logger...")
        logger = Logger(config_manager)
        logger.info("AtellicaSimulator starting...")
        
        # 初始化核心模拟逻辑
        logger.info("Initializing AtellicaCore...")
        core = AtellicaCore(config_manager, logger)
        logger.info("AtellicaCore initialized successfully")
        
        # 初始化LAS服务器
        logger.info("Initializing LASServer...")
        las_server = LASServer(config_manager, logger, core)
        logger.info("LASServer initialized successfully")
        
        # 初始化LIS服务器
        logger.info("Initializing LISServer...")
        lis_server = LISServer(config_manager, logger, core)
        logger.info("LISServer initialized successfully")
        
        if args.no_ui:
            # 无UI模式
            logger.info("Running in headless mode")
            try:
                logger.info("Starting LASServer...")
                las_server.start()
                logger.info("LASServer started successfully")
                
                logger.info("Starting LISServer...")
                lis_server.start()
                logger.info("LISServer started successfully")
                
                logger.info("AtellicaSimulator is running in headless mode. Press Ctrl+C to exit.")
                # 进入主循环
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                las_server.stop()
                lis_server.stop()
                logger.info("AtellicaSimulator stopped successfully")
        else:
            # 有UI模式
            logger.info("Running with UI")
            ui = AtellicaUI(config_manager, logger, core, las_server, lis_server)
            ui.run()
    except Exception as e:
        if logger:
            logger.error(f"Error in main: {str(e)}", exc_info=True)
        else:
            print(f"Error in main: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
