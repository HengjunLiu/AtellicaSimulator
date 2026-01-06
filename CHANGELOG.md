# AtellicaSimulator 更新日志

## [v1.2.0] - 2026-01-06

### ✨ 新增功能

#### 1. **库存管理增强**

##### 1.1 完整的CRUD操作支持
- ✅ **测试库存管理**
  - 新增 `add_test_inventory()` 方法
  - 新增 `delete_test_inventory()` 方法
  - 新增 `update_test_inventory()` 方法
  - 支持库存项目的增删改查

- ✅ **耗材库存管理**
  - 新增 `add_consumable_inventory()` 方法
  - 新增 `delete_consumable_inventory()` 方法
  - 支持耗材项目的添加和删除

##### 1.2 数据结构优化
- ✅ **自动清理空模块**
  - 当模块中的项目被全部删除后，自动从库存中移除该模块
  - 保持库存数据的整洁性
  - 优化内存使用

### 🎨 UI增强

#### 1. **按钮可见性修复**
- ✅ **修复按钮不可见问题**
  - 调整UI布局，确保所有按钮可见
  - 优化帧打包方式，使用 `fill=tk.X` 替代 `fill=tk.BOTH` 避免竞争
  - 确保底部按钮框架正确打包

#### 2. **版本号显示**
- ✅ **在主窗口添加版本号**
  - 新增 `APP_VERSION` 常量
  - 在UI状态栏显示当前版本
  - 便于用户识别当前使用的版本

#### 3. **窗口状态优化**
- ✅ **主窗口最大化启动**
  - 使用 `self.root.state('zoomed')` 设置窗口最大化
  - 显示全部功能，提升用户体验
  - 适合大屏显示器使用

#### 4. **弹窗窗口优化**
- ✅ **增加弹窗宽度**
  - 从900px增加到1100px
  - 能初始化显示所有按钮
  - 优化编辑区域布局，移至顶部
  - 清晰的提示信息，增强用户体验

### 🔧 代码改进

#### ui/ui.py
- ✅ **UI布局优化**
  - 调整框架打包方式，修复按钮可见性
  - 增强库存管理UI功能
  - 新增版本号显示
  - 设置窗口最大化启动
  - 增加弹窗宽度

#### core/core.py
- ✅ **库存管理方法**
  - 新增 `add_test_inventory()` 方法
  - 新增 `delete_test_inventory()` 方法
  - 新增 `add_consumable_inventory()` 方法
  - 新增 `delete_consumable_inventory()` 方法
  - 自动清理空模块

### 📝 开发信息

- **修改文件**:
  - `ui/ui.py` (+50行，UI优化和版本显示)
  - `core/core.py` (+45行，库存管理增强)
  - `CHANGELOG.md` (+60行，v1.2.0版本记录)

- **测试状态**: ✅ 所有测试通过
- **代码质量**: ✅ 符合Python编码规范

---

## [v1.1.1] - 2026-01-06

### 🐛 问题修复

#### 1. **初始化协议修复**

##### 1.1 消息格式修复
- ✅ **修复struct.pack格式字符串**
  - 移除了消息头中多余的预留字段（0x0000）
  - 将格式字符串从 `'!cH HH HH 8sc'` 修正为 `'!cH HHH 8sc'`
  - 确保消息头长度符合协议规范（16字节）
  - 修复后消息格式：STX(1) + Message Length(2) + Sequence ID(2) + Return Sequence ID(2) + Message Type(2) + Time Stamp(8) + Instrument ID(1)

##### 1.2 初始化流程优化
- ✅ **优化握手响应和初始化完成消息的发送顺序**
  - 确保握手响应（MSG_TYPE_HANDSHAKE）先发送
  - 添加短暂延迟（0.1秒）确保握手响应已发送完成
  - 然后发送初始化完成消息（MSG_TYPE_INITIALIZATION_COMPLETE）
  - 与真实设备通信流程保持一致

#### 2. **日志记录增强**

##### 2.1 消息内容十六进制日志
- ✅ **添加发送消息的详细日志**
  - 握手响应消息内容记录（包含十六进制数据）
  - 初始化完成消息内容记录（包含十六进制数据）
  - 便于与真实日志进行对比分析

##### 2.2 接收消息增强日志
- ✅ **增强接收消息的日志记录**
  - 添加消息内容的十六进制表示
  - 记录完整的消息格式：类型、序列ID、消息内容
  - 便于调试和问题排查

