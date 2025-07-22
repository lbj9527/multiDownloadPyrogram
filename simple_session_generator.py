"""
简单的三客户端会话文件生成程序
用于生成Telegram客户端会话文件
"""
import asyncio
import os
import time
from pathlib import Path
from pyrogram.client import Client
from pyrogram.errors import FloodWait


# ==================== 配置区域 ====================
# 请在这里填入您的配置信息

# Telegram API 配置（三个客户端共用）
API_ID = 25098445  # 请替换为您的API ID
API_HASH = "cc2fa5a762621d306d8de030614e4555"  # 请替换为您的API Hash
PHONE_NUMBER = "+8618758361347"  # 请替换为您的电话号码

# 三个客户端的会话名称
SESSION_NAMES = [
    "client_session_1",
    "client_session_2", 
    "client_session_3"
]

# SOCKS5 代理配置
PROXY_HOST = "127.0.0.1"  # 代理服务器地址
PROXY_PORT = 7890  # 代理端口
PROXY_USERNAME = None  # 代理用户名（如果需要）
PROXY_PASSWORD = None  # 代理密码（如果需要）

# ==================== 配置区域结束 ====================


def create_sessions_directory():
    """创建sessions目录"""
    sessions_dir = Path("sessions")
    sessions_dir.mkdir(exist_ok=True)
    print(f"✅ 会话目录已创建: {sessions_dir.absolute()}")
    return sessions_dir


def create_proxy_config():
    """创建代理配置"""
    proxy_config = {
        "scheme": "socks5",
        "hostname": PROXY_HOST,
        "port": PROXY_PORT
    }
    
    if PROXY_USERNAME and PROXY_PASSWORD:
        proxy_config["username"] = PROXY_USERNAME
        proxy_config["password"] = PROXY_PASSWORD
    
    return proxy_config


async def create_session(session_name, sessions_dir):
    """创建单个会话文件"""
    print(f"\n{'='*50}")
    print(f"正在创建会话: {session_name}")
    print(f"{'='*50}")
    
    # 检查会话文件是否已存在
    session_file = sessions_dir / f"{session_name}.session"
    if session_file.exists():
        print(f"⚠️  会话文件已存在: {session_file}")
        response = input("是否要重新创建？(y/n): ").strip().lower()
        if response not in ['y', 'yes']:
            print("跳过此会话")
            return False
        else:
            # 删除现有会话文件
            session_file.unlink()
            print("已删除现有会话文件")
    
    # 创建代理配置
    proxy_config = create_proxy_config()
    
    # 创建客户端
    client = Client(
        name=session_name,
        api_id=API_ID,
        api_hash=API_HASH,
        phone_number=PHONE_NUMBER,
        workdir=str(sessions_dir),
        proxy=proxy_config,
        app_version="SessionGenerator 1.0",
        device_model="Desktop",
        system_version="Windows 10",
        lang_code="zh"
    )
    
    try:
        print(f"📱 正在连接Telegram服务器...")

        # 启动客户端（这会自动处理连接和授权流程）
        await client.start()

        print(f"✅ 连接成功!")

        # 验证登录状态
        me = await client.get_me()
        print(f"✅ 会话创建成功!")
        print(f"   用户: {me.first_name} {me.last_name or ''}")
        print(f"   用户名: @{me.username or '无'}")
        print(f"   电话: {me.phone_number}")
        print(f"   会话文件: {session_file}")

        # 停止客户端
        await client.stop()
        return True
        
    except FloodWait as e:
        print(f"❌ 请求过于频繁，请等待 {e.value} 秒后重试")
        return False
        
    except Exception as e:
        print(f"❌ 创建会话失败: {e}")
        return False

    finally:
        # 确保客户端连接被关闭
        try:
            if client.is_connected:
                await client.stop()
        except:
            pass


async def main():
    """主函数"""
    print("🚀 Telegram三客户端会话文件生成程序")
    print("="*60)
    
    # 显示配置信息
    print("📋 当前配置:")
    print(f"   API ID: {API_ID}")
    print(f"   API Hash: {API_HASH[:8]}...{API_HASH[-8:] if len(API_HASH) > 16 else API_HASH}")
    print(f"   电话号码: {PHONE_NUMBER}")
    print(f"   代理: socks5://{PROXY_HOST}:{PROXY_PORT}")
    print(f"   会话名称: {', '.join(SESSION_NAMES)}")
    print()
    
    # 确认配置
    response = input("配置信息是否正确？(y/n): ").strip().lower()
    if response not in ['y', 'yes']:
        print("请修改程序中的配置信息后重新运行")
        return
    
    # 创建sessions目录
    sessions_dir = create_sessions_directory()
    
    # 创建会话文件（顺序模式）
    success_count = 0
    total_count = len(SESSION_NAMES)

    print(f"\n🔄 开始顺序创建 {total_count} 个会话文件")
    print("   每个会话之间将间隔1分钟以避免频率限制")
    print()

    for i, session_name in enumerate(SESSION_NAMES, 1):
        print(f"\n📍 进度: {i}/{total_count} - 正在创建: {session_name}")

        success = await create_session(session_name, sessions_dir)
        if success:
            success_count += 1
            print(f"✅ 会话 {session_name} 创建成功!")
        else:
            print(f"❌ 会话 {session_name} 创建失败!")

            # 询问是否继续
            response = input("是否继续创建剩余的会话？(y/n): ").strip().lower()
            if response not in ['y', 'yes']:
                print("用户选择停止创建")
                break
        
        # 如果不是最后一个会话，等待1分钟后继续
        if i < total_count:
            print()
            print("⏰ 等待1分钟后继续创建下一个会话...")
            print("   这样可以避免Telegram的频率限制")

            # 倒计时显示
            for remaining in range(60, 0, -1):
                print(f"\r   倒计时: {remaining:02d}秒", end="", flush=True)
                time.sleep(1)

            print("\r   ✅ 等待完成，继续创建下一个会话...    ")
            print()
    
    # 显示结果
    print(f"\n{'='*60}")
    print("📊 会话创建完成!")
    print(f"   成功: {success_count}/{total_count}")
    print(f"   会话目录: {sessions_dir.absolute()}")
    
    # 列出创建的会话文件
    session_files = list(sessions_dir.glob("*.session"))
    if session_files:
        print(f"\n📁 已创建的会话文件:")
        for session_file in session_files:
            print(f"   - {session_file.name}")
    
    print("\n✨ 程序执行完成!")


if __name__ == "__main__":
    # 检查配置
    if API_ID == 12345678 or API_HASH == "your_api_hash_here":
        print("❌ 请先在程序中配置您的API ID和API Hash!")
        print("   请编辑程序文件，修改配置区域的变量")
        input("按回车键退出...")
        exit(1)
    
    try:
        # 运行主程序
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  程序被用户中断")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        input("按回车键退出...")
