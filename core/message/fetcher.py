"""
消息获取器
"""
import asyncio
from typing import List, Any, Optional
from pyrogram.client import Client
from pyrogram.errors import FloodWait
from utils.logging_utils import LoggerMixin

class MessageFetcher(LoggerMixin):
    """消息获取器"""
    
    def __init__(self, clients: List[Client]):
        self.clients = clients
    
    async def parallel_fetch_messages(
        self,
        channel: str,
        start_id: int,
        end_id: int
    ) -> List[Any]:
        """
        并发获取消息 - 多客户端分工获取不同范围的消息
        """
        self.log_info(f"🚀 使用 {len(self.clients)} 个客户端并发获取消息...")

        # 将消息范围按客户端数量分配
        all_message_ids = list(range(start_id, end_id + 1))
        client_count = len(self.clients)

        # 计算每个客户端的消息范围
        messages_per_client = len(all_message_ids) // client_count
        remainder = len(all_message_ids) % client_count

        ranges = []
        start_idx = 0
        for i in range(client_count):
            extra = 1 if i < remainder else 0
            end_idx = start_idx + messages_per_client + extra
            ranges.append(all_message_ids[start_idx:end_idx])
            self.log_info(f"客户端{i+1} 分配消息范围: {all_message_ids[start_idx]} - {all_message_ids[end_idx-1]} ({len(ranges[i])} 条)")
            start_idx = end_idx

        # 并发获取消息 - 添加错开启动机制
        tasks = []
        for i, client in enumerate(self.clients):
            if i < len(ranges) and ranges[i]:  # 确保有消息ID要获取
                task = self.fetch_message_range(client, channel, ranges[i], i)
                tasks.append(task)

        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果
        all_messages = []
        successful_clients = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.log_error(f"❌ 客户端{i+1} 获取消息失败: {result}")
            else:
                all_messages.extend(result)
                successful_clients += 1
                self.log_info(f"✅ 客户端{i+1} 成功获取 {len(result)} 条消息")

        # 按消息ID排序确保顺序正确，同时过滤掉无效消息
        all_messages = sorted([msg for msg in all_messages if msg and not getattr(msg, 'empty', True)], key=lambda x: x.id)

        self.log_info(f"🎉 并发获取完成！{successful_clients}/{len(self.clients)} 个客户端成功，共获取 {len(all_messages)} 条有效消息")
        return all_messages
    
    async def fetch_message_range(
        self,
        client: Client,
        channel: str,
        message_ids: List[int],
        client_index: int
    ) -> List[Any]:
        """
        获取指定范围的消息 - 使用批量获取逻辑
        """
        # 错开启动时间避免同时发起请求
        if client_index > 0:
            delay = client_index * 0.2
            self.log_info(f"客户端{client_index+1} 将在 {delay} 秒后开始获取...")
            await asyncio.sleep(delay)

        messages = []
        batch_size = 100  # 每批获取100条消息

        self.log_info(f"客户端{client_index+1} 开始获取 {len(message_ids)} 条消息...")

        for i in range(0, len(message_ids), batch_size):
            batch_ids = message_ids[i:i + batch_size]
            try:
                # 批量获取消息
                batch_messages = await client.get_messages(channel, batch_ids)
                # 过滤掉无效消息（使用empty属性判断）
                valid_messages = [msg for msg in batch_messages if msg is not None and not getattr(msg, 'empty', True)]
                invalid_count = len(batch_ids) - len(valid_messages)

                messages.extend(valid_messages)

                if invalid_count > 0:
                    self.log_warning(f"客户端{client_index+1} 批次中发现 {invalid_count} 条无效消息")

                self.log_info(f"客户端{client_index+1} 已获取 {len(messages)} 条有效消息（批次: {len(valid_messages)}/{len(batch_ids)}）")

                # 短暂延迟避免过于频繁的请求
                await asyncio.sleep(0.1)

            except FloodWait as e:
                self.log_warning(f"客户端{client_index+1} 遇到限流，等待 {e.value} 秒")
                await asyncio.sleep(float(e.value))
                # 重试当前批次
                try:
                    batch_messages = await client.get_messages(channel, batch_ids)
                    # 过滤掉无效消息（使用empty属性判断）
                    valid_messages = [msg for msg in batch_messages if msg is not None and not getattr(msg, 'empty', True)]
                    invalid_count = len(batch_ids) - len(valid_messages)

                    messages.extend(valid_messages)

                    if invalid_count > 0:
                        self.log_warning(f"客户端{client_index+1} 重试批次中发现 {invalid_count} 条无效消息")

                    self.log_info(f"客户端{client_index+1} 重试成功，已获取 {len(messages)} 条有效消息")
                except Exception as retry_e:
                    self.log_error(f"客户端{client_index+1} 重试失败: {retry_e}")

            except Exception as e:
                self.log_error(f"客户端{client_index+1} 获取消息批次 {batch_ids[0]}-{batch_ids[-1]} 失败: {e}")
                continue

        self.log_info(f"✅ 客户端{client_index+1} 完成获取，共 {len(messages)} 条有效消息")
        return messages

