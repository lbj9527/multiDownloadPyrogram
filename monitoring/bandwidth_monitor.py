"""
带宽监控器
"""
import threading
import time
from typing import Dict, Any, Optional, Callable
from utils.network_utils import BandwidthMonitor as BaseBandwidthMonitor
from utils.logging_utils import LoggerMixin

class BandwidthMonitor(LoggerMixin):
    """
    带宽监控器 - 线程版本
    """
    
    def __init__(self, update_interval: float = 1.0, log_interval: float = 5.0):
        self.update_interval = update_interval
        self.log_interval = log_interval
        self.base_monitor = BaseBandwidthMonitor(update_interval)
        self.monitor_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.last_log_time = 0.0
        self.callback: Optional[Callable[[Dict[str, float]], None]] = None
    
    def start(self, callback: Optional[Callable[[Dict[str, float]], None]] = None):
        """
        启动带宽监控
        
        Args:
            callback: 带宽更新回调函数，接收带宽数据字典
        """
        if self.is_running:
            self.log_warning("带宽监控已在运行")
            return
        
        self.callback = callback
        self.is_running = True
        self.base_monitor.start_monitoring()
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self.log_info("带宽监控已启动")
    
    def stop(self):
        """停止带宽监控"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.base_monitor.stop_monitoring()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        
        self.log_info("带宽监控已停止")
    
    def _monitor_loop(self):
        """
        监控循环
        """
        self.last_log_time = time.time()
        
        while self.is_running:
            try:
                # 更新带宽统计
                bandwidth_data = self.base_monitor.update_bandwidth()
                
                # 调用回调函数
                if self.callback:
                    try:
                        self.callback(bandwidth_data)
                    except Exception as e:
                        self.log_error(f"带宽监控回调函数执行失败: {e}")
                
                # 定期记录日志
                current_time = time.time()
                if current_time - self.last_log_time >= self.log_interval:
                    self._log_bandwidth_info(bandwidth_data)
                    self.last_log_time = current_time
                
                # 等待下次更新
                time.sleep(self.update_interval)
                
            except Exception as e:
                self.log_error(f"带宽监控循环出错: {e}")
                time.sleep(self.update_interval)
    
    def _log_bandwidth_info(self, bandwidth_data: Dict[str, float]):
        """记录带宽信息"""
        download_mbps = bandwidth_data.get("download_mbps", 0.0)
        upload_mbps = bandwidth_data.get("upload_mbps", 0.0)
        
        if download_mbps > 0.1 or upload_mbps > 0.1:  # 只在有明显流量时记录
            self.log_info(
                f"📊 当前带宽: ↓ {download_mbps:.2f} Mbps, ↑ {upload_mbps:.2f} Mbps"
            )
    
    def get_current_bandwidth(self) -> Dict[str, float]:
        """获取当前带宽数据"""
        if not self.is_running:
            return {"download_mbps": 0.0, "upload_mbps": 0.0}
        
        return self.base_monitor.get_current_bandwidth()
    
    def get_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        return {
            "is_running": self.is_running,
            "update_interval": self.update_interval,
            "log_interval": self.log_interval,
            "current_bandwidth": self.get_current_bandwidth()
        }

def create_simple_bandwidth_monitor() -> BandwidthMonitor:
    """
    创建简单的带宽监控器
    """
    monitor = BandwidthMonitor(update_interval=1.0, log_interval=10.0)
    
    def log_callback(bandwidth_data: Dict[str, float]):
        """简单的日志回调"""
        download_mbps = bandwidth_data.get("download_mbps", 0.0)
        upload_mbps = bandwidth_data.get("upload_mbps", 0.0)
        
        # 只在有明显流量时输出（避免日志过多）
        if download_mbps > 1.0 or upload_mbps > 1.0:
            print(f"📊 网络流量: ↓ {download_mbps:.1f} Mbps ↑ {upload_mbps:.1f} Mbps")
    
    monitor.start(callback=log_callback)
    return monitor
