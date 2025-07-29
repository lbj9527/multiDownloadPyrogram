"""
智能会话文件生成程序
用于生成Telegram客户端会话文件，支持从配置文件读取客户端数量和会话名称
"""
import asyncio
import os
import sys
import time
from pathlib import Path
from pyrogram.client import Client
from pyrogram.errors import FloodWait

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入项目配置
from config import app_settings
from config.constants import DEFAULT_SESSION_NAMES, DEFAULT_SESSION_DIRECTORY


# ==================== 配置区域 ====================
# 请通过环境变量或直接修改这里的配置信息

# Telegram API 配置（多个客户端共用）
API_ID = int(os.getenv("API_ID", "12345678"))  # 请替换为您的API ID
API_HASH = os.getenv("API_HASH", "your_api_hash_here")  # 请替换为您的API Hash
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "+1234567890")  # 请替换为您的电话号码

# SOCKS5 代理配置
PROXY_HOST = os.getenv("PROXY_HOST", "127.0.0.1")  # 代理服务器地址
PROXY_PORT = int(os.getenv("PROXY_PORT", "7890"))  # 代理端口
PROXY_USERNAME = os.getenv("PROXY_USERNAME", None)  # 代理用户名（如果需要）
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD", None)  # 代理密码（如果需要）

# ==================== 配置区域结束 ====================


def load_session_config():
    """从配置文件加载会话配置"""
    try:
        # 获取客户端数量
        max_concurrent_clients = app_settings.download.max_concurrent_clients

        # 动态生成会话文件名称列表，支持任意数量
        session_names = generate_session_names(max_concurrent_clients)

        # 获取会话目录
        session_directory = app_settings.download.session_directory

        return {
            "max_concurrent_clients": max_concurrent_clients,
            "session_names": session_names,
            "session_directory": session_directory
        }
    except Exception as e:
        print(f"⚠️  加载配置失败，使用默认配置: {e}")
        # 使用默认配置（3个客户端）
        default_clients = 3
        return {
            "max_concurrent_clients": default_clients,
            "session_names": generate_session_names(default_clients),
            "session_directory": DEFAULT_SESSION_DIRECTORY
        }


def generate_session_names(count):
    """
    动态生成会话文件名称

    Args:
        count: 需要生成的会话文件数量

    Returns:
        会话文件名称列表
    """
    if count <= 0:
        return []

    # 验证数量范围
    if count > 10:
        print(f"⚠️  警告：客户端数量({count})超过推荐最大值(10)，将限制为10个")
        count = 10

    # 动态生成会话名称：client_session_1, client_session_2, ...
    session_names = [f"client_session_{i}" for i in range(1, count + 1)]

    print(f"📝 动态生成 {count} 个会话名称: {', '.join(session_names)}")
    return session_names


def analyze_existing_sessions(session_directory, required_session_names):
    """
    分析已存在的会话文件，确定需要创建的会话

    Args:
        session_directory: 会话文件目录
        required_session_names: 需要的会话名称列表

    Returns:
        dict: 包含分析结果的字典
    """
    sessions_dir = Path(session_directory)

    # 检查目录是否存在
    if not sessions_dir.exists():
        return {
            "existing_sessions": [],
            "missing_sessions": required_session_names,
            "extra_sessions": [],
            "needs_creation": required_session_names
        }

    # 获取已存在的会话文件
    existing_files = list(sessions_dir.glob("*.session"))
    existing_sessions = [f.stem for f in existing_files]  # 去掉.session扩展名

    # 分析需要创建的会话
    missing_sessions = [name for name in required_session_names if name not in existing_sessions]

    # 分析多余的会话文件
    extra_sessions = [name for name in existing_sessions if name not in required_session_names]

    return {
        "existing_sessions": existing_sessions,
        "missing_sessions": missing_sessions,
        "extra_sessions": extra_sessions,
        "needs_creation": missing_sessions
    }


