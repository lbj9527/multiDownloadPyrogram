"""
测试修复后的下载功能
只下载少量消息进行验证
"""
import asyncio
import shutil
from pathlib import Path
from multi_client_downloader import MultiClientDownloader
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestDownloader(MultiClientDownloader):
    """测试下载器，只下载少量消息"""
    
    def __init__(self):
        super().__init__()
        # 重新定义测试范围
        self.test_start = 71986
        self.test_end = 71990  # 只下载5条消息进行测试
        self.test_total = self.test_end - self.test_start + 1
        
        # 更新统计信息
        self.stats["total_messages"] = self.test_total
        
        logger.info(f"测试模式：只下载消息 {self.test_start} - {self.test_end} (共 {self.test_total} 条)")
    
    def calculate_message_ranges(self):
        """重新计算测试范围"""
        # 简单分配：每个客户端下载1-2条消息
        ranges = [
            (71986, 71987),  # 客户端1: 2条
            (71988, 71989),  # 客户端2: 2条  
            (71990, 71990),  # 客户端3: 1条
        ]
        
        for i, (start, end) in enumerate(ranges):
            count = end - start + 1
            logger.info(f"客户端 {i+1} 测试范围: {start} - {end} ({count} 条消息)")
        
        return ranges
    
    async def run_test(self):
        """运行测试下载"""
        logger.info("🧪 开始测试修复后的下载功能")
        
        # 清理旧的下载目录
        if self.download_dir.exists():
            logger.info("清理旧的下载文件...")
            shutil.rmtree(self.download_dir)
        
        # 运行下载测试
        await self.run_download()
        
        # 检查下载结果
        await self.check_results()
    
    async def check_results(self):
        """检查下载结果"""
        logger.info("\n" + "="*60)
        logger.info("🔍 检查下载结果")
        logger.info("="*60)
        
        for i in range(1, 4):
            client_dir = self.download_dir / f"client_{i}"
            if client_dir.exists():
                files = list(client_dir.glob("*"))
                logger.info(f"客户端{i} 下载文件:")
                
                for file_path in files:
                    if file_path.is_file():
                        size_mb = file_path.stat().st_size / (1024 * 1024)
                        logger.info(f"  - {file_path.name} ({size_mb:.2f} MB)")
                        
                        # 检查文件扩展名
                        if file_path.suffix:
                            logger.info(f"    ✅ 扩展名正确: {file_path.suffix}")
                        else:
                            logger.warning(f"    ⚠️  缺少扩展名")
            else:
                logger.warning(f"客户端{i} 目录不存在")
        
        logger.info("="*60)


async def main():
    """主函数"""
    try:
        test_downloader = TestDownloader()
        await test_downloader.run_test()
    except KeyboardInterrupt:
        logger.info("用户中断测试")
    except Exception as e:
        logger.error(f"测试失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
