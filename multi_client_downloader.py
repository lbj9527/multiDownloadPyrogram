"""
三客户端消息下载验证程序
核心功能：消息范围分片、异步任务管理、TgCrypto加速
"""
import asyncio
import time
from pathlib import Path
from typing import List, Dict, Tuple
from pyrogram import Client, compose
from pyrogram.errors import FloodWait
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_logging(verbose: bool = False):
    """配置日志系统"""
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
        
        downloaded = 0
        failed = 0
        
        try:
            # 获取消息范围内的所有消息ID
            message_ids = list(range(start_id, end_id + 1))
            
            # 批量获取消息（每次最多100条）
            batch_size = 100
            for i in range(0, len(message_ids), batch_size):
                batch_ids = message_ids[i:i + batch_size]
                
                try:
                    # 获取消息
                    messages = await client.get_messages(TARGET_CHANNEL, batch_ids)
                    
                    # 处理每条消息
                    for message in messages:
                        if message and hasattr(message, 'media') and message.media:
                            try:
                                # 下载媒体文件
                                file_path = await self.download_media_file(client, message, client_index)
                                if file_path:
                                    downloaded += 1
                                    logger.info(f"{client_name} 下载成功: {file_path.name}")
                                else:
                                    failed += 1
                            except Exception as e:
                                failed += 1
                                logger.error(f"{client_name} 下载消息 {message.id} 失败: {e}")
                        else:
                            # 非媒体消息，记录文本内容
                            if message:
                                await self.save_text_message(message, client_index)
                                downloaded += 1
                    
                    # 更新统计
                    self.stats["downloaded"] += len([m for m in messages if m])
                    
                    # 显示进度
                    progress = (downloaded + failed) / (end_id - start_id + 1) * 100
                    logger.info(f"{client_name} 进度: {progress:.1f}% ({downloaded} 成功, {failed} 失败)")
                    
                except FloodWait as e:
                    logger.warning(f"{client_name} 遇到限流，等待 {e.value} 秒")
                    await asyncio.sleep(e.value)
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
    
    async def download_media_file(self, client: Client, message, client_index: int) -> Path:
        """下载媒体文件"""
        try:
            # 创建客户端专用目录
            client_dir = self.download_dir / f"client_{client_index + 1}"
            client_dir.mkdir(parents=True, exist_ok=True)

            # 智能生成文件名
            file_name = self.generate_filename(message)

            # 下载文件
            file_path = await client.download_media(
                message,
                file_name=str(client_dir / file_name)
            )

            return Path(file_path) if file_path else None

        except Exception as e:
            logger.error(f"下载媒体文件失败: {e}")
            return None

    def generate_filename(self, message) -> str:
        """智能生成文件名"""
        base_name = f"msg_{message.id}"

        # 检查不同类型的媒体
        if hasattr(message, 'document') and message.document:
            # 文档类型
            if hasattr(message.document, 'file_name') and message.document.file_name:
                return f"{base_name}_{message.document.file_name}"
            else:
                # 根据MIME类型推断扩展名
                mime_type = getattr(message.document, 'mime_type', '')
                ext = self.get_extension_from_mime(mime_type)
                return f"{base_name}{ext}"

        elif hasattr(message, 'video') and message.video:
            # 视频类型
            if hasattr(message.video, 'file_name') and message.video.file_name:
                return f"{base_name}_{message.video.file_name}"
            else:
                return f"{base_name}.mp4"

        elif hasattr(message, 'photo') and message.photo:
            # 照片类型
            return f"{base_name}.jpg"

        elif hasattr(message, 'audio') and message.audio:
            # 音频类型
            if hasattr(message.audio, 'file_name') and message.audio.file_name:
                return f"{base_name}_{message.audio.file_name}"
            else:
                return f"{base_name}.mp3"

        elif hasattr(message, 'voice') and message.voice:
            # 语音类型
            return f"{base_name}.ogg"

        elif hasattr(message, 'video_note') and message.video_note:
            # 视频笔记类型
            return f"{base_name}.mp4"

        elif hasattr(message, 'animation') and message.animation:
            # 动画类型
            if hasattr(message.animation, 'file_name') and message.animation.file_name:
                return f"{base_name}_{message.animation.file_name}"
            else:
                return f"{base_name}.gif"

        elif hasattr(message, 'sticker') and message.sticker:
            # 贴纸类型
            return f"{base_name}.webp"

        else:
            # 未知类型，使用默认扩展名
            return f"{base_name}.bin"

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
    
    async def save_text_message(self, message, client_index: int):
        """保存文本消息"""
        try:
            client_dir = self.download_dir / f"client_{client_index + 1}"
            client_dir.mkdir(parents=True, exist_ok=True)

            text_file = client_dir / "messages.txt"

            with open(text_file, "a", encoding="utf-8") as f:
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
        
        logger.info("\n" + "="*60)
        logger.info("📊 下载结果统计")
        logger.info("="*60)
        
        for result in results:
            if isinstance(result, dict):
                total_downloaded += result["downloaded"]
                total_failed += result["failed"]
                logger.info(f"{result['client']}: {result['downloaded']} 成功, {result['failed']} 失败 (范围: {result['range']})")
            else:
                logger.error(f"任务异常: {result}")
        
        # 计算总体统计
        elapsed_time = time.time() - self.stats["start_time"]
        success_rate = (total_downloaded / TOTAL_MESSAGES * 100) if TOTAL_MESSAGES > 0 else 0
        
        logger.info("-" * 60)
        logger.info(f"总计: {total_downloaded} 成功, {total_failed} 失败")
        logger.info(f"成功率: {success_rate:.1f}%")
        logger.info(f"耗时: {elapsed_time:.1f} 秒")
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
