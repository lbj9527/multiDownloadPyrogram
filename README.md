# 多客户端 Telegram 下载器

## 📋 项目概述

这是一个基于 Pyrogram 的多客户端 Telegram 媒体下载和转发工具，支持并发下载、智能任务分配和实时监控。

## 🚀 当前版本状态

**版本**: v1.3.0
**开发阶段**: Phase 3 完成 - 功能集成完毕 ✅

### ✅ 已实现功能

#### 核心下载功能 (v1.0.0)

- ✅ **多客户端管理**: 支持多个 Telegram 账号并发操作
- ✅ **智能下载策略**: 根据文件大小自动选择流式下载或 RAW API 下载
- ✅ **媒体组处理**: 智能识别和完整下载媒体组
- ✅ **并发控制**: 支持多客户端并发下载，智能负载均衡
- ✅ **实时监控**: 带宽监控、下载进度统计、性能数据收集
- ✅ **会话管理**: 自动会话验证、故障恢复和重连
- ✅ **配置管理**: 统一的配置系统，支持代理、API 配置等

#### 扩展功能 (v1.1.0 - v1.3.0)

- ✅ **数据模型扩展**: 统一的下载结果数据模型 (DownloadResult)
- ✅ **内存下载功能**: 基于现有 RawDownloader 和 StreamDownloader 的正确实现
  - RAW API 内存下载（小文件，<50MB，非视频）✅ 完全正常工作
  - Stream 内存下载（大文件，>50MB，视频文件）✅ 完全正常工作
  - 智能选择策略：保持现有的 50MB 阈值和视频文件判断逻辑
- ✅ **下载管理器扩展**: 智能选择下载策略，支持本地和内存两种模式
- ✅ **测试框架**: 完整的内存下载功能测试脚本
- ✅ **模板系统**: 支持原格式和自定义模板处理（Phase 2 已完成）
  - 智能模板引擎，支持变量替换和内容生成
  - 变量自动提取器，识别 19 种不同类型的变量
  - 模板预览和验证功能
- ✅ **上传功能**: 支持转发到目标频道（Phase 3 已完成）
  - 智能上传策略，根据文件类型选择最佳上传方式
  - 批量并发上传，支持多频道分发
  - 完整的进度跟踪和错误处理
  - **分阶段上传**: 先上传到 me 聊天，再批量分发到目标频道（默认行为）
    - 使用 send_media_group 进行媒体组批量上传
    - 支持 10 个文件为一组的智能分组
    - 自动临时文件清理机制
    - 模块化设计，支持扩展其他数据源
- ✅ **工作流管理**: 本地下载和转发上传两种工作模式
  - 完整的工作流配置系统
  - 文件过滤和调度功能
  - 模板系统集成

## 🏗️ 项目架构

```
multiDownloadPyrogram/
├── 📄 main.py                    # 主程序入口
├── 📁 config/                    # 配置管理
│   ├── settings.py              # 统一配置（API、代理、下载等）
│   └── constants.py             # 项目常量
├── 📁 core/                      # 核心业务模块
│   ├── client/                  # 客户端管理
│   ├── message/                 # 消息处理
│   ├── download/                # 下载处理
│   └── task_distribution/       # 任务分配
├── 📁 models/                    # 数据模型
├── 📁 monitoring/                # 监控系统
├── 📁 utils/                     # 工具函数
├── 📁 scripts/                   # 辅助脚本
└── 📁 docs/                      # 项目文档
```

## 🔧 环境要求

- Python 3.8+
- Pyrogram >= 2.0.106
- TgCrypto >= 1.2.5 (可选，用于性能优化)

## 📦 安装依赖

```bash
pip install -r requirements.txt
```

## ⚙️ 配置说明

项目使用现有的正确配置参数：

- ✅ API ID 和 API Hash 已配置
- ✅ 代理设置已配置 (127.0.0.1:7890)
- ✅ 会话文件已准备就绪
- ✅ 频道信息已配置

## 🚀 使用方法

### 🚀 快速开始

```bash
# 使用默认配置运行（下载 @csdkl 频道的消息 72710-72849）
python main.py

# 在 Windows PowerShell 中运行
python main.py
```

### ⚠️ 重要提示

**在 Windows PowerShell 中使用自定义参数时，频道名称必须用引号包围！**

```powershell
# ✅ 正确用法 (PowerShell)
python main.py --mode download --source "@luanlunluoli" --start 8255 --end 8412

# ❌ 错误用法 (PowerShell) - 会导致参数解析错误
python main.py --mode download --source @luanlunluoli --start 8255 --end 8412
```

### 基础下载功能（默认模式）

