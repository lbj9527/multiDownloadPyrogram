# Telegram频道历史消息下载程序 - 需求文档

## 📋 项目概述

### 项目名称
Telegram频道历史消息批量下载器 (MultiDownloadPyrogram)

### 项目描述
基于Pyrogram框架开发的Telegram频道历史消息媒体文件批量下载工具，支持多客户端并发下载、大文件分片下载、媒体组完整下载等功能。

### 技术栈
- **核心框架**: Pyrogram
- **编程语言**: Python 3.8+
- **代理协议**: SOCKS5
- **并发模式**: 多客户端会话并发

---

## 🎯 功能需求 (Functional Requirements)

### FR-001: 单条消息媒体文件下载
**优先级**: P0 (最高)
**描述**: 系统能够下载单条Telegram消息中的媒体文件
**详细需求**:
- 支持图片文件下载 (.jpg, .png, .webp等)
- 支持视频文件下载 (.mp4, .mov, .avi等)
- 支持音频文件下载 (.mp3, .wav, .ogg等)
- 支持文档文件下载 (.pdf, .doc, .zip等)

**验收标准**:
- 能够正确识别消息中的媒体类型
- 下载的文件完整性验证通过
- 文件名命名规范合理
- 支持自定义下载目录

### FR-002: 媒体组文件下载
**优先级**: P0 (最高)
**描述**: 系统能够识别并完整下载Telegram媒体组(相册)中的所有文件
**详细需求**:
- 自动识别媒体组消息
- 获取媒体组中的所有媒体文件
- 保持媒体组文件的关联关系
- 支持混合媒体类型的媒体组

**验收标准**:
- 能够正确识别媒体组消息
- 媒体组中所有文件都能下载完整
- 媒体组文件按统一命名规则组织
- 支持媒体组文件夹分组存储

### FR-003: 大规模下载稳定性
**优先级**: P0 (最高)
**描述**: 系统支持大规模消息下载，具备良好的容错能力
**详细需求**:
- 支持下载1000+条消息
- 单个文件下载失败不影响其他文件下载
- 网络异常自动重试机制
- 下载进度实时显示
- 下载统计信息记录

**验收标准**:
- 能够连续稳定下载1000条消息
- 失败率控制在5%以内
- 网络异常后自动重试下载
- 提供详细的下载日志

### FR-004: 消息ID范围指定
**优先级**: P1 (高)
**描述**: 用户可以指定起始和结束消息ID进行精确范围下载
**详细需求**:
- 支持起始消息ID设置
- 支持结束消息ID设置
- 支持消息ID范围验证

**验收标准**:
- 能够准确按指定ID范围下载
- ID范围验证机制完善
- 支持边界条件处理

### FR-005: Pyrogram官方多客户端并发管理
**优先级**: P0 (最高)
**描述**: 使用Pyrogram官方的compose()方法实现多客户端并发下载管理
**详细需求**:
- **使用pyrogram.compose()方法**：官方推荐的多客户端管理方案
- **支持3-5个并发客户端**：每个客户端使用独立会话文件
- **会话隔离原则**：每个客户端必须使用独立的会话文件或会话字符串
- **智能任务分配算法**：在多个客户端间均衡分配下载任务
- **客户端故障自动切换**：单个客户端故障时自动切换到其他可用客户端

**技术实现要求**:
```python
# 使用官方compose()方法的标准实现
import asyncio
from pyrogram import Client, compose

async def main():
    clients = [
        Client("session_client_0", api_id=API_ID, api_hash=API_HASH, proxy=proxy_config),
        Client("session_client_1", api_id=API_ID, api_hash=API_HASH, proxy=proxy_config),
        Client("session_client_2", api_id=API_ID, api_hash=API_HASH, proxy=proxy_config),
    ]
    
    # 使用compose()方法并发运行多个客户端
    await compose(clients)

asyncio.run(main())
```

**验收标准**:
- 必须使用pyrogram.compose()方法管理多客户端
- 并发下载速度明显优于单客户端
- 客户端负载均衡合理
- 支持客户端动态扩缩容
- 会话文件完全隔离，无共享会话问题

### FR-006: 大文件分片下载
**优先级**: P1 (高)
**描述**: 对大文件进行分片下载，提高下载效率和稳定性
**详细需求**:
- 自动识别大文件 (>50MB)
- 分片大小可配置 (默认1MB)
- 分片并行下载
- 分片完整性验证

**验收标准**:
- 大文件下载成功率>95%
- 分片下载速度优于整体下载
- 支持分片重试机制

