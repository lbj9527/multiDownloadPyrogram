#!/usr/bin/env python3
"""
测试Photo API修复
"""

import asyncio
import logging
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import MultiDownloadApp
from src.utils.config import get_config
from src.utils.logger import get_logger

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_photo_download():
    """测试图片下载修复"""
    logger = get_logger()
    
    try:
        # 初始化应用
        config = get_config()
        app = MultiDownloadApp(config)
        
        logger.info("=" * 50)
        logger.info("开始测试图片下载修复")
        logger.info("=" * 50)
        
        # 设置测试参数 - 只下载少量消息进行测试
        channel_username = config.task.channel_username
        start_message_id = config.task.start_message_id
        end_message_id = min(config.task.start_message_id + 10, config.task.end_message_id)  # 只测试10条消息
        limit = 10
        
        logger.info(f"测试配置:")
        logger.info(f"  频道: {channel_username}")
        logger.info(f"  消息范围: {start_message_id} - {end_message_id}")
        logger.info(f"  客户端数量: {config.download.client_count}")
        logger.info(f"  限制数量: {limit}")
        
        # 执行下载
        result = await app.download_channel_history()
        
        # 显示结果
        logger.info("=" * 50)
        logger.info("测试结果")
        logger.info("=" * 50)
        
        logger.info(f"总消息数: {result.get('total_messages', 0)}")
        logger.info(f"媒体消息数: {result.get('media_messages', 0)}")
        logger.info(f"下载成功: {result.get('downloaded_files', 0)}")
        logger.info(f"下载失败: {result.get('failed_files', 0)}")
        logger.info(f"跳过文件: {result.get('skipped_files', 0)}")
        
        # 计算成功率
        success_rate = 0
        if result.get('media_messages', 0) > 0:
            success_rate = result.get('downloaded_files', 0) / result.get('media_messages', 0) * 100
        
        logger.info(f"成功率: {success_rate:.1f}%")
        
        if success_rate > 0:
            logger.info("✅ Photo API修复成功 - 可以正常下载图片")
            return True
        else:
            logger.error("❌ Photo API修复失败 - 仍然无法下载图片")
            return False
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        return False
    finally:
        # 清理
        try:
            await app.cleanup()
        except:
            pass

def main():
    """主函数"""
    print("MultiDownloadPyrogram - Photo API修复测试")
    print("本测试将验证图片下载API修复效果")
    print("-" * 50)
    
    try:
        # 运行测试
        success = asyncio.run(test_photo_download())
        
        if success:
            print("\n✅ 测试通过 - Photo API修复成功")
            return 0
        else:
            print("\n❌ 测试失败 - Photo API仍有问题")
            return 1
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n测试执行失败: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 