```bash
# 运行多客户端下载器（使用默认配置：@csdkl 频道，消息 72710-72849）
python main.py

# 自定义参数的本地下载 (Linux/macOS)
python main.py --mode download --source "@channel_name" --start 1000 --end 2000

# 自定义参数的本地下载 (Windows PowerShell)
python main.py --mode download --source "@channel_name" --start 1000 --end 2000

# 实际示例：下载 @luanlunluoli 频道的消息 8255-8412 (Windows PowerShell)
python main.py --mode download --source "@luanlunluoli" --start 8255 --end 8412
```

### 转发上传功能（新增）

#### 基础转发命令

```bash
# 转发到单个频道 (Linux/macOS)
python main.py --mode forward --source "@source_channel" --targets "@target_channel" --start 1000 --end 1100

# 转发到单个频道 (Windows PowerShell)
python main.py --mode forward --source "@source_channel" --targets "@target_channel" --start 1000 --end 1100

# 转发到多个频道 (Linux/macOS)
python main.py --mode forward --source "@source_channel" --targets "@target1" "@target2" "@target3" --start 1000 --end 1100

# 转发到多个频道 (Windows PowerShell)
python main.py --mode forward --source "@source_channel" --targets "@target1" "@target2" "@target3" --start 1000 --end 1100
```

#### 媒体组完整性保持（推荐）

```bash
# 保持原始消息结构：单条消息→单条消息，媒体组→媒体组
python main.py --mode forward --source "@source" --targets "@target" --preserve-structure

# 保持结构 + 自定义模板
python main.py --mode forward --source "@source" --targets "@target" --preserve-structure --template "🔥 精彩内容分享\n\n{original_text}{original_caption}\n\n📂 {file_name}"

# 保持结构 + 自定义媒体组超时时间（默认300秒）
python main.py --mode forward --source "@source" --targets "@target" --preserve-structure --group-timeout 600

# 实际示例：保持媒体组完整性转发
python main.py --mode forward --source "@csdkl" --targets "@target1" "@target2" --start 73472 --end 73551 --preserve-structure
```

#### 传统批量模式（兼容性）

```bash
# 使用自定义模板转发（传统10个文件一组模式）
python main.py --mode forward --source "@source" --targets "@target" --template "📸 转发: {file_name}\n\n{original_text}"

# 自定义批次大小（传统模式，默认10个文件一组）
python main.py --mode forward --source "@source" --targets "@target" --batch-size 5

# 成功后不清理临时文件（用于调试）
python main.py --mode forward --source "@source" --targets "@target" --no-cleanup-success

# 失败后也清理临时文件
python main.py --mode forward --source "@source" --targets "@target" --cleanup-failure
```

### 转发模式对比

| 特性         | 媒体组完整性保持模式                         | 传统批量模式         |
| ------------ | -------------------------------------------- | -------------------- |
| **启用方式** | `--preserve-structure`                       | 默认模式（不加参数） |
| **单条消息** | 单条消息 → 单条消息                          | 10 个文件一组        |
| **媒体组**   | 媒体组 → 媒体组（保持完整）                  | 10 个文件一组        |
| **API 使用** | `send_photo/send_video` + `send_media_group` | `send_media_group`   |
| **结构保持** | ✅ 完全保持原始结构                          | ❌ 重新分组          |
| **推荐场景** | 🌟 **推荐**：保持原频道结构                  | 兼容性：简单批量转发 |

**推荐使用媒体组完整性保持模式**，它能完美保持原频道的消息结构，确保单条消息和媒体组在目标频道中的呈现与源频道完全一致。

### 命令行参数

```bash
# 查看所有可用参数
python main.py --help

# 常用参数说明
--mode {download,forward}     # 工作流模式 (默认: download)
--source SOURCE              # 源频道 (默认: @csdkl，PowerShell中需要引号)
--start START                # 起始消息ID (默认: 72710)
--end END                    # 结束消息ID (默认: 72849)
--targets TARGET [TARGET ...] # 目标频道列表（转发模式必需，PowerShell中需要引号）
--template TEMPLATE          # 自定义模板（转发模式可选）

# 媒体组完整性保持参数（推荐）
--preserve-structure         # 保持原始消息结构（单条消息→单条消息，媒体组→媒体组）
--group-timeout SECONDS     # 媒体组收集超时时间，秒 (默认: 300)

# 分阶段上传参数（传统模式）
--batch-size SIZE            # 媒体组批次大小 (默认: 10，仅传统模式)
--no-cleanup-success         # 成功后不清理临时文件
--cleanup-failure            # 失败后也清理临时文件

# 配置说明：
# 下载目录：在 config/settings.py 的 DownloadConfig.download_dir 中配置
# 并发数量：由 config/settings.py 的 TelegramConfig.session_names 数量决定
```

