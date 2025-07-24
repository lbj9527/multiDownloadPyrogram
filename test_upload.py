#!/usr/bin/env python3
"""
上传功能测试脚本
用于测试新增的上传功能
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from config import app_settings
from utils import setup_logging, get_logger
from services import ClientManager, UploadService
from core import TelegramDownloader, FileProcessor

# 设置日志
setup_logging(verbose=True)
logger = get_logger(__name__)


async def test_upload_functionality():
    """测试上传功能"""
    logger.info("🧪 开始测试上传功能")
    
    # 检查配置
    if not app_settings.upload.enabled:
        logger.error("❌ 上传功能未启用，请设置 UPLOAD_ENABLED=true")
        return False
    
    if not app_settings.upload.target_channel:
        logger.error("❌ 未配置上传目标频道，请设置 UPLOAD_TARGET_CHANNEL")
        return False
    
    logger.info(f"📤 目标频道: {app_settings.upload.target_channel}")
    logger.info(f"🔧 存储模式: {app_settings.storage.storage_mode}")
    
    # 初始化组件
    client_manager = ClientManager()
    upload_service = UploadService()
    file_processor = FileProcessor()
    downloader = TelegramDownloader(file_processor, upload_service)
    
    try:
        # 初始化客户端
        logger.info("🔌 初始化客户端...")
        client_infos = await client_manager.initialize_clients()
        if not client_infos:
            logger.error("❌ 没有可用的客户端")
            return False
        
        # 连接客户端
        logger.info("🔗 连接客户端...")
        connected_clients = await client_manager.connect_all_clients()
        if not connected_clients:
            logger.error("❌ 客户端连接失败")
            return False
        
        logger.info(f"✅ 成功连接 {len(connected_clients)} 个客户端")
        
        # 获取第一个客户端进行测试
        client_name = connected_clients[0]
        client = client_manager.get_client(client_name)
        
        # 测试目标频道访问权限
        logger.info("🔍 测试目标频道访问权限...")
        try:
            target_chat = await client.get_chat(app_settings.upload.target_channel)
            logger.info(f"✅ 目标频道: {target_chat.title} (@{target_chat.username})")
        except Exception as e:
            logger.error(f"❌ 无法访问目标频道: {e}")
            return False
        
        # 发送测试消息
        logger.info("📝 发送测试消息...")
        try:
            test_message = f"🧪 上传功能测试消息\n时间: {asyncio.get_event_loop().time()}"
            await client.send_message(
                chat_id=app_settings.upload.target_channel,
                text=test_message
            )
            logger.info("✅ 测试消息发送成功")
        except Exception as e:
            logger.error(f"❌ 测试消息发送失败: {e}")
            return False
        
        # 显示统计信息
        stats = upload_service.get_upload_stats()
        logger.info("📊 上传统计:")
        logger.info(f"  总上传: {stats['total_uploaded']}")
        logger.info(f"  失败: {stats['total_failed']}")
        logger.info(f"  媒体组: {stats['media_groups_uploaded']}")
        
        logger.info("✅ 上传功能测试完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        return False
    
    finally:
        # 清理资源
        try:
            await client_manager.disconnect_all_clients()
            logger.info("🧹 资源清理完成")
        except Exception as e:
            logger.error(f"❌ 资源清理失败: {e}")


async def test_configuration():
    """测试配置"""
    logger.info("⚙️ 测试配置...")
    
    # 验证配置
    errors = app_settings.validate()
    if errors:
        logger.error("❌ 配置验证失败:")
        for error in errors:
            logger.error(f"  - {error}")
        return False
    
    logger.info("✅ 配置验证通过")
    
    # 显示关键配置
    logger.info("📋 当前配置:")
    logger.info(f"  存储模式: {app_settings.storage.storage_mode}")
    logger.info(f"  上传启用: {app_settings.upload.enabled}")
    logger.info(f"  目标频道: {app_settings.upload.target_channel}")
    logger.info(f"  保持媒体组: {app_settings.upload.preserve_media_groups}")
    logger.info(f"  保持说明: {app_settings.upload.preserve_captions}")
    logger.info(f"  上传延迟: {app_settings.upload.upload_delay}s")
    logger.info(f"  最大重试: {app_settings.upload.max_retries}")
    
    return True


async def main():
    """主函数"""
    logger.info("🚀 启动上传功能测试")
    
    try:
        # 测试配置
        if not await test_configuration():
            return False
        
        # 测试上传功能
        if not await test_upload_functionality():
            return False
        
        logger.info("🎉 所有测试通过！")
        return True
        
    except KeyboardInterrupt:
        logger.info("⏹️ 测试被用户中断")
        return False
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return False


if __name__ == "__main__":
    # 设置测试环境变量（如果需要）
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        print("设置测试环境变量:")
        print("export UPLOAD_ENABLED=true")
        print("export UPLOAD_TARGET_CHANNEL=@your_test_channel")
        print("export STORAGE_MODE=upload")
        print("\n然后运行: python test_upload.py")
        sys.exit(0)
    
    # 运行测试
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