def create_sessions_directory(session_directory=None):
    """创建会话目录"""
    if session_directory is None:
        session_directory = DEFAULT_SESSION_DIRECTORY

    sessions_dir = Path(session_directory)
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
    print("🚀 Telegram智能会话文件生成程序")
    print("="*60)

    # 加载会话配置
    print("📖 正在加载配置文件...")
    session_config = load_session_config()

    max_concurrent_clients = session_config["max_concurrent_clients"]
    session_names = session_config["session_names"]
    session_directory = session_config["session_directory"]

    # 显示配置信息
    print("📋 当前配置:")
    print(f"   API ID: {API_ID}")
    print(f"   API Hash: {API_HASH[:8]}...{API_HASH[-8:] if len(API_HASH) > 16 else API_HASH}")
    print(f"   电话号码: {PHONE_NUMBER}")
    print(f"   代理: socks5://{PROXY_HOST}:{PROXY_PORT}")
    print(f"   客户端数量: {max_concurrent_clients}")
    print(f"   会话目录: {session_directory}")
    print(f"   会话名称: {', '.join(session_names)}")
    print()

    # 确认配置
    response = input("配置信息是否正确？(y/n): ").strip().lower()
    if response not in ['y', 'yes']:
        print("请修改配置文件或环境变量后重新运行")
        return

    # 创建会话目录
    sessions_dir = create_sessions_directory(session_directory)

    # 分析已存在的会话文件
    print(f"\n🔍 分析已存在的会话文件...")
    session_analysis = analyze_existing_sessions(session_directory, session_names)

    existing_sessions = session_analysis["existing_sessions"]
    missing_sessions = session_analysis["missing_sessions"]
    extra_sessions = session_analysis["extra_sessions"]
    needs_creation = session_analysis["needs_creation"]

    # 显示分析结果
    print(f"📊 会话文件分析结果:")
    print(f"   需要的会话总数: {len(session_names)}")
    print(f"   已存在的会话: {len(existing_sessions)} 个")
    if existing_sessions:
        print(f"     - {', '.join(existing_sessions)}")

    print(f"   需要创建的会话: {len(missing_sessions)} 个")
    if missing_sessions:
        print(f"     - {', '.join(missing_sessions)}")

    if extra_sessions:
        print(f"   多余的会话文件: {len(extra_sessions)} 个")
        print(f"     - {', '.join(extra_sessions)}")
        print(f"     (这些文件不会被删除，但不会被主程序使用)")

    # 如果没有需要创建的会话，直接完成
    if not needs_creation:
        print(f"\n✅ 所有需要的会话文件都已存在，无需创建新的会话文件！")
        print(f"📁 会话目录: {sessions_dir.absolute()}")
        print(f"📝 可用会话: {', '.join(existing_sessions)}")
        print(f"\n✨ 程序执行完成!")
        return

    # 确认是否继续创建缺失的会话
    print(f"\n❓ 是否创建缺失的 {len(needs_creation)} 个会话文件？")
    response = input("继续创建？(y/n): ").strip().lower()
    if response not in ['y', 'yes']:
        print("用户选择取消创建")
        return

    # 创建会话文件（顺序模式，只创建缺失的）
    success_count = 0
    total_count = len(needs_creation)

    print(f"\n🔄 开始顺序创建 {total_count} 个缺失的会话文件")
    print("   每个会话之间将间隔1分钟以避免频率限制")
    print()

    for i, session_name in enumerate(needs_creation, 1):
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

    # 显示最终结果
    print(f"\n{'='*60}")
    print("📊 会话创建完成!")
    print(f"   本次创建: {success_count}/{total_count}")
    print(f"   配置的客户端数量: {max_concurrent_clients}")
    print(f"   会话目录: {sessions_dir.absolute()}")

    # 重新分析所有会话文件
    final_analysis = analyze_existing_sessions(session_directory, session_names)
    all_existing = final_analysis["existing_sessions"]

    print(f"\n📁 当前所有可用的会话文件 ({len(all_existing)}/{max_concurrent_clients}):")
    for session_name in session_names:
        status = "✅" if session_name in all_existing else "❌"
        print(f"   {status} {session_name}.session")

    # 检查是否完整
    if len(all_existing) == max_concurrent_clients:
        print(f"\n🎉 完美！所有 {max_concurrent_clients} 个会话文件都已准备就绪！")
    else:
        missing_count = max_concurrent_clients - len(all_existing)
        print(f"\n⚠️  还缺少 {missing_count} 个会话文件，请重新运行脚本完成创建")

    # 显示配置提示
    print(f"\n💡 提示:")
    print(f"   - 当前配置的客户端数量: {max_concurrent_clients}")
    print(f"   - 如需修改客户端数量，请设置环境变量 MAX_CONCURRENT_CLIENTS")
    print(f"   - 或修改配置文件中的 max_concurrent_clients 参数")
    print(f"   - 下次运行时，脚本会自动跳过已存在的会话文件")

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
