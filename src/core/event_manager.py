#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件管理系统
"""

import asyncio
import threading
from typing import Dict, List, Callable, Any, Optional
from collections import defaultdict
from datetime import datetime
import queue

from ..models.events import BaseEvent, EventType, EventSeverity
from ..utils.logger import get_logger


class EventManager:
    """事件管理器"""
    
    def __init__(self):
        """初始化事件管理器"""
        self.logger = get_logger(__name__)
        
        # 事件监听器字典 {event_type: [callback_functions]}
        self.listeners: Dict[EventType, List[Callable]] = defaultdict(list)
        
        # 全局事件监听器（监听所有事件）
        self.global_listeners: List[Callable] = []
        
        # 事件历史记录
        self.event_history: List[BaseEvent] = []
        self.max_history_size = 1000
        
        # 事件队列（用于异步处理）
        self.event_queue = queue.Queue()
        
        # 事件处理线程
        self.processing_thread = None
        self.is_running = False
        
        # 事件统计
        self.event_stats = {
            "total_events": 0,
            "events_by_type": defaultdict(int),
            "events_by_severity": defaultdict(int),
            "last_event_time": None
        }
        
        # 启动事件处理线程
        self.start_processing()
    
    def start_processing(self):
        """启动事件处理线程"""
        if not self.is_running:
            self.is_running = True
            self.processing_thread = threading.Thread(target=self._process_events, daemon=True)
            self.processing_thread.start()
            self.logger.info("事件处理线程已启动")
    
    def stop_processing(self):
        """停止事件处理线程"""
        self.is_running = False
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5)
            self.logger.info("事件处理线程已停止")
    
    def _process_events(self):
        """事件处理线程主循环"""
        while self.is_running:
            try:
                # 从队列获取事件（阻塞等待）
                event = self.event_queue.get(timeout=1)
                
                # 处理事件
                self._handle_event(event)
                
                # 标记任务完成
                self.event_queue.task_done()
                
            except queue.Empty:
                # 队列为空，继续循环
                continue
            except Exception as e:
                self.logger.error(f"处理事件时发生错误: {e}")
    
    def _handle_event(self, event: BaseEvent):
        """处理单个事件"""
        try:
            # 添加到历史记录
            self._add_to_history(event)
            
            # 更新统计信息
            self._update_stats(event)
            
            # 调用特定类型的监听器
            if event.event_type in self.listeners:
                for callback in self.listeners[event.event_type]:
                    try:
                        callback(event)
                    except Exception as e:
                        self.logger.error(f"事件监听器执行失败: {e}")
            
            # 调用全局监听器
            for callback in self.global_listeners:
                try:
                    callback(event)
                except Exception as e:
                    self.logger.error(f"全局事件监听器执行失败: {e}")
            
            # 记录日志
            self._log_event(event)
            
        except Exception as e:
            self.logger.error(f"处理事件失败: {e}")
    
    def _add_to_history(self, event: BaseEvent):
        """添加事件到历史记录"""
        self.event_history.append(event)
        
        # 限制历史记录大小
        if len(self.event_history) > self.max_history_size:
            self.event_history = self.event_history[-self.max_history_size:]
    
    def _update_stats(self, event: BaseEvent):
        """更新事件统计信息"""
        self.event_stats["total_events"] += 1
        self.event_stats["events_by_type"][event.event_type.value] += 1
        self.event_stats["events_by_severity"][event.severity.value] += 1
        self.event_stats["last_event_time"] = event.timestamp
    
    def _log_event(self, event: BaseEvent):
        """记录事件日志"""
        log_message = f"[{event.event_type.value}] {event.message}"
        
        if event.severity == EventSeverity.DEBUG:
            self.logger.debug(log_message)
        elif event.severity == EventSeverity.INFO:
            self.logger.info(log_message)
        elif event.severity == EventSeverity.WARNING:
            self.logger.warning(log_message)
        elif event.severity == EventSeverity.ERROR:
            self.logger.error(log_message)
        elif event.severity == EventSeverity.CRITICAL:
            self.logger.critical(log_message)
    
    def emit(self, event: BaseEvent):
        """
        发送事件
        
        Args:
            event: 事件对象
        """
        try:
            # 将事件添加到队列
            self.event_queue.put(event, block=False)
        except queue.Full:
            self.logger.warning("事件队列已满，丢弃事件")
        except Exception as e:
            self.logger.error(f"发送事件失败: {e}")
    
    def emit_sync(self, event: BaseEvent):
        """
        同步发送事件（立即处理）
        
        Args:
            event: 事件对象
        """
        self._handle_event(event)
    
    def subscribe(self, event_type: EventType, callback: Callable[[BaseEvent], None]):
        """
        订阅特定类型的事件
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        self.listeners[event_type].append(callback)
        self.logger.debug(f"订阅事件类型: {event_type.value}")
    
    def subscribe_all(self, callback: Callable[[BaseEvent], None]):
        """
        订阅所有事件
        
        Args:
            callback: 回调函数
        """
        self.global_listeners.append(callback)
        self.logger.debug("订阅所有事件")
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[BaseEvent], None]):
        """
        取消订阅特定类型的事件
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        if event_type in self.listeners and callback in self.listeners[event_type]:
            self.listeners[event_type].remove(callback)
            self.logger.debug(f"取消订阅事件类型: {event_type.value}")
    
    def unsubscribe_all(self, callback: Callable[[BaseEvent], None]):
        """
        取消订阅所有事件
        
        Args:
            callback: 回调函数
        """
        if callback in self.global_listeners:
            self.global_listeners.remove(callback)
            self.logger.debug("取消订阅所有事件")
    
    def get_events_by_type(self, event_type: EventType, limit: int = 100) -> List[BaseEvent]:
        """
        获取指定类型的事件历史
        
        Args:
            event_type: 事件类型
            limit: 返回数量限制
            
        Returns:
            List[BaseEvent]: 事件列表
        """
        events = [event for event in self.event_history if event.event_type == event_type]
        return events[-limit:] if limit > 0 else events
    
    def get_events_by_severity(self, severity: EventSeverity, limit: int = 100) -> List[BaseEvent]:
        """
        获取指定严重程度的事件历史
        
        Args:
            severity: 事件严重程度
            limit: 返回数量限制
            
        Returns:
            List[BaseEvent]: 事件列表
        """
        events = [event for event in self.event_history if event.severity == severity]
        return events[-limit:] if limit > 0 else events
    
    def get_recent_events(self, limit: int = 100) -> List[BaseEvent]:
        """
        获取最近的事件
        
        Args:
            limit: 返回数量限制
            
        Returns:
            List[BaseEvent]: 事件列表
        """
        return self.event_history[-limit:] if limit > 0 else self.event_history
    
    def get_events_by_source(self, source: str, limit: int = 100) -> List[BaseEvent]:
        """
        获取指定来源的事件
        
        Args:
            source: 事件来源
            limit: 返回数量限制
            
        Returns:
            List[BaseEvent]: 事件列表
        """
        events = [event for event in self.event_history if event.source == source]
        return events[-limit:] if limit > 0 else events
    
    def get_error_events(self, limit: int = 100) -> List[BaseEvent]:
        """
        获取错误事件
        
        Args:
            limit: 返回数量限制
            
        Returns:
            List[BaseEvent]: 错误事件列表
        """
        error_severities = [EventSeverity.ERROR, EventSeverity.CRITICAL]
        events = [event for event in self.event_history if event.severity in error_severities]
        return events[-limit:] if limit > 0 else events
    
    def clear_history(self):
        """清空事件历史"""
        self.event_history.clear()
        self.logger.info("事件历史已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取事件统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "total_events": self.event_stats["total_events"],
            "events_by_type": dict(self.event_stats["events_by_type"]),
            "events_by_severity": dict(self.event_stats["events_by_severity"]),
            "last_event_time": self.event_stats["last_event_time"],
            "queue_size": self.event_queue.qsize(),
            "listeners_count": {
                event_type.value: len(callbacks) 
                for event_type, callbacks in self.listeners.items()
            },
            "global_listeners_count": len(self.global_listeners),
            "history_size": len(self.event_history)
        }
    
    def export_events(self, file_path: str, event_types: Optional[List[EventType]] = None,
                     start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> bool:
        """
        导出事件到文件
        
        Args:
            file_path: 导出文件路径
            event_types: 要导出的事件类型列表
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            bool: 导出是否成功
        """
        try:
            import json
            from pathlib import Path
            
            # 过滤事件
            events = self.event_history
            
            if event_types:
                events = [e for e in events if e.event_type in event_types]
            
            if start_time:
                events = [e for e in events if e.timestamp >= start_time]
            
            if end_time:
                events = [e for e in events if e.timestamp <= end_time]
            
            # 转换为字典格式
            events_data = [event.dict() for event in events]
            
            # 保存到文件
            export_path = Path(file_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(events_data, f, ensure_ascii=False, indent=2, default=str)
            
            self.logger.info(f"事件导出成功: {file_path}, 共 {len(events_data)} 个事件")
            return True
            
        except Exception as e:
            self.logger.error(f"事件导出失败: {e}")
            return False


# 全局事件管理器实例
event_manager = EventManager()
