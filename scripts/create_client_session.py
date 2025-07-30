"""
智能会话文件生成程序 - 控制台交互版本
用于生成Telegram客户端会话文件，支持控制台输入参数
"""
import asyncio
import os
import sys
import time
from pathlib import Path
from pyrogram.client import Client
from pyrogram.errors import FloodWait

# ==================== 硬编码配置 ====================
# API 配置（硬编码）
API_ID = 25098445
API_HASH = "cc2fa5a762621d306d8de030614e4555"

# SOCKS5 代理配置
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 7890

# 会话目录
SESSION_DIRECTORY = "sessions"

# 客户端设备信息池
CLIENT_CONFIGS = [
    {
        "app_version": "TG-Manager Desktop 4.12.2",
        "device_model": "MacBook Pro",
        "system_version": "macOS 14.1",
        "lang_code": "en"
    },
    {
        "app_version": "TG-Manager Desktop 4.11.8",
        "device_model": "Dell XPS 13",
        "system_version": "Windows 11",
        "lang_code": "zh"
    },
    {
        "app_version": "TG-Manager Desktop 4.10.5",
        "device_model": "ThinkPad X1 Carbon",
        "system_version": "Ubuntu 22.04",
        "lang_code": "en"
    },
    {
        "app_version": "TG-Manager Desktop 4.12.0",
        "device_model": "iMac",
        "system_version": "macOS 13.6",
        "lang_code": "zh"
    },
    {
        "app_version": "TG-Manager Desktop 4.11.6",
        "device_model": "Surface Pro 9",
        "system_version": "Windows 10",
        "lang_code": "en"
    },
    {
        "app_version": "TG-Manager Desktop 4.10.8",
        "device_model": "HP Pavilion",
        "system_version": "Windows 11",
        "lang_code": "zh"
    },
    {
        "app_version": "TG-Manager Desktop 4.12.1",
        "device_model": "MacBook Air",
        "system_version": "macOS 14.0",
        "lang_code": "en"
    },
    {
        "app_version": "TG-Manager Desktop 4.11.9",
        "device_model": "ASUS ZenBook",
        "system_version": "Windows 10",
        "lang_code": "zh"
    },
    {
        "app_version": "TG-Manager Desktop 4.10.7",
        "device_model": "Lenovo IdeaPad",
        "system_version": "Ubuntu 20.04",
        "lang_code": "en"
    },
    {
        "app_version": "TG-Manager Desktop 4.11.7",
        "device_model": "Acer Aspire",
        "system_version": "Windows 11",
        "lang_code": "zh"
    }
]
# ==================== 配置区域结束 ====================


def get_user_input():
    """获取用户输入的参数"""
    print("🚀 Telegram智能会话文件生成程序")
    print("="*60)
    
    # 显示硬编码的API配置
    print("📋 API 配置信息:")
    print(f"   API ID: {API_ID}")
    print(f"   API Hash: {API_HASH[:8]}...{API_HASH[-8:]}")
    print(f"   代理: socks5://{PROXY_HOST}:{PROXY_PORT}")
    print()
    
    # 获取电话号码
    while True:
        phone_number = input("📱 请输入电话号码 (格式: +86xxxxxxxxxx): ").strip()
        if phone_number:
            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number
            print(f"   ✅ 电话号码: {phone_number}")
            break
        else:
            print("   ❌ 电话号码不能为空，请重新输入")
    
    # 获取会话文件数量
    while True:
        try:
            session_count = int(input("🔢 请输入需要生成的会话文件数量 (1-10): ").strip())
            if 1 <= session_count <= 10:
                print(f"   ✅ 会话文件数量: {session_count}")
                break
            else:
                print("   ❌ 数量必须在1-10之间，请重新输入")
        except ValueError:
            print("   ❌ 请输入有效的数字")
    
    return phone_number, session_count


def generate_session_names(phone_number, count):
    """
    生成会话文件名称
    格式: client_电话号码_1.session, client_电话号码_2.session, ...
    
    Args:
        phone_number: 电话号码
        count: 需要生成的会话文件数量
    
    Returns:
        会话文件名称列表
    """
    # 清理电话号码，只保留数字
    clean_phone = ''.join(filter(str.isdigit, phone_number))
    
    # 生成会话名称列表
    session_names = [f"client_{clean_phone}_{i}" for i in range(1, count + 1)]
    
    print(f"📝 生成 {count} 个会话名称:")
    for name in session_names:
        print(f"   - {name}.session")
    
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
            "needs_creation": required_session_names
        }
    
    # 获取已存在的会话文件
    existing_files = list(sessions_dir.glob("*.session"))
    existing_sessions = [f.stem for f in existing_files]  # 去掉.session扩展名
    
    # 分析需要创建的会话
    missing_sessions = [name for name in required_session_names if name not in existing_sessions]
    
    return {
        "existing_sessions": existing_sessions,
        "missing_sessions": missing_sessions,
        "needs_creation": missing_sessions
    }


