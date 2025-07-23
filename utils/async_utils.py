"""
异步工具函数
"""

import asyncio
import time
from typing import Any, Callable, List, Optional, TypeVar, Coroutine, Union
from functools import wraps
import logging

T = TypeVar('T')

logger = logging.getLogger(__name__)


async def run_with_timeout(
    coro: Coroutine[Any, Any, T], 
    timeout: float,
    default: Optional[T] = None
) -> Optional[T]:
    """
    带超时的协程执行
    
    Args:
        coro: 协程对象
        timeout: 超时时间（秒）
        default: 超时时的默认返回值
        
    Returns:
        协程结果或默认值
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"操作超时 ({timeout}秒)")
        return default
    except Exception as e:
        logger.error(f"操作失败: {e}")
        return default


def retry_async(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    异步重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff_factor: 退避因子
        exceptions: 需要重试的异常类型
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(f"{func.__name__} 重试 {max_retries} 次后仍然失败: {e}")
                        raise e
                    
                    logger.warning(f"{func.__name__} 第 {attempt + 1} 次尝试失败: {e}，{current_delay}秒后重试")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff_factor
            
            # 这行代码理论上不会执行到
            raise last_exception
        
        return wrapper
    return decorator


async def batch_process(
    items: List[T],
    processor: Callable[[T], Coroutine[Any, Any, Any]],
    batch_size: int = 10,
    delay_between_batches: float = 0.1
) -> List[Any]:
    """
    批量处理项目
    
    Args:
        items: 要处理的项目列表
        processor: 处理函数（异步）
        batch_size: 批次大小
        delay_between_batches: 批次间延迟（秒）
        
    Returns:
        处理结果列表
    """
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        # 并发处理当前批次
        batch_tasks = [processor(item) for item in batch]
        batch_results = await safe_gather(*batch_tasks)
        
        results.extend(batch_results)
        
        # 批次间延迟
        if i + batch_size < len(items) and delay_between_batches > 0:
            await asyncio.sleep(delay_between_batches)
    
    return results


async def safe_gather(*coroutines, return_exceptions: bool = True) -> List[Any]:
    """
    安全的gather，处理异常
    
    Args:
        *coroutines: 协程列表
        return_exceptions: 是否返回异常对象
        
    Returns:
        结果列表
    """
    try:
        return await asyncio.gather(*coroutines, return_exceptions=return_exceptions)
    except Exception as e:
        logger.error(f"gather执行失败: {e}")
        return [e] * len(coroutines)


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, max_calls: int, time_window: float):
        """
        初始化速率限制器
        
        Args:
            max_calls: 时间窗口内最大调用次数
            time_window: 时间窗口（秒）
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """获取调用许可"""
        async with self._lock:
            now = time.time()
            
            # 清理过期的调用记录
            self.calls = [call_time for call_time in self.calls 
                         if now - call_time < self.time_window]
            
            # 检查是否超过限制
            if len(self.calls) >= self.max_calls:
                # 计算需要等待的时间
                oldest_call = min(self.calls)
                wait_time = self.time_window - (now - oldest_call)
                
                if wait_time > 0:
                    logger.debug(f"速率限制，等待 {wait_time:.2f} 秒")
                    await asyncio.sleep(wait_time)
            
            # 记录当前调用
            self.calls.append(time.time())


def rate_limit(max_calls: int, time_window: float):
    """
    速率限制装饰器
    
    Args:
        max_calls: 时间窗口内最大调用次数
        time_window: 时间窗口（秒）
        
    Returns:
        装饰器函数
    """
    limiter = RateLimiter(max_calls, time_window)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            await limiter.acquire()
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class AsyncContextManager:
    """异步上下文管理器基类"""
    
    async def __aenter__(self):
        await self.setup()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
    
    async def setup(self):
        """设置资源"""
        pass
    
    async def cleanup(self):
        """清理资源"""
        pass


class TaskManager:
    """任务管理器"""
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.running_tasks = set()
        self.completed_tasks = []
        self.failed_tasks = []
    
    async def run_task(self, coro: Coroutine, task_name: str = None) -> Any:
        """
        运行单个任务
        
        Args:
            coro: 协程对象
            task_name: 任务名称
            
        Returns:
            任务结果
        """
        async with self.semaphore:
            task = asyncio.create_task(coro)
            if task_name:
                task.set_name(task_name)
            
            self.running_tasks.add(task)
            
            try:
                result = await task
                self.completed_tasks.append(task)
                return result
            except Exception as e:
                self.failed_tasks.append((task, e))
                logger.error(f"任务 {task_name or 'unnamed'} 失败: {e}")
                raise
            finally:
                self.running_tasks.discard(task)
    
    async def run_all(self, coroutines: List[Coroutine], task_names: List[str] = None) -> List[Any]:
        """
        运行所有任务
        
        Args:
            coroutines: 协程列表
            task_names: 任务名称列表
            
        Returns:
            结果列表
        """
        if task_names is None:
            task_names = [None] * len(coroutines)
        
        tasks = [
            self.run_task(coro, name) 
            for coro, name in zip(coroutines, task_names)
        ]
        
        return await safe_gather(*tasks)
    
    async def cancel_all(self):
        """取消所有运行中的任务"""
        for task in self.running_tasks:
            task.cancel()
        
        # 等待所有任务完成取消
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks, return_exceptions=True)
    
    def get_stats(self) -> dict:
        """获取任务统计信息"""
        return {
            "running": len(self.running_tasks),
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks),
            "total": len(self.completed_tasks) + len(self.failed_tasks) + len(self.running_tasks)
        }


async def wait_for_condition(
    condition: Callable[[], bool],
    timeout: float = 30.0,
    check_interval: float = 0.1
) -> bool:
    """
    等待条件满足
    
    Args:
        condition: 条件检查函数
        timeout: 超时时间（秒）
        check_interval: 检查间隔（秒）
        
    Returns:
        条件是否在超时前满足
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if condition():
            return True
        await asyncio.sleep(check_interval)
    
    return False
