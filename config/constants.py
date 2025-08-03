"""
常量定义
"""

# 文件大小常量
MB = 1024 * 1024
GB = 1024 * MB

# 下载方法选择阈值
STREAM_DOWNLOAD_THRESHOLD_MB = 50.0
RAW_API_MAX_CHUNK_SIZE = 1024 * 1024  # 1MB

# 客户端配置
MAX_CONCURRENT_CLIENTS = 3
DEFAULT_SESSION_NAMES = [
    "client_8618758361347_1",
    "client_8618758361347_2", 
    "client_8618758361347_3"
]

# 网络配置
DEFAULT_PROXY_HOST = "127.0.0.1"
DEFAULT_PROXY_PORT = 7890

# 日志配置
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 文件类型判断
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt', '.zip', '.rar', '.7z'}

# Telegram API 限制
TELEGRAM_MAX_FILE_SIZE = 2 * GB  # 2GB
TELEGRAM_MAX_PHOTO_SIZE = 10 * MB  # 10MB

# 监控配置
BANDWIDTH_MONITOR_INTERVAL = 1  # 秒
STATS_UPDATE_INTERVAL = 5  # 秒
