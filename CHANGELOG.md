# 更新日志

本文件记录了项目的所有重要变更和版本发布信息。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.4.0] - 2025-08-06 (性能优化 ✅)

### 新增 - 并发转发工作流优化

- ✅ **并发转发工作流** (`main.py`)

  - 重构 `_execute_forward_workflow()` 方法，实现多客户端并发转发
  - 复用下载模式的智能任务分配算法，支持媒体组感知分配
  - 新增 `_forward_client_messages()` 方法，处理单客户端转发任务
  - 新增 `_summarize_forward_results()` 方法，汇总多客户端转发结果
  - 使用 `asyncio.gather()` 实现真正的并发执行

- ✅ **性能提升**

  - 转发模式现在使用 3 个客户端并发工作，而非之前的单客户端串行
  - 下载阶段：3 客户端并行下载不同文件
  - 上传阶段：3 客户端并行上传到目标频道
  - 预期性能提升：2-3 倍吞吐量（理论上接近 3 倍）

- ✅ **架构统一**

  - 转发模式和下载模式现在使用相同的任务分配策略
  - 保持媒体组完整性，智能负载均衡
  - 统一的错误处理和统计收集机制

- ✅ **测试支持**

  - 新增 `test_concurrent_forward.py` 测试脚本
  - 验证并发转发功能的正确性和性能
  - 提供详细的性能报告和统计信息

### 改进

- 优化转发工作流的客户端利用率，从 33% 提升到 100%
- 改进日志输出，增加客户端标识和详细进度信息
- 更新函数索引文档，记录新增的并发转发方法

### 修复

- ✅ **修复数据库关闭错误** (`utils/async_context_manager.py`, `core/client/client_manager.py`, `main.py`)

  - 修复程序结束时的 `Cannot operate on a closed database` 错误
  - 新增 `SafeClientManager` 类，提供安全的客户端停止机制
  - 新增 `AsyncTaskCleaner` 类，优雅处理剩余异步任务
  - 改进客户端停止逻辑，避免 Pyrogram 后台任务的数据库操作冲突
  - 添加错误抑制机制，过滤预期的清理错误
  - 实现超时机制和强制清理，确保程序能正常退出

- ✅ **修复大文件上传策略** (`core/upload/upload_strategy.py`)

  - 移除大文件自动降级为文档的逻辑
  - 保持原始媒体类型进行上传：图片用 `send_photo`，视频用 `send_video`
  - 让 Telegram 服务器处理文件大小限制，而非客户端预判
  - 确保转发的媒体保持原始格式和显示效果

- ✅ **修复转发模式 Caption 缺失问题** (`main.py`)

  - 修复默认转发模板中缺少 `{original_caption}` 变量的问题
  - 原模板：`{original_text}` → 新模板：`{original_text}{original_caption}`
  - 确保转发的媒体文件正确显示原始说明文字
  - 支持纯文本、纯 Caption、混合内容等各种情况

### 性能对比

| 模式              | 客户端使用 | 并发类型 | 预期性能       |
| ----------------- | ---------- | -------- | -------------- |
| **下载模式**      | 3 个客户端 | ✅ 并行  | 基准性能       |
| **转发模式 (旧)** | 1 个客户端 | ❌ 串行  | ~33% 基准性能  |
| **转发模式 (新)** | 3 个客户端 | ✅ 并行  | ~100% 基准性能 |

## [1.3.0] - 2025-08-04 (Phase 3 完成 ✅)

### 新增 - Phase 3: 上传功能完成

- ✅ **UploadTask 数据模型** (`models/upload_task.py`)

  - 完整的上传任务管理，支持多种上传状态和类型
  - 实时进度跟踪和速度计算
  - 完整的序列化/反序列化支持
  - 支持重试机制和错误处理

- ✅ **UploadManager 上传管理器** (`core/upload/upload_manager.py`)

  - 智能文件上传，支持图片、视频、音频、文档等多种类型
  - 根据文件类型自动选择最佳上传方式
  - 完整的错误处理和重试机制
  - 权限检查和验证功能

