"""
主程序入口
重构后的多客户端Telegram下载器
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from config import app_settings
from utils import setup_logging, get_logger
from services import ClientManager, UploadService
from core import TelegramDownloader, FileProcessor
from interfaces import DownloadInterface

logger = get_logger(__name__)


class TelegramDownloaderApp:
    """Telegram下载器应用程序"""

    def __init__(self):
        self.client_manager = ClientManager()
        self.file_processor = FileProcessor()

        # 初始化上传服务（如果启用）
        self.upload_service = None
        if app_settings.upload.enabled:
            self.upload_service = UploadService()
            logger.info("✅ 上传服务已启用")

        self.downloader = TelegramDownloader(self.file_processor, self.upload_service)
        self.download_interface = DownloadInterface(
            self.client_manager,
            self.downloader
        )
    
    async def initialize(self):
        """初始化应用程序"""
        logger.info("🚀 启动Telegram多客户端下载器")
        
        # 验证配置
        config_errors = app_settings.validate()
        if config_errors:
            logger.error("配置验证失败:")
            for error in config_errors:
                logger.error(f"  - {error}")
            return False
        
        logger.info("✅ 配置验证通过")
        
        # 初始化客户端
        try:
            client_infos = await self.client_manager.initialize_clients()
            logger.info(f"✅ 初始化 {len(client_infos)} 个客户端")
            
            # 连接客户端
            connected_clients = await self.client_manager.connect_all_clients()
            if not connected_clients:
                logger.error("❌ 没有客户端连接成功")
                return False
            
            logger.info(f"✅ 成功连接 {len(connected_clients)} 个客户端")
            return True
            
        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}")
            return False
    
    async def run_download(self):
        """运行下载任务"""
        try:
            logger.info("📥 开始下载任务")

            # 记录开始时间
            import time
            start_time = time.time()

            # 创建下载任务
            download_config = app_settings.download

            # 执行下载
            results = await self.download_interface.download_messages(
                channel=download_config.target_channel,
                start_message_id=download_config.start_message_id,
                end_message_id=download_config.end_message_id,
                batch_size=download_config.batch_size
            )

            # 计算总耗时
            elapsed_time = time.time() - start_time

            # 显示结果
            self._display_results(results, elapsed_time)

            # 完成剩余的上传任务（如果启用了上传）
            if self.upload_service:
                logger.info("🔄 完成剩余的上传任务...")
                await self.upload_service.finalize_upload()
                self._display_upload_stats()

        except Exception as e:
            logger.error(f"❌ 下载任务失败: {e}")
            raise
    
    def _display_results(self, results, elapsed_time: float):
        """显示下载结果"""
        # 防止重复调用
        if hasattr(self, '_results_displayed'):
            return
        self._results_displayed = True

        # 收集所有有效结果
        valid_results = []
        total_downloaded = 0
        total_failed = 0

        for result in results:
            if result.get("status") == "completed":
                downloaded = result.get("downloaded", 0)
                failed = result.get("failed", 0)
                client_name = result.get("client", "unknown")

                total_downloaded += downloaded
                total_failed += failed

                valid_results.append({
                    "client": client_name,
                    "downloaded": downloaded,
                    "failed": failed
                })

        # 一次性输出所有统计信息
        logger.info("\n" + "=" * 60)
        logger.info("📊 下载结果统计")
        logger.info("=" * 60)

        # 输出每个客户端的结果
        for result in valid_results:
            logger.info(f"{result['client']}: {result['downloaded']} 成功, {result['failed']} 失败")

        # 计算总体统计
        total_messages = app_settings.download.end_message_id - app_settings.download.start_message_id + 1
        success_rate = (total_downloaded / total_messages * 100) if total_messages > 0 else 0

        # 输出总计信息
        logger.info("-" * 60)
        logger.info(f"总计: {total_downloaded} 成功, {total_failed} 失败")
        logger.info(f"成功率: {success_rate:.1f}%")
        logger.info(f"耗时: {elapsed_time:.1f} 秒")

        # 计算平均速度
        if elapsed_time > 0:
            avg_speed = total_downloaded / elapsed_time
            logger.info(f"平均速度: {avg_speed:.1f} 条/秒")

        # 显示下载目录
        download_dir = app_settings.get_download_directory()
        logger.info(f"下载目录: {download_dir.absolute()}")

        logger.info("=" * 60)
    
    async def cleanup(self):
        """清理资源"""
        logger.info("🧹 清理资源...")
        
        try:
            # 关闭压缩文件句柄
            self.file_processor.close_compression_handles()
            
            # 断开所有客户端
            await self.client_manager.disconnect_all_clients()
            
            logger.info("✅ 资源清理完成")
            
        except Exception as e:
            logger.error(f"❌ 清理资源失败: {e}")

    def _display_upload_stats(self):
        """显示上传统计信息"""
        if not self.upload_service:
            return

        logger.info("📤 上传统计信息:")
        stats = self.upload_service.get_upload_stats()

        logger.info(f"总上传文件: {stats['total_uploaded']}")
        logger.info(f"上传失败: {stats['total_failed']}")
        logger.info(f"媒体组上传: {stats['media_groups_uploaded']}")

        if stats['total_uploaded'] > 0:
            success_rate = (stats['total_uploaded'] / (stats['total_uploaded'] + stats['total_failed'])) * 100
            logger.info(f"上传成功率: {success_rate:.1f}%")

        logger.info("=" * 60)

    async def run(self):
        """运行应用程序"""
        try:
            # 初始化
            if not await self.initialize():
                return False
            
            # 运行下载
            await self.run_download()
            
            return True
            
        except KeyboardInterrupt:
            logger.info("⏹️ 用户中断下载")
            return False
        except Exception as e:
            logger.error(f"❌ 应用程序运行失败: {e}")
            return False
        finally:
            # 清理资源
            await self.cleanup()


def setup_application():
    """设置应用程序"""
    # 设置日志
    logging_config = app_settings.logging
    setup_logging(
        level=logging_config.level,
        format_string=logging_config.format,
        file_path=logging_config.file_path if logging_config.file_enabled else None,
        console_enabled=logging_config.console_enabled,
        file_enabled=logging_config.file_enabled,
        verbose_pyrogram=logging_config.verbose_pyrogram
    )
    
    # 确保下载目录存在
    download_dir = app_settings.get_download_directory()
    download_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"📂 下载目录: {download_dir}")
    logger.info(f"🎯 目标频道: {app_settings.download.target_channel}")
    logger.info(f"📝 消息范围: {app_settings.download.start_message_id}-{app_settings.download.end_message_id}")
    logger.info(f"👥 客户端数量: {app_settings.download.max_concurrent_clients}")
    logger.info(f"📦 批次大小: {app_settings.download.batch_size}")
    logger.info(f"💾 存储模式: {app_settings.storage.storage_mode}")


async def main():
    """主函数"""
    # 设置应用程序
    setup_application()
    
    # 创建并运行应用程序
    app = TelegramDownloaderApp()
    success = await app.run()
    
    # 退出
    exit_code = 0 if success else 1
    logger.info(f"🏁 程序退出，退出码: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    # 运行主程序
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ 程序被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 程序异常退出: {e}")
        sys.exit(1)
