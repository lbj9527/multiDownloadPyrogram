"""
三客户端消息下载验证程序
核心功能：消息范围分片、异步任务管理、TgCrypto加速
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

# 配置日志 - 避免重复配置
def setup_logging(verbose: bool = False):
    """配置日志系统"""
    # 获取根日志记录器
    root_logger = logging.getLogger()

    # 如果已经配置过，就不重复配置
    if not root_logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    # 配置Pyrogram日志级别
    if verbose:
        # 详细模式：显示所有日志
        logging.getLogger("pyrogram").setLevel(logging.INFO)
    else:
        # 简洁模式：只显示警告和错误
        logging.getLogger("pyrogram").setLevel(logging.WARNING)
        logging.getLogger("pyrogram.connection").setLevel(logging.WARNING)
        logging.getLogger("pyrogram.session").setLevel(logging.WARNING)
        logging.getLogger("pyrogram.dispatcher").setLevel(logging.WARNING)
        logging.getLogger("pyrogram.connection.transport").setLevel(logging.WARNING)

# 默认使用简洁模式
setup_logging(verbose=False)
logger = logging.getLogger(__name__)

# ==================== 配置区域 ====================
# Telegram API 配置
API_ID = 25098445
API_HASH = "cc2fa5a762621d306d8de030614e4555"
PHONE_NUMBER = "+8618758361347"

# 下载配置
TARGET_CHANNEL = "csdkl"  # https://t.me/csdkl
START_MESSAGE_ID = 71986
END_MESSAGE_ID = 72155
TOTAL_MESSAGES = END_MESSAGE_ID - START_MESSAGE_ID + 1

# 会话文件配置
SESSION_NAMES = [
    "client_session_1",
    "client_session_2", 
    "client_session_3"
]

# SOCKS5 代理配置
PROXY_CONFIG = {
    "scheme": "socks5",
    "hostname": "127.0.0.1",
    "port": 7890
}

# 下载目录
DOWNLOAD_DIR = Path("downloads")
# ==================== 配置区域结束 ====================


class MultiClientDownloader:
    """多客户端下载管理器"""

    def __init__(self):
        self.clients: List[Client] = []
        self.download_dir = DOWNLOAD_DIR
        self.download_dir.mkdir(exist_ok=True)
        self.channel_info = None  # 存储频道信息
        self.channel_dir = None   # 缓存频道目录路径
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
                workers=4,  # 优化工作线程数
                sleep_threshold=10  # FloodWait自动处理阈值
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

            # 清理文件名中的非法字符
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
        # 移除或替换Windows文件名中的非法字符
        illegal_chars = r'[<>:"/\\|?*]'
        safe_name = re.sub(illegal_chars, '_', filename)
        # 移除首尾空格和点
        safe_name = safe_name.strip('. ')
        return safe_name[:100]  # 限制长度

    def get_channel_directory(self) -> Path:
        """获取频道专用目录（带缓存机制）"""
        if not self.channel_info:
            raise ValueError("频道信息未初始化")

        # 如果已经创建过目录，直接返回缓存的路径
        if self.channel_dir is not None:
            return self.channel_dir

        # 首次创建目录
        self.channel_dir = self.download_dir / self.channel_info["folder_name"]

        # 检查目录是否已存在
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
        # 检查是否为媒体组消息
        if self.is_media_group_message(message):
            # 媒体组消息：媒体组ID-消息ID.扩展名
            base_name = f"{message.media_group_id}-{message.id}"
        else:
            # 单条消息：msg-消息ID.扩展名
            base_name = f"msg-{message.id}"

        # 获取文件扩展名
        extension = self.get_file_extension(message)
        return f"{base_name}{extension}"

    def get_file_extension(self, message) -> str:
        """获取消息媒体的文件扩展名"""
        # 检查不同类型的媒体
        if hasattr(message, 'document') and message.document:
            # 文档类型
            if hasattr(message.document, 'file_name') and message.document.file_name:
                # 从原文件名提取扩展名
                _, ext = os.path.splitext(message.document.file_name)
                return ext if ext else self.get_extension_from_mime(message.document.mime_type)
            else:
                # 根据MIME类型推断扩展名
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
    
    def calculate_message_ranges(self) -> List[Tuple[int, int]]:
        """计算消息范围分片"""
        client_count = len(SESSION_NAMES)
        messages_per_client = TOTAL_MESSAGES // client_count
        remainder = TOTAL_MESSAGES % client_count
        
        ranges = []
        current_start = START_MESSAGE_ID
        
        for i in range(client_count):
            # 为前几个客户端分配余数
            extra = 1 if i < remainder else 0
            messages_for_this_client = messages_per_client + extra
            
            current_end = current_start + messages_for_this_client - 1
            ranges.append((current_start, current_end))
            
            logger.info(f"客户端 {i+1} 分配范围: {current_start} - {current_end} ({messages_for_this_client} 条消息)")
            current_start = current_end + 1
        
        return ranges
    
    async def download_messages_range(self, client: Client, start_id: int, end_id: int, client_index: int) -> Dict:
        """下载指定范围的消息"""
        client_name = f"客户端{client_index + 1}"
        logger.info(f"{client_name} 开始下载消息范围: {start_id} - {end_id}")

        # 初始化频道信息（只需要一次）
        if not self.channel_info:
            self.channel_info = await self.get_channel_info(client)
            logger.info(f"频道信息: {self.channel_info['username']} - {self.channel_info['title']}")

        downloaded = 0
        failed = 0
        
        try:
            # 获取消息范围内的所有消息ID
            message_ids = list(range(start_id, end_id + 1))
            
            # 批量获取消息（每次最多200条，官方限制）
            batch_size = 200
            for i in range(0, len(message_ids), batch_size):
                batch_ids = message_ids[i:i + batch_size]
                
                try:
                    # 获取消息
                    messages = await client.get_messages(TARGET_CHANNEL, batch_ids)
                    
                    # 处理每条消息
                    for message in messages:
                        if message and hasattr(message, 'media') and message.media:
                            try:
                                # 检查是否为媒体组消息
                                is_media_group = self.is_media_group_message(message)
                                if is_media_group:
                                    logger.info(f"{client_name} 检测到媒体组消息: {message.id} (组ID: {message.media_group_id})")

                                # 下载媒体文件
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
                            # 非媒体消息，记录文本内容
                            if message:
                                await self.save_text_message(message)
                                downloaded += 1
                    
                    # 更新统计
                    self.stats["downloaded"] += len([m for m in messages if m])
                    
                    # 显示进度
                    progress = (downloaded + failed) / (end_id - start_id + 1) * 100
                    logger.info(f"{client_name} 进度: {progress:.1f}% ({downloaded} 成功, {failed} 失败)")
                    
                except FloodWait as e:
                    logger.warning(f"{client_name} 遇到限流，等待 {e.value} 秒")
                    await asyncio.sleep(float(e.value))
                except Exception as e:
                    logger.error(f"{client_name} 批量获取消息失败: {e}")
                    failed += len(batch_ids)
                
                # 小延迟避免过于频繁的请求
                await asyncio.sleep(0.1)
        
        except Exception as e:
            logger.error(f"{client_name} 下载任务失败: {e}")
        
        logger.info(f"{client_name} 完成下载: {downloaded} 成功, {failed} 失败")
        return {
            "client": client_name,
            "downloaded": downloaded,
            "failed": failed,
            "range": f"{start_id}-{end_id}"
        }
    
    async def download_media_file(self, client: Client, message) -> Optional[Path]:
        """下载媒体文件到频道目录"""
        try:
            # 获取频道目录（带缓存）
            channel_dir = self.get_channel_directory()

            # 根据消息类型生成文件名
            file_name = self.generate_filename_by_type(message)

            # 下载文件
            file_path = await client.download_media(
                message,
                file_name=str(channel_dir / file_name)
            )

            return Path(file_path) if file_path else None

        except Exception as e:
            logger.error(f"下载媒体文件失败: {e}")
            return None


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
                # 检查是否为媒体组消息
                if self.is_media_group_message(message):
                    f.write(f"消息ID: {message.id} (媒体组: {message.media_group_id})\n")
                else:
                    f.write(f"消息ID: {message.id}\n")
                f.write(f"时间: {message.date}\n")
                f.write(f"内容: {message.text or '无文本内容'}\n")
                f.write("-" * 50 + "\n")

        except Exception as e:
            logger.error(f"保存文本消息失败: {e}")
    
    async def run_download(self):
        """运行下载任务"""
        logger.info("🚀 开始三客户端消息下载验证")
        logger.info(f"目标频道: {TARGET_CHANNEL}")
        logger.info(f"消息范围: {START_MESSAGE_ID} - {END_MESSAGE_ID} (共 {TOTAL_MESSAGES} 条)")
        
        # 创建客户端
        clients = self.create_clients()
        
        # 计算消息范围分片
        message_ranges = self.calculate_message_ranges()
        
        # 记录开始时间
        self.stats["start_time"] = time.time()
        
        try:
            # 使用 asyncio.gather() 并发运行多个客户端任务
            async def client_task(client, message_range, index):
                async with client:  # 独立管理每个客户端的生命周期
                    return await self.download_messages_range(
                        client, message_range[0], message_range[1], index
                    )

            # 创建并发任务列表
            tasks = [
                client_task(clients[i], message_ranges[i], i)
                for i in range(len(clients))
            ]

            # 并发执行所有客户端任务
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            await self.process_results(results)
            
        except Exception as e:
            logger.error(f"下载任务执行失败: {e}")
    
    async def process_results(self, results):
        """处理下载结果"""
        total_downloaded = 0
        total_failed = 0
        client_results = []

        # 收集所有有效结果
        for result in results:
            if isinstance(result, dict):
                total_downloaded += result["downloaded"]
                total_failed += result["failed"]
                client_results.append(result)
            else:
                logger.error(f"任务异常: {result}")

        # 一次性输出所有统计信息，避免重复
        logger.info("\n" + "="*60)
        logger.info("📊 下载结果统计")
        logger.info("="*60)

        # 输出每个客户端的结果
        for result in client_results:
            logger.info(f"{result['client']}: {result['downloaded']} 成功, {result['failed']} 失败 (范围: {result['range']})")

        # 计算总体统计
        elapsed_time = time.time() - self.stats["start_time"]
        success_rate = (total_downloaded / TOTAL_MESSAGES * 100) if TOTAL_MESSAGES > 0 else 0

        # 输出总计信息
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
    try:
        downloader = MultiClientDownloader()
        await downloader.run_download()
    except KeyboardInterrupt:
        logger.info("用户中断下载")
    except Exception as e:
        logger.error(f"程序执行失败: {e}")


if __name__ == "__main__":
    # 检查TgCrypto是否安装
    try:
        import tgcrypto
        logger.info("✅ TgCrypto 已启用，加密操作将被加速")
    except ImportError:
        logger.warning("⚠️  TgCrypto 未安装，建议安装以提升性能: pip install tgcrypto")
    
    # 运行程序
    asyncio.run(main())