- ✅ **BatchUploader 批量上传器** (`core/upload/batch_uploader.py`)

  - 可配置的最大并发数控制
  - 批量进度管理和统计
  - 多频道上传支持
  - 上传摘要和统计功能

- ✅ **UploadStrategy 上传策略** (`core/upload/upload_strategy.py`)

  - 智能文件类型识别和上传方法选择
  - 文件大小和格式验证
  - 上传时间估算
  - 完整的任务验证

- ✅ **WorkflowConfig 工作流配置** (`models/workflow_config.py`)

  - 本地下载和转发两种工作流支持
  - 文件过滤和调度功能
  - 模板系统集成
  - 完整的配置管理和验证

- ✅ **多频道目标设置**: 灵活的频道管理
  - 支持公开频道(@channel)和私有频道 ID 格式
  - 按文件类型分类上传到不同频道
  - 动态频道选择和验证
  - 频道格式验证功能

### 测试

- **完整功能测试通过**: 100% 成功率 (6/6)
- 多频道上传验证，支持 5 个不同目标频道
- 智能策略选择测试，正确识别文件类型
- 目标频道设置验证，支持 8 个分类上传任务

## [1.2.0] - 2025-08-04 (Phase 2 完成 ✅)

### 新增 - Phase 2: 模板系统完成

- ✅ **TemplateConfig 数据模型** (`models/template_config.py`)

  - 完整的模板配置管理，支持原格式和自定义模板
  - 变量定义和验证系统
  - 完整的序列化/反序列化支持
  - 10 个内置变量支持

- ✅ **TemplateEngine 模板引擎** (`core/template/template_engine.py`)

  - 核心模板处理，支持变量替换和内容生成
  - 模板验证和预览功能
  - 变量提取和验证
  - 模板统计功能

- ✅ **VariableExtractor 变量提取器** (`core/template/variable_extractor.py`)

  - 智能内容分析，自动识别话题标签、用户提及、URL 等
  - 支持自定义正则表达式模式
  - 变量建议功能
  - 正则表达式测试功能

- ✅ **TemplateProcessor 模板处理器** (`core/template/template_processor.py`)

  - 完整的模板处理流程，集成引擎和提取器
  - 批量处理支持
  - 错误处理和回退机制
  - 模板统计和验证

- ✅ **MessageUtils 消息工具** (`utils/message_utils.py`)
  - 统一消息处理，消除代码重复
  - 统一的文件信息提取
  - 下载结果创建工具
  - 提高模块化程度

### 改进

- 重构下载器，移除重复代码，提高模块化
- 更新核心模块导入，支持模板功能
- 完善项目文档和函数索引

### 测试

- **完整功能测试通过**: 100% 成功率 (4/4)
- 19 个变量自动提取验证
- 完整模板渲染测试，生成美观格式化内容

## [1.1.0-dev] - 2024-08-04 (Phase 1 完成 ✅)

### 新增 - Phase 1 基础功能扩展完成

- 📄 创建项目 README.md 文档
- 📄 创建版本更新日志 CHANGELOG.md
- 📋 制定 Phase 1-4 开发计划
- 🏗️ 设计上传模块整体架构

### 新增 - Phase 1 基础功能扩展

- ✅ **DownloadResult 数据模型** (`models/download_result.py`)

  - 统一的下载结果格式，支持本地和内存两种模式
  - 包含文件信息、元数据、原始消息内容
  - 支持序列化和反序列化
  - 提供便捷的工厂方法和验证功能

- ✅ **正确的内存下载实现** (基于现有下载器扩展)

  - 扩展 `RawDownloader` 支持内存下载 (`download_to_memory()`)
  - 扩展 `StreamDownloader` 支持内存下载 (`download_to_memory()`)
  - 保持现有的智能选择逻辑：<50MB 非视频用 RAW API，其他用 Stream
  - 修复 RAW API OFFSET_INVALID 错误：确保 InputDocumentFileLocation 参数完全一致
  - 完全兼容现有架构，无需额外的独立下载器

