# Telegram 运维工具 MVP 版本开发文档

## 📋 项目概述

基于现有的多客户端 Telegram 下载器，开发第一阶段 MVP 版本的 Telegram 运营自动化平台。

### 🎯 MVP 目标

- 基础 Telegram 采集和分发
- 简单模板引擎
- 基础监控功能

## 🏗️ 当前项目状态分析

### ✅ 已完成的核心功能

1. **多客户端管理** (`core/client/`)

   - 支持多账号并发操作
   - 会话管理和自动重连
   - 代理配置和网络优化

2. **消息采集** (`core/message/`)

   - 并发消息获取
   - 媒体组智能分组
   - 消息范围指定采集

3. **媒体下载** (`core/download/`)

   - 智能下载策略选择
   - 流式下载和 RAW API 下载
   - 文件完整性验证

4. **监控统计** (`monitoring/`)
   - 实时带宽监控
   - 下载进度统计
   - 性能数据收集

### 🔧 需要扩展的功能

1. **内容分发模块** - 新增
2. **模板引擎** - 新增
3. **Web 管理界面** - 新增
4. **任务调度系统** - 新增

## 🚀 MVP 开发计划

### 阶段 1: 内容分发模块 (2 周)

#### 1.1 分发管理器

```python
# core/distribution/distribution_manager.py
class DistributionManager:
    """内容分发管理器"""

    async def send_message(self, client, channel, content, template=None)
    async def send_media_group(self, client, channel, media_group, template=None)
    async def batch_distribute(self, content_list, target_channels)
```

#### 1.2 频道管理

```python
# core/distribution/channel_manager.py
class ChannelManager:
    """目标频道管理"""

    def add_target_channel(self, channel_id, config)
    def remove_target_channel(self, channel_id)
    def get_channel_config(self, channel_id)
    def validate_channel_permissions(self, client, channel_id)
```

#### 1.3 发送策略

```python
# core/distribution/send_strategy.py
class SendStrategy:
    """发送策略管理"""

    def calculate_send_delay(self, channel_config)
    def check_rate_limit(self, channel_id)
    def handle_send_error(self, error, retry_count)
```

### 阶段 2: 简单模板引擎 (2 周)

#### 2.1 模板系统

```python
# core/template/template_engine.py
class TemplateEngine:
    """简单模板引擎"""

    def render_text(self, template, variables)
    def render_media_caption(self, template, media_info, variables)
    def apply_formatting(self, text, format_type)  # HTML/Markdown
```

#### 2.2 内置模板

```python
# core/template/builtin_templates.py
BUILTIN_TEMPLATES = {
    'simple_forward': '{title}\n\n{description}',
    'media_share': '📸 {title}\n\n{description}\n\n🔗 来源: {source}',
    'news_format': '📰 {title}\n\n{summary}\n\n⏰ {publish_time}',
    'product_promo': '🛍️ {product_name}\n💰 价格: {price}\n\n{description}'
}
```

#### 2.3 变量提取器

```python
# core/template/variable_extractor.py
class VariableExtractor:
    """从消息中提取模板变量"""

    def extract_from_message(self, message)
    def extract_media_info(self, media)
    def extract_text_content(self, text)
```

### 阶段 3: Web 管理界面 (3 周)

#### 3.1 后端 API 框架

```python
# web/app.py - 使用FastAPI
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Telegram运维工具")

# API路由
@app.get("/api/clients/status")
@app.post("/api/tasks/create")
@app.get("/api/tasks/{task_id}/status")
@app.post("/api/distribution/send")
```

#### 3.2 核心 API 端点

- **客户端管理**: `/api/clients/`
- **任务管理**: `/api/tasks/`
- **模板管理**: `/api/templates/`
- **分发管理**: `/api/distribution/`
- **监控数据**: `/api/monitoring/`

#### 3.3 前端界面 (Vue.js)

```
web/frontend/
├── src/
│   ├── components/
│   │   ├── ClientManager.vue
│   │   ├── TaskCreator.vue
│   │   ├── TemplateEditor.vue
│   │   └── MonitorDashboard.vue
│   ├── views/
│   │   ├── Dashboard.vue
│   │   ├── Tasks.vue
│   │   └── Settings.vue
│   └── App.vue
```

