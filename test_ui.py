#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to run UI independently
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ConfigManager
from logger import Logger
from core import AtellicaCore
from las import LASServer
from lis import LISClient
from ui import AtellicaUI

# Simple test script to run UI
if __name__ == "__main__":
    try:
        print("Initializing ConfigManager...")
        config_manager = ConfigManager("config.json")
        
        print("Initializing Logger...")
        logger = Logger(config_manager)
        
        print("Initializing AtellicaCore...")
        core = AtellicaCore(config_manager, logger)
        
        print("Initializing LASServer...")
        las_server = LASServer(config_manager, logger, core)
        
        print("Initializing LISClient...")
        lis_client = LISClient(config_manager, logger, core)
        
        core.set_lis_client(lis_client)
        
        print("Initializing UI...")
        ui = AtellicaUI(config_manager, logger, core, las_server, lis_client)
        las_server.set_ui(ui)
        
        print("Running UI mainloop...")
        ui.run()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
