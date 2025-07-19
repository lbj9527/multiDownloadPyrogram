# Telegram多客户端消息下载器

一款功能强大的Telegram消息管理工具，专注于多客户端消息下载功能，支持高效并发下载和智能错误处理。

## 🌟 功能特性

### 核心功能
- 🚀 **多客户端池管理** - 普通账户支持3个客户端，Premium账户支持4个客户端
- 📥 **高效消息下载** - 支持从指定频道下载指定数量的消息（1-1000条）
- 🎯 **智能文件命名** - 自动生成格式：日期_ID_频道名_原始文件名.扩展名
- 📊 **实时进度显示** - 下载进度、速度、剩余时间、文件计数等
- 🔄 **错误处理机制** - 自动处理FloodWait、网络错误、重连等
- 🎨 **现代化界面** - 基于CustomTkinter的原生Windows体验

### 高级特性
- 🛡️ **安全可靠** - 支持会话管理、数据加密、配置验证
- 📱 **多媒体支持** - 图片、视频、文档、音频、语音、贴纸等
- 🔍 **智能过滤** - 按媒体类型、文件大小、消息类型过滤
- 📈 **性能优化** - 异步并发下载，多客户端负载均衡
- 📝 **详细日志** - 结构化日志记录，支持级别过滤和导出
- ⚙️ **配置管理** - 支持配置导入导出、备份恢复

## 💻 系统要求

- **操作系统**: Windows 10/11 (x64)
- **Python版本**: 3.8 或更高版本
- **内存**: 建议 4GB 以上
- **存储空间**: 根据下载内容而定
- **网络**: 稳定的互联网连接

## 🚀 快速开始

### 方法一：自动安装（推荐）

1. **下载项目**
```bash
git clone https://github.com/lbj9527/multiDownloadPyrogram.git
cd multiDownloadPyrogram
```

2. **运行安装程序**
```bash
python install.py
```

3. **启动应用**
- 双击 `启动应用.bat` 文件
- 或运行: `python main.py`

### 方法二：手动安装

1. **克隆项目**
```bash
git clone https://github.com/lbj9527/multiDownloadPyrogram.git
cd multiDownloadPyrogram
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **创建目录**
```bash
mkdir downloads logs sessions config
```

4. **运行程序**
```bash
python main.py
```

## 📖 详细使用说明

### 1. 获取Telegram API凭据

在使用本工具之前，您需要获取Telegram API凭据：

1. 访问 [https://my.telegram.org/apps](https://my.telegram.org/apps)
2. 使用您的Telegram账户登录
3. 创建新应用，填写应用信息
4. 获取 `API ID` 和 `API Hash`

### 2. 配置客户端

1. **选择账户类型**
   - 普通账户：支持3个客户端
   - Premium账户：支持4个客户端

2. **填写客户端信息**
   - **API ID**: 从Telegram获取的数字ID
   - **API Hash**: 从Telegram获取的32位哈希值
   - **电话号码**: 包含国家代码（如+86138...）
   - **会话名称**: 唯一的标识名称

3. **登录客户端**
   - 按顺序逐个登录客户端
   - 首次登录需要验证码
   - 如有双重验证需要输入密码

### 3. 下载消息

1. **基本设置**
   - **频道ID**: 输入频道用户名（@channelname）或ID
   - **起始消息ID**: 从哪条消息开始下载（默认1）
   - **消息数量**: 要下载的消息数量（1-1000）
   - **下载路径**: 文件保存位置

2. **高级选项**
   - **包含内容**: 选择下载媒体文件和/或文本消息
   - **媒体类型**: 选择要下载的媒体类型
   - **文件大小限制**: 设置最大文件大小（可选）

3. **开始下载**
   - 点击"开始下载"按钮
   - 实时查看下载进度
   - 可以随时取消下载

### 4. 查看日志

- **实时日志**: 在"日志查看"选项卡查看运行日志
- **过滤功能**: 按级别（DEBUG/INFO/WARNING/ERROR）和类型过滤
- **导出日志**: 将日志导出为文本文件
- **自动滚动**: 自动滚动到最新日志

## 🔧 配置说明

### 应用配置 (config/app_config.json)
```json
{
  "app": {
    "name": "Telegram消息管理器",
    "version": "1.0.0",
    "theme": "dark",
    "window_size": {"width": 1200, "height": 800}
  },
  "download": {
    "default_path": "./downloads",
    "max_concurrent_downloads": 5,
    "timeout": 30
  },
  "logging": {
    "level": "INFO",
    "file_path": "./logs/app.log"
  }
}
```

### 客户端配置 (config/client_config.json)
```json
{
  "account_type": "normal",
  "clients": [
    {
      "api_id": 123456,
      "api_hash": "your_api_hash",
      "phone_number": "+8613800138000",
      "session_name": "session_1",
      "enabled": true
    }
  ]
}
```

## 🧪 测试

### 运行测试
```bash
# 运行所有测试
python run_tests.py

