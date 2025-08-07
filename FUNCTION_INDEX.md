# 项目函数索引文档

## 📋 概述

本文档提供了多客户端 Telegram 下载器项目中所有 Python 文件的函数索引，包括每个函数的功能描述、参数和返回值。

### 🎯 项目完成状态

- ✅ **Phase 1**: 内存下载功能 (v1.1.0)
- ✅ **Phase 2**: 模板系统 (v1.2.0)
- ✅ **Phase 3**: 上传功能 (v1.3.0)
- 📋 **Phase 4**: 网页版准备 (计划中)

### 📊 模块统计

- **核心模块**: 下载、模板、上传、消息处理、客户端管理
- **数据模型**: DownloadResult、TemplateConfig、UploadTask、WorkflowConfig
- **工具模块**: 消息处理、文件操作、网络工具、日志系统
- **总计函数**: 200+ 个函数和方法

## 📚 函数目录

### 🎯 主程序模块

- [main.py](#-mainpy) - 主程序入口和多客户端下载器
  - `MultiClientDownloader` 类
    - `__init__()`, `run_download()`, `_start_monitoring()`, `_initialize_clients()`
    - `_fetch_messages()`, `_distribute_tasks()`, `_execute_downloads()`
    - `_execute_forward_workflow()` - ✅ **统一使用分阶段转发**
    - `_execute_staged_forward_workflow()` - ✅ **分阶段转发工作流（默认）**
    - `_staged_forward_client_messages()` - ✅ **分阶段单客户端转发任务**
    - `_summarize_staged_forward_results()` - ✅ **分阶段转发结果汇总**
    - `_print_final_results()`, `_cleanup()`, `log_info()`, `log_error()`
  - `create_workflow_config_from_args()` - ✅ **分阶段上传配置**
  - `_initialize_account_info()` - ✅ **新增：初始化账户信息**
  - `main()` 函数

### ⚙️ 配置模块

- [config/settings.py](#-configsettingspy) - 统一配置管理

  - `TelegramConfig` 类: `__post_init__()`
  - `DownloadConfig` 类
  - `MonitoringConfig` 类
  - `AppConfig` 类: `__post_init__()`

- [config/constants.py](#-configconstantspy) - 常量定义

### 📊 数据模型

- [models/download_result.py](#-modelsdownload_resultpy) - 下载结果数据模型
  - `DownloadResult` 类
    - `__init__()`, `__post_init__()`, `_calculate_hash()`, `get_data()`
    - `get_size_mb()`, `get_size_formatted()`, `is_valid()`, `get_content_text()`
    - `has_media_group()`, `to_dict()`, `from_dict()`
    - `create_local_result()`, `create_memory_result()`, `__str__()`, `__repr__()`

### 🔧 核心业务模块

#### 客户端管理

- [core/client/client_manager.py](#-coreclientclient_managerpy) - 客户端管理器

  - `ClientManager` 类
    - `__init__()`, `initialize_clients()`, `_create_client()`
    - `start_all_clients()`, `_start_single_client()`, `stop_all_clients()`
    - `get_client_info()`, `get_clients()`, `get_client_names()`, `get_client_by_name()`

- [core/client/session_manager.py](#-coreclientsession_managerpy) - 会话管理器
  - `SessionManager` 类
    - `__init__()`, `get_available_sessions()`, `cleanup_invalid_sessions()`

#### 消息处理

- [core/message/fetcher.py](#-coremessagefetcherpy) - 消息获取器

  - `MessageFetcher` 类
    - `__init__()`, `parallel_fetch_messages()`, `fetch_message_range()`

- [core/message/grouper.py](#-coremessagegrouperpy) - 消息分组器

  - `MessageGrouper` 类
    - `__init__()`, `group_messages_from_list()`, `_group_messages()`
  - `is_media_group_message()` 函数

- [core/message/processor.py](#-coremessageprocessorpy) - 消息处理器
  - `MessageProcessor` 类
    - `__init__()`, `validate_messages()`, `get_message_statistics()`
    - `_is_valid_message()`, `_get_message_type()`

#### 下载处理

- [core/download/base.py](#-coredownloadbasepy) - 下载器基类

  - `BaseDownloader` 类 (抽象基类)
    - `__init__()`, `download()` (抽象方法)
    - `get_channel_directory()`, `generate_file_path()`

- [core/download/raw_downloader.py](#-coredownloadraw_downloaderpy) - RAW API 下载器

  - `RawDownloader` 类
    - `download()`

- [core/download/stream_downloader.py](#-coredownloadstream_downloaderpy) - 流式下载器

  - `StreamDownloader` 类
    - `download()`

- [core/download/memory_downloader.py](#-coredownloadmemory_downloaderpy) - 内存下载器

  - `MemoryDownloader` 类
    - `__init__()`, `download()`, `_download_to_memory()`, `_read_temp_file()`
    - `_download_via_temp_file()`, `_get_file_info()`, `get_download_stats()`

- [core/download/download_manager.py](#-coredownloaddownload_managerpy) - 下载管理器
  - `DownloadManager` 类
    - `__init__()`, `download_media()`, `download_media_enhanced()`, `batch_download()`
    - `get_download_stats()`, `reset_stats()`, `get_channel_directory()`

#### 任务分配

- [core/task_distribution/base.py](#-coretask_distributionbasepy) - 任务分配策略基类

  - `TaskDistributionStrategy` 类 (抽象基类)
    - `__init__()`, `distribute_tasks()` (抽象方法), `get_strategy_info()` (抽象方法)
  - `DistributionMode` 枚举, `LoadBalanceMetric` 枚举, `DistributionConfig` 数据类

- [core/task_distribution/distributor.py](#-coretask_distributiondistributorpy) - 任务分配器

  - `TaskDistributor` 类
    - `__init__()`, `distribute_tasks()`, `_get_strategy()`, `_update_stats()`

- [core/task_distribution/strategies.py](#-coretask_distributionstrategiespy) - 具体分配策略
  - `MediaGroupAwareDistributionStrategy` 类
    - `distribute_tasks()`, `_find_min_load_client()`, `get_strategy_info()`

### 🛠️ 工具模块

- [utils/file_utils.py](#-utilsfile_utilspy) - 文件操作工具

  - `FileUtils` 类
    - `sanitize_filename()`, `generate_filename_by_type()`, `get_file_size_bytes()`
    - `get_file_size_mb()` (静态方法)

- [utils/network_utils.py](#-utilsnetwork_utilspy) - 网络工具

  - `NetworkUtils` 类
    - `create_proxy_config()`, `get_network_stats()`, `calculate_bandwidth()` (静态方法)
  - `BandwidthMonitor` 类
    - `__init__()`, `start_monitoring()`, `stop_monitoring()`

- [utils/channel_utils.py](#-utilschannel_utilspy) - 频道工具

  - `ChannelUtils` 类
    - `get_channel_info()`, `sanitize_folder_name()` (静态方法)

- [utils/message_utils.py](#-utilsmessage_utilspy) - 消息处理工具

  - `MessageUtils` 类
    - `get_file_info()`, `create_memory_download_result()`, `create_local_download_result()`
    - `get_media_type()`, `has_media()`, `get_content_preview()`

- [utils/logging_utils.py](#-utilslogging_utilspy) - 日志工具

  - `setup_logging()` 函数
  - `get_logger()` 函数

- [utils/account_info.py](#-utilsaccount_infopy) - ✅ **新增：账户信息管理**

  - `AccountInfo` 类 - ✅ **新增：账户信息数据类**
    - `display_name`, `caption_limit` 属性
    - `to_dict()` 方法
  - `AccountInfoManager` 类 - ✅ **新增：账户信息管理器**
    - `get_account_info()` - 获取单个客户端账户信息
    - `get_all_accounts_info()` - 获取所有客户端账户信息
    - `is_premium_user()` - 检查 Premium 状态
    - `get_caption_limit()` - 获取 Caption 长度限制
    - `log_accounts_summary()` - 显示账户摘要

- [utils/async_context_manager.py](#-utilsasync_context_managerpy) - ✅ **新增异步上下文管理器**
  - `SafeClientManager` 类 - 安全的客户端管理器
    - `safe_stop_all()`, `_safe_stop_client()`, `_force_cleanup()`, `_wait_for_background_tasks()`
  - `managed_clients()` - 异步上下文管理器
  - `suppress_pyrogram_errors()` - 抑制 Pyrogram 清理错误
  - `AsyncTaskCleaner` 类 - 异步任务清理器
    - `cancel_remaining_tasks()`, `graceful_shutdown()`

## 📤 上传模块 (Phase 3)

- [models/upload_task.py](#-modelsupload_taskpy) - 上传任务数据模型

  - `UploadTask` 类 - 上传任务管理
    - `start_upload()`, `complete_upload()`, `fail_upload()`, `cancel_upload()`
    - `can_retry()`, `increment_retry()`, `get_duration()`
    - `to_dict()`, `from_dict()` - 序列化支持
  - `UploadProgress` 类 - 进度跟踪
    - `update_progress()` - 更新进度信息
  - `BatchUploadResult` 类 - 批量上传结果
    - `get_success_rate()`, `get_duration()`, `is_completed()`

- [models/workflow_config.py](#-modelsworkflow_configpy) - 工作流配置

  - `WorkflowConfig` 类 - 工作流管理
    - `is_local_download()`, `is_forward()`, `get_message_count()`
    - `should_filter_file_type()`, `should_filter_file_size()`
    - `get_subfolder_name()`, `get_estimated_duration()`
    - `to_dict()`, `from_dict()`, `clone()` - 配置管理

- [core/upload/upload_strategy.py](#-coreuploadupload_strategypy) - 上传策略

  - `UploadStrategy` 类
    - `determine_upload_type()`, `get_upload_config()`
    - `get_size_category()`, `estimate_upload_time()`
    - `should_compress()`, `validate_upload_task()`
    - `_get_photo_upload_config()` - ✅ **修改：保持原始图片格式**
    - `_get_video_upload_config()` - ✅ **修改：保持原始视频格式**

- [core/upload/upload_manager.py](#-coreuploadupload_managerpy) - 上传管理器

  - `UploadManager` 类
    - `upload_task()`, `retry_failed_task()`
    - `get_upload_stats()`, `reset_stats()`
    - `test_upload_permissions()` - 权限检查

- [core/upload/batch_uploader.py](#-coreuploadbatch_uploaderpy) - 批量上传器
  - `BatchUploader` 类
    - `upload_batch()`, `upload_with_retry()`
    - `upload_to_multiple_channels()` - 多频道上传
    - `get_active_uploads()`, `get_upload_progress()`
    - `create_upload_summary()` - 上传摘要

### 🆕 分阶段上传模块 (v1.5.0)

- [core/upload/staged/data_source.py](#-coreuploadstageddata_sourcepy) - 数据源抽象层

  - `MediaType` 枚举 - 媒体类型定义
  - `MediaData` 类 - 媒体数据模型
    - `get_display_name()` - 获取显示名称
  - `DataSource` 抽象类 - 数据源接口
    - `get_media_data()`, `validate_source_item()` - 抽象方法
  - `TelegramDataSource` 类 - Telegram 数据源实现
    - `get_media_data()`, `validate_source_item()`
    - `_determine_media_type()`, `_get_media_dimensions()` - 私有方法

- [core/upload/staged/temporary_storage.py](#-coreuploadstagedtemporary_storagepy) - 临时存储抽象层

  - `TemporaryMediaItem` 类 - 临时媒体项
    - `get_age_seconds()` - 获取存储时长
  - `TemporaryStorage` 抽象类 - 临时存储接口
    - `store_media()`, `cleanup_media()`, `cleanup_batch()` - 抽象方法
  - `TelegramMeStorage` 类 - me 聊天临时存储实现
    - `store_media()`, `cleanup_media()`, `cleanup_batch()`
    - `_upload_by_type()` - 根据媒体类型上传

- [core/upload/staged/media_group_manager.py](#-coreuploadstagedmedia_group_managerpy) - 媒体组管理器

  - `MediaGroupType` 枚举 - 媒体组类型
  - `MediaGroupBatch` 类 - 媒体组批次
    - `is_full()`, `can_add_item()`, `get_total_size()` - 批次管理
  - `MediaGroupManager` 类 - 媒体组管理器
    - `add_media_item()`, `get_ready_batches()`, `flush_all_batches()`
    - `create_input_media_group()`, `get_stats()` - 核心功能
    - `_add_to_photo_video_batch()`, `_add_to_document_batch()`, `_add_to_audio_batch()` - 私有方法
    - `_create_input_media()` - InputMedia 对象创建

- [core/upload/staged/target_distributor.py](#-coreuploadstagedtarget_distributorpy) - 目标分发器

  - `ChannelDistributionResult` 类 - 单频道分发结果
  - `DistributionResult` 类 - 分发结果
    - `is_successful()`, `get_success_rate()`, `get_duration()` - 结果分析
  - `TargetDistributor` 类 - 目标分发器
    - `distribute_media_group()`, `distribute_single_media()` - 分发方法
    - `get_stats()` - 统计信息
    - `_distribute_to_single_channel()`, `_distribute_single_to_channel()` - 私有方法

- [core/upload/staged/staged_upload_manager.py](#-coreuploadstagedstaged_upload_managerpy) - 分阶段上传管理器
  - `StagedUploadConfig` 类 - 分阶段上传配置
  - `StagedUploadResult` 类 - 分阶段上传结果
    - `get_success_rate()`, `get_duration()`, `is_successful()` - 结果分析
  - `StagedUploadManager` 类 - 主管理器
    - `upload_with_staging()` - 主要上传方法
    - `get_stats()` - 统计信息
    - `_stage_1_data_acquisition_and_staging()` - 阶段 1：数据获取和临时存储
    - `_stage_2_grouping_and_distribution()` - 阶段 2：媒体组管理和分发
    - `_stage_3_cleanup()` - 阶段 3：清理
    - `_emergency_cleanup()` - 紧急清理

## 🎨 模板模块 (Phase 2)

- [models/template_config.py](#-modelstemplate_configpy) - 模板配置数据模型

  - `TemplateConfig` 类 - 模板配置管理
    - `get_variable_by_name()`, `add_variable()`, `remove_variable()`
    - `set_variable_value()`, `get_variable_value()`
    - `get_required_variables()`, `validate_variables()`
    - `to_dict()`, `from_dict()` - 序列化支持
  - `TemplateVariable` 类 - 变量定义
  - 内置变量和默认模板

- [core/template/template_engine.py](#-coretemplatetemplate_enginepy) - 模板引擎

  - `TemplateEngine` 类
    - `render()` - 模板渲染
    - `extract_variables()`, `validate_template()`
    - `preview_template()`, `get_available_variables()`
    - `create_template_from_content()` - 模板创建

- [core/template/variable_extractor.py](#-coretemplatevariable_extractorpy) - 变量提取器

  - `VariableExtractor` 类
    - `extract_variables()` - 变量提取
    - `suggest_variables()` - 变量建议
    - `test_pattern()` - 正则测试
    - `create_variable_from_suggestion()` - 变量创建

- [core/template/template_processor.py](#-coretemplatetemplate_processorpy) - 模板处理器
  - `TemplateProcessor` 类
    - `process()`, `batch_process()` - 模板处理
    - `preview_template()`, `validate_template()`
    - `suggest_variables()`, `get_template_statistics()`

### 📊 监控模块

- [monitoring/bandwidth_monitor.py](#-monitoringbandwidth_monitorpy) - 带宽监控器

  - `BandwidthMonitor` 类 (线程版本)
    - `__init__()`, `start()`, `stop()`, `get_current_bandwidth()`, `get_status()`
  - `create_simple_bandwidth_monitor()` 函数

- [monitoring/stats_collector.py](#-monitoringstats_collectorpy) - 统计收集器
  - `StatsCollector` 类
    - `__init__()`, `set_total_messages()`, `update_download_progress()`
    - `get_final_report()`

### 📜 脚本模块

- [scripts/create_client_session.py](#-scriptscreate_client_sessionpy) - 会话文件生成器
  - `create_session()` 函数

### 📦 数据模型

- [models/message_group.py](#-modelsmessage_grouppy) - 消息组数据模型
  - `MessageGroup` 类
    - `add_message()`, `is_media_group` (属性), `__len__()`
  - `MessageGroupCollection` 类
    - `add_media_group()`, `add_single_message()`

---

## 📁 main.py

### 类: MultiClientDownloader

#### `__init__(self, config: Optional[AppConfig] = None)`

- **功能**: 初始化多客户端下载器
- **参数**:
  - `config`: 应用配置对象，可选，默认使用 AppConfig()
- **返回值**: None

#### `async run_download(self, channel: Optional[str] = None, start_id: Optional[int] = None, end_id: Optional[int] = None)`

- **功能**: 执行下载任务的主要入口点
- **参数**:
  - `channel`: 目标频道，可选
  - `start_id`: 起始消息 ID，可选
  - `end_id`: 结束消息 ID，可选
- **返回值**: None

#### `async _start_monitoring(self)`

- **功能**: 启动监控系统
- **参数**: 无
- **返回值**: None

#### `async _initialize_clients(self)`

- **功能**: 初始化和启动客户端
- **参数**: 无
- **返回值**: None

#### `async _fetch_messages(self, channel: str, start_id: int, end_id: int) -> List`

- **功能**: 获取指定范围的消息
- **参数**:
  - `channel`: 频道名称
  - `start_id`: 起始消息 ID
  - `end_id`: 结束消息 ID
- **返回值**: 消息列表

#### `async _distribute_tasks(self, messages: List) -> object`

- **功能**: 分组和分配任务到客户端
- **参数**:
  - `messages`: 消息列表
- **返回值**: 任务分配结果对象

#### `async _execute_downloads(self, distribution_result: object, channel: str)`

- **功能**: 执行下载任务
- **参数**:
  - `distribution_result`: 任务分配结果
  - `channel`: 频道名称
- **返回值**: None

#### `_print_final_results(self)`

- **功能**: 打印最终下载结果统计
- **参数**: 无
- **返回值**: None

#### `async _cleanup(self)`

- **功能**: 清理资源，停止监控和客户端
- **参数**: 无
- **返回值**: None

#### `log_info(self, message: str)`

- **功能**: 记录信息级别日志
- **参数**:
  - `message`: 日志消息
- **返回值**: None

#### `log_error(self, message: str)`

- **功能**: 记录错误级别日志
- **参数**:
  - `message`: 错误消息
- **返回值**: None

### 函数

#### `async main()`

- **功能**: 主函数，设置日志并启动下载器
- **参数**: 无
- **返回值**: None

---

## 📁 config/settings.py

### 类: TelegramConfig

#### `__post_init__(self)`

- **功能**: 初始化后处理，设置默认会话名称
- **参数**: 无
- **返回值**: None

### 类: DownloadConfig

- **功能**: 下载配置数据类，无自定义方法

### 类: MonitoringConfig

- **功能**: 监控配置数据类，无自定义方法

### 类: AppConfig

#### `__post_init__(self)`

- **功能**: 初始化后处理，设置默认配置对象
- **参数**: 无
- **返回值**: None

---

## 📁 config/constants.py

### 常量定义

- **功能**: 定义项目中使用的各种常量
- **内容**:
  - 文件大小常量 (MB, GB)
  - 下载方法选择阈值
  - 客户端配置常量
  - 网络配置常量
  - 日志配置常量
  - 文件类型扩展名集合
  - Telegram API 限制常量
  - 监控配置常量

---

## 📁 core/client/client_manager.py

### 类: ClientManager

#### `__init__(self, config: TelegramConfig)`

- **功能**: 初始化客户端管理器
- **参数**:
  - `config`: Telegram 配置对象
- **返回值**: None

#### `async initialize_clients(self, session_names: Optional[List[str]] = None) -> List[Client]`

- **功能**: 初始化多个客户端
- **参数**:
  - `session_names`: 会话名称列表，可选
- **返回值**: 客户端列表

#### `_create_client(self, session_name: str) -> Client`

- **功能**: 创建单个客户端
- **参数**:
  - `session_name`: 会话名称
- **返回值**: Pyrogram 客户端对象

#### `async start_all_clients(self) -> None`

- **功能**: 启动所有客户端
- **参数**: 无
- **返回值**: None

#### `async _start_single_client(self, client: Client) -> None`

- **功能**: 启动单个客户端
- **参数**:
  - `client`: 客户端对象
- **返回值**: None

#### `async stop_all_clients(self) -> None`

- **功能**: 停止所有客户端
- **参数**: 无
- **返回值**: None

#### `get_client_info(self) -> Dict[str, Any]`

- **功能**: 获取客户端信息统计
- **参数**: 无
- **返回值**: 包含客户端信息的字典

#### `get_clients(self) -> List[Client]`

- **功能**: 获取客户端列表副本
- **参数**: 无
- **返回值**: 客户端列表

#### `get_client_names(self) -> List[str]`

- **功能**: 获取客户端名称列表
- **参数**: 无
- **返回值**: 客户端名称字符串列表

#### `get_client_by_name(self, client_name: str)`

- **功能**: 根据名称获取客户端
- **参数**:
  - `client_name`: 客户端名称
- **返回值**: 客户端对象或 None

---

## 📁 core/client/session_manager.py

### 类: SessionManager

#### `__init__(self, session_directory: str = "sessions")`

- **功能**: 初始化会话管理器
- **参数**:
  - `session_directory`: 会话文件目录
- **返回值**: None

#### `get_available_sessions(self, session_names: List[str]) -> List[str]`

- **功能**: 获取可用的会话文件
- **参数**:
  - `session_names`: 期望的会话名称列表
- **返回值**: 实际可用的会话名称列表

#### `cleanup_invalid_sessions(self, valid_session_names: List[str]) -> int`

- **功能**: 清理无效的会话文件
- **参数**:
  - `valid_session_names`: 有效的会话名称列表
- **返回值**: 清理的文件数量

---

## 📁 core/download/download_manager.py

### 类: DownloadManager

#### `__init__(self, config: DownloadConfig)`

- **功能**: 初始化下载管理器
- **参数**:
  - `config`: 下载配置对象
- **返回值**: None

#### `async download_media(self, client: Client, message: Any, folder_name: str) -> Optional[Path]`

- **功能**: 智能选择下载策略并下载消息
- **参数**:
  - `client`: Pyrogram 客户端
  - `message`: 消息对象
  - `folder_name`: 文件夹名称
- **返回值**: 下载文件路径或 None

#### `get_download_stats(self) -> Dict[str, Any]`

- **功能**: 获取下载统计信息
- **参数**: 无
- **返回值**: 包含下载统计的字典

---

## 📁 utils/file_utils.py

### 类: FileUtils

#### `@staticmethod sanitize_filename(filename: str) -> str`

- **功能**: 清理文件名，移除非法字符
- **参数**:
  - `filename`: 原始文件名
- **返回值**: 清理后的文件名

#### `@staticmethod generate_filename_by_type(message: Any) -> str`

- **功能**: 根据消息类型生成文件名
- **参数**:
  - `message`: 消息对象
- **返回值**: 生成的文件名

#### `@staticmethod get_file_size_bytes(message: Any) -> int`

- **功能**: 获取消息文件大小（字节）
- **参数**:
  - `message`: 消息对象
- **返回值**: 文件大小（字节）

#### `@staticmethod get_file_size_mb(message: Any) -> float`

- **功能**: 获取消息文件大小（MB）
- **参数**:
  - `message`: 消息对象
- **返回值**: 文件大小（MB）

---

## 📁 utils/network_utils.py

### 类: NetworkUtils

#### `@staticmethod create_proxy_config(host: str, port: int) -> Dict[str, Any]`

- **功能**: 创建代理配置
- **参数**:
  - `host`: 代理主机
  - `port`: 代理端口
- **返回值**: 代理配置字典

#### `@staticmethod get_network_stats() -> Dict[str, float]`

- **功能**: 获取网络统计信息
- **参数**: 无
- **返回值**: 网络统计字典

#### `@staticmethod calculate_bandwidth(current_stats: Dict[str, float], previous_stats: Dict[str, float], time_interval: float) -> Dict[str, float]`

- **功能**: 计算带宽使用情况
- **参数**:
  - `current_stats`: 当前网络统计
  - `previous_stats`: 之前网络统计
  - `time_interval`: 时间间隔
- **返回值**: 带宽使用情况字典

### 类: BandwidthMonitor

#### `__init__(self, update_interval: float = 1.0)`

- **功能**: 初始化带宽监控器
- **参数**:
  - `update_interval`: 更新间隔（秒）
- **返回值**: None

#### `start_monitoring(self)`

- **功能**: 开始监控
- **参数**: 无
- **返回值**: None

#### `stop_monitoring(self)`

- **功能**: 停止监控
- **参数**: 无
- **返回值**: None

---

## 📁 utils/channel_utils.py

### 类: ChannelUtils

#### `@staticmethod async get_channel_info(client: Client, channel: str) -> Dict[str, Any]`

- **功能**: 获取频道信息并生成文件夹名称
- **参数**:
  - `client`: Pyrogram 客户端
  - `channel`: 频道名称
- **返回值**: 包含频道信息的字典

#### `@staticmethod sanitize_folder_name(name: str) -> str`

- **功能**: 清理文件夹名称，移除非法字符
- **参数**:
  - `name`: 原始名称
- **返回值**: 清理后的名称

---

## 📁 utils/logging_utils.py

### 函数

#### `setup_logging(log_level: str = DEFAULT_LOG_LEVEL, log_file: Optional[Path] = None, clear_log: bool = True, suppress_pyrogram: bool = True) -> logging.Logger`

- **功能**: 设置日志配置
- **参数**:
  - `log_level`: 日志级别
  - `log_file`: 日志文件路径，可选
  - `clear_log`: 是否清除现有日志
  - `suppress_pyrogram`: 是否屏蔽 pyrogram 日志
- **返回值**: 日志器对象

#### `get_logger(name: str) -> logging.Logger`

- **功能**: 获取指定名称的日志器
- **参数**:
  - `name`: 日志器名称
- **返回值**: 日志器对象

---

## 📁 monitoring/bandwidth_monitor.py

### 类: BandwidthMonitor

#### `__init__(self, update_interval: float = 1.0, log_interval: float = 5.0)`

- **功能**: 初始化带宽监控器（线程版本）
- **参数**:
  - `update_interval`: 更新间隔
  - `log_interval`: 日志记录间隔
- **返回值**: None

#### `start(self, callback: Optional[Callable[[Dict[str, float]], None]] = None)`

- **功能**: 启动监控线程
- **参数**:
  - `callback`: 回调函数，可选
- **返回值**: None

#### `stop(self)`

- **功能**: 停止监控线程
- **参数**: 无
- **返回值**: None

#### `get_current_bandwidth(self) -> Dict[str, float]`

- **功能**: 获取当前带宽数据
- **参数**: 无
- **返回值**: 带宽数据字典

#### `get_status(self) -> Dict[str, Any]`

- **功能**: 获取监控状态
- **参数**: 无
- **返回值**: 状态信息字典

### 函数

#### `create_simple_bandwidth_monitor() -> BandwidthMonitor`

- **功能**: 创建简单的带宽监控器
- **参数**: 无
- **返回值**: 带宽监控器对象

---

## 📁 monitoring/stats_collector.py

### 类: StatsCollector

#### `__init__(self, total_messages: int = 0)`

- **功能**: 初始化统计收集器
- **参数**:
  - `total_messages`: 总消息数
- **返回值**: None

#### `set_total_messages(self, total: int)`

- **功能**: 设置总消息数
- **参数**:
  - `total`: 总消息数
- **返回值**: None

#### `update_download_progress(self, success: bool, message_id: Optional[int] = None, client_name: Optional[str] = None, file_size_mb: float = 0.0)`

- **功能**: 更新下载进度
- **参数**:
  - `success`: 是否成功
  - `message_id`: 消息 ID，可选
  - `client_name`: 客户端名称，可选
  - `file_size_mb`: 文件大小（MB）
- **返回值**: None

#### `get_final_report(self) -> Dict[str, Any]`

- **功能**: 获取最终报告
- **参数**: 无
- **返回值**: 最终报告字典

---

## 📁 scripts/create_client_session.py

### 函数

#### `async create_session(session_name, sessions_dir, phone_number, session_index)`

- **功能**: 创建单个会话文件
- **参数**:
  - `session_name`: 会话名称
  - `sessions_dir`: 会话目录
  - `phone_number`: 电话号码
  - `session_index`: 会话索引
- **返回值**: 布尔值，表示是否成功创建

---

## 📁 models/message_group.py

### 类: MessageGroup

#### `add_message(self, message: Any)`

- **功能**: 添加消息到组
- **参数**:
  - `message`: 消息对象
- **返回值**: None

#### `@property is_media_group(self) -> bool`

- **功能**: 判断是否为媒体组
- **参数**: 无
- **返回值**: 布尔值

#### `__len__(self) -> int`

- **功能**: 返回消息数量
- **参数**: 无
- **返回值**: 消息数量

### 类: MessageGroupCollection

#### `add_media_group(self, group: MessageGroup)`

- **功能**: 添加媒体组
- **参数**:
  - `group`: 消息组对象
- **返回值**: None

#### `add_single_message(self, message: Any)`

- **功能**: 添加单条消息
- **参数**:
  - `message`: 消息对象
- **返回值**: None

---

## 📁 core/download/base.py

### 类: BaseDownloader (抽象基类)

#### `__init__(self, download_dir: str = "downloads")`

- **功能**: 初始化下载器基类
- **参数**:
  - `download_dir`: 下载目录
- **返回值**: None

#### `@abstractmethod async download(self, client: Client, message: Any) -> Optional[Path]`

- **功能**: 下载媒体文件（抽象方法）
- **参数**:
  - `client`: Pyrogram 客户端
  - `message`: 消息对象
- **返回值**: 下载文件路径或 None

#### `get_channel_directory(self, folder_name: str) -> Path`

- **功能**: 获取频道下载目录
- **参数**:
  - `folder_name`: 文件夹名称
- **返回值**: 目录路径

#### `generate_file_path(self, message: Any, folder_name: str) -> Path`

- **功能**: 生成文件保存路径
- **参数**:
  - `message`: 消息对象
  - `folder_name`: 文件夹名称
- **返回值**: 文件路径

---

## 📁 core/download/raw_downloader.py

### 类: RawDownloader

#### `async download(self, client: Client, message: Any, folder_name: str) -> Optional[Path]`

- **功能**: 使用 RAW API 方法下载媒体文件
- **参数**:
  - `client`: Pyrogram 客户端
  - `message`: 消息对象
  - `folder_name`: 文件夹名称
- **返回值**: 下载文件路径或 None

---

## 📁 core/task_distribution/base.py

### 类: TaskDistributionStrategy (抽象基类)

#### `__init__(self, config: Optional[DistributionConfig] = None)`

- **功能**: 初始化任务分配策略
- **参数**:
  - `config`: 分配配置，可选
- **返回值**: None

#### `@abstractmethod async distribute_tasks(self, message_collection: MessageGroupCollection, client_names: List[str]) -> TaskDistributionResult`

- **功能**: 分配任务到客户端（抽象方法）
- **参数**:
  - `message_collection`: 消息集合
  - `client_names`: 客户端名称列表
- **返回值**: 任务分配结果

#### `@abstractmethod get_strategy_info(self) -> Dict[str, Any]`

- **功能**: 获取策略信息（抽象方法）
- **参数**: 无
- **返回值**: 策略信息字典

### 枚举

#### `DistributionMode`

- **功能**: 分配模式枚举
- **值**:
  - `MEDIA_GROUP_AWARE`: 媒体组感知分配

#### `LoadBalanceMetric`

- **功能**: 负载均衡指标枚举
- **值**:
  - `ESTIMATED_SIZE`: 按真实文件大小

### 数据类

#### `DistributionConfig`

- **功能**: 分配配置数据类
- **属性**:
  - `mode`: 分配模式
  - `load_balance_metric`: 负载均衡指标
  - `prefer_large_groups_first`: 优先分配大组
  - `enable_validation`: 启用验证

---

## 📁 core/message/fetcher.py

### 类: MessageFetcher

#### `__init__(self, clients: List[Client])`

- **功能**: 初始化消息获取器
- **参数**:
  - `clients`: 客户端列表
- **返回值**: None

#### `async parallel_fetch_messages(self, channel: str, start_id: int, end_id: int) -> List[Any]`

- **功能**: 并发获取消息 - 多客户端分工获取不同范围的消息，同时为消息添加结构信息
- **参数**:
  - `channel`: 频道名称
  - `start_id`: 起始消息 ID
  - `end_id`: 结束消息 ID
- **返回值**: 增强的消息列表（包含\_structure_info 属性）

#### `async fetch_message_range(self, client: Client, channel: str, message_ids: List[int], client_index: int) -> List[Any]`

- **功能**: 获取指定范围的消息 - 使用批量获取逻辑
- **参数**:
  - `client`: Pyrogram 客户端
  - `channel`: 频道名称
  - `message_ids`: 消息 ID 列表
  - `client_index`: 客户端索引
- **返回值**: 消息列表

---

## 📁 core/message/structure_info.py

### 类: MessageStructureInfo

#### `@property is_group_member(self) -> bool`

- **功能**: 是否属于媒体组
- **返回值**: 布尔值

#### `@property is_media_message(self) -> bool`

- **功能**: 是否为媒体消息
- **返回值**: 布尔值

### 类: MessageStructureExtractor

#### `@staticmethod extract_structure_info(message) -> MessageStructureInfo`

- **功能**: 从消息中提取结构信息
- **参数**:
  - `message`: Telegram 消息对象
- **返回值**: 消息结构信息

#### `@staticmethod enhance_messages_batch(messages: list) -> list`

- **功能**: 批量为消息添加结构信息
- **参数**:
  - `messages`: 消息列表
- **返回值**: 增强的消息列表

---

## 📁 core/message/grouper.py

### 类: MessageGrouper

#### `__init__(self, preserve_structure: bool = False)`

- **功能**: 初始化消息分组器
- **参数**:
  - `preserve_structure`: 是否保持原始消息结构
- **返回值**: None

#### `group_messages_from_list(self, messages: List[Any]) -> MessageGroupCollection`

- **功能**: 从已获取的消息列表进行媒体组分析
- **参数**:
  - `messages`: 消息对象列表
- **返回值**: 消息组集合

#### `_group_messages(self, messages: List[Any]) -> MessageGroupCollection`

- **功能**: 将消息按媒体组分组（内部方法）
- **参数**:
  - `messages`: 消息对象列表
- **返回值**: 消息组集合

### 函数

#### `is_media_group_message(message) -> bool`

- **功能**: 检查是否为媒体组消息
- **参数**:
  - `message`: 消息对象
- **返回值**: 布尔值，True 表示是媒体组消息

---

## 📁 core/download/stream_downloader.py

### 类: StreamDownloader

#### `async download(self, client: Client, message: Any, folder_name: str) -> Optional[Path]`

- **功能**: 使用流式方法下载媒体文件
- **参数**:
  - `client`: Pyrogram 客户端
  - `message`: 消息对象
  - `folder_name`: 文件夹名称
- **返回值**: 下载文件路径或 None

---

## 📁 core/task_distribution/distributor.py

### 类: TaskDistributor

#### `__init__(self, config: Optional[DistributionConfig] = None)`

- **功能**: 初始化任务分配器
- **参数**:
  - `config`: 分配配置，可选
- **返回值**: None

#### `async distribute_tasks(self, message_collection: MessageGroupCollection, client_names: List[str], strategy_mode: Optional[DistributionMode] = None) -> TaskDistributionResult`

- **功能**: 分配任务到客户端
- **参数**:
  - `message_collection`: 消息集合
  - `client_names`: 客户端名称列表
  - `strategy_mode`: 分配策略模式，可选
- **返回值**: 任务分配结果

#### `_get_strategy(self, mode: DistributionMode) -> TaskDistributionStrategy`

- **功能**: 获取分配策略实例（内部方法）
- **参数**:
  - `mode`: 分配模式
- **返回值**: 任务分配策略实例

#### `_update_stats(self, result: TaskDistributionResult, mode: DistributionMode)`

- **功能**: 更新统计信息（内部方法）
- **参数**:
  - `result`: 任务分配结果
  - `mode`: 分配模式
- **返回值**: None

---

## 📁 core/task_distribution/strategies.py

### 类: MediaGroupAwareDistributionStrategy

#### `async distribute_tasks(self, message_collection: MessageGroupCollection, client_names: List[str]) -> TaskDistributionResult`

- **功能**: 媒体组感知的任务分配
- **参数**:
  - `message_collection`: 消息集合
  - `client_names`: 客户端名称列表
- **返回值**: 任务分配结果

#### `_find_min_load_client(self, assignments: List[ClientTaskAssignment]) -> int`

- **功能**: 根据真实文件大小找到负载最小的客户端（内部方法）
- **参数**:
  - `assignments`: 客户端任务分配列表
- **返回值**: 最小负载客户端的索引

#### `get_strategy_info(self) -> Dict[str, Any]`

- **功能**: 获取策略信息
- **参数**: 无
- **返回值**: 策略信息字典

---

## 📁 core/message/processor.py

### 类: MessageProcessor

#### `__init__(self)`

- **功能**: 初始化消息处理器
- **参数**: 无
- **返回值**: None

#### `validate_messages(self, messages: List[Any]) -> List[Any]`

- **功能**: 验证消息列表，过滤无效消息
- **参数**:
  - `messages`: 消息列表
- **返回值**: 有效消息列表

#### `get_message_statistics(self, messages: List[Any]) -> Dict[str, Any]`

- **功能**: 获取消息统计信息
- **参数**:
  - `messages`: 消息列表
- **返回值**: 统计信息字典

#### `_is_valid_message(self, message: Any) -> bool`

- **功能**: 检查消息是否有效（内部方法）
- **参数**:
  - `message`: 消息对象
- **返回值**: 是否有效

#### `_get_message_type(self, message: Any) -> str`

- **功能**: 获取消息类型（内部方法）
- **参数**:
  - `message`: 消息对象
- **返回值**: 消息类型字符串

---

## 📁 core/download/download_manager.py (补充)

### 类: DownloadManager (补充方法)

#### `async download_media(self, client: Client, message: Any, folder_name: str) -> Optional[Path]`

- **功能**: 智能选择下载方法
- **参数**:
  - `client`: Pyrogram 客户端
  - `message`: 消息对象
  - `folder_name`: 文件夹名称
- **返回值**: 下载文件路径或 None

#### `async batch_download(self, client: Client, messages: List[Any], folder_name: str) -> Dict[str, Any]`

- **功能**: 批量下载消息
- **参数**:
  - `client`: Pyrogram 客户端
  - `messages`: 消息列表
  - `folder_name`: 文件夹名称
- **返回值**: 下载结果统计字典

---

## 📝 说明

1. **异步函数**: 标记为`async`的函数需要在异步环境中调用
2. **类型注解**: 使用了 Python 类型注解，提高代码可读性
3. **可选参数**: 标记为`Optional`的参数可以传入 None 值
4. **返回值**: 明确标注了每个函数的返回值类型
5. **抽象方法**: 标记为`@abstractmethod`的方法需要在子类中实现

## 更新记录

- **初始版本**: 包含当前项目中所有主要模块的函数索引
- **扩展版本**: 添加了下载器、任务分配、消息处理等核心模块

此索引文档将随项目发展持续更新。