### 阶段 4: 任务调度系统 (2 周)

#### 4.1 任务定义

```python
# core/scheduler/task_models.py
@dataclass
class CollectionTask:
    """采集任务"""
    source_channel: str
    message_range: Tuple[int, int]
    template_id: str
    target_channels: List[str]
    schedule: str  # cron表达式
```

#### 4.2 调度器

```python
# core/scheduler/scheduler.py
class TaskScheduler:
    """任务调度器"""

    def add_task(self, task: CollectionTask)
    def remove_task(self, task_id: str)
    def start_scheduler(self)
    def stop_scheduler(self)
```

#### 4.3 任务执行器

```python
# core/scheduler/executor.py
class TaskExecutor:
    """任务执行器"""

    async def execute_collection_task(self, task: CollectionTask)
    async def execute_distribution_task(self, content, targets)
    def handle_task_error(self, task, error)
```

## 📁 新增目录结构

```
multiDownloadPyrogram/
├── core/
│   ├── distribution/          # 新增：内容分发模块
│   │   ├── __init__.py
│   │   ├── distribution_manager.py
│   │   ├── channel_manager.py
│   │   └── send_strategy.py
│   ├── template/              # 新增：模板引擎
│   │   ├── __init__.py
│   │   ├── template_engine.py
│   │   ├── builtin_templates.py
│   │   └── variable_extractor.py
│   └── scheduler/             # 新增：任务调度
│       ├── __init__.py
│       ├── scheduler.py
│       ├── executor.py
│       └── task_models.py
├── web/                       # 新增：Web界面
│   ├── __init__.py
│   ├── app.py
│   ├── api/
│   │   ├── clients.py
│   │   ├── tasks.py
│   │   ├── templates.py
│   │   └── monitoring.py
│   └── frontend/
│       ├── package.json
│       ├── src/
│       └── dist/
├── data/                      # 新增：数据存储
│   ├── tasks.json
│   ├── templates.json
│   └── channels.json
└── docs/
    └── MVP_DEVELOPMENT_PLAN.md
```

## 🔧 技术栈扩展

### 后端新增依赖

```txt
# web/requirements.txt
fastapi>=0.104.0
uvicorn>=0.24.0
websockets>=12.0
jinja2>=3.1.0
apscheduler>=3.10.0
aiofiles>=23.2.0
```

### 前端技术栈

```json
{
  "dependencies": {
    "vue": "^3.3.0",
    "vue-router": "^4.2.0",
    "axios": "^1.6.0",
    "element-plus": "^2.4.0",
    "echarts": "^5.4.0"
  }
}
```

## 📊 数据模型设计

### 任务配置

```json
{
  "task_id": "task_001",
  "name": "热门内容采集",
  "type": "collection",
  "source": {
    "channel": "@source_channel",
    "message_range": [1000, 2000]
  },
  "template_id": "media_share",
  "targets": ["@target1", "@target2"],
  "schedule": "0 */2 * * *",
  "status": "active"
}
```

### 模板配置

```json
{
  "template_id": "media_share",
  "name": "媒体分享模板",
  "content": "📸 {title}\n\n{description}\n\n🔗 来源: {source}",
  "format": "html",
  "variables": ["title", "description", "source"]
}
```

## 🚀 部署方案

### 开发环境

```bash
# 启动后端
cd web
uvicorn app:app --reload --port 8000

# 启动前端
cd web/frontend
npm run dev
```

### 生产环境

```bash
# 使用Docker部署
docker-compose up -d
```

## 📈 MVP 验收标准

### 功能验收

- [ ] 支持从指定频道采集消息
- [ ] 支持使用模板格式化内容
- [ ] 支持分发到多个目标频道
- [ ] 提供 Web 管理界面
- [ ] 支持任务调度和监控

### 性能指标

- 支持同时管理 10 个采集任务
- 支持同时向 50 个频道分发
- Web 界面响应时间 < 2 秒
- 系统稳定运行 24 小时无故障

