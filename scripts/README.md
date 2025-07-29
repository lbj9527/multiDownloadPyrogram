# Scripts 目录

这个目录包含项目的辅助脚本和工具。

## 📁 文件列表

### `simple_session_generator.py`

智能会话文件生成程序，用于为多客户端下载器创建 Telegram 会话文件。

## 🚀 使用方法

### 会话文件生成器

```bash
# 从项目根目录运行
python scripts/simple_session_generator.py
```

## ✨ 新功能特性

### 智能配置读取

- ✅ **自动读取客户端数量**: 从配置文件读取 `max_concurrent_clients` 参数
- ✅ **动态会话名称**: 根据客户端数量自动生成对应数量的会话文件
- ✅ **配置文件集成**: 与主程序配置保持一致
- ✅ **环境变量支持**: 支持通过 `MAX_CONCURRENT_CLIENTS` 环境变量控制

### 智能增量创建 🆕

- ✅ **会话文件检测**: 自动检测已存在的会话文件
- ✅ **增量创建**: 只创建缺失的会话文件，跳过已存在的
- ✅ **完整性验证**: 验证所有需要的会话文件是否完整
- ✅ **多余文件提醒**: 识别并提醒多余的会话文件

### 配置示例

#### 通过环境变量设置

```bash
# 设置客户端数量为2
export MAX_CONCURRENT_CLIENTS=2

# 运行会话生成器
python scripts/simple_session_generator.py
```

#### 配置文件设置

程序会自动读取项目配置文件中的以下参数：

- `max_concurrent_clients`: 客户端数量
- `session_directory`: 会话文件目录
- `DEFAULT_SESSION_NAMES`: 会话文件名称模板

### 输出示例

#### 客户端数量为 2 时

```
sessions/
├── client_session_1.session
└── client_session_2.session
```

#### 客户端数量为 3 时（默认）

```
sessions/
├── client_session_1.session
├── client_session_2.session
└── client_session_3.session
```

## 🚀 智能增量创建示例

### 场景 1: 首次运行（无会话文件）

```bash
export MAX_CONCURRENT_CLIENTS=4
python scripts/simple_session_generator.py
```

**输出:**

```
🔍 分析已存在的会话文件...
📊 会话文件分析结果:
   需要的会话总数: 4
   已存在的会话: 0 个
   需要创建的会话: 4 个
     - client_session_1, client_session_2, client_session_3, client_session_4

🔄 开始顺序创建 4 个缺失的会话文件
```

### 场景 2: 增加客户端数量（已有 3 个，需要 4 个）

```bash
# 当前已有: client_session_1.session, client_session_2.session, client_session_3.session
export MAX_CONCURRENT_CLIENTS=4
python scripts/simple_session_generator.py
```

**输出:**

```
🔍 分析已存在的会话文件...
📊 会话文件分析结果:
   需要的会话总数: 4
   已存在的会话: 3 个
     - client_session_1, client_session_2, client_session_3
   需要创建的会话: 1 个
     - client_session_4

❓ 是否创建缺失的 1 个会话文件？
继续创建？(y/n): y

🔄 开始顺序创建 1 个缺失的会话文件
```

### 场景 3: 所有会话文件已存在

```bash
# 当前已有所有需要的会话文件
export MAX_CONCURRENT_CLIENTS=3
python scripts/simple_session_generator.py
```

**输出:**

```
🔍 分析已存在的会话文件...
📊 会话文件分析结果:
   需要的会话总数: 3
   已存在的会话: 3 个
     - client_session_1, client_session_2, client_session_3
   需要创建的会话: 0 个

✅ 所有需要的会话文件都已存在，无需创建新的会话文件！
📁 会话目录: E:\pythonProject\multiDownloadPyrogram\sessions
📝 可用会话: client_session_1, client_session_2, client_session_3

✨ 程序执行完成!
```

### 场景 4: 有多余的会话文件

```bash
# 当前有: client_session_1~5.session, old_session.session
export MAX_CONCURRENT_CLIENTS=3
python scripts/simple_session_generator.py
```

**输出:**

```
📊 会话文件分析结果:
   需要的会话总数: 3
   已存在的会话: 6 个
     - client_session_1, client_session_2, client_session_3, client_session_4, client_session_5, old_session
   需要创建的会话: 0 个
   多余的会话文件: 3 个
     - client_session_4, client_session_5, old_session
     (这些文件不会被删除，但不会被主程序使用)

✅ 所有需要的会话文件都已存在，无需创建新的会话文件！
```

## 🔧 技术改进

1. **模块化设计**: 与主项目配置系统集成
2. **错误处理**: 配置加载失败时自动回退到默认配置
3. **智能提示**: 显示当前配置和修改方法
4. **路径管理**: 自动处理项目路径和模块导入

## 📋 配置参数

| 参数       | 环境变量                 | 默认值    | 说明                 |
| ---------- | ------------------------ | --------- | -------------------- |
| 客户端数量 | `MAX_CONCURRENT_CLIENTS` | 3         | 要创建的会话文件数量 |
| API ID     | `API_ID`                 | -         | Telegram API ID      |
| API Hash   | `API_HASH`               | -         | Telegram API Hash    |
| 电话号码   | `PHONE_NUMBER`           | -         | Telegram 注册手机号  |
| 代理主机   | `PROXY_HOST`             | 127.0.0.1 | SOCKS5 代理地址      |
| 代理端口   | `PROXY_PORT`             | 7890      | SOCKS5 代理端口      |

## 💡 使用建议

1. **首次使用**: 先设置好 API 凭据和代理配置
2. **客户端数量**: 根据实际需要设置，建议 1-5 个
3. **网络环境**: 确保代理配置正确（如果需要）
4. **会话管理**: 生成的会话文件请妥善保管

## 🔄 与主程序的关系

```
scripts/simple_session_generator.py
    ↓ 生成会话文件
sessions/client_session_*.session
    ↓ 被主程序使用
main.py (多客户端下载器)
```

这个脚本是整个多客户端下载系统的**基础设施组件**，为后续的并发下载操作提供必要的认证会话。