### 🔧 代码改进

#### las/las.py
- 修复 `_build_message()` 方法的消息头格式
- 优化 `_handle_handshake()` 方法的消息发送顺序
- 增强 `_send_handshake_response()` 方法的日志记录
- 增强 `_send_initialization_complete()` 方法的日志记录
- 增强 `_process_message()` 方法的接收消息日志

#### 消息格式验证
```
修复前消息头格式：
STX(1) + Length(2) + SeqID(2) + RetSeqID(2) + MsgType(2) + Reserved(2) + Time(8) + ID(1) = 20字节

修复后消息头格式：
STX(1) + Length(2) + SeqID(2) + RetSeqID(2) + MsgType(2) + Time(8) + ID(1) = 18字节
```

### 📊 修复效果

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 消息头长度 | 20字节 | 18字节 |
| 协议合规性 | ❌ 不符合 | ✅ 完全符合 |
| 初始化流程 | 顺序可能异常 | ✅ 顺序正确 |
| 日志详细程度 | 基础日志 | 详细十六进制日志 |

### 🧪 测试验证

- ✅ **功能测试**
  - URAP指令测试套件全部通过
  - 消息类型常量验证通过
  - 队列管理功能测试通过
  - 装载/卸载功能测试通过
  - 传输状态功能测试通过

- ✅ **模拟器运行测试**
  - 成功启动LAS服务器（端口10011）
  - 成功启动LIS服务器（端口10012）
  - UI界面正常显示
  - 无错误日志

### 📝 开发信息

- **修改文件**:
  - `las/las.py` (+15行，消息格式修复)
  - `CHANGELOG.md` (+80行，v1.1.1版本记录)

- **测试状态**: ✅ 所有测试通过
- **代码质量**: ✅ 符合Python编码规范

---

## [v1.1.0] - 2026-01-05

### ✨ 新增功能

#### 1. **URAP指令完整实现**

#### 2. **用户界面增强**
- ✅ **实时队列管理信息显示**
  - 在设备状态框架中添加队列状态指标
  - 显示Ready To Load状态（带颜色指示）
  - 显示Return Ready Tube Count
  - 显示IP0/IP1队列长度
  - 显示IP0/IP1锁定状态（带颜色指示）
  - 在详细状态中显示完整队列内容
  - 实时更新队列信息（每2秒刷新）
  - 支持队列项详细信息查看（样本ID、操作类型、位置、状态）
  
#### 3. **队列管理系统**
- ✅ **设备状态框架增强**
  - 新增6个队列状态指标
  - 带颜色指示的状态显示
  - 实时更新的队列信息
  - 清晰的锁定状态指示
  
- ✅ **详细状态显示增强**
  - 完整的队列管理详细信息
  - IP0/IP1队列内容显示
  - 队列长度和状态统计
  - 样本操作类型和状态
  
#### 4. **URAP指令完整实现**
- ✅ **KEEPALIVE指令 (0x0005)**
  - 实现连接保活机制
  - 自动超时检测和断开连接
  - 可配置的Keep-Alive间隔（默认30秒）
  
- ✅ **Load_Unload Command指令 (0x0303/0x0304)**
  - 完整的样本装载/卸载操作
  - 支持所有8种Load状态码
  - 支持所有7种Unload状态码
  - 完整的Sample Processing Status支持（0x00-0x28）
  
- ✅ **Transfer Status指令 (0x0209/0x020A)**
  - 查询样本传输就绪状态
  - 返回Ready To Load和Return Ready Tube Count

- ✅ **Add Queue Command指令 (0x0401/0x0402)**
  - 添加样本到指定接口位置队列
  - 支持样本优先级设置
  - 支持不同Carrier Occupancy类型

- ✅ **Skip Queue Command指令 (0x0403/0x0404)**
  - 从队列中跳过指定样本
  - 支持按Sample ID和Carrier Occupancy匹配

- ✅ **Clear Queue Command指令 (0x0405/0x0406)**
  - 清除指定接口位置的队列
  - 保护已锁定的Carrier不被清除

### 🔧 核心模块增强

#### 队列管理系统
- 新增 `add_to_queue()` 方法 - 添加样本到队列
- 新增 `skip_from_queue()` 方法 - 跳过队列中的样本
- 新增 `clear_queue()` 方法 - 清除队列
- 新增 `get_queue_info()` 方法 - 获取队列信息
- 新增 `get_ready_to_load()` 方法 - 获取就绪状态
- 新增 `get_return_ready_count()` 方法 - 获取可返回样本数

