# 快速开始指南

## 🚀 5分钟快速上手

### 第一步：安装依赖

```bash
pip install -r requirements.txt
```

### 第二步：获取API凭据

1. 访问 [my.telegram.org](https://my.telegram.org)
2. 登录你的Telegram账号
3. 点击 "API development tools"
4. 创建新应用，记录下 `api_id` 和 `api_hash`

### 第三步：配置API

**方法一：环境变量（推荐）**
```bash
# Windows
set TELEGRAM_API_ID=12345678
set TELEGRAM_API_HASH=your_api_hash_here

# Linux/Mac
export TELEGRAM_API_ID=12345678
export TELEGRAM_API_HASH=your_api_hash_here
```

**方法二：配置文件**
```bash
cp config.example.json config.json
# 编辑config.json，填入你的API信息
```

### 第四步：配置任务

编辑 `config.json` 文件，设置下载任务：

```json
{
  "api": {
    "api_id": 12345678,
    "api_hash": "your_api_hash_here"
  },
  "task": {
    "channel_username": "@channel_name",
    "start_message_id": null,
    "end_message_id": null,
    "limit": 1000
  }
}
```

### 第五步：运行程序

```bash
# 使用配置文件运行
python -m src.main

# 或者使用简化脚本
python run.py
```

## 📝 常用命令

```bash
# 下载指定范围的消息
python -m src.main @channel_name --start 1000 --end 2000

# 限制下载数量
python -m src.main @channel_name --limit 100

# 健康检查
python -m src.main --health-check

# 使用自定义配置
python -m src.main @channel_name --config my_config.json
```

## ⚙️ 基础配置

### 最小配置文件 (config.json)
```json
{
  "api": {
    "api_id": 12345678,
    "api_hash": "your_api_hash_here"
  }
}
```

### 完整配置文件
```json
{
  "api": {
    "api_id": 12345678,
    "api_hash": "your_api_hash_here"
  },
  "proxy": {
    "scheme": "socks5",
    "hostname": "127.0.0.1",
    "port": 7890
  },
  "download": {
    "client_count": 3,
    "download_dir": "downloads",
    "max_retries": 3
  }
}
```

## 🔧 首次运行

第一次运行时，程序会：

1. **创建会话文件**：为每个客户端创建独立的会话
2. **请求认证**：需要输入手机号和验证码
3. **创建目录**：自动创建下载目录和日志目录

```
项目目录/
├── sessions/           # 会话文件（自动创建）
├── downloads/          # 下载文件（自动创建）
├── logs/              # 日志文件（自动创建）
└── config.json        # 配置文件（需要创建）
```

## 📱 认证流程

首次运行时会看到类似输出：
```
请输入手机号 (国际格式，如 +1234567890): +1234567890
请输入验证码: 12345
```

认证成功后，会话文件会保存认证信息，下次运行无需重新认证。

## 🎯 使用示例

### 示例1：下载频道最新100条媒体
```bash
python -m src.main @example_channel --limit 100
```

### 示例2：下载指定时间段的消息
```bash
python -m src.main @example_channel --start 5000 --end 6000
```

### 示例3：使用代理下载
```bash
# 编辑config.json添加代理配置，然后运行
python -m src.main @example_channel
```

## 📊 输出示例

```
2024-12-XX 10:00:00 - MultiDownloadPyrogram - INFO - MultiDownloadPyrogram 启动
2024-12-XX 10:00:01 - MultiDownloadPyrogram - INFO - 使用 3 个客户端进行下载
2024-12-XX 10:00:02 - MultiDownloadPyrogram - INFO - 获取到 150 条消息
2024-12-XX 10:00:03 - MultiDownloadPyrogram - INFO - 其中包含媒体的消息: 45 条
2024-12-XX 10:00:04 - MultiDownloadPyrogram - INFO - 开始下载会话，预计下载 45 个文件
...
2024-12-XX 10:05:30 - MultiDownloadPyrogram - INFO - 下载完成: 成功 43, 失败 2, 跳过 0
```

## ❗ 常见问题

### Q: 提示"没有可用的客户端"
A: 检查API配置是否正确，确保网络连接正常

### Q: FloodWait错误
A: 程序会自动处理，耐心等待即可

### Q: 代理连接失败
A: 确认代理服务器正常运行，检查配置是否正确

### Q: 认证失败
A: 删除sessions目录，重新运行程序进行认证

## 🎉 成功运行标志

看到以下输出说明程序运行成功：
```
==================================================
下载统计:
  频道: @example_channel
  总消息数: 150
  媒体消息数: 45
  下载成功: 43
  下载失败: 2
  跳过文件: 0
  成功率: 95.6%
==================================================
```

## 📞 获取帮助

- 查看完整文档：`README.md`
- 查看命令行帮助：`python -m src.main --help`
- 查看需求文档：`requirements_document.md`

祝你使用愉快！🎉 

## 📝 配置说明

### 任务配置参数

```json
{
  "task": {
    "channel_username": "@example_channel",  // 必填：目标频道
    "start_message_id": 1000,               // 可选：起始消息ID
    "end_message_id": 2000,                 // 可选：结束消息ID  
    "limit": 500                            // 可选：消息数量限制
  }
}
```

**参数说明**：
- `channel_username`: 目标频道用户名，必须以@开头
- `start_message_id`: 起始消息ID，null表示从最新消息开始
- `end_message_id`: 结束消息ID，null表示不限制
- `limit`: 最大下载消息数量，默认1000