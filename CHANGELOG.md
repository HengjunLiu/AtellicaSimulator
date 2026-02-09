# 更新日志

## v1.6.4 (2026-02-09)

### 修复
- **修复UNLOAD RESPONSE未发送问题**
  - 修复`remove_sample_from_queue`死锁问题
    - 问题：方法内部使用`with self.sample_lock:`，但调用者`process_load_unload`已持有该锁，导致死锁
    - 解决：移除`remove_sample_from_queue`内部的锁获取，由调用者统一管理
  - 修复UNLOAD请求处理逻辑
    - 问题：验证UNLOAD请求时使用`get_next_sample_to_unload()`返回的样本ID，而非用户输入的样本ID
    - 解决：优先使用请求中传递的`sample_id`进行验证

- **修复结果重复发送问题**
  - 在`_schedule_workflow_step`中添加重复调度检查
    - 问题：`generate_results`在`receive_sample`、`_workflow_step_lis_query`、`_workflow_step_process_lis_query_result`三个地方被调度，导致结果被生成和发送多次
    - 解决：调度前检查是否已存在该步骤的定时器，避免重复调度

- **修复Keep-Alive消息发送太频繁问题**
  - 禁用主消息循环中的Keep-Alive发送
    - 问题：`_keep_alive_loop`线程和主消息循环同时发送Keep-Alive，导致消息过于频繁
    - 解决：统一由`_keep_alive_loop`线程处理，主循环只记录日志

- **修复准备UNLOAD步骤状态设置问题**
  - 添加`status='completed'`设置
    - 问题：`_workflow_step_ready_for_unload`只设置`ready_for_unload=True`，未设置`status='completed'`
    - 解决：添加`self.samples[sample_id]['status'] = 'completed'`，确保样本能被正确识别为可卸载

- **修复pack错误**
  - 修复拒绝UNLOAD请求时的struct.pack参数错误
    - 问题：使用`0s`格式字符串处理0长度字符串时参数数量不匹配
    - 解决：移除`0s`格式，直接使用字节计数

### 优化
- **优化UI提示**
  - 移除`onboard_window.grab_set()`
    - 问题：在机标本窗口的`grab_set()`会阻止用户与手动操作提示交互
    - 解决：移除`grab_set()`调用，允许用户正常操作

### 改进
- 增强工作流步骤调度的可靠性
- 优化多线程锁管理，避免死锁
- 改进日志记录，便于问题诊断

## v1.6.3 (2026-02-08)

### 修复
- 修复"在机标本"列表刷新问题
  - 修正UI过滤条件，将'ejected'状态加入过滤列表
  - 确保手工弹出后的标本正确从列表中移除
  - 统一UI和LAS模块的样本状态过滤逻辑

### 改进
- 优化用户界面体验
- 增强列表刷新机制的可靠性

## v1.6.2 (2026-02-07)

### 修复
- 进一步优化LIS查询方法调用
- 完善ASTM协议通信流程
- 增强错误处理和日志记录

### 功能
- 优化整体系统性能
- 改进调试工具支持

## v1.6.1 (2026-02-07)

### 修复
- 修复LIS查询方法调用，使用`get_apply`替代`send_query_request`
- 优化ASTM协议通信流程
- 改进错误处理和日志记录

### 功能
- 集成真实LIS客户端（lis_client）
- 支持完整的ASTM协议消息处理
- 增强LIS连接状态管理

## v1.6.0 (2026-01-23)

### 修复
- 修复加载/卸载操作的整数参数错误
- 修复卸载时样本ID不匹配问题
- 修复LIS集成问题

### 功能
- 增加LIS客户端支持
- 优化工作流处理逻辑
- 改进用户界面体验

## v1.5.0

### 修复
- 修复各种bug和错误

### 功能
- 初始版本发布
- 基本的Atellica模拟器功能
- LAS服务器实现
- 样本工作流处理
- 图形用户界面
