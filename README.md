# MultiDownloadPyrogram - 高性能Telegram媒体下载工具

## 🎯 项目简介

MultiDownloadPyrogram是一个基于Pyrogram框架开发的高性能Telegram频道历史消息批量下载工具，支持多客户端并发下载、代理管理、现代化GUI界面等功能。

## ✨ 核心特性

- **🚀 多客户端并发**: 使用3-5个Pyrogram客户端并行下载，大幅提升下载速度
- **📱 现代化GUI**: 基于tkinter的现代化用户界面，支持实时进度监控
- **🔗 代理管理**: 完整的代理管理系统，支持SOCKS5/HTTP代理，自动测试和切换
- **📂 媒体组支持**: 完整下载Telegram相册中的所有文件
- **⚡ 分片下载**: 大文件(>50MB)自动分片并行下载，最大化网络利用率
- **🎯 高稳定性**: 支持1000+条消息稳定下载，失败率<5%
- **🔄 智能重试**: 自动重试机制，处理网络波动和API限流
- **📊 进度监控**: 实时显示下载进度、速度、统计信息
- **⚙️ 配置管理**: 完整的配置系统，支持导入/导出配置文件

## 🛠️ 安装和运行

### 环境要求

- Python 3.8+
- Windows/Linux/macOS

### 快速开始

1. **克隆项目**
```bash
git clone https://github.com/your-username/multiDownloadPyrogram.git
cd multiDownloadPyrogram
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **启动GUI界面**
```bash
python run_gui.py
```

或双击运行：
```bash
# Windows
run_gui.bat

# Linux/macOS
chmod +x run_gui.sh && ./run_gui.sh
```

## 🔧 配置说明

### 首次使用配置

1. **获取Telegram API信息**
   - 访问 [https://my.telegram.org/auth](https://my.telegram.org/auth)
   - 登录并创建应用
   - 记录API ID和API Hash

2. **配置API信息**
   - 启动程序后，点击"设置" -> "配置设置"
   - 在Telegram标签页中填入：
     - API ID: 你的API ID
     - API Hash: 你的API Hash
     - 电话号码: 你的手机号码（包含国家代码，如+86）
   - 点击"保存"

3. **首次认证**
   - 保存配置后，程序会自动进行认证
   - 根据提示输入收到的验证码
   - 认证成功后会自动保存会话信息

### 配置文件说明

程序会创建`config.json`配置文件，你也可以参考`config.example.json`：

```json
{
  "telegram": {
    "api_id": 12345678,
    "api_hash": "your_api_hash_here",
    "phone_number": "+86138xxxxxxxx",
    "session_string": ""
  },
  "proxy": {
    "enabled": true,
    "scheme": "socks5",
    "hostname": "127.0.0.1",
    "port": 7890
  },
  "download": {
    "download_path": "downloads",
    "max_concurrent_downloads": 5,
    "max_clients": 3,
    "skip_existing": true
  }
}
```

## 🎮 使用指南

### GUI界面使用

1. **主界面**
   - 输入频道用户名（如：@channelname）
   - 设置下载选项（消息数量限制、ID范围等）
   - 点击"开始下载"

2. **配置管理**
   - 菜单栏 -> "设置" -> "配置设置"
   - 支持Telegram、代理、下载、日志配置
   - 可以导入/导出配置文件

3. **代理管理**
   - 菜单栏 -> "工具" -> "代理管理"
   - 添加多个代理服务器
   - 测试代理连接状态
   - 自动切换最佳代理

4. **进度监控**
   - 菜单栏 -> "视图" -> "进度窗口"
   - 实时显示下载进度
   - 速度和完成时间估算
   - 任务管理和控制

5. **日志查看**
   - 菜单栏 -> "视图" -> "日志窗口"
   - 实时查看程序运行日志
   - 按级别过滤日志
   - 搜索和导出功能

### 命令行使用

```bash
# 基本用法
python src/main.py --channel @channelname

