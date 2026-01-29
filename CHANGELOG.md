# AtellicaSimulator 更新日志

## [v1.3.9] - 2026-01-29

### 🐛 问题修复

#### 1. **LAS协议UNLOAD请求处理修复**
- ✅ **0x020A消息格式修复**
  - 确保0x020A-Transfer status response message符合协议规范
  - 添加状态字段 = `0x03`（检测完成，等待卸载）
  - 添加接口空闲标识 = `0x01`
  - 添加故障码 = `0x00`（无故障）
  - 添加待卸载样本ID到消息中，确保样本ID匹配

- ✅ **UNLOAD请求验证逻辑**
  - 实现协议要求的完整触发条件链
  - 只有在收到0x020A消息且状态为0x03时才允许处理UNLOAD请求
  - 验证样本ID匹配
  - 对于不符合条件的UNLOAD请求发送拒绝响应
  - 增强日志记录，添加详细的拒绝原因

- ✅ **协议合规性验证**
  - 符合`Atellica Solution LAS Interface Guide`协议规范
  - 核心触发命令：0x020A-Transfer status response message
  - 状态字段要求：0x03（检测完成，等待卸载）
  - 配套字段验证：样本ID匹配、接口空闲标识、无故障码
  - 完整触发条件链：前置条件 → 关键通知 → 状态校验 → 执行请求

### 📝 开发信息

- **修改文件**:
  - `las/las.py` (+60行，LAS协议UNLOAD请求处理修复)
  - `CHANGELOG.md` (+50行，v1.3.9版本记录)

- **测试状态**: ✅ 所有测试通过
- **代码质量**: ✅ 符合Python编码规范
- **向后兼容性**: ✅ 完全向后兼容
- **协议合规性**: ✅ 符合`Atellica Solution LAS Interface Guide`规范

## [v1.3.8] - 2026-01-26

### 🐛 问题修复

#### 1. **手工弹出功能修复**
- ✅ **LAS协议合规性修复**
  - 确保手工弹出命令符合`Atellica_Solution_LAS_Interface_Guide`协议规范
  - 更新`sample_status`为`0x03` (Sample Ejected)，正确反映手工弹出状态
  - 修改`load_status`为`0x00` (Not Applicable，纯卸载操作)
  - 添加明确注释说明手工弹出场景："标本已离开ATS，且不在LAS上"

- ✅ **核心逻辑优化**
  - 新增`ejected`状态，明确标记手工弹出的样本
  - 添加`ejected_manually`标志，区分手工弹出和正常处理
  - 修正计数器逻辑：手工弹出样本**不计入**`return_ready_count`
  - 完善注释说明，明确手工弹出的语义

#### 2. **退出按钮修复**
- ✅ **组件名称修正**
  - 将不存在的`lis_server`改为正确的`lis_client`
  - 添加`root.destroy()`调用，确保窗口完全关闭
  - 确保所有组件（LAS服务器、LIS客户端）正确停止

### 📝 开发信息

- **修改文件**:
  - `core/core.py` (+15行，手工弹出核心逻辑修复)
  - `las/las.py` (+10行，LAS协议合规性修复)
  - `ui/ui.py` (+5行，退出按钮修复)
  - `CHANGELOG.md` (+40行，v1.3.8版本记录)

- **测试状态**: ✅ 所有测试通过
- **代码质量**: ✅ 符合Python编码规范
- **向后兼容性**: ✅ 完全向后兼容

## [v1.3.7] - 2026-01-21

### 🐛 问题修复

#### 1. **测试算法改进**
- ✅ **确保测试和计算包含ETX字符**
  - 修复了校验码计算时丢失ETX的问题
  - 确保消息完整性验证准确

#### 2. **Clear Queue Command Response修复**
- ✅ **根据请求中的Interface Position Index字段进行对应响应**
  - 不再硬编码为IP0
  - 从请求消息中提取接口位置索引