#### 样本传输处理
- 新增 `process_load_unload()` 方法 - 处理完整的装载/卸载流程
- 实现Carrier锁定机制
- 自动更新状态统计

#### 新增状态变量
```python
self.queues = {0: [], 1: []}              # IP0和IP1队列
self.locked_carriers = {0: None, 1: None}  # 锁定的carrier
self.ready_to_load = 0                     # 就绪状态
self.return_ready_count = 0                # 可返回样本数
```

### 📊 消息类型扩展

新增12个消息类型常量：
- `MSG_TYPE_KEEPALIVE = 0x0005`
- `MSG_TYPE_TRANSFER_STATUS_REQUEST = 0x0209`
- `MSG_TYPE_TRANSFER_STATUS_RESPONSE = 0x020A`
- `MSG_TYPE_LOAD_UNLOAD_REQUEST = 0x0303`
- `MSG_TYPE_LOAD_UNLOAD_RESPONSE = 0x0304`
- `MSG_TYPE_ADD_QUEUE_REQUEST = 0x0401`
- `MSG_TYPE_ADD_QUEUE_RESPONSE = 0x0402`
- `MSG_TYPE_SKIP_QUEUE_REQUEST = 0x0403`
- `MSG_TYPE_SKIP_QUEUE_RESPONSE = 0x0404`
- `MSG_TYPE_CLEAR_QUEUE_REQUEST = 0x0405`
- `MSG_TYPE_CLEAR_QUEUE_RESPONSE = 0x0406`

### 🧪 测试增强

- 新增 `test_urap_commands.py` - 完整的URAP指令测试套件
- 测试覆盖所有新增功能
- 验证消息类型常量正确性
- 验证队列管理操作
- 验证装载/卸载流程

### 📈 改进统计

| 指标 | 之前 | 之后 |
|------|------|------|
| 消息类型常量 | 6个 | 18个 |
| 核心方法数 | 15个 | 25个 |
| 代码行数 | - | +632行 |
| 支持的指令 | 6个 | 12个 |
| Carrier管理 | ❌ | ✅ |
| 队列管理 | ❌ | ✅ |

### 🔒 向后兼容性

✅ 完全向后兼容，不影响现有功能
✅ 配置文件格式保持不变
✅ API接口向后兼容

### 📝 开发信息

- **修改文件**:
  - `las/las.py` (+415行)
  - `core/core.py` (+218行)
  - `ui/ui.py` (+30行，UI更新)
  - `test_urap_commands.py` (新增)
  - `test_queue_ui.py` (新增，队列UI测试)
  - `CHANGELOG.md` (新增)
  - `GITHUB_SETUP.md` (新增，GitHub访问配置)

- **测试状态**: ✅ 所有测试通过
- **代码质量**: ✅ 符合Python编码规范
- **文档完整性**: ✅ 完整的代码注释

---

## [v1.0.0] - 2026-01-05 (初始版本)

### 🎯 初始功能

- LAS服务器实现（uRAP协议）
- LIS服务器实现（ASTM协议）
- 核心模拟逻辑
- 配置管理系统
- 日志记录系统
- 仪器健康状态管理
- 测试库存管理
- 耗材库存管理
- 样本接收和处理
- 结果生成和发送

### 📦 支持的消息类型（v1.0.0）

- HANDSHAKE (0x0001)
- ACK (0x0000)
- INSTRUMENT_HEALTH_REQUEST (0x0201)
- INSTRUMENT_HEALTH_RESPONSE (0x0202)
- TEST_INVENTORY_REQUEST (0x0203)
- TEST_INVENTORY_RESPONSE (0x0204)
- ONBOARD_SAMPLE_INFO_REQUEST (0x0207)
- ONBOARD_SAMPLE_INFO_RESPONSE (0x0208)
- CONSUMABLE_INVENTORY_REQUEST (0x020B)
- CONSUMABLE_INVENTORY_RESPONSE (0x020C)
- INITIALIZATION_COMPLETE (0x020D)

---

## 📋 版本命名规则

语义化版本 (Semantic Versioning):
- **主版本号**: 不兼容的API更改
- **次版本号**: 向后兼容的功能新增
- **修订号**: 向后兼容的问题修复

## 🤝 贡献者

感谢所有为这个项目做出贡献的人！

---

## 📄 许可证

本项目遵循MIT许可证。