# 指定下载数量
python src/main.py --channel @channelname --limit 100

# 指定消息ID范围
python src/main.py --channel @channelname --start-id 1000 --end-id 2000

# 使用配置文件
python src/main.py --config config.json --channel @channelname
```

## 🔍 常见问题

### 1. 配置验证失败

**问题**: 提示"API ID不能为空"或"API Hash不能为空"

**解决方案**:
- 确保已正确填写API ID和API Hash
- 检查API信息是否来自 [https://my.telegram.org/auth](https://my.telegram.org/auth)
- 确保API ID是纯数字，API Hash是32位字符串

### 2. 客户端连接失败

**问题**: 提示"Invalid base64-encoded string"或连接错误

**解决方案**:
- 检查网络连接
- 确认代理设置正确（如果使用代理）
- 删除`sessions/`目录重新认证
- 检查防火墙设置

### 3. 下载速度慢

**解决方案**:
- 检查网络环境
- 启用代理（如果网络受限）
- 调整并发设置：配置 -> 下载 -> 最大并发数
- 检查代理服务器性能

### 4. 频繁触发限流

**解决方案**:
- 降低并发数量
- 增加重试延迟
- 使用高质量代理
- 分时段下载

### 5. 代理连接测试失败

**解决方案**:
- 检查代理服务器是否运行
- 确认代理地址和端口正确
- 检查代理认证信息
- 测试代理是否支持目标协议

## 📊 性能优化建议

### 网络优化
- 使用高质量的代理服务器
- 合理设置并发数量（建议3-5个客户端）
- 避免在网络高峰期下载

### 系统优化
- 确保足够的磁盘空间
- 使用SSD硬盘提高写入性能
- 适当调整系统网络缓冲区设置

### 程序优化
- 定期清理日志文件
- 及时删除不需要的会话文件
- 关闭不必要的GUI窗口

## 🛡️ 安全注意事项

1. **API密钥安全**
   - 不要分享你的API ID和API Hash
   - 定期更换API密钥
   - 使用环境变量存储敏感信息

2. **会话安全**
   - 妥善保管会话文件
   - 不要在不安全的网络环境下使用
   - 定期清理旧的会话文件

3. **代理安全**
   - 使用可信的代理服务器
   - 避免使用免费的公共代理
   - 定期检查代理服务器日志

## 📚 技术架构

### 项目结构
```
multiDownloadPyrogram/
├── src/
│   ├── client/          # 客户端管理
│   ├── downloader/      # 下载器模块
│   ├── task/           # 任务管理
│   ├── utils/          # 工具模块
│   └── gui/            # GUI界面
├── tests/              # 测试用例
├── config.example.json # 配置示例
└── requirements.txt    # 依赖文件
```

### 核心模块
- **ClientManager**: 管理单个Pyrogram客户端
- **ClientPool**: 管理多个客户端的连接池
- **MediaDownloader**: 处理媒体文件下载
- **ChunkDownloader**: 实现大文件分片下载
- **GroupDownloader**: 处理媒体组下载
- **TaskManager**: 管理下载任务队列
- **ProxyManager**: 管理代理服务器

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 📄 许可证

本项目采用MIT许可证。详情请参阅 [LICENSE](LICENSE) 文件。

## 📞 支持

如果您在使用过程中遇到问题，请：

1. 查看本文档的常见问题部分
2. 检查 [Issues](https://github.com/your-username/multiDownloadPyrogram/issues) 页面
3. 创建新的Issue描述问题
4. 提供详细的错误信息和日志

## 🙏 致谢

感谢以下项目的支持：
- [Pyrogram](https://github.com/pyrogram/pyrogram) - 优秀的Telegram客户端库
- [tkinter](https://docs.python.org/3/library/tkinter.html) - Python GUI工具包
- [aiohttp](https://github.com/aio-libs/aiohttp) - 异步HTTP客户端库

---

⭐ 如果这个项目对你有帮助，请给我们一个星标！