### 用户体验

- 界面操作直观易懂
- 任务创建流程简单
- 实时状态反馈
- 错误信息清晰明确

## 💻 详细实现指南

### 1. 内容分发模块实现

#### 1.1 创建分发管理器

```python
# core/distribution/distribution_manager.py
import asyncio
from typing import List, Dict, Any, Optional
from pyrogram import Client
from pyrogram.types import Message
from utils.logging_utils import LoggerMixin
from .channel_manager import ChannelManager
from .send_strategy import SendStrategy

class DistributionManager(LoggerMixin):
    """内容分发管理器"""

    def __init__(self):
        self.channel_manager = ChannelManager()
        self.send_strategy = SendStrategy()
        self.send_queue = asyncio.Queue()
        self.is_running = False

    async def send_message(
        self,
        client: Client,
        channel: str,
        content: str,
        template: Optional[str] = None,
        media_path: Optional[str] = None
    ) -> bool:
        """发送单条消息"""
        try:
            # 检查频道权限
            if not await self.channel_manager.validate_permissions(client, channel):
                self.log_error(f"没有向频道 {channel} 发送消息的权限")
                return False

            # 应用发送策略
            delay = self.send_strategy.calculate_send_delay(channel)
            if delay > 0:
                await asyncio.sleep(delay)

            # 发送消息
            if media_path:
                await client.send_photo(channel, media_path, caption=content)
            else:
                await client.send_message(channel, content)

            self.log_info(f"成功发送消息到 {channel}")
            return True

        except Exception as e:
            self.log_error(f"发送消息失败: {e}")
            return False

    async def batch_distribute(
        self,
        content_list: List[Dict[str, Any]],
        target_channels: List[str]
    ) -> Dict[str, int]:
        """批量分发内容"""
        results = {"success": 0, "failed": 0}

        for content in content_list:
            for channel in target_channels:
                success = await self.send_message(
                    content["client"],
                    channel,
                    content["text"],
                    content.get("template"),
                    content.get("media_path")
                )

                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1

        return results
```

#### 1.2 频道管理器

```python
# core/distribution/channel_manager.py
import json
from pathlib import Path
from typing import Dict, List, Any
from pyrogram import Client
from utils.logging_utils import LoggerMixin

class ChannelManager(LoggerMixin):
    """目标频道管理"""

    def __init__(self, config_file: str = "data/channels.json"):
        self.config_file = Path(config_file)
        self.channels = self._load_channels()

    def _load_channels(self) -> Dict[str, Any]:
        """加载频道配置"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_channels(self):
        """保存频道配置"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.channels, f, ensure_ascii=False, indent=2)

    def add_target_channel(
        self,
        channel_id: str,
        config: Dict[str, Any]
    ):
        """添加目标频道"""
        self.channels[channel_id] = {
            "name": config.get("name", channel_id),
            "description": config.get("description", ""),
            "send_interval": config.get("send_interval", 60),  # 秒
            "max_daily_posts": config.get("max_daily_posts", 100),
            "template_id": config.get("template_id", "default"),
            "active": config.get("active", True)
        }
        self._save_channels()
        self.log_info(f"添加目标频道: {channel_id}")

    def remove_target_channel(self, channel_id: str):
        """移除目标频道"""
        if channel_id in self.channels:
            del self.channels[channel_id]
            self._save_channels()
            self.log_info(f"移除目标频道: {channel_id}")

    def get_channel_config(self, channel_id: str) -> Dict[str, Any]:
        """获取频道配置"""
        return self.channels.get(channel_id, {})

    async def validate_permissions(self, client: Client, channel_id: str) -> bool:
        """验证频道权限"""
        try:
            chat = await client.get_chat(channel_id)
            # 检查是否有发送消息的权限
            return True  # 简化实现，实际需要检查具体权限
        except Exception as e:
            self.log_error(f"验证频道权限失败 {channel_id}: {e}")
            return False
```

### 2. 模板引擎实现

#### 2.1 模板引擎核心