# 或使用pytest
pip install pytest
pytest tests/ -v
```

### 测试覆盖
- ✅ 数据模型验证测试
- ✅ 配置管理测试
- ✅ 文件工具测试
- ✅ 错误处理测试
- ✅ 性能测试

## 📁 项目结构

```
multiDownloadPyrogram/
├── src/                          # 源代码目录
│   ├── models/                   # 数据模型
│   │   ├── client_config.py      # 客户端配置模型
│   │   ├── download_config.py    # 下载配置模型
│   │   └── events.py             # 事件模型
│   ├── core/                     # 核心功能
│   │   ├── client_manager.py     # 客户端管理器
│   │   ├── download_manager.py   # 下载管理器
│   │   └── event_manager.py      # 事件管理器
│   ├── ui/                       # 用户界面
│   │   ├── main_window.py        # 主窗口
│   │   ├── client_config_frame.py # 客户端配置界面
│   │   ├── download_frame.py     # 下载界面
│   │   └── log_frame.py          # 日志界面
│   └── utils/                    # 工具模块
│       ├── config_manager.py     # 配置管理
│       ├── error_handler.py      # 错误处理
│       ├── file_utils.py         # 文件工具
│       └── logger.py             # 日志系统
├── tests/                        # 测试文件
├── config/                       # 配置文件
├── downloads/                    # 下载目录
├── logs/                         # 日志目录
├── sessions/                     # 会话文件
├── main.py                       # 主程序入口
├── install.py                    # 安装脚本
├── run_tests.py                  # 测试脚本
└── requirements.txt              # 依赖列表
```

## ⚠️ 注意事项

### 使用限制
- 遵守Telegram的服务条款和API使用限制
- 不要用于商业用途或大规模数据采集
- 尊重频道所有者的版权和隐私
- 合理设置下载频率，避免触发限流

### 安全建议
- 妥善保管API凭据，不要泄露给他人
- 定期备份会话文件和配置
- 使用强密码保护Telegram账户
- 在公共网络环境下谨慎使用

### 性能优化
- 根据网络状况调整并发数量
- 合理设置文件大小限制
- 定期清理下载目录和日志文件
- 监控系统资源使用情况

## 🐛 故障排除

### 常见问题

**Q: 客户端登录失败**
A: 检查API凭据是否正确，网络连接是否正常，电话号码格式是否包含国家代码

**Q: 下载速度慢**
A: 检查网络连接，尝试减少并发客户端数量，或更换网络环境

**Q: 触发FloodWait限制**
A: 这是Telegram的保护机制，程序会自动等待，请耐心等待

**Q: 文件下载失败**
A: 检查磁盘空间，文件权限，或尝试重新下载

**Q: 界面显示异常**
A: 尝试切换主题，重启应用，或检查系统兼容性

### 日志分析
- 查看 `logs/app.log` 了解详细错误信息
- 使用日志过滤功能定位特定问题
- 导出日志文件用于问题报告

### 获取帮助
- 查看GitHub Issues页面
- 提交详细的错误报告
- 包含日志文件和系统信息

## 🔄 更新日志

### v1.0.0 (2024-01-XX)
- ✨ 初始版本发布
- 🚀 多客户端池管理
- 📥 消息下载功能
- 🎨 现代化UI界面
- 📝 完整的日志系统
- 🔧 配置管理系统

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 开发环境设置
```bash
# 克隆项目
git clone https://github.com/lbj9527/multiDownloadPyrogram.git
cd multiDownloadPyrogram

# 安装开发依赖
pip install -r requirements.txt
pip install pytest flake8 black mypy

# 运行测试
python run_tests.py
```

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [Pyrogram](https://github.com/pyrogram/pyrogram) - 优秀的Telegram客户端库
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - 现代化的Tkinter UI库
- [Loguru](https://github.com/Delgan/loguru) - 强大的Python日志库
- [Pydantic](https://github.com/pydantic/pydantic) - 数据验证库

## 📞 联系方式

- GitHub: [@lbj9527](https://github.com/lbj9527)
- Email: 1147431798@qq.com
- 项目地址: [https://github.com/lbj9527/multiDownloadPyrogram](https://github.com/lbj9527/multiDownloadPyrogram)

---

**免责声明**: 本工具仅供学习和个人使用，请遵守相关法律法规和Telegram服务条款。开发者不对使用本工具产生的任何后果承担责任。
