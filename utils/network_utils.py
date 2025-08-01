"""
网络工具类
从test_downloader_stream.py提取的网络相关功能
"""
import psutil
import time
from typing import Dict, Any, Optional
from pyrogram.client import Client

class NetworkUtils:
    """网络工具类"""
    
    @staticmethod
    def create_proxy_config(host: str, port: int) -> Dict[str, Any]:
        """
        创建代理配置
        从test_downloader_stream.py提取
        """
        return {
            "scheme": "socks5",
            "hostname": host,
            "port": port
        }
    
    @staticmethod
    def get_network_stats() -> Dict[str, float]:
        """
        获取网络统计信息
        从test_downloader_stream.py的带宽监控功能提取
        """
        try:
            # 获取网络IO统计
            net_io = psutil.net_io_counters()
            return {
                "bytes_sent": float(net_io.bytes_sent),
                "bytes_recv": float(net_io.bytes_recv),
                "packets_sent": float(net_io.packets_sent),
                "packets_recv": float(net_io.packets_recv)
            }
        except Exception:
            return {
                "bytes_sent": 0.0,
                "bytes_recv": 0.0,
                "packets_sent": 0.0,
                "packets_recv": 0.0
            }
    
    @staticmethod
    def calculate_bandwidth(
        current_stats: Dict[str, float], 
        previous_stats: Dict[str, float], 
        time_interval: float
    ) -> Dict[str, float]:
        """
        计算带宽使用情况
        从test_downloader_stream.py的monitor_bandwidth功能提取
        """
        if time_interval <= 0:
            return {"download_mbps": 0.0, "upload_mbps": 0.0}
        
        # 计算字节差值
        bytes_recv_diff = current_stats["bytes_recv"] - previous_stats["bytes_recv"]
        bytes_sent_diff = current_stats["bytes_sent"] - previous_stats["bytes_sent"]
        
        # 转换为Mbps
        download_mbps = (bytes_recv_diff * 8) / (time_interval * 1024 * 1024)
        upload_mbps = (bytes_sent_diff * 8) / (time_interval * 1024 * 1024)
        
        return {
            "download_mbps": max(0.0, download_mbps),
            "upload_mbps": max(0.0, upload_mbps)
        }

class BandwidthMonitor:
    """
    带宽监控器
    从test_downloader_stream.py提取的monitor_bandwidth功能
    """
    
    def __init__(self, update_interval: float = 1.0):
        self.update_interval = update_interval
        self.previous_stats = NetworkUtils.get_network_stats()
        self.previous_time = time.time()
        self.current_bandwidth = {"download_mbps": 0.0, "upload_mbps": 0.0}
        self.is_running = False
    
    def start_monitoring(self):
        """开始监控"""
        self.is_running = True
        self.previous_stats = NetworkUtils.get_network_stats()
        self.previous_time = time.time()
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
    
    def update_bandwidth(self) -> Dict[str, float]:
        """更新带宽统计"""
        if not self.is_running:
            return self.current_bandwidth
        
        current_time = time.time()
        current_stats = NetworkUtils.get_network_stats()
        time_interval = current_time - self.previous_time
        
        if time_interval >= self.update_interval:
            self.current_bandwidth = NetworkUtils.calculate_bandwidth(
                current_stats, self.previous_stats, time_interval
            )
            self.previous_stats = current_stats
            self.previous_time = current_time
        
        return self.current_bandwidth
    
    def get_current_bandwidth(self) -> Dict[str, float]:
        """获取当前带宽"""
        return self.current_bandwidth.copy()
