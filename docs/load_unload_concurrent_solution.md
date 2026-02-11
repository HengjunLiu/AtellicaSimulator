# LOAD/UNLOAD 并发处理问题解决方案

## 问题描述

当LOAD指令和UNLOAD指令先后到达，但前一动作还未执行完时，后一指令的执行会出现问题。

### 具体表现

1. **请求队列混乱**：`pending_requests`是全局列表，没有按接口位置(IP0/IP1)分离
2. **Carrier锁定检查不足**：在`pending_requests`阶段没有检查carrier是否已被锁定
3. **响应顺序问题**：用户点击完成的顺序可能与请求到达顺序不一致
4. **缺乏超时机制**：pending请求可能永远等待，不会超时

## 根本原因

根据uRAP协议设计原则，Atellica Solution与LAS之间的LOAD/UNLOAD操作需要严格的顺序控制：

1. **接口位置独立**：IP0(装载口)和IP1(卸载口)的操作应该独立处理
2. **Carrier锁定**：同一接口位置同一时间只能处理一个请求
3. **顺序响应**：必须按请求到达顺序发送响应
4. **超时处理**：长时间未完成的请求应该超时并返回错误

## 解决方案

### 1. 按接口位置分离请求队列

**当前代码：**
```python
self.pending_requests = []  # 全局列表
```

**建议修改：**
```python
self.pending_requests = {
    0: [],  # IP0的请求队列
    1: []   # IP1的请求队列
}
```

### 2. 添加Carrier锁定检查

在接收请求时检查carrier是否已被锁定：

```python
def _handle_load_unload_request(self, conn, header, body, manual_complete=False):
    # 解析请求...
    interface_position_index = body[0]
    
    # 检查carrier是否已被锁定
    if self.core.locked_carriers[interface_position_index] is not None:
        # Carrier已被锁定，返回错误响应
        self._send_load_unload_error_response(
            conn, header, interface_position_index,
            status=2  # Error: Lock Carrier in place
        )
        return
    
    # 检查该接口位置是否已有待处理请求
    if self.pending_requests[interface_position_index]:
        # 已有待处理请求，根据协议决定是否拒绝或排队
        self._send_load_unload_error_response(
            conn, header, interface_position_index,
            status=2  # Error: Lock Carrier in place
        )
        return
```

### 3. 实现请求去重机制

防止重复请求被多次处理：

```python
def _handle_load_unload_request(self, conn, header, body, ...):
    seq_id = header['sequence_id']
    ip = body[0]
    
    # 检查是否已存在相同序列号的请求
    for req in self.pending_requests[ip]:
        if req['header']['sequence_id'] == seq_id:
            # 重复请求，忽略
            return
```

### 4. 添加请求超时机制

```python
def _check_pending_request_timeout(self):
    """检查pending请求是否超时"""
    current_time = time.time()
    for ip in [0, 1]:
        for request in self.pending_requests[ip][:]:  # 使用切片复制列表
            if current_time - request['timestamp'] > self.request_timeout:
                # 请求超时，发送错误响应
                self._send_timeout_response(request)
                self.pending_requests[ip].remove(request)
```

### 5. 改进手动操作完成处理

确保按FIFO顺序处理请求：

```python
def on_manual_operation_complete(self, request):
    ip = request['interface_position']
    
    # 检查该接口位置是否有待处理请求
    if not self.pending_requests[ip]:
        self.logger.warning(f"No pending request for IP{ip}")
        return
    
    # 获取该接口位置的第一个请求（FIFO）
    pending_request = self.pending_requests[ip].pop(0)
    
    # 处理请求...
    self._send_load_unload_response_after_delay(...)
```

## 协议要求

根据uRAP协议（Atellica Solution LAS Interface Guide）：

1. **Load/Unload Command (0x0303)**：
   - LAS发送装载/卸载命令请求
   - Atellica必须返回Load/Unload Command Response (0x8303)

2. **Carrier锁定**：
   - 当Atellica正在处理某个接口位置的LOAD/UNLOAD时，该位置的carrier被锁定
   - 如果LAS在carrier锁定时发送新请求，Atellica应返回错误状态

3. **状态码**：
   - Status = 1: Success
   - Status = 2: Error - Lock Carrier in place
   - Status = 6: Load/Unload Skipped

## 实施建议

### 优先级1：立即修复
1. 按接口位置分离`pending_requests`
2. 添加carrier锁定检查

### 优先级2：短期改进
3. 实现请求去重机制
4. 添加请求超时处理

### 优先级3：长期优化
5. 完善错误处理和日志记录
6. 添加请求序列号验证

## 测试用例

1. **并发LOAD测试**：
   - LAS连续发送两个IP0的LOAD请求
   - 验证第二个请求被拒绝（carrier locked）

2. **并发UNLOAD测试**：
   - LAS连续发送两个IP1的UNLOAD请求
   - 验证第二个请求被拒绝（carrier locked）

3. **IP0/IP1并发测试**：
   - 同时发送IP0的LOAD和IP1的UNLOAD
   - 验证两个请求都能正常处理

4. **超时测试**：
   - 发送LOAD请求后，用户长时间不点击完成
   - 验证请求超时并返回错误响应
