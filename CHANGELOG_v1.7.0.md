# Atellica Solution Simulator v1.7.0 更新日志

## 版本信息
- **版本号**: v1.7.0
- **发布日期**: 2026-03-10
- **更新类型**: 重大Bug修复

---

## 修复内容

### 1. 0304 Load/Unload Command Response 消息格式修复

#### 问题描述
0304响应消息的字节格式不符合协议规范，导致LAS无法正确解析消息。

#### 修复详情
修正了 `las/las.py` 中的struct.pack格式字符串：

**修改前:**
```python
f'!B B {load_sample_id_len}s B B {unload_sample_id_len}s B H H H H B'
```

**修改后:**
```python
f'!B B {load_sample_id_len}s B B {unload_sample_id_len}s B B H H B H'
```

**字段变更:**
| 字段 | 修改前 | 修改后 | 说明 |
|------|--------|--------|------|
| Sample Processing Status | 2字节 (H) | 1字节 (B) | 符合协议规范 |
| Ready To Load | 2字节 (H) | 1字节 (B) | 符合协议规范 |
| Return Ready Count | 1字节 (B) | 2字节 (H) | 符合协议规范 |

### 2. Sample ID 截断问题修复

#### 问题描述
代码中将Sample ID错误地截断为6字节，而协议规定最大长度为24字节。

#### 修复详情
移除了6字节截断逻辑，改为使用完整的Sample ID（最大24字节）。

**修改前:**
```python
load_sample_id_bytes = load_sample_id_full[:6].encode('ascii')  # 只取前6字节
unload_sample_id_bytes = unload_sample_id_full[:6].encode('ascii')  # 只取前6字节
```

**修改后:**
```python
load_sample_id_bytes = load_sample_id_full[:24].encode('ascii')  # 最大24字节
unload_sample_id_bytes = unload_sample_id_full[:24].encode('ascii')  # 最大24字节
```

### 3. 错误响应消息格式同步修复

同步修复了 `_send_load_unload_error_response` 方法中的格式字符串，确保错误响应也符合协议规范。

---

## 技术细节

### 0304消息格式（协议规范）
```
Header | Interface Position Index (1 Byte) | 
F L | Load Sample ID (n Bytes) | 
Load Command Status (1 Byte) | 
F L | Unload Sample ID (n Bytes) | 
Unload Command Status (1 Byte) | 
Sample Processing Status (1 Byte) | 
On Board Tube Count (2 Bytes) | 
Completed Tube Count (2 Bytes) | 
Ready To Load (1 Byte) | 
Return Ready Tube Count (2 Bytes) | 
Footer
```

### Sample ID 规范
- **最大长度**: 24字节（协议支持）
- **Atellica限制**: 不超过20个字符
- **支持字符**: 标准7位ASCII，字母数字和特定符号

---

## 测试结果

✅ **全部测试通过**
- X23试剂信息正确发送到LAS
- 202501230270标本LOAD/UNLOAD流程正常
- Sample Processing Status正确返回0x01
- 完整的Sample ID（12字节）正确传输
- UNLOAD操作不再显示"放弃出样"错误

---

## 影响范围

### 修改文件
1. `las/las.py` - 主要修复文件
   - `_handle_load_unload_request` 方法
   - `_send_load_unload_error_response` 方法

### 兼容性
- 与LAS协议版本0x0330完全兼容
- 与Atellica Solution软件版本0x0101完全兼容

---

## 已知问题

无

---

## 后续建议

1. 建议在实际环境中进行全面回归测试
2. 监控LAS通信日志，确保消息格式正确
3. 考虑添加消息格式自动校验机制

---

## 作者
Atellica Solution Simulator 开发团队

## 许可证
内部使用