### FR-007: 非阻塞式下载
**优先级**: P1 (高)
**描述**: 媒体组中小文件不阻塞大文件下载，实现高效并发
**详细需求**:
- 任务优先级队列管理
- 小文件快速通道
- 大文件后台下载
- 资源调度优化

**验收标准**:
- 小文件下载延迟<5秒
- 大文件下载不阻塞小文件
- 相比单客户端下载，整体下载效率提升30%以上

### FR-008: SOCKS5代理支持
**优先级**: P2 (中)
**描述**: 支持SOCKS5代理连接，满足网络环境需求
**详细需求**:
- 支持SOCKS5代理配置
- 代理地址: 127.0.0.1:7890
- 代理连接状态检测
- 代理故障自动重连

**验收标准**:
- 代理连接成功率>98%
- 支持代理配置验证
- 代理异常处理完善

---

## 🏗️ 代码质量需求 (Code Quality Requirements)

### CQ-001: 模块化设计
**描述**: 系统采用模块化架构，功能模块分离，降低耦合度
**具体要求**:
- 客户端管理模块独立
- 下载器模块独立
- 任务管理模块独立
- 工具模块独立
- 模块间接口清晰

### CQ-002: 单一职责原则
**描述**: 每个类和函数只负责一个明确的功能
**具体要求**:
- 类职责单一明确
- 函数功能原子化
- 避免上帝类和万能函数
- 代码复用性良好

### CQ-003: 文件组织合理
**描述**: 项目目录结构清晰，文件分类合理
**具体要求**:
- 按功能模块组织目录
- 文件命名规范统一
- 配置文件独立管理
- 资源文件分类存储

### CQ-004: 各文件功能单一明确
**描述**: 每个文件只包含相关功能，避免功能混杂
**具体要求**:
- 一个文件对应一个主要功能
- 相关工具函数可以归类
- 避免跨域功能混合
- 文件大小适中 (<500行)

---

## 🧪 测试需求 (Testing Requirements)

### TR-001: 单元测试覆盖率
**优先级**: P0 (最高)
**描述**: 所有代码文件和函数都必须有对应的单元测试
**详细要求**:

#### TR-001-1: 测试覆盖率指标
- **代码覆盖率**: ≥90%
- **分支覆盖率**: ≥85%  
- **函数覆盖率**: 100%
- **文件覆盖率**: 100%

#### TR-001-2: 文件级测试要求
- 每个.py文件都必须有对应的test_*.py测试文件
- 测试文件命名规范: `test_[原文件名].py`
- 测试文件位置: `/tests/` 目录下，保持与源码相同的目录结构

#### TR-001-3: 函数级测试要求
- 每个函数都必须有对应的测试函数
- 测试函数命名规范: `test_[原函数名]_[测试场景]`
- 每个函数至少包含以下测试场景:
  - 正常输入测试
  - 边界条件测试  
  - 异常输入测试
  - 空值/None测试

### TR-002: 测试文件组织结构
**描述**: 测试文件必须按照源码结构组织，便于管理和维护

#### TR-002-1: 目录结构要求
```
tests/
├── test_client/
│   ├── test_client_pool.py
│   ├── test_client_manager.py
│   └── test_client_factory.py
├── test_downloader/
│   ├── test_media_downloader.py
│   ├── test_chunk_downloader.py
│   └── test_group_downloader.py
├── test_task/
│   ├── test_task_manager.py
│   └── test_task_queue.py
├── test_utils/
│   ├── test_logger.py
│   ├── test_config.py
│   └── test_exceptions.py
├── fixtures/           # 测试数据和模拟文件
├── mocks/             # Mock对象和模拟服务
└── conftest.py        # pytest配置文件
```

**对应源码结构**:
```
src/
├── client/
│   ├── client_pool.py      # 客户端池管理
│   ├── client_manager.py   # 单客户端管理
│   └── client_factory.py   # 客户端工厂类
├── downloader/
│   ├── media_downloader.py # 媒体下载器
│   ├── chunk_downloader.py # 分片下载器
│   └── group_downloader.py # 媒体组下载器
├── task/
│   ├── task_manager.py     # 任务管理器
│   └── task_queue.py       # 任务队列
└── utils/
    ├── logger.py           # 日志管理
    ├── config.py           # 配置管理
    └── exceptions.py       # 异常处理
```

### TR-003: 具体测试类型要求

#### TR-003-1: 客户端管理模块测试
**文件**: `client/client_pool.py`
**测试需求**:
- `test_create_client_pool()` - 客户端池创建
- `test_get_available_client()` - 获取可用客户端
- `test_release_client()` - 释放客户端
- `test_client_pool_capacity()` - 客户端池容量管理
- `test_client_failure_handling()` - 客户端故障处理
- `test_concurrent_client_access()` - 并发客户端访问

