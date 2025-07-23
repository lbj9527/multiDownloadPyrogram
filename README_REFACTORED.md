# Telegram多客户端下载器 - 重构版

## 🏗️ 架构概述

本项目已完全重构，采用现代软件架构原则，实现了数据与逻辑分离、模块化设计、单一职责等最佳实践。

### 📁 项目结构

```
project/
├── config/                 # 配置层
│   ├── __init__.py
│   ├── settings.py         # 应用配置
│   └── constants.py        # 常量定义
├── models/                 # 数据模型层
│   ├── __init__.py
│   ├── download_task.py    # 下载任务模型
│   ├── client_info.py      # 客户端信息模型
│   └── file_info.py        # 文件信息模型
├── core/                   # 核心业务层
│   ├── __init__.py
│   ├── downloader.py       # 核心下载逻辑
│   ├── file_processor.py   # 文件处理逻辑
│   └── message_handler.py  # 消息处理逻辑
├── services/               # 服务层
│   ├── __init__.py
│   ├── client_manager.py   # 客户端管理服务
│   ├── task_scheduler.py   # 任务调度服务
│   └── storage_service.py  # 存储服务
├── utils/                  # 工具层
│   ├── __init__.py
│   ├── file_utils.py       # 文件工具
│   ├── logging_utils.py    # 日志工具
│   └── async_utils.py      # 异步工具
├── interfaces/             # 接口层
│   ├── __init__.py
│   └── download_interface.py # 下载接口
└── main.py                 # 主程序入口
```

## 🎯 设计原则

### 1. **数据与逻辑分离**
- 配置数据集中在 `config/` 模块
- 业务数据模型定义在 `models/` 模块
- 业务逻辑实现在 `core/` 和 `services/` 模块

### 2. **单一职责原则**
- 每个模块、类、函数都有明确的单一职责
- `ClientManager` 只负责客户端管理
- `FileProcessor` 只负责文件处理
- `MessageHandler` 只负责消息处理

### 3. **接口良好**
- 所有公共接口都有清晰的参数和返回值定义
- 使用类型注解提高代码可读性
- 统一的错误处理和日志记录

### 4. **可扩展性**
- 接口层为未来的UI、API提供统一入口
- 服务层支持任务调度、存储策略扩展
- 插件化的文件处理器支持不同存储模式

## 🔧 核心组件

### 配置层 (config/)
- **AppSettings**: 应用程序主配置类
- **TelegramConfig**: Telegram API配置
- **DownloadConfig**: 下载相关配置
- **StorageConfig**: 存储策略配置

### 数据模型层 (models/)
- **DownloadTask**: 下载任务数据模型
- **ClientInfo**: 客户端信息和状态
- **FileInfo**: 文件信息和元数据
- **MediaInfo**: 媒体文件详细信息

### 核心业务层 (core/)
- **TelegramDownloader**: 核心下载逻辑
- **MessageHandler**: 消息类型处理
- **FileProcessor**: 文件存储和压缩

### 服务层 (services/)
- **ClientManager**: 客户端生命周期管理
- **TaskScheduler**: 任务调度和队列管理
- **StorageService**: 存储策略和优化

### 工具层 (utils/)
- **file_utils**: 文件操作工具函数
- **logging_utils**: 日志系统和性能监控
- **async_utils**: 异步编程辅助工具

### 接口层 (interfaces/)
- **DownloadInterface**: 统一的下载接口，为UI/API提供服务

## 🚀 使用方法

### 基本使用
```python
# 直接运行主程序
python main.py
```

### 编程接口使用
```python
from config import app_settings
from services import ClientManager
from core import TelegramDownloader, FileProcessor
from interfaces import DownloadInterface

# 创建组件
client_manager = ClientManager()
file_processor = FileProcessor()
downloader = TelegramDownloader(file_processor)
interface = DownloadInterface(client_manager, downloader)

# 初始化并下载
await client_manager.initialize_clients()
await client_manager.connect_all_clients()

results = await interface.download_messages(
    channel="your_channel",
    start_message_id=1000,
    end_message_id=2000
)
```

## ⚙️ 配置说明

### 环境变量配置
```bash
# Telegram API
API_ID=your_api_id
API_HASH=your_api_hash
PHONE_NUMBER=your_phone

# 下载配置
TARGET_CHANNEL=channel_name
START_MESSAGE_ID=1000
END_MESSAGE_ID=2000
BATCH_SIZE=200
MAX_CLIENTS=3

# 代理配置
USE_PROXY=true
```

### 存储模式
- **raw**: 原始文件存储
- **compressed**: 全部压缩存储
- **hybrid**: 智能混合存储（推荐）

## 🔌 扩展功能

### 1. 添加新的存储策略
```python
class CustomFileProcessor(FileProcessor):
    async def _store_custom(self, file_info: FileInfo) -> bool:
        # 实现自定义存储逻辑
        pass
```

### 2. 添加进度回调
```python
def progress_callback(progress_data):
    print(f"进度: {progress_data['progress_percentage']:.1f}%")

interface.add_progress_callback(progress_callback)
```

### 3. 自定义任务调度
```python
scheduler = TaskScheduler()
await scheduler.start_scheduler()

# 创建定时任务
task = scheduler.create_download_task(
    channel="test_channel",
    start_message_id=1000,
    end_message_id=2000
)

# 调度任务
scheduler.schedule_task(task, datetime.now() + timedelta(hours=1))
```

## 📊 监控和统计

### 获取下载统计
```python
stats = interface.get_download_statistics()
print(f"活动任务: {stats['active_tasks']}")
print(f"客户端状态: {stats['client_stats']}")
```

### 获取存储信息
```python
storage_info = storage_service.get_storage_info()
print(f"总文件数: {storage_info['file_count']}")
print(f"总大小: {storage_info['total_size_formatted']}")
```

## 🧪 测试

### 单元测试
```bash
# 运行所有测试
python -m pytest tests/

# 运行特定模块测试
python -m pytest tests/test_downloader.py
```

### 集成测试
```bash
# 测试完整下载流程
python tests/integration_test.py
```

## 🔧 开发指南

### 添加新功能
1. 在相应的层级添加新模块
2. 遵循单一职责原则
3. 添加适当的类型注解
4. 编写单元测试
5. 更新文档

### 代码规范
- 使用类型注解
- 遵循PEP 8代码风格
- 添加详细的文档字符串
- 使用有意义的变量和函数名

## 📝 更新日志

### v2.0.0 (重构版)
- ✅ 完全重构架构，实现模块化设计
- ✅ 数据与逻辑分离
- ✅ 添加配置管理系统
- ✅ 实现任务调度器
- ✅ 添加存储服务和压缩支持
- ✅ 提供统一的编程接口
- ✅ 完善的日志和监控系统
- ✅ 为UI扩展做好准备

### 未来计划
- 🔄 Web UI界面
- 🔄 REST API接口
- 🔄 数据库支持
- 🔄 分布式下载
- 🔄 更多压缩算法支持

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目！

## 📄 许可证

MIT License