#### 3. **初始化完成状态判断改进**
- ✅ **优化初始化流程**
  - 正确处理各种请求类型的数量（Clear Queue和Transfer Status各两个）
  - 只有在发送Initialization Completed Message并收到ACK后才切换到Connected状态

#### 4. **Load Unload Command Response修复**
- ✅ **修复unload_sample_id_bytes条件判断错误**
  - 确保使用unload_result作为条件判断，而不是load_result

### 📝 开发信息

- **修改文件**:
  - `las/las.py` (+15行，修复校验码计算和响应逻辑)
  - `CHANGELOG.md` (+30行，v1.3.7版本记录)

- **测试状态**: ✅ 所有测试通过
- **代码质量**: ✅ 符合Python编码规范
- **向后兼容性**: ✅ 完全向后兼容

## [v1.3.5] - 2026-01-20

### 🎨 UI界面优化

#### 1. **设备状态组框调整**

##### 1.1 垂直空间优化
- ✅ **减少组框内边距**
  - 将设备状态组框padding从10改为5
  - 将pady从10改为5
  - 调整所有网格元素的pady从5改为2
  - 有效减少了设备状态组框的垂直空间占用

##### 1.2 框架布局优化
- ✅ **优化中间内容框架**
  - 将pady从10改为5
  - 添加了expand=False参数，防止过度占据垂直空间
  - 确保左侧参数配置、中间手动处理和右侧状态显示区域布局紧凑

- ✅ **优化日志显示框架**
  - 将pady从10改为5
  - 将expand=True改为expand=False，防止日志区域过度扩展
  - 减少了通讯日志组框的垂直空间占用

##### 1.3 底部按钮显示修复
- ✅ **确保所有按钮可见**
  - 通过优化各框架布局参数，确保底部按钮区域完整显示
  - 包括"刷新状态"、"在机标本"、"编辑库存"、"清空日志"和"退出"按钮

### ✨ 状态显示优化

#### 1. **自动化接口状态扩展**
- ✅ **添加Critical状态**
  - 支持自动化接口状态的Critical值（0x04）
  - 在UI中显示为"Critical"，红色字体
  - 更新了状态更新方法，支持值为4的Critical状态

#### 2. **就绪装载状态国际化**
- ✅ **改为英文描述**
  - 将中文显示"是/否"改为英文"Ready to Load/Not Ready to Load"
  - 与uRAP文档保持一致
  - 提升了国际兼容性

#### 3. **远程控制状态详细显示**
- ✅ **根据IP索引显示不同描述**
  - IP0：显示"Offline or Local" (1) 或 "Online Loading Only Mode" (4)
  - IP1：显示"Offline or Local" (1) 或 "Online Unloading Only Mode" (5)

#### 4. **锁所有权状态详细显示**
- ✅ **更详细的状态描述**
  - 显示"Locked by Instrument" (1) 或 "Not Locked by Instrument" (2)
  - 与uRAP文档保持一致

### ⚙️ UI配置扩展

#### 1. **自动化接口状态配置增强**
- ✅ **添加Critical选项**
  - 在参数配置的设备状态选项卡中添加了Critical选项
  - 允许用户手工切换自动化接口状态为Green、Red或Critical

#### 2. **远程控制状态配置**
- ✅ **IP0远程控制状态**
  - 可配置为"Offline or Local" (1) 或 "Online Loading Only Mode" (4)
  - 对应uRAP文档中的First Remote Control Status

- ✅ **IP1远程控制状态**
  - 可配置为"Offline or Local" (1) 或 "Online Unloading Only Mode" (5)
  - 对应uRAP文档中的Last Remote Control Status

#### 3. **锁所有权配置**
- ✅ **IP0锁所有权**
  - 可配置为"Locked by Instrument" (1) 或 "Not Locked by Instrument" (2)
  - 对应uRAP文档中的First Lock Ownership

- ✅ **IP1锁所有权**
  - 可配置为"Locked by Instrument" (1) 或 "Not Locked by Instrument" (2)
  - 对应uRAP文档中的Last Lock Ownership

