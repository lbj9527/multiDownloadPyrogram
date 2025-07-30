"""
三客户端消息下载验证程序 - Stream Media 版本
核心功能：消息范围分片、异步任务管理、TgCrypto加速、流式下载
使用 Pyrogram 的 stream_media 方法进行高效流式下载

注意：此文件使用硬编码配置，请在配置区域修改相关参数
"""
import asyncio
import os
import re
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from pyrogram.client import Client
from pyrogram.errors import FloodWait
import logging
import psutil
import threading

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
        logging.getLogger("pyrogram").setLevel(logging.WARNING)
        logging.getLogger("pyrogram.connection").setLevel(logging.WARNING)
        logging.getLogger("pyrogram.session").setLevel(logging.WARNING)
        logging.getLogger("pyrogram.dispatcher").setLevel(logging.WARNING)
        logging.getLogger("pyrogram.connection.transport").setLevel(logging.WARNING)

setup_logging(verbose=True)  # 启用详细日志
logger = logging.getLogger(__name__)

# ==================== 配置区域 ====================
API_ID = 25098445
API_HASH = "cc2fa5a762621d306d8de030614e4555"
PHONE_NUMBER = "+8618758361347"
TARGET_CHANNEL = "@zbzwx"
START_MESSAGE_ID = 37788
END_MESSAGE_ID = 37794
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
# ==================== 配置区域结束 ====================

def monitor_bandwidth():
    old_stats = psutil.net_io_counters()
    while True:
        time.sleep(1)
        new_stats = psutil.net_io_counters()
        download_speed = (new_stats.bytes_recv - old_stats.bytes_recv) / 1024
        upload_speed = (new_stats.bytes_sent - old_stats.bytes_sent) / 1024
        logger.info(f"Download: {download_speed:.2f} KB/s, Upload: {upload_speed:.2f} KB/s")
        old_stats = new_stats

