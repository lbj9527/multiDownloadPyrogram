# Telegram 三客户端会话文件生成程序

这是一个简单的 Telegram 会话文件生成程序，用于创建三个客户端的会话文件，支持 SOCKS5 代理。

## 功能特点

- ✅ 三个客户端共用 API ID、API Hash 和电话号码
- ✅ 使用不同的会话文件名称
- ✅ 支持 SOCKS5 代理
- ✅ 自动创建 sessions 目录
- ✅ 简单易用，无复杂验证
- ✅ 顺序创建会话文件，间隔 1 分钟
- ✅ 自动倒计时显示，避免频率限制

## 安装依赖

```bash
pip install -r requirements_simple.txt
```

## 使用方法

### 1. 配置程序

编辑 `simple_session_generator.py` 文件，修改配置区域的变量：

```python
# Telegram API 配置（三个客户端共用）
API_ID = 12345678  # 替换为您的API ID
API_HASH = "your_api_hash_here"  # 替换为您的API Hash
PHONE_NUMBER = "+1234567890"  # 替换为您的电话号码

# 三个客户端的会话名称
SESSION_NAMES = [
    "client_session_1",
    "client_session_2",
    "client_session_3"
]

# SOCKS5 代理配置
PROXY_HOST = "127.0.0.1"  # 代理服务器地址
PROXY_PORT = 1080  # 代理端口
PROXY_USERNAME = None  # 代理用户名（如果需要）
PROXY_PASSWORD = None  # 代理密码（如果需要）
```

### 2. 运行程序

```bash
python simple_session_generator.py
```

### 3. 按提示操作

1. 程序会显示当前配置信息，确认无误后继续
2. 程序会自动创建 `sessions` 目录
3. **顺序模式**依次为每个客户端创建会话文件：
   - 发送验证码到您的手机
   - 输入收到的验证码
   - 如果启用了双重验证，输入密码
   - 会话文件创建成功
   - **自动等待 1 分钟**后创建下一个会话（避免频率限制）
   - 显示倒计时进度

## 输出结果

程序运行成功后，会在 `sessions` 目录下生成三个会话文件：

```
sessions/
├── client_session_1.session
├── client_session_2.session
└── client_session_3.session
```

## 注意事项

1. **API 配置**: 确保 API ID 和 API Hash 正确，可从 https://my.telegram.org 获取
2. **电话号码**: 必须是注册 Telegram 的手机号码，包含国家代码
3. **代理设置**: 如果网络环境需要代理，请正确配置 SOCKS5 代理信息
4. **验证码**: 验证码有时效性，请及时输入
5. **双重验证**: 如果账户启用了双重验证，需要输入密码
6. **会话文件**: 生成的会话文件请妥善保管，不要泄露给他人

## 常见问题

### Q: 提示"请求过于频繁"怎么办？

A: 这是 Telegram 的限流保护，请等待提示的时间后重试。

### Q: 验证码输入错误怎么办？

A: 程序会提示错误，可以重新运行程序获取新的验证码。

### Q: 代理连接失败怎么办？

A: 检查代理服务器是否正常运行，确认代理地址和端口配置正确。

### Q: 会话文件已存在怎么办？

A: 程序会询问是否重新创建，选择"y"会删除旧文件并创建新的。

## 技术说明

- **Pyrogram**: 使用 Pyrogram 库与 Telegram API 交互
- **异步处理**: 使用 asyncio 进行异步操作
- **代理支持**: 内置 SOCKS5 代理支持
- **错误处理**: 包含基本的错误处理和用户提示

## 文件结构

```
.
├── simple_session_generator.py  # 主程序
├── requirements_simple.txt      # 依赖文件
├── README_简单会话生成器.md     # 使用说明
└── sessions/                    # 会话文件目录（自动创建）
    ├── client_session_1.session
    ├── client_session_2.session
    └── client_session_3.session
```

## 许可证

本程序仅供学习和个人使用，请遵守 Telegram 的服务条款。
