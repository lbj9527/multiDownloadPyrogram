"""
下载接口
为UI、API等提供统一的下载接口
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from models import DownloadTask, TaskRange, TaskStatus
from services import ClientManager
from core import TelegramDownloader
from core.message_grouper import MessageGrouper
# 延迟导入以避免循环导入
# from core.task_distribution import TaskDistributor, DistributionConfig, DistributionMode
# from core.task_distribution.base import LoadBalanceMetric
from utils import get_logger

logger = get_logger(__name__)


class DownloadInterface:
    """下载接口类"""
    
    def __init__(self, client_manager: ClientManager, downloader: TelegramDownloader):
        self.client_manager = client_manager
        self.downloader = downloader
        self.active_tasks: Dict[str, DownloadTask] = {}
        self.progress_callbacks: List[Callable] = []
    
    def add_progress_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        添加进度回调函数
        
        Args:
            callback: 进度回调函数
        """
        self.progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable):
        """
        移除进度回调函数
        
        Args:
            callback: 要移除的回调函数
        """
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)
    
    def _notify_progress(self, progress_data: Dict[str, Any]):
        """
        通知进度更新
        
        Args:
            progress_data: 进度数据
        """
        for callback in self.progress_callbacks:
            try:
                callback(progress_data)
            except Exception as e:
                logger.error(f"进度回调函数执行失败: {e}")
    
    async def download_messages(
        self,
        channel: str,
        start_message_id: int,
        end_message_id: int,
        batch_size: int = 200,
        storage_mode: str = "hybrid"
    ) -> List[Dict[str, Any]]:
        """
        下载消息范围
        
        Args:
            channel: 频道名称
            start_message_id: 开始消息ID
            end_message_id: 结束消息ID
            batch_size: 批次大小
            storage_mode: 存储模式
            
        Returns:
            下载结果列表
        """
        logger.info(f"开始下载任务: {channel} ({start_message_id}-{end_message_id})")
        
        # 获取可用客户端
        available_clients = self.client_manager.get_available_clients()
        if not available_clients:
            raise ValueError("没有可用的客户端")
        
        # 创建任务范围
        task_ranges = self.downloader.create_task_ranges(
            start_message_id, end_message_id, len(available_clients)
        )
        
        # 创建下载任务
        tasks = []
        for i, (client_name, task_range) in enumerate(zip(available_clients, task_ranges)):
            task = DownloadTask(
                client_name=client_name,
                channel=channel,
                message_range=task_range,
                batch_size=batch_size,
                storage_mode=storage_mode
            )
            
            # 启动任务
            task.start(client_name)
            
            # 存储活动任务
            self.active_tasks[task.task_id] = task
            
            # 更新客户端任务信息
            self.client_manager.update_client_task(client_name, task.task_id)
            
            tasks.append(task)
            
            logger.info(f"创建任务 {i+1}: {client_name} -> {task_range}")
        
        # 并发执行所有任务
        download_tasks = []
        for task in tasks:
            client = self.client_manager.get_client(task.client_name)
            if client:
                download_task = self._execute_task_with_progress(client, task)
                download_tasks.append(download_task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*download_tasks, return_exceptions=True)
        
        # 处理结果
        processed_results = []
        for task, result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.error(f"任务 {task.task_id} 执行失败: {result}")
                task.fail(str(result))
                processed_results.append({
                    "task_id": task.task_id,
                    "client": task.client_name,
                    "status": "failed",
                    "error": str(result),
                    "downloaded": 0,
                    "failed": task.message_range.total_messages if task.message_range else 0
                })
            else:
                task.complete(result)
                processed_results.append({
                    "task_id": task.task_id,
                    "client": task.client_name,
                    "status": "completed",
                    "downloaded": result.downloaded,
                    "failed": result.failed,
                    "duration": result.duration
                })
            
            # 清理任务信息
            self.client_manager.update_client_task(task.client_name, None)
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
        
        logger.info("所有下载任务完成")
        return processed_results
    
    async def _execute_task_with_progress(self, client, task: DownloadTask):
        """
        执行任务并报告进度
        
        Args:
            client: Pyrogram客户端
            task: 下载任务
            
        Returns:
            任务结果
        """
        try:
            # 创建进度监控任务
            progress_task = asyncio.create_task(
                self._monitor_task_progress(task)
            )
            
            # 执行下载任务
            result = await self.downloader.download_range(client, task)
            
            # 取消进度监控
            progress_task.cancel()
            
            return result
            
        except Exception as e:
            logger.error(f"执行任务失败: {e}")
            raise
    
    async def _monitor_task_progress(self, task: DownloadTask):
        """
        监控任务进度
        
        Args:
            task: 下载任务
        """
        try:
            while not task.is_completed:
                # 发送进度更新
                progress_data = {
                    "task_id": task.task_id,
                    "client": task.client_name,
                    "status": task.status.value,
                    "progress_percentage": task.progress_percentage,
                    "processed_messages": task.processed_messages,
                    "total_messages": task.total_messages,
                    "downloaded_files": task.downloaded_files,
                    "failed_downloads": task.failed_downloads,
                    "duration": task.duration,
                    "timestamp": datetime.now().isoformat()
                }
                
                self._notify_progress(progress_data)
                
                # 等待一段时间再次检查
                await asyncio.sleep(1.0)
                
        except asyncio.CancelledError:
            # 任务被取消，正常退出
            pass
        except Exception as e:
            logger.error(f"监控任务进度失败: {e}")
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """
        获取活动任务列表
        
        Returns:
            活动任务信息列表
        """
        return [task.to_dict() for task in self.active_tasks.values()]
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        task = self.active_tasks.get(task_id)
        return task.to_dict() if task else None
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否取消成功
        """
        task = self.active_tasks.get(task_id)
        if not task:
            return False
        
        try:
            # 标记任务为取消状态
            task.cancel()
            
            # 更新客户端状态
            self.client_manager.update_client_task(task.client_name, None)
            
            # 从活动任务中移除
            del self.active_tasks[task_id]
            
            logger.info(f"任务 {task_id} 已取消")
            return True
            
        except Exception as e:
            logger.error(f"取消任务 {task_id} 失败: {e}")
            return False
    
    async def cancel_all_tasks(self) -> int:
        """
        取消所有活动任务
        
        Returns:
            取消的任务数量
        """
        cancelled_count = 0
        task_ids = list(self.active_tasks.keys())
        
        for task_id in task_ids:
            if await self.cancel_task(task_id):
                cancelled_count += 1
        
        logger.info(f"已取消 {cancelled_count} 个任务")
        return cancelled_count
    
    def get_download_statistics(self) -> Dict[str, Any]:
        """
        获取下载统计信息
        
        Returns:
            统计信息字典
        """
        # 获取客户端统计
        client_stats = self.client_manager.get_client_stats()
        
        # 获取下载器统计
        download_stats = self.downloader.get_download_stats()
        
        # 获取活动任务统计
        active_tasks_count = len(self.active_tasks)
        running_tasks = sum(1 for task in self.active_tasks.values() if task.is_running)
        
        return {
            "client_stats": client_stats,
            "download_stats": download_stats,
            "active_tasks": active_tasks_count,
            "running_tasks": running_tasks,
            "task_details": self.get_active_tasks()
        }

    async def download_messages_with_media_group_awareness(
        self,
        channel: str,
        start_message_id: int,
        end_message_id: int,
        batch_size: int = 200,
        distribution_mode = None,
        task_distribution_config = None
    ) -> List[Dict[str, Any]]:
        """
        媒体组感知的消息下载

        Args:
            channel: 频道名称
            start_message_id: 开始消息ID
            end_message_id: 结束消息ID
            batch_size: 批次大小
            distribution_mode: 分配模式（可选）

        Returns:
            下载结果列表
        """
        # 延迟导入以避免循环导入
        from core.task_distribution import TaskDistributor, DistributionConfig, DistributionMode
        from core.task_distribution.base import LoadBalanceMetric

        logger.info(f"开始媒体组感知下载: {channel} ({start_message_id}-{end_message_id})")

        # 获取可用客户端
        available_clients = self.client_manager.get_available_clients()
        if not available_clients:
            raise ValueError("没有可用的客户端")

        try:
            # 1. 消息分组阶段
            logger.info("📦 开始消息分组...")
            # 使用传入的配置或默认值
            max_retries = 3
            if task_distribution_config and hasattr(task_distribution_config, 'max_retries'):
                max_retries = task_distribution_config.max_retries

            message_grouper = MessageGrouper(
                batch_size=batch_size,
                max_retries=max_retries
            )

            # 使用第一个客户端获取并分组消息
            first_client = self.client_manager.get_client(available_clients[0])
            message_collection = await message_grouper.group_messages_from_range(
                first_client, channel, start_message_id, end_message_id
            )

            # 记录分组统计
            grouping_stats = message_collection.get_statistics()

            # 2. 任务分配阶段

            # 创建分配配置
            if task_distribution_config:
                # 转换配置类型
                distribution_config = DistributionConfig(
                    mode=DistributionMode(task_distribution_config.mode.value),
                    load_balance_metric=LoadBalanceMetric(task_distribution_config.load_balance_metric.value),
                    max_imbalance_ratio=task_distribution_config.max_imbalance_ratio,
                    prefer_large_groups_first=task_distribution_config.prefer_large_groups_first,
                    enable_validation=task_distribution_config.enable_validation
                )

                # 添加消息ID验证配置（如果存在）
                if hasattr(task_distribution_config, 'enable_message_id_validation'):
                    distribution_config.enable_message_id_validation = task_distribution_config.enable_message_id_validation
                if distribution_mode:
                    distribution_config.mode = distribution_mode
            else:
                # 使用默认配置
                distribution_config = DistributionConfig(
                    mode=distribution_mode or DistributionMode.MEDIA_GROUP_AWARE,
                    load_balance_metric=LoadBalanceMetric.FILE_COUNT,
                    max_imbalance_ratio=0.3,
                    prefer_large_groups_first=True,
                    enable_validation=True
                )
                # 默认启用消息ID验证
                distribution_config.enable_message_id_validation = True

            # 执行任务分配
            task_distributor = TaskDistributor(distribution_config)
            distribution_result = await task_distributor.distribute_tasks(
                message_collection, available_clients, client=first_client, channel=channel
            )

            # 打印任务分配详情
            self._log_task_distribution_details(distribution_result)

            # 3. 执行下载任务
            logger.info("🚀 开始并发下载...")
            download_tasks = []

            for assignment in distribution_result.client_assignments:
                if assignment.total_messages > 0:
                    # 获取该客户端的所有消息
                    client_messages = assignment.get_all_messages()

                    # 创建下载任务
                    task = self._create_media_group_aware_task(
                        assignment.client_name,
                        channel,
                        client_messages,
                        batch_size
                    )
                    download_tasks.append(task)

            # 并发执行下载任务
            results = await self._execute_media_group_aware_tasks(download_tasks)

            # 4. 记录最终统计
            self._log_media_group_aware_results(results, distribution_result)

            return results

        except Exception as e:
            logger.error(f"媒体组感知下载失败: {e}")
            raise

    def _create_media_group_aware_task(
        self,
        client_name: str,
        channel: str,
        messages: List[Any],
        batch_size: int
    ) -> Dict[str, Any]:
        """创建媒体组感知的下载任务"""
        return {
            "client_name": client_name,
            "channel": channel,
            "messages": messages,
            "batch_size": batch_size,
            "task_type": "media_group_aware"
        }

    async def _execute_media_group_aware_tasks(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """执行媒体组感知的下载任务"""
        async def execute_single_task(task_info: Dict[str, Any]) -> Dict[str, Any]:
            client_name = task_info["client_name"]
            channel = task_info["channel"]
            messages = task_info["messages"]

            try:
                client = self.client_manager.get_client(client_name)

                # 使用下载器处理消息列表
                result = await self.downloader.download_message_list(
                    client, channel, messages
                )

                return {
                    "client": client_name,
                    "status": "completed",
                    "downloaded": result.get("downloaded", 0),
                    "failed": result.get("failed", 0),
                    "total_messages": len(messages)
                }

            except Exception as e:
                logger.error(f"客户端 {client_name} 下载失败: {e}")
                return {
                    "client": client_name,
                    "status": "failed",
                    "error": str(e),
                    "downloaded": 0,
                    "failed": len(messages),
                    "total_messages": len(messages)
                }

        # 并发执行所有任务
        return await asyncio.gather(*[
            execute_single_task(task) for task in tasks
        ])

    def _log_media_group_aware_results(
        self,
        results: List[Dict[str, Any]],
        distribution_result
    ):
        """记录媒体组感知下载的结果"""
        logger.info("=" * 60)
        logger.info("📊 媒体组感知下载结果")
        logger.info("=" * 60)

        total_downloaded = sum(r.get("downloaded", 0) for r in results)
        total_failed = sum(r.get("failed", 0) for r in results)
        total_messages = sum(r.get("total_messages", 0) for r in results)

        logger.info(f"总计: {total_downloaded} 成功, {total_failed} 失败")
        logger.info(f"成功率: {(total_downloaded / total_messages * 100) if total_messages > 0 else 0:.1f}%")

        # 显示分配统计
        balance_stats = distribution_result.get_load_balance_stats()
        logger.info(f"负载均衡比例: {balance_stats.get('file_balance_ratio', 0):.3f}")

        logger.info("=" * 60)

    def _log_task_distribution_details(self, distribution_result):
        """记录任务分配详情"""
        logger.info("\n" + "🎯" * 20 + " 任务分配详情 " + "🎯" * 20)
        logger.info(f"分配策略: {distribution_result.distribution_strategy}")
        logger.info(f"客户端数量: {len(distribution_result.client_assignments)}")
        logger.info(f"总消息数: {distribution_result.total_messages}")
        logger.info(f"总文件数: {distribution_result.total_files}")

        logger.info("\n📊 各客户端分配概览:")
        for assignment in distribution_result.client_assignments:
            # 获取所有消息ID
            all_message_ids = []
            for group in assignment.message_groups:
                all_message_ids.extend(group.message_ids)

            if all_message_ids:
                all_message_ids.sort()
                # 完整显示所有消息ID，而不是范围
                id_list = str(all_message_ids)
            else:
                id_list = "无消息"

            # 统计媒体组和单消息
            media_groups = [g for g in assignment.message_groups if g.is_media_group]
            single_messages = [g for g in assignment.message_groups if not g.is_media_group]

            logger.info(f"  {assignment.client_name}:")
            logger.info(f"    📝 消息数量: {assignment.total_messages}")
            logger.info(f"    📁 文件数量: {assignment.total_files}")
            logger.info(f"    🔢 完整消息ID列表: {id_list}")
            logger.info(f"    📦 媒体组: {len(media_groups)} 个")
            logger.info(f"    📄 单条消息: {len(single_messages)} 个")

            # 显示估算大小
            size_mb = assignment.estimated_size / (1024 * 1024)
            logger.info(f"    💾 估算大小: {size_mb:.1f} MB")

        # 显示负载均衡统计
        balance_stats = distribution_result.get_load_balance_stats()
        if balance_stats:
            logger.info(f"\n⚖️ 负载均衡统计:")
            logger.info(f"  文件分布: {balance_stats.get('file_distribution', [])}")
            logger.info(f"  均衡比例: {balance_stats.get('file_balance_ratio', 0):.3f}")
            logger.info(f"  平均文件数/客户端: {balance_stats.get('average_files_per_client', 0):.1f}")

        logger.info("🎯" * 60)
