"""
三客户端消息下载验证程序 - Stream Media 版本
核心功能：智能消息分配、异步任务管理、TgCrypto加速、流式下载
使用 Pyrogram 的 stream_media 方法进行高效流式下载
支持基于文件大小和类型的智能下载方法选择

注意：此文件使用硬编码配置，请在配置区域修改相关参数
"""
import asyncio
import os
import re
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from pyrogram.client import Client
from pyrogram.errors import FloodWait
from pyrogram.raw.functions.upload import GetFile
from pyrogram.raw.types import InputDocumentFileLocation, InputPhotoFileLocation
from pyrogram.file_id import FileId, FileType
import logging
import psutil
import threading
import time

# 导入主程序的分配组件
from core.task_distribution import (
    DistributionConfig,
    DistributionMode,
    TaskDistributor
)
from core.task_distribution.base import LoadBalanceMetric

# 配置日志 - 强制清除并重新配置
def setup_logging(verbose: bool = True):
    """配置日志系统"""
    # 确保logs目录存在
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / "test_downloader_stream.log"

    # 强制清除之前的日志文件
    if log_file.exists():
        log_file.unlink()

    # 清除所有现有的日志处理器
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 清除所有子logger的处理器
    for name in logging.Logger.manager.loggerDict:
        logger_obj = logging.getLogger(name)
        logger_obj.handlers.clear()
        logger_obj.propagate = True

    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 配置文件处理器
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # 配置控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # 配置根日志记录器
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # 配置Pyrogram日志级别
    if verbose:
        logging.getLogger("pyrogram").setLevel(logging.INFO)
    else:
        # 设置更严格的日志级别，减少网络连接日志
        logging.getLogger("pyrogram").setLevel(logging.ERROR)
        logging.getLogger("pyrogram.connection").setLevel(logging.ERROR)
        logging.getLogger("pyrogram.session").setLevel(logging.ERROR)
        logging.getLogger("pyrogram.dispatcher").setLevel(logging.WARNING)
        logging.getLogger("pyrogram.connection.transport").setLevel(logging.ERROR)
        logging.getLogger("pyrogram.connection.transport.tcp").setLevel(logging.ERROR)

setup_logging(verbose=False)  # 禁用Pyrogram详细日志
logger = logging.getLogger(__name__)

# ==================== 配置区域 ====================
API_ID = 25098445
API_HASH = "cc2fa5a762621d306d8de030614e4555"
PHONE_NUMBER = "+8618758361347"
TARGET_CHANNEL = "csdkl"
START_MESSAGE_ID = 72710
END_MESSAGE_ID = 72849
TOTAL_MESSAGES = END_MESSAGE_ID - START_MESSAGE_ID + 1
SESSION_NAMES = [
    "client_8618758361347_1",
    "client_8618758361347_2",
    "client_8618758361347_3",
]
USE_PROXY = True
PROXY_CONFIG = {
    "scheme": "socks5",
    "hostname": "127.0.0.1",
    "port": 7890
} if USE_PROXY else None
DOWNLOAD_DIR = Path("downloads")

# 调试选项 - 已移除无用的配置项
# ==================== 配置区域结束 ====================

def monitor_bandwidth():
    """监控网络带宽使用情况"""
    old_stats = psutil.net_io_counters()
    while True:
        time.sleep(1)
        new_stats = psutil.net_io_counters()
        download_speed = (new_stats.bytes_recv - old_stats.bytes_recv) / 1024
        upload_speed = (new_stats.bytes_sent - old_stats.bytes_sent) / 1024
        logger.info(f"Download: {download_speed:.2f} KB/s, Upload: {upload_speed:.2f} KB/s")
        old_stats = new_stats

