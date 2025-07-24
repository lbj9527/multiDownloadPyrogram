#!/usr/bin/env python3
"""
简单的上传功能测试脚本
"""

import asyncio
import os
import sys
from pathlib import Path

# 设置环境变量
os.environ['STORAGE_MODE'] = 'upload'
os.environ['UPLOAD_ENABLED'] = 'true'
os.environ['UPLOAD_TARGET_CHANNEL'] = '@wghrwf'
os.environ['PRESERVE_MEDIA_GROUPS'] = 'true'
os.environ['PRESERVE_CAPTIONS'] = 'true'
os.environ['UPLOAD_DELAY'] = '1.5'

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from config import app_settings
from utils import setup_logging, get_logger

# 设置日志
setup_logging(level="INFO", verbose_pyrogram=True)
logger = get_logger(__name__)


async def test_config():
    """测试配置"""
    logger.info("🔧 测试配置...")
    
    # 显示配置
    logger.info(f"存储模式: {app_settings.storage.storage_mode}")
    logger.info(f"上传启用: {app_settings.upload.enabled}")
    logger.info(f"目标频道: {app_settings.upload.target_channel}")
    logger.info(f"保持媒体组: {app_settings.upload.preserve_media_groups}")
    logger.info(f"保持说明: {app_settings.upload.preserve_captions}")
    logger.info(f"上传延迟: {app_settings.upload.upload_delay}")
    
    # 验证配置
    errors = app_settings.validate()
    if errors:
        logger.error("❌ 配置验证失败:")
        for error in errors:
            logger.error(f"  - {error}")
        return False
    
    logger.info("✅ 配置验证通过")
    return True


async def test_upload_service():
    """测试上传服务"""
    logger.info("📤 测试上传服务...")
    
    try:
        from services import UploadService
        upload_service = UploadService()
        
        logger.info("✅ 上传服务初始化成功")
        
        # 显示统计
        stats = upload_service.get_upload_stats()
        logger.info(f"初始统计: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 上传服务测试失败: {e}")
        return False


async def test_client_connection():
    """测试客户端连接"""
    logger.info("🔌 测试客户端连接...")
    
    try:
        from services import ClientManager
        client_manager = ClientManager()
        
        # 初始化客户端
        client_infos = await client_manager.initialize_clients()
        if not client_infos:
            logger.error("❌ 没有可用的客户端")
            return False
        
        logger.info(f"✅ 找到 {len(client_infos)} 个客户端")
        
        # 连接第一个客户端进行测试
        connected_clients = await client_manager.connect_all_clients()
        if not connected_clients:
            logger.error("❌ 客户端连接失败")
            return False
        
        logger.info(f"✅ 成功连接 {len(connected_clients)} 个客户端")
        
        # 测试目标频道访问
        client_name = connected_clients[0]
        client = client_manager.get_client(client_name)
        
        try:
            target_chat = await client.get_chat(app_settings.upload.target_channel)
            logger.info(f"✅ 目标频道: {target_chat.title}")
            if hasattr(target_chat, 'username') and target_chat.username:
                logger.info(f"   用户名: @{target_chat.username}")
        except Exception as e:
            logger.error(f"❌ 无法访问目标频道: {e}")
            return False
        finally:
            # 断开连接
            await client_manager.disconnect_all_clients()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 客户端连接测试失败: {e}")
        return False


async def main():
    """主函数"""
    logger.info("🚀 开始上传功能测试")
    
    try:
        # 测试配置
        if not await test_config():
            return False
        
        # 测试上传服务
        if not await test_upload_service():
            return False
        
        # 测试客户端连接
        if not await test_client_connection():
            return False
        
        logger.info("🎉 所有测试通过！上传功能配置正确")
        logger.info("💡 现在可以运行 'python main.py' 来执行实际的上传任务")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
