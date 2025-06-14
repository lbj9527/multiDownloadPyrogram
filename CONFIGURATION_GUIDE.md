# 配置文件使用指南

## 📋 概述

MultiDownloadPyrogram 现在完全使用配置文件驱动，无需命令行参数。所有设置都在 `config.json` 文件中配置。

## 🔧 配置文件结构

### 完整配置示例

```json
{
  "api": {
    "api_id": 12345678,
    "api_hash": "your_api_hash_here"
  },
  "proxy": {
    "scheme": "socks5",
    "hostname": "127.0.0.1",
    "port": 7890,
    "username": null,
    "password": null
  },
  "download": {
    "client_count": 3,
    "max_concurrent_transmissions": 1,
    "sleep_threshold": 10,
    "download_dir": "downloads",
    "large_file_threshold": 52428800,
    "chunk_size": 1048576,
    "max_retries": 3,
    "max_concurrent_downloads": 5,
    "progress_update_interval": 1.0
  },
  "task": {
    "channel_username": "@your_channel_name",
    "start_message_id": 1000,
    "end_message_id": 2000,
    "limit": 1000
  }
}
```

## 📝 配置项详解

### 1. API配置 (api)

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `api_id` | int | ✅ | Telegram API ID |
| `api_hash` | string | ✅ | Telegram API Hash |

### 2. 代理配置 (proxy)

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `scheme` | string | ❌ | "socks5" | 代理协议 |
| `hostname` | string | ❌ | "127.0.0.1" | 代理服务器地址 |
| `port` | int | ❌ | 7890 | 代理端口 |
| `username` | string | ❌ | null | 代理用户名 |
| `password` | string | ❌ | null | 代理密码 |

### 3. 下载配置 (download)

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `client_count` | int | ❌ | 3 | 并发客户端数量 |
| `max_concurrent_transmissions` | int | ❌ | 1 | 单客户端并发传输数 |
| `sleep_threshold` | int | ❌ | 10 | FloodWait自动处理阈值(秒) |
| `download_dir` | string | ❌ | "downloads" | 下载目录 |
| `large_file_threshold` | int | ❌ | 52428800 | 大文件阈值(50MB) |
| `chunk_size` | int | ❌ | 1048576 | 分片大小(1MB) |
| `max_retries` | int | ❌ | 3 | 最大重试次数 |
| `max_concurrent_downloads` | int | ❌ | 5 | 全局最大并发下载数 |
| `progress_update_interval` | float | ❌ | 1.0 | 进度更新间隔(秒) |

### 4. 任务配置 (task) ⭐

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `channel_username` | string | ✅ | "" | 目标频道用户名 |
| `start_message_id` | int | ❌ | null | 起始消息ID |
| `end_message_id` | int | ❌ | null | 结束消息ID |
| `limit` | int | ❌ | 1000 | 消息数量限制 |

## 🎯 任务配置详解

### 频道设置

```json
{
  "task": {
    "channel_username": "@example_channel"
  }
}
```

- 必须以 `@` 开头
- 如果不以 `@` 开头，程序会自动添加

### 消息范围设置

#### 1. 下载所有消息（受limit限制）
```json
{
  "task": {
    "channel_username": "@example_channel",
    "start_message_id": null,
    "end_message_id": null,
    "limit": 1000
  }
}
```

#### 2. 下载指定范围的消息
```json
{
  "task": {
    "channel_username": "@example_channel",
    "start_message_id": 1000,
    "end_message_id": 2000,
    "limit": null
  }
}
```

#### 3. 从指定消息开始下载
```json
{
  "task": {
    "channel_username": "@example_channel",
    "start_message_id": 1000,
    "end_message_id": null,
    "limit": 500
  }
}
```

## 🚀 使用方法

### 1. 创建配置文件

```bash
cp config.example.json config.json
```

### 2. 编辑配置文件

填写你的API信息和任务设置：

```json
{
  "api": {
    "api_id": 你的API_ID,
    "api_hash": "你的API_Hash"
  },
  "task": {
    "channel_username": "@目标频道",
    "start_message_id": 起始消息ID,
    "end_message_id": 结束消息ID,
    "limit": 消息数量限制
  }
}
```

### 3. 运行程序

```bash
# 方法1：直接运行
python -m src.main

# 方法2：使用脚本
python run.py
```

## ⚙️ 性能调优

### 网络条件好
```json
{
  "download": {
    "client_count": 5,
    "max_concurrent_downloads": 8,
    "max_retries": 3
  }
}
```

### 网络条件一般
```json
{
  "download": {
    "client_count": 3,
    "max_concurrent_downloads": 5,
    "max_retries": 5
  }
}
```

### 网络不稳定
```json
{
  "download": {
    "client_count": 1,
    "max_concurrent_downloads": 1,
    "max_retries": 10,
    "sleep_threshold": 30
  }
}
```

## ❗ 注意事项

1. **API配置**: 必须正确填写，否则无法连接Telegram
2. **频道权限**: 确保账号有访问目标频道的权限
3. **代理设置**: 如果在受限地区，确保代理正常工作
4. **消息ID**: 消息ID必须存在，否则会跳过
5. **并发设置**: 过高的并发可能触发频率限制

## 🔍 故障排除

### 配置文件不存在
```
错误: 配置文件 config.json 不存在
请复制 config.example.json 为 config.json 并填写配置
```

**解决方法**: 复制示例配置文件并填写

### 频道用户名为空
```
ValueError: 频道用户名不能为空
```

**解决方法**: 在task配置中填写channel_username

### 消息ID范围错误
```
ValueError: 起始消息ID不能大于结束消息ID
```

**解决方法**: 确保start_message_id < end_message_id

## 📊 配置验证

程序启动时会自动验证配置：

- ✅ API配置完整性
- ✅ 频道用户名格式
- ✅ 消息ID范围合理性
- ✅ 数值参数有效性

配置验证失败时，程序会显示具体错误信息并退出。 