**文件**: `client/client_manager.py`
**测试需求**:
- `test_initialize_client()` - 客户端初始化
- `test_client_authentication()` - 客户端认证
- `test_proxy_configuration()` - 代理配置
- `test_client_connection_status()` - 连接状态检测
- `test_client_session_management()` - 会话管理

**文件**: `client/client_factory.py`
**测试需求**:
- `test_create_client_instance()` - 创建客户端实例
- `test_client_configuration_application()` - 客户端配置应用
- `test_multiple_client_creation()` - 多客户端创建
- `test_client_type_selection()` - 客户端类型选择
- `test_factory_parameter_validation()` - 工厂参数验证

#### TR-003-2: 下载器模块测试
**文件**: `downloader/media_downloader.py`
**测试需求**:
- `test_download_single_media()` - 单媒体文件下载
- `test_download_different_media_types()` - 不同媒体类型下载
- `test_download_with_custom_filename()` - 自定义文件名下载
- `test_download_progress_callback()` - 下载进度回调
- `test_download_failure_retry()` - 下载失败重试
- `test_download_large_file()` - 大文件下载

**文件**: `downloader/chunk_downloader.py`
**测试需求**:
- `test_split_file_chunks()` - 文件分片切割
- `test_download_chunk_parallel()` - 并行分片下载
- `test_merge_chunks()` - 分片合并
- `test_chunk_integrity_verification()` - 分片完整性验证
- `test_chunk_download_retry()` - 分片下载重试

**文件**: `downloader/group_downloader.py`
**测试需求**:
- `test_identify_media_group()` - 媒体组识别
- `test_download_complete_group()` - 完整媒体组下载
- `test_group_file_organization()` - 媒体组文件组织
- `test_mixed_media_group()` - 混合媒体组处理

#### TR-003-3: 任务管理模块测试
**文件**: `task/task_manager.py`
**测试需求**:
- `test_create_download_task()` - 创建下载任务
- `test_task_priority_handling()` - 任务优先级处理
- `test_task_scheduling()` - 任务调度
- `test_task_status_tracking()` - 任务状态跟踪
- `test_failed_task_handling()` - 失败任务处理
- `test_concurrent_task_execution()` - 并发任务执行

**文件**: `task/task_queue.py`
**测试需求**:
- `test_enqueue_task()` - 任务入队
- `test_dequeue_task()` - 任务出队
- `test_queue_priority_order()` - 队列优先级排序
- `test_queue_capacity_management()` - 队列容量管理
- `test_queue_thread_safety()` - 队列线程安全

#### TR-003-4: 工具模块测试
**文件**: `utils/logger.py`
**测试需求**:
- `test_logger_initialization()` - 日志器初始化
- `test_log_different_levels()` - 不同级别日志
- `test_log_file_rotation()` - 日志文件轮转
- `test_log_format_validation()` - 日志格式验证

**文件**: `utils/config.py`
**测试需求**:
- `test_load_config_file()` - 配置文件加载
- `test_config_validation()` - 配置验证
- `test_default_config_values()` - 默认配置值
- `test_config_environment_override()` - 环境变量覆盖

**文件**: `utils/exceptions.py`
**测试需求**:
- `test_custom_exception_creation()` - 自定义异常创建
- `test_exception_message_formatting()` - 异常消息格式化
- `test_exception_inheritance()` - 异常继承关系

### TR-004: 集成测试要求
**描述**: 测试各模块间的集成和协作

#### TR-004-1: 端到端测试
- `test_complete_download_workflow()` - 完整下载流程测试
- `test_multi_client_integration()` - 多客户端集成测试
- `test_large_scale_download()` - 大规模下载测试
- `test_error_recovery_integration()` - 错误恢复集成测试

#### TR-004-2: 性能测试
- `test_download_speed_performance()` - 下载速度性能测试
- `test_concurrent_performance()` - 并发性能测试
- `test_memory_usage_test()` - 内存使用测试
- `test_resource_cleanup()` - 资源清理测试

### TR-005: Mock和测试数据要求
**描述**: 提供完善的Mock对象和测试数据支持

#### TR-005-1: Mock对象要求
- **Pyrogram Client Mock**: 模拟Telegram客户端
- **Media Message Mock**: 模拟媒体消息对象
- **Download Progress Mock**: 模拟下载进度
- **Network Exception Mock**: 模拟网络异常

#### TR-005-2: 测试数据要求
- **样本媒体文件**: 不同类型和大小的测试媒体文件
- **测试消息数据**: JSON格式的测试消息数据
- **配置文件样本**: 各种配置场景的配置文件
- **日志文件样本**: 用于日志解析测试的样本文件