def create_sessions_directory(session_directory=None):
    """创建会话目录"""
    if session_directory is None:
        session_directory = SESSION_DIRECTORY
    
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
    return proxy_config


def get_client_config(session_index):
    """
    根据会话索引获取客户端配置信息

    Args:
        session_index: 会话索引（从1开始）

    Returns:
        dict: 包含客户端配置的字典
    """
    # 使用索引循环选择配置，确保每个会话都有不同的配置
    config_index = (session_index - 1) % len(CLIENT_CONFIGS)
    config = CLIENT_CONFIGS[config_index].copy()

    # 为每个会话添加唯一标识
    config["app_version"] = f"{config['app_version']} (Client {session_index})"

    return config


async def create_session(session_name, sessions_dir, phone_number, session_index):
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

    # 获取客户端配置
    client_config = get_client_config(session_index)

    print(f"📱 客户端配置:")
    print(f"   应用版本: {client_config['app_version']}")
    print(f"   设备型号: {client_config['device_model']}")
    print(f"   系统版本: {client_config['system_version']}")
    print(f"   语言代码: {client_config['lang_code']}")

    # 创建客户端
    client = Client(
        name=session_name,
        api_id=API_ID,
        api_hash=API_HASH,
        phone_number=phone_number,
        workdir=str(sessions_dir),
        proxy=proxy_config,
        app_version=client_config['app_version'],
        device_model=client_config['device_model'],
        system_version=client_config['system_version'],
        lang_code=client_config['lang_code']
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
    # 获取用户输入
    phone_number, session_count = get_user_input()
    
    # 生成会话名称
    session_names = generate_session_names(phone_number, session_count)
    
    print()
    
    # 确认配置
    response = input("配置信息是否正确？(y/n): ").strip().lower()
    if response not in ['y', 'yes']:
        print("程序已取消")
        return
    
    # 创建会话目录
    sessions_dir = create_sessions_directory(SESSION_DIRECTORY)
    
    # 分析已存在的会话文件
    print(f"\n🔍 分析已存在的会话文件...")
    session_analysis = analyze_existing_sessions(SESSION_DIRECTORY, session_names)
    
    existing_sessions = session_analysis["existing_sessions"]
    missing_sessions = session_analysis["missing_sessions"]
    needs_creation = session_analysis["needs_creation"]
    
    # 显示分析结果
    print(f"📊 会话文件分析结果:")
    print(f"   需要的会话总数: {len(session_names)}")
    print(f"   已存在的会话: {len(existing_sessions)} 个")
    if existing_sessions:
        existing_required = [name for name in existing_sessions if name in session_names]
        if existing_required:
            print(f"     - {', '.join(existing_required)}")
    
    print(f"   需要创建的会话: {len(missing_sessions)} 个")
    if missing_sessions:
        print(f"     - {', '.join(missing_sessions)}")
    
    # 如果没有需要创建的会话，直接完成
    if not needs_creation:
        print(f"\n✅ 所有需要的会话文件都已存在，无需创建新的会话文件！")
        print(f"📁 会话目录: {sessions_dir.absolute()}")
        print(f"📝 可用会话: {', '.join([name for name in existing_sessions if name in session_names])}")
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

        # 从会话名称中提取索引号
        session_index = int(session_name.split('_')[-1])

        success = await create_session(session_name, sessions_dir, phone_number, session_index)
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
    print(f"   配置的会话数量: {session_count}")
    print(f"   会话目录: {sessions_dir.absolute()}")
    
    # 重新分析所有会话文件
    final_analysis = analyze_existing_sessions(SESSION_DIRECTORY, session_names)
    all_existing = final_analysis["existing_sessions"]
    
    print(f"\n📁 当前所有可用的会话文件 ({len([name for name in all_existing if name in session_names])}/{session_count}):")
    for session_name in session_names:
        status = "✅" if session_name in all_existing else "❌"
        print(f"   {status} {session_name}.session")
    
    # 检查是否完整
    available_count = len([name for name in all_existing if name in session_names])
    if available_count == session_count:
        print(f"\n🎉 完美！所有 {session_count} 个会话文件都已准备就绪！")
    else:
        missing_count = session_count - available_count
        print(f"\n⚠️  还缺少 {missing_count} 个会话文件，请重新运行脚本完成创建")
    
    print("\n✨ 程序执行完成!")


if __name__ == "__main__":
    try:
        # 运行主程序
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  程序被用户中断")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        input("按回车键退出...")
