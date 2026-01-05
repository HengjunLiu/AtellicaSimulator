# AtellicaSimulator 更新日志

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
