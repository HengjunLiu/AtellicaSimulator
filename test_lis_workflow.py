#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：模拟LAS发送LOAD请求，测试LIS工作流
"""

import socket
import time
import sys

def send_load_request():
    """模拟LAS发送LOAD请求"""
    try:
        # 连接到LAS服务器
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 10011))
        
        print("Connected to LAS server")
        
        # 构造LOAD请求消息
        # 格式：LOAD|IP0|sample_id|tube_height|tube_diameter|elapsed_time
        sample_id = "TEST-" + str(int(time.time()))
        load_message = f"LOAD|IP0|{sample_id}|100|15|0\n"
        
        print(f"Sending LOAD request: {load_message.strip()}")
        sock.sendall(load_message.encode('utf-8'))
        
        # 接收响应
        response = sock.recv(1024).decode('utf-8')
        print(f"Received response: {response.strip()}")
        
        sock.close()
        print(f"Load test completed for sample {sample_id}")
        return sample_id
    except Exception as e:
        print(f"Error sending LOAD request: {str(e)}")
        return None

def main():
    """主函数"""
    print("Testing LIS workflow...")
    
    # 发送多个LOAD请求
    for i in range(3):
        print(f"\n--- Sending LOAD request {i+1} ---")
        sample_id = send_load_request()
        if sample_id:
            print(f"Sample {sample_id} sent for processing")
        
        # 等待3秒再发送下一个请求
        time.sleep(3)
    
    print("\n--- All LOAD requests sent ---")
    print("The simulator will process the samples according to the workflow:")
    print("1. 5 seconds wait after LOAD")
    print("2. LIS query and test validation")
    print("3. 5 minutes wait for valid test results generation")
    print("4. 2 minutes wait for UNLOAD preparation")
    print("Check the logs for detailed processing information.")

if __name__ == "__main__":
    main()