```python
# core/template/template_engine.py
import re
import json
from pathlib import Path
from typing import Dict, Any, List
from utils.logging_utils import LoggerMixin

class TemplateEngine(LoggerMixin):
    """简单模板引擎"""

    def __init__(self, templates_file: str = "data/templates.json"):
        self.templates_file = Path(templates_file)
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Any]:
        """加载模板配置"""
        if self.templates_file.exists():
            with open(self.templates_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._get_builtin_templates()

    def _get_builtin_templates(self) -> Dict[str, Any]:
        """获取内置模板"""
        return {
            "default": {
                "name": "默认模板",
                "content": "{title}\n\n{description}",
                "format": "text"
            },
            "media_share": {
                "name": "媒体分享",
                "content": "📸 {title}\n\n{description}\n\n🔗 来源: {source}",
                "format": "html"
            },
            "news_format": {
                "name": "新闻格式",
                "content": "📰 <b>{title}</b>\n\n{summary}\n\n⏰ {publish_time}",
                "format": "html"
            }
        }

    def render_text(self, template_id: str, variables: Dict[str, Any]) -> str:
        """渲染文本模板"""
        template = self.templates.get(template_id)
        if not template:
            self.log_error(f"模板不存在: {template_id}")
            return ""

        content = template["content"]

        # 简单变量替换
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            content = content.replace(placeholder, str(value))

        # 清理未替换的占位符
        content = re.sub(r'\{[^}]+\}', '', content)

        return content.strip()

    def add_template(self, template_id: str, template_data: Dict[str, Any]):
        """添加新模板"""
        self.templates[template_id] = template_data
        self._save_templates()
        self.log_info(f"添加模板: {template_id}")

    def _save_templates(self):
        """保存模板配置"""
        self.templates_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.templates_file, 'w', encoding='utf-8') as f:
            json.dump(self.templates, f, ensure_ascii=False, indent=2)
```

#### 2.2 变量提取器

```python
# core/template/variable_extractor.py
import re
from datetime import datetime
from typing import Dict, Any
from pyrogram.types import Message
from utils.logging_utils import LoggerMixin

class VariableExtractor(LoggerMixin):
    """从消息中提取模板变量"""

    def extract_from_message(self, message: Message) -> Dict[str, Any]:
        """从消息中提取变量"""
        variables = {
            "message_id": message.id,
            "date": message.date.strftime("%Y-%m-%d %H:%M:%S") if message.date else "",
            "title": "",
            "description": "",
            "source": "",
            "media_count": 0
        }

        # 提取文本内容
        if message.text:
            variables.update(self._extract_text_variables(message.text))
        elif message.caption:
            variables.update(self._extract_text_variables(message.caption))

        # 提取媒体信息
        if message.media:
            variables.update(self._extract_media_variables(message))

        return variables

    def _extract_text_variables(self, text: str) -> Dict[str, Any]:
        """从文本中提取变量"""
        lines = text.strip().split('\n')

        # 简单规则：第一行作为标题，其余作为描述
        title = lines[0] if lines else ""
        description = '\n'.join(lines[1:]) if len(lines) > 1 else ""

        # 提取链接
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
        source = urls[0] if urls else ""

        return {
            "title": title,
            "description": description,
            "source": source,
            "full_text": text
        }

    def _extract_media_variables(self, message: Message) -> Dict[str, Any]:
        """从媒体中提取变量"""
        media_info = {
            "media_count": 1,
            "media_type": "",
            "file_size": 0
        }

        if message.photo:
            media_info["media_type"] = "photo"
            media_info["file_size"] = message.photo.file_size or 0
        elif message.video:
            media_info["media_type"] = "video"
            media_info["file_size"] = message.video.file_size or 0
            media_info["duration"] = message.video.duration or 0
        elif message.document:
            media_info["media_type"] = "document"
            media_info["file_size"] = message.document.file_size or 0
            media_info["file_name"] = message.document.file_name or ""

        return media_info
```

### 3. Web 界面实现

#### 3.1 FastAPI 后端

