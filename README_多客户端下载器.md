# 三客户端消息下载验证程序

这是一个验证多客户端并发下载Telegram消息的核心程序，实现了消息范围分片、异步任务管理和TgCrypto加速等功能。

## 🎯 功能特点

- ✅ **三客户端并发下载** - 使用已生成的3个会话文件
- ✅ **消息范围分片** - 智能分配下载任务到各客户端
- ✅ **异步任务管理** - 使用asyncio实现高效并发
- ✅ **TgCrypto加速** - 启用加密操作硬件加速
- ✅ **智能错误处理** - FloodWait自动处理和重试机制
- ✅ **实时进度监控** - 详细的下载统计和进度显示
- ✅ **文件分类存储** - 按客户端分目录存储下载文件

## 📋 下载任务配置

### 目标频道
- **频道**: https://t.me/csdkl
- **消息范围**: 71986 - 72155
- **总消息数**: 170条

### 分片策略
- **客户端1**: 消息 71986 - 72042 (57条)
- **客户端2**: 消息 72043 - 72099 (57条) 
- **客户端3**: 消息 72100 - 72155 (56条)

## 🚀 使用方法

### 1. 确保依赖已安装
```bash
pip install -r requirements_simple.txt
```

### 2. 确认会话文件存在
程序会自动使用以下会话文件：
```
sessions/
├── client_session_1.session
├── client_session_2.session
└── client_session_3.session
```

### 3. 运行下载程序
```bash
python multi_client_downloader.py
```

## 📁 输出结构

下载完成后，文件将按以下结构存储：

```
downloads/
├── client_1/
│   ├── msg_71986_filename.ext
│   ├── msg_71987_filename.ext
│   └── messages.txt
├── client_2/
│   ├── msg_72043_filename.ext
│   ├── msg_72044_filename.ext
│   └── messages.txt
└── client_3/
    ├── msg_72100_filename.ext
    ├── msg_72101_filename.ext
    └── messages.txt
```

## 📊 性能监控

程序提供实时监控信息：

### 运行时监控
- 每个客户端的下载进度
- 成功/失败统计
- FloodWait处理状态
- 实时下载速度

### 完成后统计
- 总下载数量和成功率
- 总耗时和平均速度
- 各客户端性能对比
- 错误详情和建议

## ⚙️ 核心技术实现

### 1. 消息范围分片算法
```python
# 智能分配算法，处理余数分配
messages_per_client = TOTAL_MESSAGES // client_count
remainder = TOTAL_MESSAGES % client_count

# 前几个客户端分配余数
for i in range(client_count):
    extra = 1 if i < remainder else 0
    messages_for_this_client = messages_per_client + extra
```

### 2. 异步任务管理
```python
# 并发执行多个客户端任务
tasks = [
    client_task(clients[i], message_ranges[i], i)
    for i in range(len(clients))
]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### 3. 批量消息获取
```python
# 每次获取100条消息，减少API调用次数
batch_size = 100
for i in range(0, len(message_ids), batch_size):
    batch_ids = message_ids[i:i + batch_size]
    messages = await client.get_messages(TARGET_CHANNEL, batch_ids)
```

### 4. 智能错误处理
```python
# 自动处理FloodWait
try:
    messages = await client.get_messages(TARGET_CHANNEL, batch_ids)
except FloodWait as e:
    logger.warning(f"遇到限流，等待 {e.value} 秒")
    await asyncio.sleep(e.value)
```

## 🔧 配置参数说明

### 客户端配置
- `workers=4` - 每个客户端4个工作线程
- `max_concurrent_transmissions=2` - 最多2个并发传输
- `sleep_threshold=10` - 10秒内的FloodWait自动处理

### 下载配置
- `batch_size=100` - 每批获取100条消息
- `asyncio.sleep(0.1)` - 批次间0.1秒延迟

## 📈 性能优化

### 1. TgCrypto加速
- 自动检测TgCrypto安装状态
- 启用硬件加速的加密操作
- 显著提升MTProto协议性能

### 2. 并发优化
- 三客户端并行下载
- 异步I/O操作
- 智能任务分配

### 3. 网络优化
- SOCKS5代理支持
- 连接池复用
- 自动重连机制

## ⚠️ 注意事项

1. **会话文件**: 确保三个会话文件已正确生成且可用
2. **代理设置**: 根据网络环境配置正确的代理信息
3. **频道权限**: 确保账户有权限访问目标频道
4. **存储空间**: 确保有足够的磁盘空间存储下载文件
5. **网络稳定**: 保持网络连接稳定，避免频繁断线

## 🐛 故障排除

### 常见问题
1. **会话文件无效**: 重新运行会话生成程序
2. **代理连接失败**: 检查代理服务器状态
3. **频道访问被拒**: 确认账户权限和频道可访问性
4. **下载速度慢**: 检查网络连接和代理性能

### 日志分析
程序提供详细的日志输出，包括：
- 客户端连接状态
- 消息获取进度
- 文件下载状态
- 错误详情和建议

## 📝 示例输出

```
2024-01-20 10:00:00 - INFO - 🚀 开始三客户端消息下载验证
2024-01-20 10:00:00 - INFO - 目标频道: csdkl
2024-01-20 10:00:00 - INFO - 消息范围: 71986 - 72155 (共 170 条)
2024-01-20 10:00:01 - INFO - 客户端 1 分配范围: 71986 - 72042 (57 条消息)
2024-01-20 10:00:01 - INFO - 客户端 2 分配范围: 72043 - 72099 (57 条消息)
2024-01-20 10:00:01 - INFO - 客户端 3 分配范围: 72100 - 72155 (56 条消息)
...
============================================================
📊 下载结果统计
============================================================
客户端1: 55 成功, 2 失败 (范围: 71986-72042)
客户端2: 57 成功, 0 失败 (范围: 72043-72099)
客户端3: 54 成功, 2 失败 (范围: 72100-72155)
------------------------------------------------------------
总计: 166 成功, 4 失败
成功率: 97.6%
耗时: 45.2 秒
平均速度: 3.7 条/秒
下载目录: E:\pythonProject\multiDownloadPyrogram\downloads
============================================================
```

这个程序验证了多客户端并发下载的核心功能，为后续完整的消息管理系统奠定了基础。