class MultiClientDownloader:
    """多客户端下载管理器 - Stream Media 版本 + 智能消息分配"""
    def __init__(self):
        self.clients: List[Client] = []
        self.download_dir = DOWNLOAD_DIR
        self.download_dir.mkdir(exist_ok=True)
        self.channel_info = None
        self.channel_dir = None
        self.stats = {
            "total_messages": TOTAL_MESSAGES,
            "downloaded": 0,
            "failed": 0,
            "start_time": None
        }
        self._results_processed = False  # 防止重复输出统计信息

        # 初始化智能消息分配器（简化配置）
        self.distribution_config = DistributionConfig(
            mode=DistributionMode.MEDIA_GROUP_AWARE,  # 使用媒体组感知分配
            load_balance_metric=LoadBalanceMetric.ESTIMATED_SIZE,  # 使用真实文件大小进行负载均衡
            prefer_large_groups_first=True,  # 优先分配大媒体组
            enable_validation=True  # 启用基本验证
        )

    def create_clients(self) -> List[Client]:
        """创建客户端实例"""
        clients = []
        for session_name in SESSION_NAMES:
            client = Client(
                name=session_name,
                api_id=API_ID,
                api_hash=API_HASH,
                workdir="sessions",
                proxy=PROXY_CONFIG,
                workers=4,
                sleep_threshold=10
            )
            clients.append(client)
            logger.info(f"创建客户端: {session_name}")
        self.clients = clients
        return clients

    async def get_channel_info(self, client: Client) -> Dict:
        """获取频道信息"""
        try:
            chat = await client.get_chat(TARGET_CHANNEL)
            username = f"@{chat.username}" if chat.username else f"id_{chat.id}"
            title = chat.title or "Unknown"
            safe_title = self.sanitize_filename(title)
            folder_name = f"{username}-{safe_title}"
            return {
                "username": username,
                "title": title,
                "folder_name": folder_name,
                "chat_id": chat.id
            }
        except Exception as e:
            logger.error(f"获取频道信息失败: {e}")
            return {
                "username": f"@{TARGET_CHANNEL}",
                "title": "Unknown",
                "folder_name": f"@{TARGET_CHANNEL}-Unknown",
                "chat_id": None
            }

    def sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        illegal_chars = r'[<>:"/\\|?*]'
        safe_name = re.sub(illegal_chars, '_', filename)
        safe_name = safe_name.strip('. ')
        return safe_name[:100]

    def get_channel_directory(self) -> Path:
        """获取频道专用目录（带缓存机制）"""
        if not self.channel_info:
            raise ValueError("频道信息未初始化")
        if self.channel_dir is not None:
            return self.channel_dir
        self.channel_dir = self.download_dir / self.channel_info["folder_name"]
        if self.channel_dir.exists():
            logger.info(f"频道目录已存在: {self.channel_dir}")
        else:
            self.channel_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"频道目录已创建: {self.channel_dir}")
        return self.channel_dir

    def is_media_group_message(self, message) -> bool:
        """检查消息是否属于媒体组"""
        return hasattr(message, 'media_group_id') and message.media_group_id is not None

    def generate_filename_by_type(self, message) -> str:
        """根据消息类型生成文件名"""
        if self.is_media_group_message(message):
            base_name = f"{message.media_group_id}-{message.id}"
        else:
            base_name = f"msg-{message.id}"
        extension = self.get_file_extension(message)
        return f"{base_name}{extension}"

    def get_file_extension(self, message) -> str:
        """获取消息媒体的文件扩展名"""
        if hasattr(message, 'document') and message.document:
            if hasattr(message.document, 'file_name') and message.document.file_name:
                _, ext = os.path.splitext(message.document.file_name)
                return ext if ext else self.get_extension_from_mime(message.document.mime_type)
            else:
                return self.get_extension_from_mime(getattr(message.document, 'mime_type', ''))
        elif hasattr(message, 'video') and message.video:
            return '.mp4'
        elif hasattr(message, 'photo') and message.photo:
            return '.jpg'
        elif hasattr(message, 'audio') and message.audio:
            if hasattr(message.audio, 'file_name') and message.audio.file_name:
                _, ext = os.path.splitext(message.audio.file_name)
                return ext if ext else '.mp3'
            return '.mp3'
        elif hasattr(message, 'voice') and message.voice:
            return '.ogg'
        elif hasattr(message, 'video_note') and message.video_note:
            return '.mp4'
        elif hasattr(message, 'animation') and message.animation:
            if hasattr(message.animation, 'file_name') and message.animation.file_name:
                _, ext = os.path.splitext(message.animation.file_name)
                return ext if ext else '.gif'
            return '.gif'
        elif hasattr(message, 'sticker') and message.sticker:
            return '.webp'
        else:
            return '.bin'

    def get_extension_from_mime(self, mime_type: str) -> str:
        """根据MIME类型获取文件扩展名"""
        mime_to_ext = {
            'video/mp4': '.mp4',
            'video/avi': '.avi',
            'video/mkv': '.mkv',
            'video/mov': '.mov',
            'video/webm': '.webm',
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'audio/ogg': '.ogg',
            'audio/m4a': '.m4a',
            'application/pdf': '.pdf',
            'application/zip': '.zip',
            'application/x-rar': '.rar',
            'text/plain': '.txt',
            'application/msword': '.doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        }
        return mime_to_ext.get(mime_type, '.bin')

    async def save_text_message(self, message):
        """保存文本消息到频道目录"""
        try:
            channel_dir = self.get_channel_directory()
            text_file = channel_dir / "messages.txt"
            with open(text_file, "a", encoding="utf-8") as f:
                if self.is_media_group_message(message):
                    f.write(f"消息ID: {message.id} (媒体组: {message.media_group_id})\n")
                else:
                    f.write(f"消息ID: {message.id}\n")
                f.write(f"时间: {message.date}\n")
                f.write(f"内容: {message.text or '无文本内容'}\n")
                f.write("-" * 50 + "\n")
        except Exception as e:
            logger.error(f"保存文本消息失败: {e}")



    async def parallel_fetch_messages(self, clients: List[Client]) -> List[Any]:
        """
        并发获取消息 - 多客户端分工获取不同范围的消息

        Args:
            clients: 客户端列表

        Returns:
            所有获取到的消息列表
        """
        logger.info(f"🚀 使用 {len(clients)} 个客户端并发获取消息...")

        # 将消息范围按客户端数量分配
        all_message_ids = list(range(START_MESSAGE_ID, END_MESSAGE_ID + 1))
        client_count = len(clients)

        # 计算每个客户端的消息范围
        messages_per_client = len(all_message_ids) // client_count
        remainder = len(all_message_ids) % client_count

        ranges = []
        start_idx = 0
        for i in range(client_count):
            extra = 1 if i < remainder else 0
            end_idx = start_idx + messages_per_client + extra
            ranges.append(all_message_ids[start_idx:end_idx])
            logger.info(f"客户端{i+1} 分配消息范围: {all_message_ids[start_idx]} - {all_message_ids[end_idx-1]} ({len(ranges[i])} 条)")
            start_idx = end_idx

        async def fetch_range(client, message_ids, client_index):
            """单个客户端获取指定范围的消息"""
            # 错开启动时间避免同时发起请求
            if client_index > 0:
                delay = client_index * 0.2
                logger.info(f"客户端{client_index+1} 将在 {delay} 秒后开始获取...")
                await asyncio.sleep(delay)

            messages = []
            batch_size = 100  # 每批获取100条消息

            logger.info(f"客户端{client_index+1} 开始获取 {len(message_ids)} 条消息...")

            for i in range(0, len(message_ids), batch_size):
                batch_ids = message_ids[i:i + batch_size]
                try:
                    batch_messages = await client.get_messages(TARGET_CHANNEL, batch_ids)
                    # 过滤掉无效消息（使用empty属性判断）
                    valid_messages = [msg for msg in batch_messages if msg is not None and not getattr(msg, 'empty', True)]
                    invalid_count = len(batch_ids) - len(valid_messages)

                    messages.extend(valid_messages)

                    if invalid_count > 0:
                        logger.warning(f"客户端{client_index+1} 批次中发现 {invalid_count} 条无效消息")

                    logger.info(f"客户端{client_index+1} 已获取 {len(messages)} 条有效消息（批次: {len(valid_messages)}/{len(batch_ids)}）")

                    # 短暂延迟避免过于频繁的请求
                    await asyncio.sleep(0.1)

                except FloodWait as e:
                    logger.warning(f"客户端{client_index+1} 遇到限流，等待 {e.value} 秒")
                    await asyncio.sleep(float(e.value))
                    # 重试当前批次
                    try:
                        batch_messages = await client.get_messages(TARGET_CHANNEL, batch_ids)
                        # 过滤掉无效消息（使用empty属性判断）
                        valid_messages = [msg for msg in batch_messages if msg is not None and not getattr(msg, 'empty', True)]
                        invalid_count = len(batch_ids) - len(valid_messages)

                        messages.extend(valid_messages)

                        if invalid_count > 0:
                            logger.warning(f"客户端{client_index+1} 重试批次中发现 {invalid_count} 条无效消息")

                        logger.info(f"客户端{client_index+1} 重试成功，已获取 {len(messages)} 条有效消息")
                    except Exception as retry_e:
                        logger.error(f"客户端{client_index+1} 重试失败: {retry_e}")

                except Exception as e:
                    logger.error(f"客户端{client_index+1} 获取消息批次 {batch_ids[0]}-{batch_ids[-1]} 失败: {e}")
                    continue

            logger.info(f"✅ 客户端{client_index+1} 完成获取，共 {len(messages)} 条有效消息")
            return messages

        # 启动所有客户端并发获取
        tasks = []
        for i, client in enumerate(clients):
            task = fetch_range(client, ranges[i], i)
            tasks.append(task)

        # 等待所有任务完成
        logger.info("⏳ 等待所有客户端完成消息获取...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并所有消息
        all_messages = []
        successful_clients = 0

        for i, result in enumerate(results):
            if isinstance(result, list):
                all_messages.extend(result)
                successful_clients += 1
                logger.info(f"✅ 客户端{i+1} 成功获取 {len(result)} 条消息")
            else:
                logger.error(f"❌ 客户端{i+1} 获取消息失败: {result}")

        # 按消息ID排序确保顺序正确，同时过滤掉无效消息
        all_messages = sorted([msg for msg in all_messages if msg and not getattr(msg, 'empty', True)], key=lambda x: x.id)

        logger.info(f"🎉 并发获取完成！{successful_clients}/{len(clients)} 个客户端成功，共获取 {len(all_messages)} 条有效消息")
        return all_messages

    async def smart_distribute_messages(self, clients: List[Client]) -> Tuple[Dict[str, List[int]], Dict[str, List[Any]], Dict[str, Any]]:
        """
        智能消息分配 - 并发获取 + 媒体组感知算法 + 消息验证

        Args:
            clients: 客户端列表（用于并发获取）

        Returns:
            Tuple[Dict[client_name, List[message_ids]], Dict[client_name, List[message_objects]], validation_stats] - 分配结果、消息对象和验证统计
        """
        logger.info("🧠 开始智能消息分配（并发获取 + 智能分配）...")

        try:
            # 1. 并发获取所有消息对象
            logger.info(f"📦 使用 {len(clients)} 个客户端并发获取消息范围 {START_MESSAGE_ID}-{END_MESSAGE_ID}...")
            all_messages = await self.parallel_fetch_messages(clients)

            if not all_messages:
                raise ValueError("未能获取到任何有效消息")

            # 2. 使用主程序的分组方法（避免消息转换过程中的信息丢失）
            logger.info("🧠 使用主程序的MessageGrouper进行分组...")
            from core.message_grouper import MessageGrouper

            # 创建消息分组器（简化版本）
            message_grouper = MessageGrouper()

            # 直接从消息列表进行分组（避免转换过程中的信息丢失）
            message_collection = message_grouper.group_messages_from_list(all_messages)

            # 记录分组统计
            grouping_stats = message_collection.get_statistics()
            logger.info(f"📊 分组完成: {grouping_stats['media_groups_count']} 个媒体组, {grouping_stats['single_messages_count']} 个单消息")

            # 3. 使用主程序的TaskDistributor进行分配
            logger.info("⚖️ 使用主程序的TaskDistributor进行分配...")

            # 使用类的配置（避免重复配置）
            distribution_config = self.distribution_config

            # 执行任务分配
            task_distributor = TaskDistributor(distribution_config)
            distribution_result = await task_distributor.distribute_tasks(
                message_collection, SESSION_NAMES
            )

            # 4. 转换为客户端消息ID映射和消息对象映射
            client_message_mapping = {}
            client_message_objects = {}

            # 不再需要消息ID映射，直接使用主程序的方法

            for assignment in distribution_result.client_assignments:
                client_name = assignment.client_name
                # 直接获取所有消息对象（主程序方法）
                message_objects = assignment.get_all_messages()
                message_ids = [msg.id for msg in message_objects if msg]

                client_message_mapping[client_name] = message_ids
                client_message_objects[client_name] = message_objects

            # 5. 记录分配统计（使用主程序的统计方法）
            load_balance_stats = distribution_result.get_load_balance_stats()
            logger.info("📊 任务分配统计:")
            logger.info(f"  总消息数: {distribution_result.total_messages}")
            logger.info(f"  总文件数: {distribution_result.total_files}")
            logger.info(f"  客户端数量: {load_balance_stats['clients_count']}")

            # 打印每个客户端分配到的完整消息ID
            for i, client_name in enumerate(SESSION_NAMES):
                if client_name in client_message_mapping:
                    message_ids = client_message_mapping[client_name]
                    if message_ids:
                        # 排序消息ID以便查看
                        sorted_ids = sorted(message_ids)
                        id_ranges = []

                        # 将连续的ID合并为范围显示
                        start = sorted_ids[0]
                        end = sorted_ids[0]

                        for msg_id in sorted_ids[1:]:
                            if msg_id == end + 1:
                                end = msg_id
                            else:
                                if start == end:
                                    id_ranges.append(str(start))
                                else:
                                    id_ranges.append(f"{start}-{end}")
                                start = end = msg_id

                        # 添加最后一个范围
                        if start == end:
                            id_ranges.append(str(start))
                        else:
                            id_ranges.append(f"{start}-{end}")

                        logger.info(f"  客户端{i+1} 分配消息ID: {', '.join(id_ranges)} (共{len(message_ids)}条)")
                    else:
                        logger.info(f"  客户端{i+1} 分配消息ID: 无 (共0条)")

            logger.info(f"  文件分布: {load_balance_stats['file_distribution']}")
            logger.info(f"  大小分布: {[f'{size/(1024*1024):.2f} MB' for size in load_balance_stats['size_distribution']]}")
            logger.info(f"  文件均衡比例: {load_balance_stats['file_balance_ratio']:.3f}")
            logger.info(f"  大小均衡比例: {load_balance_stats['size_balance_ratio']:.3f}")

            logger.info("✅ 智能消息分配完成")

            # 创建兼容的统计信息
            validation_stats = {
                "enabled": True,
                "original_count": len(all_messages),
                "valid_count": distribution_result.total_messages,
                "invalid_count": len(all_messages) - distribution_result.total_messages,
                "validation_rate": distribution_result.total_messages / len(all_messages) if all_messages else 0,
                "invalid_ids": []
            }

            return client_message_mapping, client_message_objects, validation_stats

        except Exception as e:
            logger.error(f"❌ 智能消息分配失败: {e}")
            # 重新抛出异常，不再回退
            raise

    def is_video_file(self, message) -> bool:
        """检查消息是否为视频文件"""
        if hasattr(message, 'video') and message.video:
            return True
        elif hasattr(message, 'video_note') and message.video_note:
            return True
        elif hasattr(message, 'animation') and message.animation:
            return True
        elif hasattr(message, 'document') and message.document:
            mime_type = getattr(message.document, 'mime_type', '')
            if mime_type.startswith('video/'):
                return True
            # 检查文件扩展名
            file_name = getattr(message.document, 'file_name', '')
            if file_name:
                video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.webm', '.flv', '.wmv', '.m4v']
                _, ext = os.path.splitext(file_name.lower())
                return ext in video_extensions
        return False

    def get_file_size_bytes(self, message) -> int:
        """获取文件大小（字节）- 支持所有媒体类型"""
        # 检查所有可能的媒体类型
        media_types = ['document', 'video', 'photo', 'audio', 'voice',
                      'video_note', 'animation', 'sticker']

        for media_type in media_types:
            media = getattr(message, media_type, None)
            if media and hasattr(media, 'file_size') and media.file_size:
                return media.file_size

        return 0

    def get_file_size_mb(self, message) -> float:
        """获取文件大小（MB）- 支持所有媒体类型"""
        return self.get_file_size_bytes(message) / 1024 / 1024

    async def download_media_file_raw_api(self, client: Client, message) -> Optional[Path]:
        """使用RAW API方法下载媒体文件（来自test_downloader.py）"""
        try:
            channel_dir = self.get_channel_directory()
            file_name = self.generate_filename_by_type(message)
            file_path = channel_dir / file_name
            file_size = self.get_file_size_bytes(message)
            logger.info(f"RAW API下载消息 {message.id} (大小: {file_size / 1024 / 1024:.2f} MB)")

            # 获取媒体对象
            media = (message.document or message.video or message.photo or message.audio or
                     message.voice or message.video_note or message.animation or message.sticker)
            if not media:
                logger.error(f"消息 {message.id} 无有效媒体")
                return None

            # 解码 file_id 获取文件位置
            file_id_str = media.file_id
            file_id_obj = FileId.decode(file_id_str)
            logger.info(f"消息 {message.id} 媒体类型: {FileType(file_id_obj.file_type).name}")

            # 构造文件位置
            if file_id_obj.file_type == FileType.PHOTO:
                location = InputPhotoFileLocation(
                    id=file_id_obj.media_id,
                    access_hash=file_id_obj.access_hash,
                    file_reference=file_id_obj.file_reference,
                    thumb_size=file_id_obj.thumbnail_size or ''
                )
            else:
                location = InputDocumentFileLocation(
                    id=file_id_obj.media_id,
                    access_hash=file_id_obj.access_hash,
                    file_reference=file_id_obj.file_reference,
                    thumb_size=file_id_obj.thumbnail_size or ''
                )

            # 处理数据中心迁移和分片下载
            offset = 0
            chunk_size = 1024 * 1024  # 1MB，Telegram API 最大值

            # 检查文件的数据中心ID
            dc_id = file_id_obj.dc_id
            current_dc_id = await client.storage.dc_id()

            # 如果文件在不同的数据中心，需要特殊处理
            if dc_id != current_dc_id:
                logger.info(f"消息 {message.id} 文件位于数据中心 {dc_id}，当前连接到 {current_dc_id}")
                # 使用 Pyrogram 的内置下载方法处理数据中心迁移
                try:
                    downloaded_path = await client.download_media(message, file_name=str(file_path))
                    if downloaded_path:
                        logger.info(f"✅ 使用内置方法下载完成: {downloaded_path}")
                        return Path(downloaded_path)
                    else:
                        logger.error(f"❌ 内置方法下载失败")
                        return None
                except Exception as e:
                    logger.error(f"❌ 内置方法下载异常: {e}")
                    return None

            # 如果在同一数据中心，使用 RAW API 下载
            try:
                with open(file_path, 'wb') as f:
                    while offset < file_size or file_size == 0:
                        try:
                            result = await client.invoke(GetFile(
                                location=location,
                                offset=offset,
                                limit=chunk_size
                            ))
                            if not hasattr(result, 'bytes') or not result.bytes:
                                break
                            f.write(result.bytes)
                            offset += len(result.bytes)
                        except FloodWait as e:
                            logger.warning(f"RAW API下载消息 {message.id} 遇到限流，等待 {e.value} 秒")
                            await asyncio.sleep(float(e.value))
                            continue
                        except Exception as e:
                            logger.error(f"RAW API下载消息 {message.id} 分片失败: {e}")
                            return None
                return Path(file_path) if file_path.exists() else None
            except FloodWait as e:
                logger.warning(f"RAW API下载消息 {message.id} 遇到限流，等待 {e.value} 秒")
                await asyncio.sleep(float(e.value))
                return await self.download_media_file_raw_api(client, message)
            except Exception as e:
                logger.error(f"RAW API下载消息 {message.id} 失败: {e}")
                return None
        except Exception as e:
            logger.error(f"RAW API下载消息 {message.id} 失败: {e}")
            return None

    async def download_media_file_stream(self, client: Client, message) -> Optional[Path]:
        """使用 stream_media 方法下载媒体文件"""
        try:
            channel_dir = self.get_channel_directory()
            file_name = self.generate_filename_by_type(message)
            file_path = channel_dir / file_name

            # 获取文件大小信息
            file_size = self.get_file_size_bytes(message)

            logger.info(f"Stream下载消息 {message.id} (大小: {file_size / 1024 / 1024:.2f} MB)")

            # 检查是否有有效媒体
            media = (message.document or message.video or message.photo or message.audio or
                     message.voice or message.video_note or message.animation or message.sticker)
            if not media:
                logger.error(f"消息 {message.id} 无有效媒体")
                return None

            # 使用 stream_media 进行流式下载
            try:
                downloaded_bytes = 0
                with open(file_path, 'wb') as f:
                    async for chunk in client.stream_media(message):
                        f.write(chunk)
                        downloaded_bytes += len(chunk)

                        # 可选：显示下载进度（每10MB显示一次）
                        if downloaded_bytes % (10 * 1024 * 1024) == 0:
                            progress_mb = downloaded_bytes / 1024 / 1024
                            logger.info(f"消息 {message.id} 已下载: {progress_mb:.1f} MB")

                # 验证下载完整性
                actual_size = file_path.stat().st_size
                if file_size > 0 and actual_size != file_size:
                    logger.warning(f"消息 {message.id} 文件大小不匹配: 期望 {file_size}, 实际 {actual_size}")

                logger.info(f"Stream下载完成: {file_path.name} ({actual_size / 1024 / 1024:.2f} MB)")
                return file_path

            except FloodWait as e:
                logger.warning(f"Stream下载消息 {message.id} 遇到限流，等待 {e.value} 秒")
                await asyncio.sleep(float(e.value))
                # 递归重试
                return await self.download_media_file_stream(client, message)

            except Exception as e:
                logger.error(f"Stream下载消息 {message.id} 失败: {e}")
                # 清理不完整的文件
                if file_path.exists():
                    file_path.unlink()
                return None

        except Exception as e:
            logger.error(f"Stream下载消息 {message.id} 失败: {e}")
            return None

    async def download_media_file(self, client: Client, message) -> Optional[Path]:
        """智能选择下载方法：小于50MB的非视频文件使用RAW API，其他使用stream_media"""
        try:
            # 获取文件大小（MB）
            file_size_mb = self.get_file_size_mb(message)
            is_video = self.is_video_file(message)

            # 决策逻辑：文件大小小于50MB且非视频文件使用RAW API，其他使用stream_media
            use_raw_api = file_size_mb < 50.0 and not is_video

            if use_raw_api:
                logger.info(f"消息 {message.id}: 使用RAW API下载 (大小: {file_size_mb:.2f} MB, 视频: {is_video})")
                return await self.download_media_file_raw_api(client, message)
            else:
                logger.info(f"消息 {message.id}: 使用Stream下载 (大小: {file_size_mb:.2f} MB, 视频: {is_video})")
                return await self.download_media_file_stream(client, message)

        except Exception as e:
            logger.error(f"下载消息 {message.id} 失败: {e}")
            return None



    async def download_messages_by_ids(self, client: Client, message_ids: List[int], client_index: int,
                                      pre_fetched_messages: Optional[List[Any]] = None) -> Dict:
        """根据消息ID列表下载消息"""
        client_name = f"客户端{client_index + 1}"

        if not message_ids:
            logger.warning(f"{client_name} 没有分配到消息")
            return {
                "client": client_name,
                "downloaded": 0,
                "failed": 0,
                "range": "empty"
            }

        min_id, max_id = min(message_ids), max(message_ids)
        logger.info(f"{client_name} 开始下载 {len(message_ids)} 条消息 (ID范围: {min_id}-{max_id})")

        if not self.channel_info:
            self.channel_info = await self.get_channel_info(client)
            logger.info(f"频道信息: {self.channel_info['username']} - {self.channel_info['title']}")

        downloaded = 0
        failed = 0

        try:
            # 如果有预获取的消息，直接使用，否则重新获取
            if pre_fetched_messages:
                logger.info(f"{client_name} 使用预获取的 {len(pre_fetched_messages)} 条消息")
                all_messages = pre_fetched_messages

                # 直接处理所有消息
                for message in all_messages:
                    if message and hasattr(message, 'media') and message.media:
                        # 获取文件大小信息
                        file_size = self.get_file_size_bytes(message)

                        logger.info(f"{client_name} 消息 {message.id} 文件大小: {file_size / 1024 / 1024:.2f} MB")

                        try:
                            is_media_group = self.is_media_group_message(message)
                            if is_media_group:
                                logger.info(f"{client_name} 检测到媒体组消息: {message.id} (组ID: {message.media_group_id})")

                            file_path = await self.download_media_file(client, message)

                            if file_path:
                                downloaded += 1
                                if is_media_group:
                                    logger.info(f"{client_name} 媒体组文件下载成功: {file_path.name}")
                                else:
                                    logger.info(f"{client_name} 下载成功: {file_path.name}")
                            else:
                                failed += 1

                        except Exception as e:
                            failed += 1
                            logger.error(f"{client_name} 下载消息 {message.id} 失败: {e}")
                    else:
                        # 处理文本消息
                        if message:
                            await self.save_text_message(message)
                            downloaded += 1

                    # 显示进度
                    progress = (downloaded + failed) / len(all_messages) * 100
                    if (downloaded + failed) % 10 == 0:  # 每10个消息显示一次进度
                        logger.info(f"{client_name} 进度: {progress:.1f}% ({downloaded} 成功, {failed} 失败)")

                    # 短暂延迟，避免过于频繁的请求
                    await asyncio.sleep(0.1)



        except Exception as e:
            logger.error(f"{client_name} 下载任务失败: {e}")

        logger.info(f"{client_name} 完成下载: {downloaded} 成功, {failed} 失败")
        return {
            "client": client_name,
            "downloaded": downloaded,
            "failed": failed,
            "range": f"{min_id}-{max_id}",
            "total_messages": len(message_ids)
        }

    async def run_download(self):
        """运行下载任务 - 智能消息分配 + 并发获取"""
        logger.info("🚀 开始多客户端消息下载验证 - Stream Media + 并发获取 + 智能分配版本")
        logger.info(f"目标频道: {TARGET_CHANNEL}")
        logger.info(f"消息范围: {START_MESSAGE_ID} - {END_MESSAGE_ID} (共 {TOTAL_MESSAGES} 条)")
        logger.info(f"客户端数量: {len(SESSION_NAMES)} 个")
        logger.info("💡 新特性: 多客户端并发获取消息，减少API限流风险")

        clients = self.create_clients()
        self.stats["start_time"] = time.time()

        try:
            # 使用智能分配
            logger.info("🚀 启动并发获取 + 智能分配模式")

            # 先连接所有客户端用于消息获取（添加超时处理）
            connected_clients = []
            for i, client in enumerate(clients):
                try:
                    logger.info(f"🔄 正在连接客户端{i+1}...")
                    # 添加超时处理，避免无限等待
                    await asyncio.wait_for(client.start(), timeout=30.0)
                    connected_clients.append(client)
                    logger.info(f"✅ 客户端{i+1} 连接成功")
                except asyncio.TimeoutError:
                    logger.warning(f"⚠️ 客户端{i+1} 连接超时（30秒）")
                except Exception as e:
                    logger.warning(f"⚠️ 客户端{i+1} 连接失败: {e}")

            if not connected_clients:
                raise ValueError("没有可用的客户端")

            # 使用连接的客户端进行并发获取和智能分配
            client_message_mapping, client_message_objects, validation_stats = await self.smart_distribute_messages(connected_clients)

            # 断开客户端连接（稍后会重新连接用于下载）
            for client in connected_clients:
                try:
                    await client.stop()
                except:
                    pass

            logger.info("✅ 使用并发获取 + 智能消息分配")

            async def client_task(client, message_ids, pre_fetched_messages, index):
                # 错开启动时间，避免同时连接
                if index > 0:
                    delay_seconds = index * 0.5
                    logger.info(f"客户端{index + 1} 将在 {delay_seconds} 秒后启动...")
                    await asyncio.sleep(delay_seconds)

                logger.info(f"客户端{index + 1} 正在启动...")
                async with client:
                    return await self.download_messages_by_ids(client, message_ids, index, pre_fetched_messages)

            # 创建并发任务
            tasks = []
            for i, client in enumerate(clients):
                session_name = SESSION_NAMES[i]
                message_ids = client_message_mapping.get(session_name, [])
                pre_fetched_messages = client_message_objects.get(session_name, []) if client_message_objects else []
                task = client_task(client, message_ids, pre_fetched_messages, i)
                tasks.append(task)

            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            await self.process_results(results, validation_stats)

        except Exception as e:
            logger.error(f"下载任务执行失败: {e}")

    async def process_results(self, results, validation_stats=None):
        """处理下载结果"""
        # 防止重复处理
        if self._results_processed:
            logger.warning("⚠️ 结果已经处理过，跳过重复处理")
            return

        self._results_processed = True

        total_downloaded = 0
        total_failed = 0
        client_results = []

        for result in results:
            if isinstance(result, dict):
                total_downloaded += result["downloaded"]
                total_failed += result["failed"]
                client_results.append(result)
            else:
                logger.error(f"任务异常: {result}")

        # 输出详细统计信息
        logger.info("\n" + "="*60)
        logger.info("📊 Stream Media + 并发获取 + 智能分配 下载结果统计")
        logger.info("="*60)

        # 显示验证统计（如果有）
        if validation_stats and validation_stats.get("enabled"):
            if validation_stats.get("parallel_fetch"):
                logger.info("� 并发获取统计:")
                logger.info(f"  使用客户端数: {len(SESSION_NAMES)} 个")
                logger.info(f"  并发获取模式: ✅ 启用")
                logger.info("-" * 60)

            logger.info("�🔍 消息验证统计:")
            logger.info(f"  原始消息数: {validation_stats['original_count']}")
            logger.info(f"  有效消息数: {validation_stats['valid_count']}")
            logger.info(f"  无效消息数: {validation_stats['invalid_count']}")
            logger.info(f"  验证通过率: {validation_stats['validation_rate']:.1%}")
            logger.info("-" * 60)


        for result in client_results:
            range_info = result.get('range', 'unknown')
            total_msgs = result.get('total_messages', 'unknown')
            logger.info(f"{result['client']}: {result['downloaded']} 成功, {result['failed']} 失败 (范围: {range_info}, 总数: {total_msgs})")

        elapsed_time = time.time() - self.stats["start_time"]

        # 计算成功率（基于实际分配的消息数）
        actual_total = validation_stats.get('valid_count', TOTAL_MESSAGES) if validation_stats and validation_stats.get('enabled') else TOTAL_MESSAGES
        success_rate = (total_downloaded / actual_total * 100) if actual_total > 0 else 0

        logger.info("-" * 60)
        logger.info(f"总计: {total_downloaded} 成功, {total_failed} 失败")
        logger.info(f"成功率: {success_rate:.1f}% (基于有效消息)")
        logger.info(f"耗时: {elapsed_time:.1f} 秒")

        if elapsed_time > 0:
            logger.info(f"平均速度: {total_downloaded / elapsed_time:.1f} 条/秒")

        logger.info(f"下载目录: {self.download_dir.absolute()}")
        logger.info("="*60)


async def main():
    """主函数"""
    # 启动带宽监控
    threading.Thread(target=monitor_bandwidth, daemon=True).start()

    try:
        downloader = MultiClientDownloader()
        await downloader.run_download()
    except KeyboardInterrupt:
        logger.info("用户中断下载")
    except Exception as e:
        logger.error(f"程序执行失败: {e}")


if __name__ == "__main__":
    # 显示日志文件位置
    logs_dir = Path("logs")
    log_file = logs_dir / "test_downloader_stream.log"
    logger.info(f"📝 日志文件位置: {log_file.absolute()}")
    logger.info("🗑️ 日志文件已清除，开始新的日志记录")

    # 检查 TgCrypto - 简化版本
    try:
        import tgcrypto
        logger.info("✅ TgCrypto 已启用")
    except ImportError:
        logger.warning("⚠️ TgCrypto 未安装，建议安装: pip install tgcrypto")

    # 显示版本信息
    logger.info("🌊 使用 Pyrogram stream_media 方法进行流式下载")
    logger.info("🚀 特性: 多客户端并发获取消息，减少API限流")
    logger.info("🧠 核心: 智能媒体组感知分配算法")
    logger.info("⚡ 智能: 基于文件大小和类型的下载方法选择")
    logger.info("💡 优势: 内存效率高、自动数据中心选择、内置错误处理、并发加速")

    asyncio.run(main())
