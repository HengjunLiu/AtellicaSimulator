#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析通讯日志中的握手消息
"""

import re


def analyze_handshake_messages():
    """分析通讯日志中的握手消息"""
    log_file = "d:\ATS_SIM\AtellicaSimulator\test_log\ANALYZER_uRAPLogFile_20210705_14.log"
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        # 查找所有包含HANDSHAKE的行
        handshake_lines = re.findall(r'.*HANDSHAKE.*', log_content)
        
        print(f"找到 {len(handshake_lines)} 行包含HANDSHAKE的日志")
        
        if handshake_lines:
            print("\n前10行HANDSHAKE日志：")
            for i, line in enumerate(handshake_lines[:10]):
                print(f"{i+1}. {line}")
        
        # 查找所有消息类型为0x0001的行（握手消息）
        handshake_message_lines = re.findall(r'.*Message Type.*0x0001.*', log_content)
        print(f"\n找到 {len(handshake_message_lines)} 行消息类型为0x0001的日志")
        
        if handshake_message_lines:
            print("\n前10行消息类型为0x0001的日志：")
            for i, line in enumerate(handshake_message_lines[:10]):
                print(f"{i+1}. {line}")
        
        # 查找所有包含0x0001的行
        msg_type_0001_lines = re.findall(r'.*0x0001.*', log_content)
        print(f"\n找到 {len(msg_type_0001_lines)} 行包含0x0001的日志")
        
        if msg_type_0001_lines:
            print("\n前5行包含0x0001的日志：")
            for i, line in enumerate(msg_type_0001_lines[:5]):
                print(f"{i+1}. {line}")
        
        # 查找所有ACK消息
        ack_lines = re.findall(r'.*ACK.*', log_content)
        print(f"\n找到 {len(ack_lines)} 行包含ACK的日志")
        
        if ack_lines:
            print("\n前5行ACK日志：")
            for i, line in enumerate(ack_lines[:5]):
                print(f"{i+1}. {line}")
                
    except Exception as e:
        print(f"分析日志时发生错误: {str(e)}")


if __name__ == "__main__":
    analyze_handshake_messages()
