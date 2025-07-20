# 配置持久化问题修复报告

## 🐛 问题描述

用户反馈：修改代理配置后，配置确实保存到了`app_config.json`文件，但关闭程序时，配置又恢复为默认配置。

## 🔍 问题分析

### 根本原因
程序在关闭时会执行以下逻辑（`src/ui/main_window.py:376`）：
```python
def on_closing(self):
    # ...
    # 保存配置
    self.config_manager.save_app_config(self.app_config)  # 问题所在！
    # ...
```

**问题所在**：
1. `self.app_config` 是在程序启动时加载的配置
2. 用户在设置窗口修改配置后，设置窗口会保存到文件，但**没有更新主窗口的 `self.app_config`**
3. 程序关闭时，主窗口用旧的 `self.app_config` 覆盖了用户的修改

### 问题流程
```
1. 程序启动 → 主窗口加载配置到 self.app_config
2. 用户打开设置窗口 → 修改代理配置 → 保存到文件 ✓
3. 主窗口的 self.app_config 仍然是旧配置 ✗
4. 程序关闭 → 用旧的 self.app_config 覆盖文件 ✗
```

## ✅ 修复方案

### 1. 移除程序关闭时的配置保存
**文件**: `src/ui/main_window.py`

**修复前**:
```python
def on_closing(self):
    # ...
    # 保存配置
    self.config_manager.save_app_config(self.app_config)  # 会覆盖用户修改
    # ...
```

**修复后**:
```python
def on_closing(self):
    # ...
    # 重新加载最新配置，避免覆盖用户修改
    self.reload_app_config()
    
    # 关闭窗口（不再保存配置，因为配置已经在设置窗口中保存了）
    self.root.destroy()
    # ...
```

### 2. 添加配置重新加载方法
**文件**: `src/ui/main_window.py`

```python
def reload_app_config(self):
    """重新加载应用配置"""
    try:
        self.app_config = self.config_manager.load_app_config()
        self.logger.debug("应用配置已重新加载")
    except Exception as e:
        self.logger.error(f"重新加载应用配置失败: {e}")
```

### 3. 添加配置更新事件机制
**文件**: `src/models/events.py`

添加了 `ConfigUpdatedEvent` 事件类和创建函数：
```python
class ConfigUpdatedEvent(BaseModel):
    """配置更新事件"""
    event_id: str
    event_type: EventType = EventType.CONFIG_UPDATED
    message: str
    config_type: str
    config_data: Optional[Dict[str, Any]] = None
    # ...
```

### 4. 设置窗口通知主窗口
**文件**: `src/ui/settings_window.py`

在保存配置成功后，通知主窗口重新加载配置：
```python
if self.config_manager.save_app_config(new_config):
    # ...
    # 通知主窗口重新加载配置
    try:
        # 多种方式尝试通知主窗口
        if hasattr(self.parent, 'reload_app_config'):
            self.parent.reload_app_config()
        else:
            # 通过事件系统通知
            event_manager.emit(create_config_updated_event(...))
    except Exception as e:
        self.logger.warning(f"通知主窗口重新加载配置失败: {e}")
```

### 5. 主窗口监听配置更新事件
**文件**: `src/ui/main_window.py`

```python
def _update_ui_from_event(self, event: BaseEvent):
    """从事件更新UI（在主线程中执行）"""
    try:
        # 处理配置更新事件
        if event.event_type == EventType.CONFIG_UPDATED:
            self.reload_app_config()
            self.update_status("配置已更新", "green")
            return
        # ...
```

## 🔧 修复的文件列表

1. **`src/ui/main_window.py`**
   - 添加 `reload_app_config()` 方法
   - 修改 `on_closing()` 方法，移除配置保存逻辑
   - 修改 `_update_ui_from_event()` 方法，监听配置更新事件

2. **`src/ui/settings_window.py`**
   - 修改 `apply_settings()` 方法，添加主窗口通知逻辑

3. **`src/models/events.py`**
   - 添加 `ConfigUpdatedEvent` 事件类
   - 添加 `create_config_updated_event()` 创建函数

## 🧪 验证结果

### 测试场景
1. 启动程序
2. 打开设置窗口
3. 修改代理配置（启用代理，修改主机、端口等）
4. 保存设置
5. 关闭程序
6. 重新启动程序
7. 检查代理配置是否保持

### 测试结果
✅ **修复成功**：用户修改的代理配置在程序重启后完全保持，不再被覆盖。

### 当前配置文件状态
```json
{
  "proxy": {
    "enabled": true,
    "type": "socks5",
    "host": "192.168.1.100",
    "port": 8080,
    "username": "test_user",
    "password": "test_pass",
    "test_url": "https://api.telegram.org"
  }
}
```

## 🔍 其他潜在问题检查

### 已检查的组件
1. **客户端配置框架** (`src/ui/client_config_frame.py`) ✅
   - 只在用户点击"保存配置"按钮时保存
   - 没有程序关闭时的自动保存逻辑

2. **下载框架** (`src/ui/download_frame.py`) ✅
   - 没有配置保存逻辑
   - 不会影响配置持久化

3. **配置管理器** (`src/utils/config_manager.py`) ✅
   - 初始化逻辑正确，只在配置文件不存在时创建默认配置
   - 没有自动覆盖现有配置的逻辑

### 结论
**没有发现其他类似问题**。只有主窗口的关闭逻辑存在配置覆盖问题，现已修复。

## 🎯 修复效果

### 修复前的问题
- ❌ 用户修改代理配置后，程序重启配置丢失
- ❌ 程序关闭时用旧配置覆盖新配置
- ❌ 设置窗口与主窗口配置不同步

### 修复后的效果
- ✅ 用户修改的所有配置在程序重启后完全保持
- ✅ 程序关闭时不再覆盖用户配置
- ✅ 设置窗口保存配置后立即通知主窗口更新
- ✅ 通过事件机制实现配置同步
- ✅ 多重保障确保配置通知成功

## 📋 用户使用指南

现在用户可以放心地：

1. **修改代理设置**：在设置窗口中修改代理配置，点击"确定"保存
2. **修改客户端配置**：在客户端配置界面添加或修改客户端信息
3. **修改应用设置**：主题、窗口大小、下载设置等
4. **关闭程序**：所有配置都会保持，重启后不会丢失

**所有配置修改都是持久的，程序重启后完全保持！**
