# Atellica Simulator 软件设计文档 (SDD)

**版本**: v1.6.7  
**日期**: 2026-02-11  
**作者**: Development Team  

---

## 目录

1. [引言](#1-引言)
2. [系统概述](#2-系统概述)
3. [系统架构](#3-系统架构)
4. [模块设计](#4-模块设计)
5. [接口定义](#5-接口定义)
6. [数据流设计](#6-数据流设计)
7. [协议实现](#7-协议实现)
8. [错误处理](#8-错误处理)
9. [附录](#9-附录)

---

## 1. 引言

### 1.1 文档目的

本文档描述 Atellica Simulator 软件的详细设计，包括系统架构、模块划分、接口定义、数据流和协议实现等内容。

### 1.2 适用范围

本文档适用于 Atellica Simulator v1.6.7 版本，用于指导开发、测试和维护工作。

### 1.3 参考资料

- Atellica Solution LAS Interface Guide, SW 1.23
- uRAP (Universal Remote Access Protocol) 规范
- ASTM E1381/E1394 协议规范

---

## 2. 系统概述

### 2.1 系统目标

Atellica Simulator 是一个模拟 Atellica Solution 实验室自动化系统的软件，用于：

- 模拟 LAS (Laboratory Automation System) 与 Atellica 仪器的通信
- 支持 uRAP 协议的消息交换
- 提供用户界面进行手动操作模拟
- 支持与 LIS (Laboratory Information System) 的 ASTM 协议通信

### 2.2 运行环境

- **操作系统**: Windows 10/11
- **Python版本**: Python 3.8+
- **依赖库**: 
  - tkinter (UI)
  - sqlite3 (数据库)
  - socket (网络通信)
  - threading (并发处理)

### 2.3 系统功能

| 功能模块 | 描述 |
|---------|------|
| LAS通信 | 处理uRAP协议消息，支持Handshake、Health Status、Load/Unload等 |
| LIS通信 | 处理ASTM协议，支持样本订单查询和结果发送 |
| 样本管理 | 管理样本生命周期（接收、处理、完成、卸载） |
| 队列管理 | 管理LAS样本队列（Add/Skip/Clear Queue） |
| UI界面 | 提供用户操作界面，显示系统状态和手动操作提示 |
| 日志记录 | 记录系统运行日志和LAS通信日志 |

---

## 3. 系统架构

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Atellica Simulator                    │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │   UI     │  │   LAS    │  │   LIS    │  │   Core   │    │
│  │  Module  │◄─┤  Module  │  │  Module  │◄─┤  Module  │    │
│  │          │  │          │  │          │  │          │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       │             │             │             │          │
│       └─────────────┴─────────────┴─────────────┘          │
│                     Config & Logger                         │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 模块关系图

```
                    ┌─────────────┐
                    │    main     │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
   ┌─────────┐       ┌─────────┐       ┌─────────┐
   │   UI    │◄─────►│  Core   │◄─────►│  LAS    │
   │  (tk)   │       │ (业务)  │       │ (uRAP)  │
   └─────────┘       └────┬────┘       └────┬────┘
                          │                  │
                          ▼                  ▼
                     ┌─────────┐       ┌─────────┐
                     │   LIS   │       │  网络   │
                     │ (ASTM)  │       │  Socket │
                     └─────────┘       └─────────┘
```

### 3.3 目录结构

```
AtellicaSimulator/
├── main.py                 # 程序入口
├── config/                 # 配置模块
│   ├── config.py          # 配置管理
│   └── config.json        # 配置文件
├── core/                   # 核心业务逻辑
│   └── core.py            # 样本管理、队列管理
├── las/                    # LAS通信模块
│   └── las.py             # uRAP协议实现
├── lis/                    # LIS通信模块
│   └── lis.py             # ASTM协议实现
├── ui/                     # 用户界面
│   ├── ui.py              # 主UI
│   └── lisui.py           # LIS UI
├── logger/                 # 日志模块
│   └── logger.py          # 日志记录
├── tests/                  # 测试用例
│   └── test_*.py          # 各类测试
└── docs/                   # 文档
    ├── SDD_Software_Design_Document.md  # 本文档
    └── ...
```

---

## 4. 模块设计

### 4.1 Core模块 (core/core.py)

#### 4.1.1 职责
- 样本生命周期管理
- 队列管理
- 仪器健康状态管理
- 数据库操作

#### 4.1.2 核心类

**Core类**

| 方法 | 功能 |
|------|------|
| `receive_sample()` | 接收新样本 |
| `process_load_unload()` | 处理Load/Unload请求 |
| `add_queue()` | 添加队列 |
| `skip_queue()` | 跳过队列项 |
| `clear_queue()` | 清空队列 |
| `get_instrument_health()` | 获取仪器健康状态 |
| `manual_eject_sample()` | 手动弹出样本 |

#### 4.1.3 数据模型

**样本状态流转**

```
received → processing → completed → ready_to_unload → unloaded
                ↓
           error (处理失败)
```

**队列管理**

```python
queues = {
    0: [{'sample_id': 'S001', 'timestamp': ...}, ...],  # IP0队列
    1: [{'sample_id': 'S002', 'timestamp': ...}, ...]   # IP1队列
}
```

### 4.2 LAS模块 (las/las.py)

#### 4.2.1 职责
- uRAP协议消息处理
- TCP socket通信管理
- 消息序列号管理
- 超时处理

#### 4.2.2 核心类

**LASServer类**

| 方法 | 功能 |
|------|------|
| `start()` | 启动LAS服务器 |
| `stop()` | 停止LAS服务器 |
| `_handle_client()` | 处理客户端连接 |
| `_process_message()` | 处理接收的消息 |
| `_handle_load_unload_request()` | 处理Load/Unload请求 |
| `_send_load_unload_response()` | 发送Load/Unload响应 |
| `on_manual_operation_complete()` | 手动操作完成回调 |

#### 4.2.3 消息处理流程

```
接收消息 → 解析Header → 根据Type分发 → 处理Body → 发送响应
```

#### 4.2.4 支持的uRAP消息类型

| 消息类型 | 值 | 描述 |
|---------|-----|------|
| Initialization Request | 0x0001 | 初始化请求 |
| Initialization Response | 0x0002 | 初始化响应 |
| Instrument Health Request | 0x0201 | 仪器健康状态请求 |
| Instrument Health Response | 0x0202 | 仪器健康状态响应 |
| Add Queue Command | 0x0401 | 添加队列命令 |
| Add Queue Response | 0x0402 | 添加队列响应 |
| Load/Unload Command | 0x0303 | 装载/卸载命令 |
| Load/Unload Response | 0x0304 | 装载/卸载响应 |
| Transfer Status Request | 0x0209 | 传输状态请求 |
| Transfer Status Response | 0x020A | 传输状态响应 |

### 4.3 LIS模块 (lis/lis.py)

#### 4.3.1 职责
- ASTM E1381/E1394协议实现
- 样本订单查询
- 测试结果发送
- TCP socket通信

#### 4.3.2 核心类

**LISClient类**

| 方法 | 功能 |
|------|------|
| `connect()` | 连接LIS服务器 |
| `disconnect()` | 断开连接 |
| `send_enquiry()` | 发送查询请求 |
| `send_result()` | 发送测试结果 |
| `_handle_astm_message()` | 处理ASTM消息 |

### 4.4 UI模块 (ui/ui.py)

#### 4.4.1 职责
- 提供图形用户界面
- 显示系统状态
- 手动操作提示
- 队列管理界面

#### 4.4.2 核心类

**SimulatorUI类**

| 方法 | 功能 |
|------|------|
| `_create_widgets()` | 创建UI组件 |
| `_show_manual_prompt()` | 显示手动操作提示 |
| `_on_complete_button_click()` | 完成按钮点击处理 |
| `update_status()` | 更新状态显示 |
| `_show_queue_management()` | 显示队列管理界面 |

### 4.5 Logger模块 (logger/logger.py)

#### 4.5.1 职责
- 系统日志记录
- LAS通信日志记录
- 日志文件管理

#### 4.5.2 日志级别

| 级别 | 用途 |
|------|------|
| DEBUG | 调试信息 |
| INFO | 一般信息 |
| WARNING | 警告信息 |
| ERROR | 错误信息 |
| CRITICAL | 严重错误 |

---

## 5. 接口定义

### 5.1 Core模块接口

#### 5.1.1 样本管理接口

```python
def receive_sample(self, sample_id: str, tests: List[str]) -> bool:
    """接收新样本
    
    Args:
        sample_id: 样本ID
        tests: 测试项目列表
        
    Returns:
        bool: 是否成功接收
    """

def process_load_unload(self, 
    interface_position_index: int,
    carrier_occupancy: int,
    sample_id: str,
    tube_height: int,
    tube_diameter: int,
    elapsed_time: int
) -> Tuple[Dict, Dict, int, int, int, int, int]:
    """处理Load/Unload请求
    
    Returns:
        (load_result, unload_result, sample_status, 
         onboard_count, completed_count, ready_to_load, return_ready_count)
    """
```

#### 5.1.2 队列管理接口

```python
def add_queue(self, sample_id: str, interface_position: int) -> bool:
    """添加样本到队列"""

def skip_queue(self, sample_id: str, interface_position: int) -> bool:
    """跳过队列中的样本"""

def clear_queue(self, interface_position: int) -> bool:
    """清空队列"""
```

### 5.2 LAS模块接口

#### 5.2.1 服务器管理

```python
def start(self, host: str = '0.0.0.0', port: int = 8080) -> bool:
    """启动LAS服务器"""

def stop(self) -> None:
    """停止LAS服务器"""

def set_ui(self, ui) -> None:
    """设置UI引用"""
```

#### 5.2.2 消息发送接口

```python
def send_instrument_health_response(self, 
    return_sequence_id: int = None
) -> Tuple[bytes, int]:
    """发送仪器健康状态响应"""

def send_transfer_status_response(self,
    interface_position_index: int = 0,
    ready_to_load: int = 0,
    return_ready_count: int = 0
) -> None:
    """发送传输状态响应"""
```

### 5.3 UI模块接口

```python
def _show_manual_prompt(self, 
    request_type: str, 
    interface_position: int, 
    sample_id: str
) -> bool:
    """显示手动操作提示
    
    Returns:
        bool: 是否成功显示（如果已有请求正在显示则返回False）
    """

def on_manual_operation_complete(self, request: Dict) -> None:
    """手动操作完成回调（由LAS调用）"""
```

---

## 6. 数据流设计

### 6.1 样本加载流程

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  LAS    │────►│  Core   │────►│   UI    │────►│  User   │
│(Receive │     │(Process│     │(Display │     │(Manual │
│ Request)│     │ Request)│     │ Prompt) │     │ Action) │
└─────────┘     └─────────┘     └─────────┘     └────┬────┘
     ▲                                               │
     │                                               ▼
     │                                          ┌─────────┐
     │                                          │  Core   │
     │                                          │(Update │
     │                                          │ Status) │
     │                                          └────┬────┘
     │                                               │
     └───────────────────────────────────────────────┘
                    (Send Response)
```

### 6.2 样本卸载流程

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  LAS    │────►│  Core   │────►│   UI    │────►│  User   │
│(Receive │     │(Check  │     │(Display │     │(Enter  │
│ Unload  │     │ Sample │     │ Unload │     │ Sample │
│ Request)│     │ Status)│     │ Prompt)│     │  ID)   │
└─────────┘     └─────────┘     └─────────┘     └────┬────┘
     ▲                                               │
     │                                               ▼
     │                                          ┌─────────┐
     │                                          │  Core   │
     │                                          │(Unload │
     │                                          │ Sample) │
     │                                          └────┬────┘
     │                                               │
     └───────────────────────────────────────────────┘
                    (Send Response)
```

### 6.3 LIS查询流程

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  Core   │────►│   LIS   │────►│  LIS    │────►│  Core   │
│(Request│     │(Send   │     │(Receive│     │(Process│
│  Order) │     │ Enquiry)│     │  Order) │     │  Order) │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
```

---

## 7. 协议实现

### 7.1 uRAP协议实现

#### 7.1.1 消息格式

**消息头 (18字节)**

| 字段 | 大小 | 描述 |
|------|------|------|
| STX | 1 | 起始符 (0x02) |
| Length | 2 | 消息长度 |
| Sequence ID | 2 | 序列号 |
| Return Sequence ID | 2 | 返回序列号 |
| Message Type | 2 | 消息类型 |
| Timestamp | 8 | 时间戳 |
| Spare | 1 | 保留 |

**消息尾 (3字节)**

| 字段 | 大小 | 描述 |
|------|------|------|
| Checksum | 2 | 校验和 |
| ETX | 1 | 结束符 (0x03) |

#### 7.1.2 Load/Unload Command 请求格式

| 字段 | 大小 | 描述 |
|------|------|------|
| Interface Position Index | 1 | 接口位置索引 (0=IP0, 1=IP1) |
| Carrier Occupancy | 1 | 载体占用状态 |
| Sample ID Length | 1 | 样本ID长度 |
| Sample ID | n | 样本ID (ASCII) |
| Tube Height | 1 | 管高度 |
| Tube Diameter | 1 | 管直径 |
| Elapsed Time | 2 | 经过时间 |

#### 7.1.3 Load/Unload Command 响应格式

| 字段 | 大小 | 描述 |
|------|------|------|
| Interface Position Index | 1 | 接口位置索引 |
| Load Sample ID Length | 1 | 装载样本ID长度 |
| Load Sample ID | n | 装载样本ID |
| Load Command Status | 1 | 装载命令状态 |
| Unload Sample ID Length | 1 | 卸载样本ID长度 |
| Unload Sample ID | n | 卸载样本ID |
| Unload Command Status | 1 | 卸载命令状态 |
| Sample Processing Status | 1 | 样本处理状态 |
| On Board Tube Count | 2 | 在板管数 |
| Completed Tube Count | 2 | 已完成管数 |
| Ready To Load | 1 | 是否准备好装载 |
| Return Ready Tube Count | 2 | 准备返回管数 |

#### 7.1.4 状态码定义

**Load Command Status**

| 值 | 名称 | 描述 |
|----|------|------|
| 0x01 | Success | 成功 |
| 0x02 | Error: Lock Carrier in place | 错误：锁定载体到位 |
| 0x03 | Error: OK to Unlock Carrier | 错误：可以解锁载体 |
| 0x04 | Queue Mismatch | 队列不匹配 |
| 0x05 | Interface position is offline | 接口位置离线 |
| 0x06 | Load Skipped | 装载跳过 |
| 0x07 | Instrument Skipped Loading | 仪器跳过装载 |
| 0x08 | Unsupported Sample ID | 不支持的样本ID |

**Unload Command Status**

| 值 | 名称 | 描述 |
|----|------|------|
| 0x01 | Success | 成功 |
| 0x02 | Error: Lock Carrier in place | 错误：锁定载体到位 |
| 0x03 | Error: OK to Unlock Carrier | 错误：可以解锁载体 |
| 0x04 | Queue Mismatch | 队列不匹配 |
| 0x05 | Interface position is offline | 接口位置离线 |
| 0x06 | Unload Skipped | 卸载跳过 |
| 0x07 | Instrument Skipped Unloading | 仪器跳过卸载 |

### 7.2 ASTM协议实现

#### 7.2.1 记录类型

| 记录类型 | 描述 |
|---------|------|
| H | 消息头记录 |
| P | 患者记录 |
| O | 订单记录 |
| R | 结果记录 |
| L | 消息终止记录 |

#### 7.2.2 通信流程

1. 建立TCP连接
2. 发送ENQ (Enquiry)
3. 接收ACK (Acknowledge)
4. 发送数据帧
5. 接收ACK
6. 发送EOT (End of Transmission)

---

## 8. 错误处理

### 8.1 错误分类

| 类别 | 描述 | 处理方式 |
|------|------|----------|
| 网络错误 | 连接断开、超时等 | 重连机制、日志记录 |
| 协议错误 | 消息格式错误、无效类型等 | 发送NACK、记录日志 |
| 业务错误 | 样本不存在、队列满等 | 返回错误状态码 |
| 系统错误 | 数据库错误、文件错误等 | 异常捕获、日志记录 |

### 8.2 超时处理

| 超时类型 | 超时时间 | 处理方式 |
|---------|---------|----------|
| Handshake Response | 20秒 | 断开连接 |
| Message ACK | 1秒 | 重发消息 |
| Load/Unload Response | 600秒 | 返回错误 |
| Keep-Alive Inactivity | 15秒 | 发送Keep-Alive |
| Pending Request | 600秒 | 自动清理 |

### 8.3 日志记录

```python
# 日志格式
"%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 示例
"2026-02-11 10:04:21 - LASCommunication - INFO - Load/Unload response sent, SeqID=0x0028"
```

---

## 9. 附录

### 9.1 版本历史

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| v1.6.7 | 2026-02-11 | 修复协议不符合项（超时时间、样本ID长度验证） |
| v1.6.6 | 2026-02-11 | 修复UI并发处理问题 |
| v1.6.5 | 2026-02-09 | 修复LOAD/UNLOAD并发处理问题 |
| v1.6.4 | 2026-02-09 | 修复UNLOAD RESPONSE未发送问题 |

### 9.2 配置文件说明

**config.json**

```json
{
  "las": {
    "host": "0.0.0.0",
    "port": 8080,
    "keep_alive_interval": 30
  },
  "lis": {
    "host": "127.0.0.1",
    "port": 5000,
    "enabled": false
  },
  "ui": {
    "width": 1200,
    "height": 800
  },
  "logging": {
    "level": "INFO",
    "max_bytes": 10485760,
    "backup_count": 5
  }
}
```

### 9.3 数据库结构

**样本表 (samples)**

| 字段 | 类型 | 描述 |
|------|------|------|
| sample_id | TEXT | 样本ID (主键) |
| status | TEXT | 样本状态 |
| tests | TEXT | 测试项目 (JSON) |
| results | TEXT | 测试结果 (JSON) |
| timestamp | REAL | 创建时间 |
| load_time | REAL | 装载时间 |
| interface_position | INTEGER | 接口位置 |

**队列表 (queues)**

| 字段 | 类型 | 描述 |
|------|------|------|
| id | INTEGER | 自增ID (主键) |
| sample_id | TEXT | 样本ID |
| interface_position | TEXT | 接口位置 |
| timestamp | REAL | 入队时间 |

---

**文档结束**
