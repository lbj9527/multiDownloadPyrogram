"""
主程序入口 - 重构版本
协调各个模块完成多客户端下载任务，保持与test_downloader_stream.py相同的功能
"""
import asyncio
import threading
from pathlib import Path
from typing import List, Optional

# 配置和工具
from config.settings import AppConfig
from utils.logging_utils import setup_logging

# 核心模块
from core.client import ClientManager
from core.message import MessageFetcher, MessageGrouper
from core.task_distribution import TaskDistributor
from core.download import DownloadManager

# 监控模块
from monitoring import StatsCollector, BandwidthMonitor

class MultiClientDownloader:
    """
    多客户端下载器 - 重构版本
    保持与test_downloader_stream.py相同的功能和接口
    """
    
    def __init__(self, config: Optional[AppConfig] = None):
        # 使用配置或默认配置
        self.config = config or AppConfig.from_test_downloader_stream()
        
        # 初始化各个管理器
        self.client_manager = ClientManager(self.config.telegram)
        self.download_manager = DownloadManager(self.config.download)
        self.message_grouper = MessageGrouper()
        self.task_distributor = TaskDistributor()
        
        # 监控组件
        self.stats_collector = StatsCollector()
        self.bandwidth_monitor = BandwidthMonitor()
        
        # 状态
        self.is_running = False
        self.clients = []
    
    async def run_download(
        self, 
        channel: Optional[str] = None,
        start_id: Optional[int] = None,
        end_id: Optional[int] = None
    ):
        """
        执行下载任务 - 主要入口点
        保持与test_downloader_stream.py相同的接口
        """
        try:
            # 使用配置中的默认值
            channel = channel or self.config.download.channel
            start_id = start_id or self.config.download.start_message_id
            end_id = end_id or self.config.download.end_message_id
            
            self.log_info("🚀 启动多客户端下载器...")
            self.log_info(f"目标频道: {channel}")
            self.log_info(f"消息范围: {start_id} - {end_id}")
            
            # 启动监控
            await self._start_monitoring()
            
            # 初始化和启动客户端
            await self._initialize_clients()
            
            # 获取消息
            messages = await self._fetch_messages(channel, start_id, end_id)
            if not messages:
                self.log_error("未获取到任何消息，退出")
                return
            
            # 分组和分配任务
            distribution_result = await self._distribute_tasks(messages)
            
            # 执行下载
            await self._execute_downloads(distribution_result, channel)
            
            # 输出最终报告
            self._print_final_results()
            
        except KeyboardInterrupt:
            self.log_info("用户中断下载")
        except Exception as e:
            self.log_error(f"下载过程出错: {e}")
        finally:
            await self._cleanup()
    
    async def _start_monitoring(self):
        """启动监控"""
        # 启动带宽监控
        self.bandwidth_monitor.start()
        self.log_info("📊 带宽监控已启动")
    
    async def _initialize_clients(self):
        """初始化客户端"""
        self.log_info("🔧 初始化客户端...")
        
        # 初始化客户端
        self.clients = await self.client_manager.initialize_clients()
        if not self.clients:
            raise RuntimeError("没有可用的客户端")
        
        # 启动客户端
        await self.client_manager.start_all_clients()
        
        # 显示客户端信息
        client_info = self.client_manager.get_client_info()
        self.log_info(f"✅ 成功启动 {client_info['active_clients']} 个客户端")
    
    async def _fetch_messages(self, channel: str, start_id: int, end_id: int) -> List:
        """获取消息"""
        self.log_info("📥 开始获取消息...")
        
        # 创建消息获取器
        message_fetcher = MessageFetcher(self.clients)
        
        # 并发获取消息
        messages = await message_fetcher.parallel_fetch_messages(channel, start_id, end_id)
        
        self.log_info(f"📊 成功获取 {len(messages)} 条消息")
        return messages
    
    async def _distribute_tasks(self, messages: List) -> object:
        """分组和分配任务"""
        self.log_info("🧠 开始消息分组...")
        
        # 消息分组
        message_collection = self.message_grouper.group_messages_from_list(messages)
        
        # 任务分配
        self.log_info("⚖️ 开始任务分配...")
        client_names = self.client_manager.get_client_names()
        distribution_result = await self.task_distributor.distribute_tasks(
            message_collection, client_names
        )
        
        # 显示分配结果
        balance_stats = distribution_result.get_load_balance_stats()
        self.log_info(f"📊 任务分配完成: {balance_stats}")
        
        # 设置统计总数
        self.stats_collector.set_total_messages(distribution_result.total_messages)
        
        return distribution_result
    
    async def _execute_downloads(self, distribution_result: object, channel: str):
        """执行下载任务"""
        self.log_info("📥 开始并发下载...")
        
        # 创建下载任务
        download_tasks = []
        for assignment in distribution_result.client_assignments:
            client = self._get_client_by_name(assignment.client_name)
            if client:
                task = self._download_client_messages(client, assignment, channel)
                download_tasks.append(task)
        
        # 并发执行下载
        await asyncio.gather(*download_tasks, return_exceptions=True)
    
    async def _download_client_messages(self, client, assignment, channel: str):
        """单个客户端的下载任务"""
        client_name = assignment.client_name
        messages = assignment.get_all_messages()

        self.log_info(f"🔄 {client_name} 开始下载 {len(messages)} 个文件...")

        # 获取频道信息并创建目录（与原程序保持一致）
        channel_info = await self._get_channel_info(client, channel)

        for message in messages:
            try:
                # 下载文件 - 使用频道信息
                result = await self.download_manager.download_media(client, message, channel_info["folder_name"])

                # 更新统计
                success = result is not None
                file_size_mb = 0.0
                if success and result:
                    file_size_mb = result.stat().st_size / (1024 * 1024)

                self.stats_collector.update_download_progress(
                    success=success,
                    message_id=message.id,
                    client_name=client_name,
                    file_size_mb=file_size_mb
                )

            except Exception as e:
                self.log_error(f"{client_name} 下载消息 {message.id} 失败: {e}")
                self.stats_collector.update_download_progress(
                    success=False,
                    message_id=message.id,
                    client_name=client_name
                )

        self.log_info(f"✅ {client_name} 下载任务完成")
    
    def _get_client_by_name(self, client_name: str):
        """根据名称获取客户端"""
        for client in self.clients:
            if client.name == client_name:
                return client
        return None

    async def _get_channel_info(self, client, channel: str) -> dict:
        """获取频道信息 - 与原程序保持一致"""
        try:
            chat = await client.get_chat(channel)
            username = f"@{chat.username}" if chat.username else f"id_{chat.id}"
            title = chat.title or "Unknown"

            # 清理文件名
            import re
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', title).strip('. ')[:100]
            folder_name = f"{username}-{safe_title}"

            return {
                "username": username,
                "title": title,
                "folder_name": folder_name
            }
        except Exception as e:
            self.log_error(f"获取频道信息失败: {e}")
            # 回退到简单的文件夹名
            clean_channel = re.sub(r'[<>:"/\\|?*@]', '_', channel)
            return {
                "username": channel,
                "title": channel,
                "folder_name": clean_channel
            }
    
    def _print_final_results(self):
        """打印最终结果"""
        self.log_info("📊 生成最终报告...")
        self.stats_collector.print_final_report()
        
        # 下载管理器统计
        download_stats = self.download_manager.get_download_stats()
        self.log_info(f"下载方法统计: Stream={download_stats['stream_downloads']}, RAW={download_stats['raw_downloads']}")
    
    async def _cleanup(self):
        """清理资源"""
        self.log_info("🧹 清理资源...")
        
        # 停止监控
        self.bandwidth_monitor.stop()
        
        # 停止客户端
        await self.client_manager.stop_all_clients()
        
        self.log_info("✅ 清理完成")
    
    def log_info(self, message: str):
        """记录信息日志"""
        import logging
        logging.getLogger(self.__class__.__name__).info(message)
    
    def log_error(self, message: str):
        """记录错误日志"""
        import logging
        logging.getLogger(self.__class__.__name__).error(message)

async def main():
    """
    主函数 - 保持与test_downloader_stream.py相同的入口
    """
    # 设置日志
    log_file = Path("logs") / "main.log"
    setup_logging(log_file=log_file, clear_log=True)
    
    # 启动带宽监控线程（兼容原有功能）
    from monitoring.bandwidth_monitor import create_simple_bandwidth_monitor
    bandwidth_monitor = create_simple_bandwidth_monitor()
    
    try:
        # 创建下载器并运行
        downloader = MultiClientDownloader()
        await downloader.run_download()
        
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        print(f"程序执行失败: {e}")
    finally:
        # 停止带宽监控
        bandwidth_monitor.stop()

if __name__ == "__main__":
    # 显示启动信息
    print("🚀 多客户端Telegram下载器 - 重构版本")
    print("📝 日志文件: logs/main.log")
    
    # 检查TgCrypto
    try:
        import tgcrypto
        print("✅ TgCrypto 已启用")
    except ImportError:
        print("⚠️ TgCrypto 未安装，下载速度可能较慢")
    
    # 运行主程序
    asyncio.run(main())