```python
# web/app.py
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio
import json

from core.client import ClientManager
from core.distribution import DistributionManager
from core.template import TemplateEngine
from core.scheduler import TaskScheduler

app = FastAPI(title="Telegram运维工具", version="1.0.0")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局管理器实例
client_manager = ClientManager()
distribution_manager = DistributionManager()
template_engine = TemplateEngine()
task_scheduler = TaskScheduler()

# 数据模型
class TaskCreate(BaseModel):
    name: str
    source_channel: str
    message_range: List[int]
    template_id: str
    target_channels: List[str]
    schedule: str

class TemplateCreate(BaseModel):
    name: str
    content: str
    format: str = "text"

# API路由
@app.get("/api/clients/status")
async def get_clients_status():
    """获取客户端状态"""
    return {
        "clients": len(client_manager.clients),
        "active": len([c for c in client_manager.clients if c.is_connected]),
        "details": client_manager.client_stats
    }

@app.post("/api/tasks/create")
async def create_task(task: TaskCreate):
    """创建新任务"""
    try:
        task_id = await task_scheduler.add_task(task.dict())
        return {"task_id": task_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """获取任务状态"""
    status = task_scheduler.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在")
    return status

@app.post("/api/templates/create")
async def create_template(template: TemplateCreate):
    """创建新模板"""
    template_id = f"custom_{len(template_engine.templates)}"
    template_engine.add_template(template_id, template.dict())
    return {"template_id": template_id, "status": "created"}

@app.get("/api/templates/")
async def list_templates():
    """获取模板列表"""
    return template_engine.templates

@app.websocket("/ws/monitoring")
async def websocket_monitoring(websocket: WebSocket):
    """WebSocket监控数据推送"""
    await websocket.accept()
    try:
        while True:
            # 推送实时监控数据
            data = {
                "clients": len(client_manager.clients),
                "tasks": task_scheduler.get_running_tasks_count(),
                "timestamp": asyncio.get_event_loop().time()
            }
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(5)
    except Exception as e:
        print(f"WebSocket连接断开: {e}")

# 静态文件服务
app.mount("/", StaticFiles(directory="web/frontend/dist", html=True), name="static")
```

#### 3.2 任务调度器

