"""
主程序入口
协调各个模块完成多客户端下载任务
支持本地下载和转发上传两种工作流模式
"""
import asyncio
import argparse
from pathlib import Path
from typing import List, Optional

# 配置和工具
from config.settings import AppConfig
from utils.logging_utils import setup_logging
from utils.channel_utils import ChannelUtils
from utils.async_context_manager import SafeClientManager, suppress_pyrogram_errors, AsyncTaskCleaner

# 核心模块
from core.client import ClientManager
from core.message import MessageFetcher, MessageGrouper
from core.task_distribution import TaskDistributor
from core.download import DownloadManager

# 模板和上传模块 (Phase 2 & 3)
from core.template import TemplateProcessor
from core.upload import UploadManager, BatchUploader

# 数据模型
from models.workflow_config import WorkflowConfig, WorkflowType
from models.template_config import TemplateConfig, TemplateMode
from models.upload_task import UploadTask

# 监控模块
from monitoring import StatsCollector

class MultiClientDownloader:
    """
    多客户端下载器
    支持本地下载和转发上传两种工作流模式
    """

    def __init__(self, config: Optional[AppConfig] = None, workflow_config: Optional[WorkflowConfig] = None):
        # 使用配置或默认配置
        self.config = config or AppConfig()
        self.workflow_config = workflow_config

        # 初始化各个管理器
        self.client_manager = ClientManager(self.config.telegram)
        self.download_manager = DownloadManager(self.config.download)
        self.message_grouper = MessageGrouper()
        self.task_distributor = TaskDistributor()

        # 模板和上传管理器 (Phase 2 & 3)
        self.template_processor = TemplateProcessor()
        self.upload_manager = UploadManager()
        self.batch_uploader = BatchUploader(max_concurrent=3)

        # 监控组件
        self.stats_collector = StatsCollector()

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
        支持本地下载和转发上传两种模式
        """
        try:
            # 确定工作流配置
            if self.workflow_config:
                # 使用工作流配置
                channel = self.workflow_config.source_channel
                start_id, end_id = self.workflow_config.message_range
                workflow_type = self.workflow_config.workflow_type
            else:
                # 使用传统配置（向后兼容）
                channel = channel or self.config.download.channel
                start_id = start_id or self.config.download.start_message_id
                end_id = end_id or self.config.download.end_message_id
                workflow_type = WorkflowType.LOCAL_DOWNLOAD

            self.log_info("🚀 启动多客户端下载器...")
            self.log_info(f"工作流模式: {workflow_type.value}")
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

            # 根据工作流类型执行不同的逻辑
            if workflow_type == WorkflowType.LOCAL_DOWNLOAD:
                await self._execute_local_download_workflow(messages, channel)
            elif workflow_type == WorkflowType.FORWARD:
                await self._execute_forward_workflow(messages)
            else:
                raise ValueError(f"不支持的工作流类型: {workflow_type}")

            # 输出最终报告
            self._print_final_results()

        except KeyboardInterrupt:
            self.log_info("用户中断下载")
        except Exception as e:
            self.log_error(f"执行过程出错: {e}")
        finally:
            await self._cleanup()
    
    async def _start_monitoring(self):
        """启动监控"""
        self.log_info("📊 监控系统已启动")
    
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
    
    async def _execute_local_download_workflow(self, messages: List, channel: str):
        """执行本地下载工作流"""
        self.log_info("📥 执行本地下载工作流...")

        # 分组和分配任务
        distribution_result = await self._distribute_tasks(messages)

        # 创建下载任务
        download_tasks = []
        for assignment in distribution_result.client_assignments:
            client = self.client_manager.get_client_by_name(assignment.client_name)
            if client:
                task = self._download_client_messages(client, assignment, channel)
                download_tasks.append(task)

        # 并发执行下载
        await asyncio.gather(*download_tasks, return_exceptions=True)

    async def _execute_forward_workflow(self, messages: List):
        """执行转发上传工作流（并发版本）"""
        self.log_info("📤 执行并发转发上传工作流...")

        if not self.workflow_config or not self.workflow_config.target_channels:
            raise ValueError("转发工作流需要配置目标频道")

        if not self.workflow_config.template_config:
            raise ValueError("转发工作流需要配置模板")

        # 1. 分组和分配任务（复用下载模式的分配逻辑）
        distribution_result = await self._distribute_tasks(messages)

        # 2. 创建并发转发任务
        forward_tasks = []
        for assignment in distribution_result.client_assignments:
            client = self.client_manager.get_client_by_name(assignment.client_name)
            if client:
                task = self._forward_client_messages(client, assignment)
                forward_tasks.append(task)

        # 3. 并发执行转发
        self.log_info(f"🚀 启动 {len(forward_tasks)} 个客户端并发转发...")
        results = await asyncio.gather(*forward_tasks, return_exceptions=True)

        # 4. 汇总结果
        self._summarize_forward_results(results, len(messages))

    async def _forward_client_messages(self, client, assignment):
        """单个客户端的转发任务"""
        client_name = assignment.client_name
        messages = assignment.get_all_messages()

        self.log_info(f"🔄 {client_name} 开始转发 {len(messages)} 个文件...")

        successful_forwards = 0
        failed_forwards = 0

        for message in messages:
            try:
                # 1. 内存下载
                download_result = await self.download_manager.download_media_enhanced(
                    client, message, mode="memory"
                )

                if not download_result:
                    self.log_warning(f"{client_name} 消息 {message.id} 下载失败，跳过")
                    failed_forwards += 1
                    continue

                # 2. 模板处理
                processed_result = self.template_processor.process(
                    self.workflow_config.template_config,
                    download_result,
                    auto_extract=True
                )

                if not processed_result.get("success", True):
                    self.log_warning(f"{client_name} 消息 {message.id} 模板处理失败: {processed_result.get('error', 'Unknown error')}")

                # 3. 创建上传任务
                upload_tasks = []
                for target_channel in self.workflow_config.target_channels:
                    upload_task = UploadTask(
                        source_message_id=message.id,
                        target_channel=target_channel,
                        file_name=download_result.file_name,
                        file_size=download_result.file_size,
                        file_data=download_result.file_data,
                        formatted_content=processed_result.get('content', ''),
                        caption=processed_result.get('content', '')
                    )
                    upload_tasks.append(upload_task)

                # 4. 批量上传
                if upload_tasks:
                    batch_result = await self.batch_uploader.upload_batch(client, upload_tasks)
                    if batch_result.is_completed():
                        successful_forwards += 1
                        self.log_info(f"{client_name} 消息 {message.id} 转发成功: {batch_result.get_success_rate():.1%}")
                    else:
                        failed_forwards += 1
                        self.log_error(f"{client_name} 消息 {message.id} 转发失败")
                else:
                    failed_forwards += 1
                    self.log_error(f"{client_name} 消息 {message.id} 没有创建上传任务")

            except Exception as e:
                failed_forwards += 1
                self.log_error(f"{client_name} 处理消息 {message.id} 时出错: {e}")

        self.log_info(f"✅ {client_name} 转发任务完成: 成功 {successful_forwards}, 失败 {failed_forwards}")

        # 返回结果统计
        return {
            "client_name": client_name,
            "successful_forwards": successful_forwards,
            "failed_forwards": failed_forwards,
            "total_messages": len(messages)
        }

    def _summarize_forward_results(self, results: List, total_messages: int):
        """汇总转发结果"""
        total_successful = 0
        total_failed = 0

        for result in results:
            if isinstance(result, Exception):
                self.log_error(f"客户端转发任务异常: {result}")
                continue

            if isinstance(result, dict):
                total_successful += result.get("successful_forwards", 0)
                total_failed += result.get("failed_forwards", 0)

                # 更新统计信息
                client_name = result.get("client_name", "unknown")
                for i in range(result.get("successful_forwards", 0)):
                    self.stats_collector.update_download_progress(True, None, client_name, 0)
                for i in range(result.get("failed_forwards", 0)):
                    self.stats_collector.update_download_progress(False, None, client_name, 0)

        self.log_info(f"🎉 并发转发工作流完成: 成功 {total_successful}, 失败 {total_failed}")

        # 设置统计总数
        self.stats_collector.set_total_messages(total_messages)
    
    async def _download_client_messages(self, client, assignment, channel: str):
        """单个客户端的下载任务"""
        client_name = assignment.client_name
        messages = assignment.get_all_messages()

        self.log_info(f"🔄 {client_name} 开始下载 {len(messages)} 个文件...")

        # 获取频道信息并创建目录
        channel_info = await ChannelUtils.get_channel_info(client, channel)

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

        try:
            # 使用安全的客户端管理器停止所有客户端
            if self.clients:
                safe_manager = SafeClientManager(self.clients)
                await safe_manager.safe_stop_all()
            else:
                # 如果没有直接的客户端列表，使用原有方法
                await self.client_manager.stop_all_clients()

            # 优雅关闭剩余任务
            await AsyncTaskCleaner.graceful_shutdown(timeout=3.0)

        except Exception as e:
            self.log_error(f"清理过程中出现错误: {e}")

        self.log_info("✅ 清理完成")
    
    def log_info(self, message: str):
        """记录信息日志"""
        import logging
        logging.getLogger(self.__class__.__name__).info(message)
    
    def log_error(self, message: str):
        """记录错误日志"""
        import logging
        logging.getLogger(self.__class__.__name__).error(message)

    def log_debug(self, message: str):
        """记录调试日志"""
        import logging
        logging.getLogger(self.__class__.__name__).debug(message)

    def log_warning(self, message: str):
        """记录警告日志"""
        import logging
        logging.getLogger(self.__class__.__name__).warning(message)

def create_workflow_config_from_args(args) -> Optional[WorkflowConfig]:
    """根据命令行参数创建工作流配置"""
    if args.mode == "download":
        return WorkflowConfig(
            workflow_type=WorkflowType.LOCAL_DOWNLOAD,
            source_channel=args.source,
            message_range=(args.start, args.end),
            create_subfolder=True
        )
    elif args.mode == "forward":
        if not args.targets:
            raise ValueError("转发模式需要指定目标频道 (--targets)")

        # 创建默认模板配置
        template_config = TemplateConfig(
            template_id="default_forward",
            name="默认转发模板",
            mode=TemplateMode.CUSTOM,
            content=args.template or "📸 来自 {source_channel} 的内容\n\n{original_text}{original_caption}\n\n📁 文件: {file_name} ({file_size_formatted})"
        )

        return WorkflowConfig(
            workflow_type=WorkflowType.FORWARD,
            source_channel=args.source,
            message_range=(args.start, args.end),
            target_channels=args.targets,
            template_config=template_config
        )
    else:
        return None

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="多客户端 Telegram 下载器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  本地下载: python main.py --mode download --source "@channel" --start 1000 --end 2000
  转发上传: python main.py --mode forward --source "@source" --targets "@target1" "@target2"

注意: 在 PowerShell 中，频道名称需要用引号包围，如 "@channel"
        """
    )

    # 工作流模式
    parser.add_argument("--mode", choices=["download", "forward"], default="download",
                       help="工作流模式: download=本地下载, forward=转发上传")

    # 通用参数
    parser.add_argument("--source", type=str, default="@csdkl",
                       help="源频道 (默认: @csdkl)，在 PowerShell 中请用引号包围")
    parser.add_argument("--start", type=int, default=72710,
                       help="起始消息ID (默认: 72710)")
    parser.add_argument("--end", type=int, default=72849,
                       help="结束消息ID (默认: 72849)")
    # 本地下载参数
    # 注意：下载目录由 config/settings.py 中的 DownloadConfig.download_dir 配置
    # 并发数由 config/settings.py 中的 TelegramConfig.session_names 数量决定

    # 转发参数
    parser.add_argument("--targets", nargs="+",
                       help="目标频道列表 (转发模式必需)，在 PowerShell 中请用引号包围")
    parser.add_argument("--template", type=str,
                       help="自定义模板内容")

    args = parser.parse_args()

    # 参数验证
    validate_arguments(args)

    return args