### TR-006: 测试工具和框架
**描述**: 指定测试工具链和测试框架

#### TR-006-1: 测试框架
- **主测试框架**: pytest
- **覆盖率工具**: pytest-cov
- **Mock框架**: unittest.mock / pytest-mock
- **异步测试**: pytest-asyncio

#### TR-006-2: 测试命令
```bash
# 运行所有测试
pytest tests/

# 运行测试并生成覆盖率报告
pytest tests/ --cov=src --cov-report=html --cov-report=term

# 运行特定模块测试
pytest tests/test_client/

# 运行特定测试函数
pytest tests/test_client/test_client_pool.py::test_create_client_pool
```

### TR-007: 测试持续集成要求
**描述**: 测试必须集成到开发流程中

#### TR-007-1: 自动化测试
- 代码提交前必须通过所有测试
- 测试覆盖率不得低于设定标准
- 性能测试回归检查
- 集成测试自动化执行

#### TR-007-2: 测试报告
- 生成详细的测试报告
- 覆盖率报告可视化
- 失败测试详细日志
- 性能测试趋势分析

---

## 📋 验收标准总结

### 功能验收标准
1. **所有P0优先级功能**必须100%实现并通过测试
2. **所有P1优先级功能**必须90%以上实现并通过测试
3. **下载成功率**不低于95%
4. **相比单客户端下载，并发性能提升30%以上**
5. **必须使用pyrogram.compose()方法**管理多客户端

### 代码质量验收标准
1. **代码覆盖率**≥90%
2. **函数覆盖率**100%
3. **所有函数**都有对应测试
4. **所有文件**都有测试文件
5. **模块化程度**符合设计要求

### 测试验收标准
1. **单元测试**覆盖所有函数
2. **集成测试**覆盖主要流程
3. **性能测试**满足指标要求
4. **错误测试**覆盖异常场景
5. **测试文档**完整清晰

---

## 📅 开发里程碑

### 阶段一: 核心架构和基础功能 (Week 1-2)
- 搭建项目基础架构
- 实现客户端管理模块(使用compose()方法)
- 实现基础下载功能
- **对应测试**: 客户端模块测试、基础下载测试

### 阶段二: 高级功能实现 (Week 3-4)
- 实现媒体组下载
- 实现分片下载
- 实现任务管理
- **对应测试**: 媒体组测试、分片下载测试、任务管理测试

### 阶段三: 性能优化和测试完善 (Week 5-6)
- 并发性能优化
- 错误处理完善
- 测试覆盖率达标
- **对应测试**: 性能测试、集成测试、错误场景测试

### 阶段四: 文档和发布准备 (Week 7)
- 完善项目文档
- 最终测试验收
- 部署和发布准备

---

**文档版本**: v1.1  
**最后更新**: 2024年12月  
**文档状态**: 已更新compose()方法要求

## 技术架构

### 核心文件结构
```
src/
├── client_factory.py          # 客户端工厂类，管理多客户端创建
├── downloader.py              # 下载器核心功能
├── message_handler.py         # 消息获取和处理
├── media_processor.py         # 媒体文件处理
├── config.py                  # 配置管理
├── utils.py                   # 工具函数
└── main.py                    # 主程序入口
```

### Pyrogram多会话最佳实践

**官方compose()方法使用**
- 使用`pyrogram.compose()`方法管理多客户端并发运行
- 支持并发(concurrent)和顺序(sequential)两种运行模式
- 默认并发模式，提供最佳性能

**会话隔离原则**
- 每个客户端必须使用独立的会话文件或会话字符串
- 会话文件存储在独立的工作目录中
- 禁止多个客户端共享同一会话

**客户端配置规范**
```python
# 正确的多客户端创建方式
clients = [
    Client("session_client_0", api_id, api_hash, proxy=proxy_config),
    Client("session_client_1", api_id, api_hash, proxy=proxy_config),
    Client("session_client_2", api_id, api_hash, proxy=proxy_config),
]

# 使用compose()方法并发运行
await compose(clients)
```

**性能优化配置**
- 设置合适的`max_concurrent_transmissions`值(默认1)
- 合理配置`sleep_threshold`处理频率限制
- 使用`no_updates=True`禁用更新接收(下载专用)

**异常处理策略**
- 捕获并处理`FloodWait`异常，实现自动等待重试
- 处理`FLOOD_PREMIUM_WAIT`通知性异常，不中断下载
- 实现网络异常重连机制

## 性能指标
- 支持1000条消息稳定下载，成功率≥95%
- 相比单客户端下载提升30%以上的下载速度
- 支持GB级大文件下载，内存占用≤500MB
- 网络异常自动重试，重试间隔1-30秒指数退避