```python
# core/scheduler/scheduler.py
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from utils.logging_utils import LoggerMixin
from .executor import TaskExecutor

class TaskScheduler(LoggerMixin):
    """任务调度器"""

    def __init__(self, tasks_file: str = "data/tasks.json"):
        self.tasks_file = Path(tasks_file)
        self.scheduler = AsyncIOScheduler()
        self.executor = TaskExecutor()
        self.tasks = self._load_tasks()
        self.running_tasks = {}

    def _load_tasks(self) -> Dict[str, Any]:
        """加载任务配置"""
        if self.tasks_file.exists():
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_tasks(self):
        """保存任务配置"""
        self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)

    async def add_task(self, task_data: Dict[str, Any]) -> str:
        """添加新任务"""
        task_id = f"task_{len(self.tasks)}_{int(datetime.now().timestamp())}"

        task_config = {
            "id": task_id,
            "name": task_data["name"],
            "source_channel": task_data["source_channel"],
            "message_range": task_data["message_range"],
            "template_id": task_data["template_id"],
            "target_channels": task_data["target_channels"],
            "schedule": task_data["schedule"],
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "last_run": None,
            "next_run": None
        }

        self.tasks[task_id] = task_config
        self._save_tasks()

        # 添加到调度器
        if task_config["status"] == "active":
            self._schedule_task(task_config)

        self.log_info(f"添加任务: {task_id}")
        return task_id

    def _schedule_task(self, task_config: Dict[str, Any]):
        """将任务添加到调度器"""
        try:
            # 解析cron表达式
            cron_parts = task_config["schedule"].split()
            if len(cron_parts) == 5:
                minute, hour, day, month, day_of_week = cron_parts
                trigger = CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week
                )

                self.scheduler.add_job(
                    self._execute_task,
                    trigger=trigger,
                    args=[task_config["id"]],
                    id=task_config["id"],
                    replace_existing=True
                )

                self.log_info(f"任务已调度: {task_config['id']}")
        except Exception as e:
            self.log_error(f"调度任务失败 {task_config['id']}: {e}")

    async def _execute_task(self, task_id: str):
        """执行任务"""
        if task_id in self.running_tasks:
            self.log_warning(f"任务 {task_id} 正在运行中，跳过本次执行")
            return

        task_config = self.tasks.get(task_id)
        if not task_config:
            self.log_error(f"任务不存在: {task_id}")
            return

        self.running_tasks[task_id] = {
            "start_time": datetime.now(),
            "status": "running"
        }

        try:
            self.log_info(f"开始执行任务: {task_id}")
            result = await self.executor.execute_collection_task(task_config)

            # 更新任务状态
            self.tasks[task_id]["last_run"] = datetime.now().isoformat()
            self.tasks[task_id]["last_result"] = result
            self._save_tasks()

            self.running_tasks[task_id]["status"] = "completed"
            self.log_info(f"任务执行完成: {task_id}")

        except Exception as e:
            self.running_tasks[task_id]["status"] = "failed"
            self.running_tasks[task_id]["error"] = str(e)
            self.log_error(f"任务执行失败 {task_id}: {e}")

        finally:
            # 清理运行状态
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]

    def start_scheduler(self):
        """启动调度器"""
        # 加载所有活跃任务
        for task_config in self.tasks.values():
            if task_config["status"] == "active":
                self._schedule_task(task_config)

        self.scheduler.start()
        self.log_info("任务调度器已启动")

    def stop_scheduler(self):
        """停止调度器"""
        self.scheduler.shutdown()
        self.log_info("任务调度器已停止")

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        task = self.tasks.get(task_id)
        if not task:
            return None

        status = {
            "task": task,
            "is_running": task_id in self.running_tasks,
            "running_info": self.running_tasks.get(task_id)
        }

        return status

    def get_running_tasks_count(self) -> int:
        """获取正在运行的任务数量"""
        return len(self.running_tasks)
```

#### 3.3 任务执行器

```python
# core/scheduler/executor.py
import asyncio
from typing import Dict, Any, List
from core.client import ClientManager
from core.message import MessageFetcher
from core.template import TemplateEngine, VariableExtractor
from core.distribution import DistributionManager
from utils.logging_utils import LoggerMixin

class TaskExecutor(LoggerMixin):
    """任务执行器"""

    def __init__(self):
        self.client_manager = ClientManager()
        self.template_engine = TemplateEngine()
        self.variable_extractor = VariableExtractor()
        self.distribution_manager = DistributionManager()

    async def execute_collection_task(self, task_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行采集任务"""
        try:
            # 1. 初始化客户端
            if not self.client_manager.clients:
                clients = self.client_manager.create_clients()
                await self.client_manager.start_all_clients()

            # 2. 获取消息
            message_fetcher = MessageFetcher(self.client_manager.clients)
            messages = await message_fetcher.parallel_fetch_messages(
                task_config["source_channel"],
                task_config["message_range"][0],
                task_config["message_range"][1]
            )

            if not messages:
                return {"status": "no_messages", "count": 0}

            # 3. 处理消息并应用模板
            processed_content = []
            for message in messages:
                # 提取变量
                variables = self.variable_extractor.extract_from_message(message)

                # 应用模板
                formatted_text = self.template_engine.render_text(
                    task_config["template_id"],
                    variables
                )

                if formatted_text:
                    processed_content.append({
                        "client": self.client_manager.clients[0],  # 使用第一个客户端发送
                        "text": formatted_text,
                        "template": task_config["template_id"],
                        "original_message": message
                    })

            # 4. 分发到目标频道
            distribution_result = await self.distribution_manager.batch_distribute(
                processed_content,
                task_config["target_channels"]
            )

            return {
                "status": "completed",
                "messages_processed": len(messages),
                "content_generated": len(processed_content),
                "distribution_result": distribution_result
            }

        except Exception as e:
            self.log_error(f"执行任务失败: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
```

## 🚀 快速开始指南

### 1. 环境准备