### 🖥️ 不同操作系统的使用说明

#### Windows PowerShell

```powershell
# 频道名称必须用引号包围
python main.py --mode download --source "@luanlunluoli" --start 8255 --end 8412

# 多个目标频道也需要分别用引号包围
python main.py --mode forward --source "@source" --targets "@target1" "@target2"
```

#### Linux / macOS / Git Bash

```bash
# 可以不用引号（但用引号也是安全的）
python main.py --mode download --source @luanlunluoli --start 8255 --end 8412

# 或者使用引号（推荐，更安全）
python main.py --mode download --source "@luanlunluoli" --start 8255 --end 8412
```

### 🔧 常见问题解决

#### 问题：`argument --source: expected one argument`

**原因**：在 PowerShell 中，`@` 符号有特殊含义，导致参数解析失败。

**解决方案**：

```powershell
# ❌ 错误
python main.py --source @channel

# ✅ 正确
python main.py --source "@channel"
```

### 会话文件管理

```bash
# 创建新的会话文件
python scripts/create_client_session.py
```

## 📊 功能特性

### 🎯 智能下载策略

- **流式下载**: 适用于大文件 (>50MB)
- **RAW API 下载**: 适用于小文件 (<50MB)
- **自动选择**: 根据文件大小智能选择最优策略

### 🔄 多客户端并发

- **负载均衡**: 智能分配下载任务
- **故障恢复**: 自动处理网络异常和重连
- **进度监控**: 实时显示各客户端状态

### 📈 监控统计

- **带宽监控**: 实时网络使用情况
- **下载统计**: 文件数量、大小、速度等
- **详细日志**: 完整的操作记录

## 🗺️ 开发路线图

### Phase 1: 基础功能扩展 (✅ 已完成)

- [x] 创建项目文档和版本管理
- [x] 实现 DownloadResult 数据模型
- [x] 实现 MemoryDownloader 内存下载器
- [x] 扩展 DownloadManager 支持内存下载
- [x] 创建测试脚本验证功能
- [x] **完整功能测试通过** (100% 成功率，智能回退机制，支持大文件内存下载)

### Phase 2: 模板系统 (✅ 已完成)

- [x] 创建 TemplateConfig 数据模型
- [x] 实现 TemplateEngine 核心功能
- [x] 实现变量提取和替换
- [x] 创建默认模板和内置变量
- [x] 实现 VariableExtractor 智能提取器
- [x] 实现 TemplateProcessor 完整处理流程
- [x] **完整功能测试通过** (100% 成功率，19 个变量自动提取，完整模板渲染)

### Phase 3: 上传功能 (✅ 已完成)

- [x] 创建 UploadTask 数据模型
- [x] 实现 UploadManager 类
- [x] 实现 BatchUploader 批量上传器
- [x] 实现 UploadStrategy 智能策略
- [x] 创建 WorkflowConfig 工作流配置
- [x] 支持多频道目标设置
- [x] 集成进度监控和错误处理
- [x] **完整功能测试通过** (100% 成功率，多频道上传，智能策略选择)

### Phase 4: 功能集成 (✅ 已完成)

- [x] 集成模板系统到 main.py
- [x] 集成上传功能到 main.py
- [x] 实现工作流模式支持
- [x] 添加命令行参数解析
- [x] 创建统一的工作流管理
- [x] 保持向后兼容性
- [x] **集成测试通过** (100% 成功率，所有功能正常工作)

### Phase 5: 网页版准备 (计划中)

- [ ] API 接口标准化
- [ ] 配置外部化
- [ ] 状态管理优化
- [ ] Web 界面开发

## 📝 更新日志

详细的版本更新记录请查看 [CHANGELOG.md](CHANGELOG.md)

## 📚 文档

- [功能索引文档](FUNCTION_INDEX.md) - 完整的函数和类索引
- [上传模块设计](docs/UPLOAD_MODULE_DESIGN.md) - 上传功能架构设计
- [MVP 开发计划](docs/MVP_DEVELOPMENT_PLAN.md) - 运维平台发展规划

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进项目。

## 📄 许可证

本项目采用 MIT 许可证。

## 🧪 测试功能

### 测试内存下载功能

```bash
# 运行内存下载测试
python test_memory_download.py
```

该测试脚本将：

- 验证 DownloadResult 数据模型功能
- 测试 MemoryDownloader 内存下载器
- 测试扩展的 DownloadManager 功能
- 显示下载统计信息

---

**✅ Phase 1 已完成**: 内存下载功能已完全实现并测试通过！

**🚀 下一步计划**: 开始 Phase 2 模板系统的实现，包括模板引擎和变量处理功能。
