"""
统计收集器
"""
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from utils.logging_utils import LoggerMixin

@dataclass
class DownloadStats:
    """
    下载统计数据
    """
    total_messages: int = 0
    downloaded: int = 0
    failed: int = 0
    start_time: float = field(default_factory=time.time)
    
    def get_progress_percentage(self) -> float:
        """获取进度百分比"""
        if self.total_messages == 0:
            return 0.0
        return (self.downloaded / self.total_messages) * 100
    
    def get_elapsed_time(self) -> float:
        """获取已用时间（秒）"""
        return time.time() - self.start_time
    
    def get_remaining_time(self) -> float:
        """估算剩余时间（秒）"""
        if self.downloaded == 0:
            return 0.0
        
        elapsed = self.get_elapsed_time()
        rate = self.downloaded / elapsed
        remaining_items = self.total_messages - self.downloaded
        
        return remaining_items / rate if rate > 0 else 0.0
    
    def get_download_rate(self) -> float:
        """获取下载速率（文件/秒）"""
        elapsed = self.get_elapsed_time()
        return self.downloaded / elapsed if elapsed > 0 else 0.0
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        total_processed = self.downloaded + self.failed
        return self.downloaded / total_processed if total_processed > 0 else 0.0

class StatsCollector(LoggerMixin):
    """
    统计收集器
    """
    
    def __init__(self, total_messages: int = 0):
        self.stats = DownloadStats(total_messages=total_messages)
        self.client_stats: Dict[str, Dict[str, Any]] = {}
        self.detailed_results: List[Dict[str, Any]] = []
        self._last_report_time = time.time()
        self.report_interval = 10.0  # 10秒报告一次
    
    def set_total_messages(self, total: int):
        """设置总消息数"""
        self.stats.total_messages = total
        self.log_info(f"设置总消息数: {total}")
    
    def update_download_progress(self, success: bool, message_id: Optional[int] = None,
                               client_name: Optional[str] = None, file_size_mb: float = 0.0):
        """
        更新下载进度
        """
        if success:
            self.stats.downloaded += 1
        else:
            self.stats.failed += 1
        
        # 更新客户端统计
        if client_name:
            if client_name not in self.client_stats:
                self.client_stats[client_name] = {
                    "downloaded": 0,
                    "failed": 0,
                    "total_size_mb": 0.0
                }
            
            if success:
                self.client_stats[client_name]["downloaded"] += 1
                self.client_stats[client_name]["total_size_mb"] += file_size_mb
            else:
                self.client_stats[client_name]["failed"] += 1
        
        # 记录详细结果
        self.detailed_results.append({
            "message_id": message_id,
            "success": success,
            "client_name": client_name,
            "file_size_mb": file_size_mb,
            "timestamp": time.time()
        })
        
        # 定期报告进度
        self._maybe_report_progress()
    
    def _maybe_report_progress(self):
        """可能报告进度（基于时间间隔）"""
        current_time = time.time()
        if current_time - self._last_report_time >= self.report_interval:
            self.report_progress()
            self._last_report_time = current_time
    
    def report_progress(self):
        """
        报告当前进度
        """
        progress = self.stats.get_progress_percentage()
        elapsed = self.stats.get_elapsed_time()
        rate = self.stats.get_download_rate()
        remaining = self.stats.get_remaining_time()
        
        self.log_info(
            f"📊 进度: {self.stats.downloaded}/{self.stats.total_messages} "
            f"({progress:.1f}%) | "
            f"速率: {rate:.2f} 文件/秒 | "
            f"已用时间: {elapsed/60:.1f} 分钟 | "
            f"预计剩余: {remaining/60:.1f} 分钟"
        )
        
        if self.stats.failed > 0:
            success_rate = self.stats.get_success_rate()
            self.log_info(f"成功率: {success_rate:.1%} ({self.stats.failed} 个失败)")
    
    def get_final_report(self) -> Dict[str, Any]:
        """
        获取最终报告
        """
        total_time = self.stats.get_elapsed_time()
        
        report = {
            "summary": {
                "total_messages": self.stats.total_messages,
                "downloaded": self.stats.downloaded,
                "failed": self.stats.failed,
                "success_rate": self.stats.get_success_rate(),
                "total_time_minutes": total_time / 60,
                "average_rate": self.stats.get_download_rate()
            },
            "client_stats": self.client_stats.copy(),
            "performance": {
                "total_size_mb": sum(
                    client["total_size_mb"] for client in self.client_stats.values()
                ),
                "average_file_size_mb": 0.0,
                "throughput_mbps": 0.0
            }
        }
        
        # 计算平均文件大小
        if self.stats.downloaded > 0:
            total_size = report["performance"]["total_size_mb"]
            report["performance"]["average_file_size_mb"] = total_size / self.stats.downloaded
            
            # 计算吞吐量（MB/s转换为Mbps）
            if total_time > 0:
                mb_per_second = total_size / total_time
                report["performance"]["throughput_mbps"] = mb_per_second * 8  # MB/s to Mbps
        
        return report
    
    def print_final_report(self):
        """
        打印最终报告
        """
        report = self.get_final_report()
        summary = report["summary"]
        performance = report["performance"]
        
        self.log_info("=" * 60)
        self.log_info("📊 下载完成统计报告")
        self.log_info("=" * 60)
        
        self.log_info(f"总消息数: {summary['total_messages']}")
        self.log_info(f"成功下载: {summary['downloaded']}")
        self.log_info(f"下载失败: {summary['failed']}")
        self.log_info(f"成功率: {summary['success_rate']:.1%}")
        self.log_info(f"总用时: {summary['total_time_minutes']:.1f} 分钟")
        self.log_info(f"平均速率: {summary['average_rate']:.2f} 文件/秒")
        
        if performance["total_size_mb"] > 0:
            self.log_info(f"总下载量: {performance['total_size_mb']:.1f} MB")
            self.log_info(f"平均文件大小: {performance['average_file_size_mb']:.1f} MB")
            self.log_info(f"网络吞吐量: {performance['throughput_mbps']:.1f} Mbps")
        
        # 客户端统计
        if self.client_stats:
            self.log_info("\n📱 客户端统计:")
            for client_name, stats in self.client_stats.items():
                self.log_info(
                    f"  {client_name}: {stats['downloaded']} 成功, "
                    f"{stats['failed']} 失败, "
                    f"{stats['total_size_mb']:.1f} MB"
                )
        
        self.log_info("=" * 60)
    
    def reset_stats(self):
        """重置统计数据"""
        self.stats = DownloadStats(total_messages=self.stats.total_messages)
        self.client_stats.clear()
        self.detailed_results.clear()
        self._last_report_time = time.time()
        self.log_info("统计数据已重置")
