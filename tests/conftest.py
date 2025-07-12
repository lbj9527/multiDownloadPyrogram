"""
pytest配置文件

提供测试环境的全局配置和fixtures
"""

import pytest
import asyncio
import logging
from typing import AsyncGenerator, Generator
from pathlib import Path

# 禁用pyrogram和telegram相关的日志
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("telegram").setLevel(logging.ERROR)

# 测试环境配置
TEST_API_ID = 12345
TEST_API_HASH = "test_hash"
TEST_PROXY = {
    "scheme": "socks5",
    "hostname": "127.0.0.1",
    "port": 7890
}


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环以支持异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config() -> dict:
    """测试配置"""
    return {
        "api_id": TEST_API_ID,
        "api_hash": TEST_API_HASH,
        "proxy": TEST_PROXY,
        "max_clients": 3,
        "max_concurrent_downloads": 5,
        "chunk_size": 1024 * 1024,  # 1MB
        "download_path": "downloads/",
        "log_level": "INFO"
    }


@pytest.fixture
def temp_download_dir(tmp_path: Path) -> Path:
    """临时下载目录"""
    download_dir = tmp_path / "downloads"
    download_dir.mkdir(exist_ok=True)
    return download_dir


@pytest.fixture
def temp_session_dir(tmp_path: Path) -> Path:
    """临时会话目录"""
    session_dir = tmp_path / "sessions"
    session_dir.mkdir(exist_ok=True)
    return session_dir 