```bash
# 1. 安装新增依赖
pip install fastapi uvicorn websockets jinja2 apscheduler

# 2. 创建必要目录
mkdir -p data web/frontend

# 3. 初始化配置文件
echo '{}' > data/tasks.json
echo '{}' > data/templates.json
echo '{}' > data/channels.json
```

### 2. 启动开发环境

```bash
# 启动后端API服务
cd web
uvicorn app:app --reload --port 8000

# 访问Web界面
# http://localhost:8000
```

### 3. 创建第一个任务

```python
# 示例：通过API创建任务
import requests

task_data = {
    "name": "测试采集任务",
    "source_channel": "@source_channel",
    "message_range": [1000, 1100],
    "template_id": "default",
    "target_channels": ["@target_channel"],
    "schedule": "0 */2 * * *"  # 每2小时执行一次
}

response = requests.post("http://localhost:8000/api/tasks/create", json=task_data)
print(response.json())
```

## 📋 开发检查清单

### 阶段 1: 内容分发模块

- [ ] 实现 `DistributionManager` 类
- [ ] 实现 `ChannelManager` 类
- [ ] 实现 `SendStrategy` 类
- [ ] 添加发送权限验证
- [ ] 添加发送频率控制
- [ ] 编写单元测试

### 阶段 2: 模板引擎

- [ ] 实现 `TemplateEngine` 类
- [ ] 实现 `VariableExtractor` 类
- [ ] 添加内置模板
- [ ] 支持 HTML/Markdown 格式
- [ ] 添加模板验证
- [ ] 编写模板测试用例

### 阶段 3: Web 界面

- [ ] 搭建 FastAPI 后端框架
- [ ] 实现核心 API 端点
- [ ] 添加 WebSocket 实时监控
- [ ] 开发 Vue.js 前端界面
- [ ] 实现任务管理界面
- [ ] 实现模板编辑器

### 阶段 4: 任务调度

- [ ] 实现 `TaskScheduler` 类
- [ ] 实现 `TaskExecutor` 类
- [ ] 支持 Cron 表达式调度
- [ ] 添加任务状态管理
- [ ] 实现任务执行监控
- [ ] 添加错误处理和重试

## 🧪 测试策略

### 单元测试

```python
# tests/test_distribution.py
import pytest
from core.distribution import DistributionManager

@pytest.mark.asyncio
async def test_send_message():
    manager = DistributionManager()
    # 测试消息发送功能

# tests/test_template.py
from core.template import TemplateEngine

def test_render_template():
    engine = TemplateEngine()
    # 测试模板渲染功能
```

### 集成测试

```python
# tests/test_integration.py
@pytest.mark.asyncio
async def test_full_workflow():
    # 测试完整的采集->处理->分发流程
    pass
```

### 性能测试

- 测试并发任务处理能力
- 测试大量消息处理性能
- 测试 Web 界面响应时间

## 📦 部署配置

### Docker 部署

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  telegram-tool:
    build: .
    ports:
      - '8000:8000'
    volumes:
      - ./data:/app/data
      - ./sessions:/app/sessions
      - ./logs:/app/logs
    environment:
      - PYTHONPATH=/app
```

### 生产环境配置

```python
# web/config.py
import os

class Config:
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/app.db')
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
```

## 🎯 下一步规划

MVP 完成后，可以继续开发：

1. **多平台爬虫支持** (第二阶段)

   - YouTube、Bilibili 视频采集
   - 电商平台商品监控
   - 社交媒体内容抓取

2. **高级模板功能** (第二阶段)

   - 条件渲染和循环结构
   - 自定义过滤器
   - 模板继承和组合

3. **AI 内容处理** (第三阶段)

   - 智能内容摘要
   - 自动标签生成
   - 内容质量评分

4. **企业级功能** (第四阶段)
   - 多租户支持
   - 权限管理系统
   - 企业级安全认证

## 📞 技术支持

如有问题，请参考：

1. 项目文档：`docs/`
2. 示例代码：`examples/`
3. 测试用例：`tests/`
4. 问题反馈：GitHub Issues
