# 更新日志

## v1.6.8 (2026-02-28)

### 修复协议不符合项
- **修复Instrument Health Response格式**
  - 问题：Body长度与真实ATS不一致
  - 解决：
    - 添加填充字节（第3字节为0）
    - 修正字段顺序：automation_interface_status, instrument_process_status, 填充字节, lis_connection_status, interface_positions
    - 固定发送2组接口状态（IP0和IP1）
    - 移除额外的字节（之前错误地添加了值为2的字节）
  
- **修正Instrument Health配置**
  - `interface_positions`: 1 → 2（支持IP0和IP1）
  - `remote_control_status`: [2, 2] → [4, 5]（与真实ATS一致）
  - `lock_ownership`: [4, 5]（与真实ATS一致）
  - `lis_connection_status`: 0 → 1（已连接）

- **修复Handshake响应**
  - 问题：`return_sequence_id`始终为0
  - 解决：使用请求中的`sequence_id`作为`return_sequence_id`

- **修复Load/Unload Response格式**
  - 问题：格式字符串错误导致字段长度不匹配
  - 解决：统一使用`'!B B {load_sample_id_len}s B B {unload_sample_id_len}s B H H H H H'`格式
  - Sample Status、Ready to Load等字段从1字节改为2字节

- **修复Transfer Status Response格式**
  - 问题：格式与真实ATS不一致
  - 解决：改为`'!B H H'`格式（Interface Position + Ready to Load + Return Ready Count）

### 协议符合性改进
- Instrument Health Response Body格式与真实ATS完全一致
- 所有响应消息的字段长度与真实ATS一致
- 初始化流程与真实ATS一致

## v1.6.7 (2026-02-11)

### 修复协议不符合项
- **修复Load/Unload请求超时时间**
  - 问题：超时时间设置为300秒（5分钟）
  - 协议要求：600秒（10分钟）
  - 解决：将`request_timeout`从300秒改为600秒
  
- **添加样本ID长度验证**
  - 问题：未验证样本ID长度
  - 协议要求：最大20个字符
  - 解决：添加长度检查，超过20字符返回状态码0x08（Unsupported Sample ID）

### 协议符合性改进
- 已支持的状态码：
  - 0x01 - Success
  - 0x02 - Error: Lock Carrier in place
  - 0x04 - Queue Mismatch（已存在）
  - 0x05 - Interface position is offline（已存在）
  - 0x06 - Load/Unload Skipped
  - 0x07 - Instrument Skipped Loading/Unloading（已存在）
  - 0x08 - Unsupported Sample ID（新增）

## v1.6.6 (2026-02-11)

### 修复
- **修复UNLOAD未完成时LOAD指令导致的UI混乱问题**
  - UI请求显示管理
    - 问题：UI的`_show_manual_prompt`方法每次都会覆盖`self.current_request`，导致同时只能显示一个请求
    - 解决：方法现在返回bool值，如果已有请求正在显示则返回False
  - 请求队列管理
    - 问题：当UNLOAD还在等待手动完成时，LOAD请求到达会覆盖UNLOAD的UI提示
    - 解决：新请求被标记为`waiting_for_ui`并加入队列，等待UI可用时再显示
  - 自动显示等待请求
    - 添加`UI._check_and_show_pending_requests`方法
    - 在完成当前请求后自动检查并显示等待的请求
    - 确保所有请求都能按顺序被处理

### 改进
- 增强UI并发处理能力，支持请求排队等待
- 完善请求处理流程，避免请求丢失
- 优化用户体验，确保操作顺序清晰

## v1.6.5 (2026-02-09)

### 修复
- **修复LOAD/UNLOAD并发处理问题**
  - 按接口位置分离pending请求队列