- ✅ **扩展 DownloadManager** (`core/download/download_manager.py`)

  - 新增 `download_media_enhanced()` 方法
  - 支持本地和内存两种下载模式
  - 统一返回 DownloadResult 对象
  - 扩展下载统计功能

- ✅ **测试框架** (`test_memory_download.py`, `simple_test.py`)
  - 验证数据模型功能
  - 测试内存下载器
  - 测试扩展的下载管理器
  - 提供详细的测试报告
  - **完整功能测试通过**: 100% 成功率，RAW API 和 Stream 都能正常进行内存下载

### 计划新增 (Phase 2)

- 📋 模板系统 - 支持原格式和自定义模板
- 📋 变量提取和替换功能
- 📋 模板配置管理

### 计划新增 (Phase 3)

- 📋 上传管理器 - 支持转发到目标频道
- 📋 批量上传功能
- 📋 上传进度监控

### 计划新增 (Phase 4)

- 📋 Web API 接口
- 📋 配置外部化
- 📋 Web 管理界面

## [1.0.0] - 2024-01-XX (基线版本)

### 新增

- ✅ **多客户端管理系统**

  - 支持多个 Telegram 账号并发操作
  - 自动会话验证和管理
  - 智能故障恢复和重连机制

- ✅ **智能下载系统**

  - 流式下载器 (StreamDownloader) - 适用于大文件 (>50MB)
  - RAW API 下载器 (RawDownloader) - 适用于小文件 (<50MB)
  - 自动下载策略选择
  - 文件完整性验证

- ✅ **消息处理系统**

  - 并发消息获取 (MessageFetcher)
  - 媒体组智能分组 (MessageGrouper)
  - 消息验证和统计 (MessageProcessor)

- ✅ **任务分配系统**

  - 智能任务分配器 (TaskDistributor)
  - 多种分配策略支持
  - 负载均衡和性能优化

- ✅ **监控统计系统**

  - 实时带宽监控 (BandwidthMonitor)
  - 下载统计收集 (StatsCollector)
  - 详细日志记录

- ✅ **配置管理系统**

  - 统一配置管理 (AppConfig)
  - Telegram API 配置
  - 下载和监控配置
  - 代理和网络配置

- ✅ **工具和脚本**
  - 会话文件生成器 (create_client_session.py)
  - 网络工具 (NetworkUtils)
  - 文件操作工具 (FileUtils)
  - 频道工具 (ChannelUtils)

### 技术特性

- 🔧 基于 Pyrogram 2.0.106+
- 🔧 支持 TgCrypto 加密优化
- 🔧 异步并发处理
- 🔧 模块化架构设计
- 🔧 完整的错误处理和日志系统

### 配置信息

- ✅ API ID 和 API Hash 已配置
- ✅ 代理设置 (127.0.0.1:7890) 已配置
- ✅ 默认会话文件已准备
- ✅ 默认频道 (@csdkl) 已配置
- ✅ 消息范围 (72710-72849) 已配置

### 文档

- 📚 完整的函数索引文档 (FUNCTION_INDEX.md)
- 📚 MVP 开发计划 (docs/MVP_DEVELOPMENT_PLAN.md)
- 📚 脚本使用说明 (scripts/README.md)

---

## 版本说明

### 版本号格式

- **主版本号**: 重大功能变更或架构调整
- **次版本号**: 新功能添加
- **修订号**: 问题修复和小改进
- **开发标识**: `-dev` 表示开发版本

### 变更类型

- **新增**: 新功能
- **变更**: 对现有功能的变更
- **弃用**: 即将移除的功能
- **移除**: 已移除的功能
- **修复**: 问题修复
- **安全**: 安全相关的修复

### 开发阶段

- **Phase 1**: ✅ 基础功能扩展 (内存下载、数据模型) - v1.1.0
- **Phase 2**: ✅ 模板系统 (模板引擎、变量处理) - v1.2.0
- **Phase 3**: ✅ 上传功能 (上传管理、批量处理) - v1.3.0
- **Phase 4**: 📋 网页版准备 (API 接口、Web 界面) - 计划中