class MultiClientDownloader:
    """多客户端下载管理器 - Stream Media 版本"""
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

    def calculate_message_ranges(self) -> List[Tuple[int, int]]:
        """计算消息范围分片"""
        client_count = len(SESSION_NAMES)
        messages_per_client = TOTAL_MESSAGES // client_count
        remainder = TOTAL_MESSAGES % client_count
        ranges = []
        current_start = START_MESSAGE_ID
        for i in range(client_count):
            extra = 1 if i < remainder else 0
            messages_for_this_client = messages_per_client + extra
            current_end = current_start + messages_for_this_client - 1
            ranges.append((current_start, current_end))
            logger.info(f"客户端 {i+1} 分配范围: {current_start} - {current_end} ({messages_for_this_client} 条消息)")
            current_start = current_end + 1
        return ranges

    async def download_media_file(self, client: Client, message) -> Optional[Path]:
        """使用 stream_media 方法下载媒体文件"""
        try:
            channel_dir = self.get_channel_directory()
            file_name = self.generate_filename_by_type(message)
            file_path = channel_dir / file_name

            # 获取文件大小信息
            file_size = getattr(getattr(message, 'document', None), 'file_size', 0) or \
                        getattr(getattr(message, 'video', None), 'file_size', 0) or \
                        getattr(getattr(message, 'photo', None), 'file_size', 0) or 0

            logger.info(f"开始流式下载消息 {message.id} (大小: {file_size / 1024 / 1024:.2f} MB)")

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

                logger.info(f"流式下载完成: {file_path.name} ({actual_size / 1024 / 1024:.2f} MB)")
                return file_path

            except FloodWait as e:
                logger.warning(f"下载消息 {message.id} 遇到限流，等待 {e.value} 秒")
                await asyncio.sleep(float(e.value))
                # 递归重试
                return await self.download_media_file(client, message)

            except Exception as e:
                logger.error(f"流式下载消息 {message.id} 失败: {e}")
                # 清理不完整的文件
                if file_path.exists():
                    file_path.unlink()
                return None

        except Exception as e:
            logger.error(f"下载消息 {message.id} 失败: {e}")
            return None

    async def download_messages_range(self, client: Client, start_id: int, end_id: int, client_index: int) -> Dict:
        """下载指定范围的消息"""
        client_name = f"客户端{client_index + 1}"
        logger.info(f"{client_name} 开始下载消息范围: {start_id} - {end_id}")

        if not self.channel_info:
            self.channel_info = await self.get_channel_info(client)
            logger.info(f"频道信息: {self.channel_info['username']} - {self.channel_info['title']}")

        downloaded = 0
        failed = 0

        try:
            message_ids = list(range(start_id, end_id + 1))
            batch_size = 50

            for i in range(0, len(message_ids), batch_size):
                batch_ids = message_ids[i:i + batch_size]

                try:
                    messages = await client.get_messages(TARGET_CHANNEL, batch_ids)

                    for message in messages:
                        if message and hasattr(message, 'media') and message.media:
                            # 获取文件大小信息
                            file_size = getattr(getattr(message, 'document', None), 'file_size', 0) or \
                                        getattr(getattr(message, 'video', None), 'file_size', 0) or \
                                        getattr(getattr(message, 'photo', None), 'file_size', 0) or 0

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

                    # 更新统计信息
                    self.stats["downloaded"] += len([m for m in messages if m])
                    progress = (downloaded + failed) / (end_id - start_id + 1) * 100
                    logger.info(f"{client_name} 进度: {progress:.1f}% ({downloaded} 成功, {failed} 失败)")

                except FloodWait as e:
                    logger.warning(f"{client_name} 遇到限流，等待 {e.value} 秒")
                    await asyncio.sleep(float(e.value))

                except Exception as e:
                    logger.error(f"{client_name} 批量获取消息失败: {e}")
                    failed += len(batch_ids)

                # 短暂延迟，避免过于频繁的请求
                await asyncio.sleep(0.2)

        except Exception as e:
            logger.error(f"{client_name} 下载任务失败: {e}")

        logger.info(f"{client_name} 完成下载: {downloaded} 成功, {failed} 失败")
        return {
            "client": client_name,
            "downloaded": downloaded,
            "failed": failed,
            "range": f"{start_id}-{end_id}"
        }

    async def run_download(self):
        """运行下载任务"""
        logger.info("🚀 开始多客户端消息下载验证 - Stream Media 版本")
        logger.info(f"目标频道: {TARGET_CHANNEL}")
        logger.info(f"消息范围: {START_MESSAGE_ID} - {END_MESSAGE_ID} (共 {TOTAL_MESSAGES} 条)")

        clients = self.create_clients()
        message_ranges = self.calculate_message_ranges()
        self.stats["start_time"] = time.time()

        try:
            async def client_task(client, message_range, index):
                # 错开启动时间，避免同时连接
                if index > 0:
                    delay_seconds = index * 0.5
                    logger.info(f"客户端{index + 1} 将在 {delay_seconds} 秒后启动...")
                    await asyncio.sleep(delay_seconds)

                logger.info(f"客户端{index + 1} 正在启动...")
                async with client:
                    return await self.download_messages_range(
                        client, message_range[0], message_range[1], index
                    )

            # 创建并发任务
            tasks = [
                client_task(clients[i], message_ranges[i], i)
                for i in range(len(clients))
            ]

            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            await self.process_results(results)

        except Exception as e:
            logger.error(f"下载任务执行失败: {e}")

    async def process_results(self, results):
        """处理下载结果"""
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
        logger.info("📊 Stream Media 下载结果统计")
        logger.info("="*60)

        for result in client_results:
            logger.info(f"{result['client']}: {result['downloaded']} 成功, {result['failed']} 失败 (范围: {result['range']})")

        elapsed_time = time.time() - self.stats["start_time"]
        success_rate = (total_downloaded / TOTAL_MESSAGES * 100) if TOTAL_MESSAGES > 0 else 0

        logger.info("-" * 60)
        logger.info(f"总计: {total_downloaded} 成功, {total_failed} 失败")
        logger.info(f"成功率: {success_rate:.1f}%")
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

    # 检查 TgCrypto
    try:
        import tgcrypto
        logger.info("✅ TgCrypto 已启用，加密操作将被加速")
    except ImportError:
        logger.warning("⚠️ TgCrypto 未安装，建议安装以提升性能: pip install tgcrypto")

    # 显示版本信息
    logger.info("🌊 使用 Pyrogram stream_media 方法进行流式下载")
    logger.info("💡 优势: 内存效率高、自动数据中心选择、内置错误处理")

    asyncio.run(main())
