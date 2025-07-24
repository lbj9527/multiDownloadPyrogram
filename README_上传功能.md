# Telegram 多客户端下载器 - 上传功能

## 📋 功能概述

新增的上传功能允许将下载的消息直接转发到指定的Telegram频道，支持三种工作模式：

- **🔽 Raw模式** - 仅下载到本地（原有功能）
- **🔄 Upload模式** - 内存下载后直接上传到目标频道
- **🔀 Hybrid模式** - 既下载到本地又上传到目标频道

## 🎯 核心特性

- ✅ **保持原消息格式** - 完整保留媒体组、说明文字、文件类型
- ✅ **内存高效处理** - Upload模式使用内存下载，无需本地存储
- ✅ **智能媒体组处理** - 自动识别并重组媒体组消息
- ✅ **灵活配置选项** - 支持环境变量和配置文件
- ✅ **错误重试机制** - 自动重试失败的上传操作
- ✅ **实时统计监控** - 详细的上传进度和统计信息

## ⚙️ 配置说明

### 环境变量配置

```bash
# 存储模式配置
STORAGE_MODE=upload          # raw/upload/hybrid

# 上传功能配置
UPLOAD_ENABLED=true          # 启用上传功能
UPLOAD_TARGET_CHANNEL=@your_channel  # 目标频道
PRESERVE_MEDIA_GROUPS=true   # 保持媒体组格式
PRESERVE_CAPTIONS=true       # 保持原始说明文字
UPLOAD_DELAY=1.0            # 上传间隔（秒）
UPLOAD_MAX_RETRIES=3        # 最大重试次数
```

### 配置文件示例

```python
# 在代码中配置
app_settings.storage.storage_mode = "upload"
app_settings.upload.enabled = True
app_settings.upload.target_channel = "@your_channel"
app_settings.upload.preserve_media_groups = True
app_settings.upload.preserve_captions = True
app_settings.upload.upload_delay = 1.0
app_settings.upload.max_retries = 3
```

## 🚀 使用方法

### 1. 基础上传模式

```bash
# 设置环境变量
export STORAGE_MODE=upload
export UPLOAD_ENABLED=true
export UPLOAD_TARGET_CHANNEL=@your_target_channel

# 运行程序
python main.py
```

### 2. 混合模式（推荐）

```bash
# 既下载到本地又上传到频道
export STORAGE_MODE=hybrid
export UPLOAD_ENABLED=true
export UPLOAD_TARGET_CHANNEL=@your_target_channel

python main.py
```

### 3. 程序化配置

```python
import asyncio
from main import TelegramDownloaderApp
from config import app_settings

async def main():
    # 配置上传功能
    app_settings.storage.storage_mode = "upload"
    app_settings.upload.enabled = True
    app_settings.upload.target_channel = "@your_channel"
    
    # 运行应用
    app = TelegramDownloaderApp()
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())
```

## 📊 工作模式详解

### Raw模式（原有功能）
```
源频道 → 下载到本地 → 本地存储
```
- 仅下载文件到本地目录
- 保持原有的文件组织结构
- 适合需要本地备份的场景

### Upload模式（新功能）
```
源频道 → 内存下载 → 上传到目标频道
```
- 文件在内存中处理，不占用本地存储
- 直接转发到目标频道
- 适合频道转发和内容分发

### Hybrid模式（推荐）
```
源频道 → 下载到本地 → 本地存储
       ↘ 同时上传到目标频道
```
- 同时进行本地存储和频道上传
- 提供最大的灵活性
- 适合需要备份和分发的场景

## 🔧 技术实现

### 核心组件

1. **UploadService** - 上传服务核心类
   - 处理单条消息和媒体组上传
   - 管理上传队列和重试机制
   - 提供统计信息和监控

2. **MessageHandler扩展** - 消息处理器增强
   - 支持内存下载模式
   - 智能选择处理策略
   - 保持原消息格式

3. **配置系统扩展** - 新增上传配置
   - 环境变量支持
   - 配置验证和错误处理
   - 灵活的参数调整

### 消息格式保持

#### 单条消息
```python
# 原消息: msg-12345.jpg
# 上传后: 保持相同的文件名和格式
```

#### 媒体组消息
```python
# 原消息组:
# - 1234567890-12345.jpg
# - 1234567890-12346.jpg  
# - 1234567890-12347.mp4

# 上传后: 作为媒体组一起发送，保持组织结构
```

#### 文本和说明文字
```python
# 原消息的caption和text完整保留
# 支持Markdown和HTML格式
```

## 📈 监控和统计

### 实时统计信息
```
📤 上传统计信息:
总上传文件: 156
上传失败: 2
媒体组上传: 12
上传成功率: 98.7%
```

### 日志监控
```
2024-01-15 10:30:15 - INFO - 消息 12345 上传成功
2024-01-15 10:30:16 - INFO - 媒体组 1234567890 上传成功，包含 3 个文件
2024-01-15 10:30:17 - ERROR - 上传消息失败: FLOOD_WAIT_X
```

## ⚠️ 注意事项

### 1. 频道权限
- 确保机器人有目标频道的发送权限
- 私有频道需要先添加机器人为管理员

### 2. 速率限制
- 合理设置上传延迟避免触发Flood Wait
- 建议上传延迟设置为1-2秒

### 3. 文件大小限制
- 普通用户：最大2GB
- Bot账户：最大50MB
- 大文件会自动分块处理

### 4. 内存使用
- Upload模式会将文件加载到内存
- 大文件可能占用较多内存
- 建议监控内存使用情况

## 🔍 故障排除

### 常见问题

1. **上传失败：PEER_ID_INVALID**
   ```bash
   # 解决方案：确保目标频道ID正确
   export UPLOAD_TARGET_CHANNEL=@correct_channel_name
   ```

2. **上传失败：CHAT_WRITE_FORBIDDEN**
   ```bash
   # 解决方案：检查机器人权限
   # 确保机器人是频道管理员或有发送消息权限
   ```

3. **内存不足**
   ```bash
   # 解决方案：使用hybrid模式或增加系统内存
   export STORAGE_MODE=hybrid
   ```

4. **媒体组不完整**
   ```bash
   # 解决方案：增加媒体组等待时间
   # 在UploadService中调整等待时间
   ```

## 🎯 最佳实践

1. **推荐配置**
   ```bash
   STORAGE_MODE=hybrid
   UPLOAD_DELAY=1.5
   PRESERVE_MEDIA_GROUPS=true
   PRESERVE_CAPTIONS=true
   ```

2. **性能优化**
   - 使用SSD存储提高I/O性能
   - 合理设置并发客户端数量
   - 监控网络带宽使用

3. **安全考虑**
   - 定期轮换API密钥
   - 使用专用的转发账户
   - 避免在公共网络使用

## 📝 更新日志

### v2.0.0 (2024-01-15)
- ✅ 新增上传功能
- ✅ 支持三种工作模式
- ✅ 完整的媒体组处理
- ✅ 配置系统扩展
- ✅ 统计和监控功能

这个上传功能为Telegram多客户端下载器提供了强大的内容分发能力，让您可以轻松地将内容从一个频道转发到另一个频道，同时保持完整的消息格式和媒体组织结构。