#### 4. **状态更新方法**
- ✅ **新增状态更新方法**
  - `_update_ip0_remote_status()`：更新IP0远程控制状态
  - `_update_ip0_lock_ownership()`：更新IP0锁所有权
  - `_update_ip1_remote_status()`：更新IP1远程控制状态
  - `_update_ip1_lock_ownership()`：更新IP1锁所有权

### 🔧 代码改进

#### ui/ui.py
- ✅ **UI布局优化**
  - 调整了设备状态组框的padding和pady
  - 优化了中间内容框架和日志显示框架的布局参数
  - 确保底部按钮能全部显示

- ✅ **状态显示增强**
  - 扩展了自动化接口状态显示
  - 优化了就绪装载状态显示
  - 改进了远程控制状态和锁所有权状态的显示

- ✅ **UI配置扩展**
  - 添加了自动化接口状态的Critical选项
  - 添加了远程控制状态配置
  - 添加了锁所有权配置
  - 添加了对应的状态更新方法

### 🧪 测试脚本

#### test_ui.py
- ✅ **UI独立运行测试脚本**
  - 用于测试UI是否能正常启动和运行
  - 包含完整的初始化流程
  - 便于调试UI相关问题

### 📝 开发信息

- **修改文件**:
  - `ui/ui.py` (+50行，UI优化和配置扩展)
  - `CHANGELOG.md` (+80行，v1.3.5版本记录)
  - `test_ui.py` (新增，UI测试脚本)

- **测试状态**: ✅ 所有测试通过
- **代码质量**: ✅ 符合Python编码规范
- **向后兼容性**: ✅ 完全向后兼容

## [v1.3.4] - 2026-01-20

### ✨ 新增功能

#### 1. **在机标本管理**

##### 1.1 样本列表显示
- ✅ **在机标本弹窗**
  - 新增"在机标本"按钮，显示当前在机的标本列表
  - 包含样本ID、状态和装载时间信息
  - 支持列表高亮选中

##### 1.2 手工弹出功能
- ✅ **手动样本弹出**
  - 可从列表中选择样本进行手工弹出
  - 自动更新样本状态为completed
  - 正确更新计数器（在线试管数、完成试管数、可返回数）
  - 按照URAP协议通知LAS服务器

##### 1.3 LAS通知机制
- ✅ **符合URAP协议**
  - 发送MSG_TYPE_LOAD_UNLOAD_RESPONSE消息
  - 正确的消息格式和状态码
  - 通知所有连接的LAS客户端

## [v1.3.3] - 2026-01-20

### ✨ 新增功能

#### 1. **手动样本处理增强**

##### 1.1 UNLOAD样本ID输入框
- ✅ **手动样本ID输入功能**
  - 仅在UNLOAD请求时显示输入框
  - 预填建议的样本ID
  - 允许操作员手动修改样本ID
  - 支持自定义样本ID输入

##### 1.2 改进的操作流程
- ✅ **优化的UNLOAD流程**
  - 操作员可确认或修改要装载的样本ID
  - 提高操作灵活性
  - 适应不同的测试场景

## [v1.3.2] - 2026-01-16

### ✨ 新增功能

#### 1. **手动样本处理UI增强**

##### 1.1 闪烁效果提示
- ✅ **动态闪烁视觉效果**
  - 绿色圆圈和文字闪烁：LOAD请求 - "请手工卸载IP0的标本"
  - 黄色圆圈和文字闪烁：UNLOAD请求 - "请手工装载IP1的标本"
  - 500ms闪烁间隔，增强视觉吸引力
  - 自动停止闪烁，节省资源

##### 1.2 清晰的状态过渡
- ✅ **明确的状态变化**
  - 闪烁ON：完整颜色显示
  - 闪烁OFF：半透明效果
  - 点击"完成"后停止闪烁

## [v1.3.1] - 2026-01-16

### ✨ 新增功能

#### 1. **手动样本处理UI**

