"""
应用程序常量定义
定义所有魔法数字和常量值
"""

from typing import Dict, Set

# 下载相关常量
DEFAULT_BATCH_SIZE = 200
MAX_BATCH_SIZE = 200  # Pyrogram官方限制
MIN_BATCH_SIZE = 1
MAX_CONCURRENT_DOWNLOADS = 10
# 注意：并发客户端数量现在完全通过环境变量 MAX_CONCURRENT_CLIENTS 控制

# 文件大小常量 (字节)
MB = 1024 * 1024
GB = 1024 * MB
MAX_FILE_SIZE = 2 * GB

# 支持的媒体类型
SUPPORTED_MEDIA_TYPES: Set[str] = {
    'photo', 'video', 'audio', 'voice', 'video_note', 
    'animation', 'document', 'sticker'
}

# 文件扩展名映射
FILE_EXTENSIONS: Dict[str, str] = {
    # 视频格式
    'video/mp4': '.mp4',
    'video/avi': '.avi',
    'video/mkv': '.mkv',
    'video/mov': '.mov',
    'video/webm': '.webm',
    'video/flv': '.flv',
    'video/wmv': '.wmv',
    
    # 图片格式
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'image/webp': '.webp',
    'image/bmp': '.bmp',
    'image/tiff': '.tiff',
    'image/svg+xml': '.svg',
    
    # 音频格式
    'audio/mpeg': '.mp3',
    'audio/wav': '.wav',
    'audio/ogg': '.ogg',
    'audio/m4a': '.m4a',
    'audio/flac': '.flac',
    'audio/aac': '.aac',
    
    # 文档格式
    'application/pdf': '.pdf',
    'application/msword': '.doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'application/vnd.ms-excel': '.xls',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
    'application/vnd.ms-powerpoint': '.ppt',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
    'text/plain': '.txt',
    'text/csv': '.csv',
    'application/json': '.json',
    'application/xml': '.xml',
    
    # 压缩格式
    'application/zip': '.zip',
    'application/x-rar': '.rar',
    'application/x-7z-compressed': '.7z',
    'application/gzip': '.gz',
    'application/x-tar': '.tar',
}

# 文件类型分类（基于FILE_EXTENSIONS自动生成）
def _generate_file_type_categories() -> Dict[str, Set[str]]:
    """根据FILE_EXTENSIONS自动生成文件类型分类"""
    categories = {
        'images': set(),
        'videos': set(),
        'audio': set(),
        'documents': set(),
        'archives': set(),
    }

    # 根据MIME类型前缀分类
    for mime_type, extension in FILE_EXTENSIONS.items():
        if mime_type.startswith('image/'):
            categories['images'].add(extension)
        elif mime_type.startswith('video/'):
            categories['videos'].add(extension)
        elif mime_type.startswith('audio/'):
            categories['audio'].add(extension)
        elif mime_type.startswith('application/') and any(x in mime_type for x in ['zip', 'rar', '7z', 'gzip', 'tar']):
            categories['archives'].add(extension)
        elif mime_type.startswith(('application/', 'text/')):
            categories['documents'].add(extension)

    return categories

FILE_TYPE_CATEGORIES: Dict[str, Set[str]] = _generate_file_type_categories()

# 媒体类型到文件扩展名的默认映射（用于没有MIME类型时的回退）
MEDIA_TYPE_DEFAULT_EXTENSIONS: Dict[str, str] = {
    'photo': '.jpg',
    'video': '.mp4',
    'audio': '.mp3',
    'voice': '.ogg',
    'video_note': '.mp4',
    'animation': '.gif',
    'document': '.bin',
    'sticker': '.webp'
}



# 错误重试设置
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1  # 秒
DEFAULT_MAX_DELAY = 60  # 秒
DEFAULT_BACKOFF_FACTOR = 2
RETRY_SETTINGS: Dict[str, int] = {
    'max_retries': DEFAULT_MAX_RETRIES,
    'base_delay': DEFAULT_BASE_DELAY,
    'max_delay': DEFAULT_MAX_DELAY,
    'backoff_factor': DEFAULT_BACKOFF_FACTOR
}

# 上传相关常量
DEFAULT_UPLOAD_ENABLED = False
DEFAULT_UPLOAD_DELAY = 1.0
DEFAULT_PRESERVE_MEDIA_GROUPS = True
DEFAULT_PRESERVE_CAPTIONS = True

# 下载延迟常量
DEFAULT_BATCH_DELAY = 0.1

# Pyrogram客户端配置常量
DEFAULT_WORKERS = 4
DEFAULT_SLEEP_THRESHOLD = 10

# 会话文件名称常量（支持最多10个客户端）
DEFAULT_SESSION_NAMES = [
    "client_8618758361347_1",
    "client_8618758361347_2",
    "client_8618758361347_3",
    "client_session_4",
    "client_session_5",
    "client_session_6",
    "client_session_7",
    "client_session_8",
    "client_session_9",
    "client_session_10"
]
DEFAULT_SESSION_DIRECTORY = "sessions"

# 日志相关常量
LOG_LEVELS: Set[str] = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_LOG_FILE = "logs/downloader.log"
DEFAULT_LOG_FILE_ENABLED = True
DEFAULT_LOG_CONSOLE_ENABLED = True
DEFAULT_VERBOSE_PYROGRAM = False

# 网络相关常量
DEFAULT_TIMEOUT = 30  # 秒
MAX_TIMEOUT = 300  # 秒
CONNECTION_POOL_SIZE = 10

# 存储模式
STORAGE_MODES: Set[str] = {'raw', 'upload', 'hybrid'}

# 任务状态
TASK_STATUS = {
    'PENDING': 'pending',
    'RUNNING': 'running',
    'COMPLETED': 'completed',
    'FAILED': 'failed',
    'CANCELLED': 'cancelled'
}

# 客户端状态
CLIENT_STATUS = {
    'IDLE': 'idle',
    'CONNECTING': 'connecting',
    'CONNECTED': 'connected',
    'DOWNLOADING': 'downloading',
    'ERROR': 'error',
    'DISCONNECTED': 'disconnected'
}
