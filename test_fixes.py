#!/usr/bin/env python3
"""
测试修复后的并发下载功能
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

async def test_concurrent_download():
    """测试并发下载功能"""
    logger = get_logger()
    
    try:
        # 初始化应用
        config = get_config()
        app = MultiDownloadApp(config)
        
        logger.info("=" * 50)
        logger.info("开始测试并发下载功能")
        logger.info("=" * 50)
        
        # 设置测试参数
        channel_username = config.task.channel_username
        start_message_id = config.task.start_message_id
        end_message_id = config.task.end_message_id
        limit = min(config.task.limit, 20)  # 限制测试数量
        
        logger.info(f"测试配置:")
        logger.info(f"  频道: {channel_username}")
        logger.info(f"  消息范围: {start_message_id} - {end_message_id}")
        logger.info(f"  客户端数量: {config.download.client_count}")
        logger.info(f"  限制数量: {limit}")
        
        # 执行下载
        result = await app.download_channel_history(
            channel_username=channel_username,
            start_message_id=start_message_id,
            end_message_id=end_message_id,
            limit=limit
        )
        
        # 显示结果
        logger.info("=" * 50)
        logger.info("下载测试完成")
        logger.info("=" * 50)
        
        logger.info(f"总消息数: {result.get('total_messages', 0)}")
        logger.info(f"媒体消息数: {result.get('media_messages', 0)}")
        logger.info(f"下载成功: {result.get('downloaded_count', 0)}")
        logger.info(f"下载失败: {result.get('failed_count', 0)}")
        logger.info(f"跳过文件: {result.get('skipped_count', 0)}")
        logger.info(f"耗时: {result.get('duration', 0):.1f}秒")
        
        # 客户端结果详情
        if 'client_results' in result:
            logger.info("\n客户端下载详情:")
            for client_result in result['client_results']:
                client_idx = client_result.get('client_index', 'unknown')
                downloaded = client_result.get('downloaded_count', 0)
                failed = client_result.get('failed_count', 0)
                skipped = client_result.get('skipped_count', 0)
                
                logger.info(f"  客户端 {client_idx}: 成功 {downloaded}, 失败 {failed}, 跳过 {skipped}")
        
        return result
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        raise
    finally:
        # 清理
        try:
            await app.cleanup()
        except:
            pass

def main():
    """主函数"""
    print("MultiDownloadPyrogram - 并发下载测试")
    print("本测试将验证修复后的并发下载功能")
    print("-" * 50)
    
    try:
        # 运行测试
        result = asyncio.run(test_concurrent_download())
        
        print("\n" + "=" * 50)
        print("测试结果总结:")
        
        success_rate = 0
        if result.get('media_messages', 0) > 0:
            success_rate = result.get('downloaded_count', 0) / result.get('media_messages', 0) * 100
        
        print(f"成功率: {success_rate:.1f}%")
        
        if success_rate > 80:
            print("✅ 测试通过 - 下载功能正常")
            return 0
        elif success_rate > 50:
            print("⚠️ 测试部分通过 - 下载功能基本正常，但有改进空间")
            return 0
        else:
            print("❌ 测试失败 - 下载功能存在问题")
            return 1
            
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n测试执行失败: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 