##### 1.1 直观的样本操作提示
- ✅ **彩色圆圈可视化提示**
  - 绿色圆圈：LOAD请求 - "请手工卸载IP0的标本"
  - 黄色圆圈：UNLOAD请求 - "请手工装载IP1的标本"
  - 清晰的操作指引，提升操作效率

##### 1.2 完整的样本ID显示
- ✅ **详细的样本信息展示**
  - LOAD请求：显示要卸载的样本ID
  - UNLOAD请求：显示要装载的样本ID
  - 操作人员可明确知道具体处理哪个样本

##### 1.3 简单的完成确认
- ✅ **一键完成操作**
  - 操作完成后点击"完成"按钮
  - 自动发送MSG_TYPE_LOAD_UNLOAD_RESPONSE
  - 流程继续执行

### 🔧 核心功能增强

#### 1. **LAS服务器手动操作支持**
- ✅ **UI与LAS服务器通信**
  - UI请求提示和完成确认机制
  - 暂停/恢复处理流程
  - 安全的请求队列管理

#### 2. **样本预览功能**
- ✅ **获取下一个要处理的样本**
  - 新增 `get_next_sample_to_unload()` 方法
  - 准确显示即将处理的样本ID
  - 提升操作准确性

### 🔧 代码改进

#### ui/ui.py
- ✅ **新增手动样本处理UI组件**
  - Canvas绘图显示彩色提示圆圈
  - 动态文本提示更新
  - 完成按钮事件处理

#### las/las.py
- ✅ **手动操作流程集成**
  - UI引用管理
  - 请求队列机制
  - 手动操作完成回调

#### core/core.py
- ✅ **样本预览功能**
  - 新增 `get_next_sample_to_unload()` 方法
  - 准确的样本状态检查

### 📝 开发信息

- **修改文件**:
  - `ui/ui.py` (+40行，手动处理UI)
  - `las/las.py` (+25行，手动操作支持)
  - `core/core.py` (+15行，样本预览)
  - `CHANGELOG.md` (+45行，v1.3.1版本记录)
  - `main.py` (+1行，UI引用设置)

- **测试状态**: ✅ 所有测试通过
- **代码质量**: ✅ 符合Python编码规范

---

## [v1.3.0] - 2026-01-09

### ✨ 新增功能

#### 1. **LIS真实连接处理**

##### 1.1 完整的ASTM协议查询支持
- ✅ **LIS工作单查询**
  - 实现了完整的ASTM查询记录(Q类型)处理
  - 支持真实LIS服务器的查询请求和响应
  - 线程安全的查询结果存储和获取

##### 1.2 样本工作流优化
- ✅ **完整的样本处理流程**
  - LOAD → 5秒LIS查询 → 测试验证 → 结果生成 → UNLOAD准备
  - 5分钟有效项目结果生成
  - 2分钟UNLOAD准备

### 🔧 核心功能增强

#### 1. **测试项目验证**
- ✅ **完整的测试项目验证逻辑**
  - 检查测试项目是否存在
  - 验证试剂是否充足
  - 检查项目状态是否正常

#### 2. **无效项目处理**
- ✅ **立即ERROR结果生成**
  - 对无效测试项目立即生成ERROR结果
  - 包含详细的错误原因
  - 立即发送ERROR结果给LIS

#### 3. **样本状态管理**
- ✅ **优化的状态流转**
  - 正确处理各种样本状态
  - 确保计数器准确更新
  - 支持混合结果（有效+无效项目）

### 🔧 代码改进

#### core/core.py
- ✅ **LIS查询集成**
  - 等待LIS回复，超时30秒
  - 解析真实测试项目
  - 测试项目有效性验证
  - ERROR结果生成和发送
  - 优化的样本工作流控制

### 📝 开发信息

- **修改文件**:
  - `core/core.py` (+30行，样本工作流优化)
  - `ui/ui.py` (版本号更新)
  - `CHANGELOG.md` (+40行，v1.3.0版本记录)

- **测试状态**: ✅ 所有测试通过
- **代码质量**: ✅ 符合Python编码规范

---

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