def validate_arguments(args):
    """验证命令行参数"""
    # 验证消息ID范围
    if args.start >= args.end:
        raise ValueError(f"起始消息ID ({args.start}) 必须小于结束消息ID ({args.end})")

    if args.start < 1 or args.end < 1:
        raise ValueError("消息ID必须大于0")

    # 注意：并发数由 config/settings.py 中的 TelegramConfig.session_names 数量决定

    # 验证转发模式的必需参数
    if args.mode == "forward" and not args.targets:
        raise ValueError("转发模式必须指定目标频道 (--targets)")

    # 验证频道名称格式
    if not args.source.startswith('@') and not args.source.startswith('-'):
        print(f"⚠️ 警告: 源频道 '{args.source}' 可能格式不正确，建议使用 @channel 或 -100xxx 格式")

    if args.targets:
        for target in args.targets:
            if not target.startswith('@') and not target.startswith('-'):
                print(f"⚠️ 警告: 目标频道 '{target}' 可能格式不正确，建议使用 @channel 或 -100xxx 格式")

async def main():
    """
    主函数
    """
    # 抑制Pyrogram的常见清理错误
    suppress_pyrogram_errors()

    # 解析命令行参数
    args = parse_arguments()

    # 设置日志
    log_file = Path("logs") / "main.log"
    setup_logging(log_file=log_file, clear_log=True, suppress_pyrogram=True)

    # 启动带宽监控线程
    from monitoring.bandwidth_monitor import create_simple_bandwidth_monitor
    bandwidth_monitor = create_simple_bandwidth_monitor()

    try:
        # 创建工作流配置
        workflow_config = create_workflow_config_from_args(args)

        # 创建下载器并运行
        downloader = MultiClientDownloader(workflow_config=workflow_config)
        await downloader.run_download()

    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        print(f"程序执行失败: {e}")
    finally:
        # 停止带宽监控
        bandwidth_monitor.stop()

        # 最终清理剩余任务
        await AsyncTaskCleaner.graceful_shutdown(timeout=2.0)

if __name__ == "__main__":
    # 显示启动信息
    print("🚀 多客户端Telegram下载器 v1.3.0")
    print("📝 日志文件: logs/main.log")
    print()
    print("💡 使用说明:")
    print('   本地下载: python main.py --mode download --source "@channel" --start 1000 --end 2000')
    print('   转发上传: python main.py --mode forward --source "@source" --targets "@target1" "@target2" --start 1000 --end 1100')
    print("   查看帮助: python main.py --help")
    print()
    print("⚙️ 配置说明:")
    print("   下载目录: 在 config/settings.py 的 DownloadConfig.download_dir 中配置")
    print("   并发数量: 由 config/settings.py 的 TelegramConfig.session_names 数量决定")
    print()
    print("📝 注意: 在 PowerShell 中，频道名称需要用引号包围，如 \"@channel\"")
    print()

    # 检查TgCrypto
    try:
        import tgcrypto  # noqa: F401
        print("✅ TgCrypto 已启用")
    except ImportError:
        print("⚠️ TgCrypto 未安装，下载速度可能较慢")

    print()

    # 运行主程序
    asyncio.run(main())
