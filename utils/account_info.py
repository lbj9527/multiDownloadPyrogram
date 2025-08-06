"""
账户信息管理工具
获取和管理Telegram账户的详细信息，包括Premium状态
"""
from typing import Dict, Optional, Any
from pyrogram import Client
from utils.logging_utils import LoggerMixin


class AccountInfo:
    """账户信息数据类"""
    
    def __init__(self, user_id: int, username: Optional[str] = None, 
                 first_name: Optional[str] = None, last_name: Optional[str] = None,
                 is_premium: bool = False, is_verified: bool = False,
                 is_bot: bool = False, dc_id: Optional[int] = None):
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.is_premium = is_premium
        self.is_verified = is_verified
        self.is_bot = is_bot
        self.dc_id = dc_id
    
    @property
    def display_name(self) -> str:
        """获取显示名称"""
        if self.first_name:
            name = self.first_name
            if self.last_name:
                name += f" {self.last_name}"
            return name
        elif self.username:
            return f"@{self.username}"
        else:
            return f"User {self.user_id}"
    
    @property
    def caption_limit(self) -> int:
        """根据Premium状态返回Caption长度限制"""
        return 4096 if self.is_premium else 1024
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "display_name": self.display_name,
            "is_premium": self.is_premium,
            "is_verified": self.is_verified,
            "is_bot": self.is_bot,
            "dc_id": self.dc_id,
            "caption_limit": self.caption_limit
        }


class AccountInfoManager(LoggerMixin):
    """账户信息管理器"""
    
    def __init__(self):
        """初始化账户信息管理器"""
        self.accounts_info: Dict[str, AccountInfo] = {}
    
    async def get_account_info(self, client: Client, client_name: str) -> Optional[AccountInfo]:
        """
        获取指定客户端的账户信息
        
        Args:
            client: Pyrogram客户端
            client_name: 客户端名称
            
        Returns:
            AccountInfo: 账户信息对象，失败时返回None
        """
        try:
            # 获取当前用户信息
            me = await client.get_me()
            
            # 创建账户信息对象
            account_info = AccountInfo(
                user_id=me.id,
                username=me.username,
                first_name=me.first_name,
                last_name=me.last_name,
                is_premium=me.is_premium or False,
                is_verified=me.is_verified or False,
                is_bot=me.is_bot or False,
                dc_id=me.dc_id
            )
            
            # 缓存账户信息
            self.accounts_info[client_name] = account_info
            
            # 记录账户信息
            self.log_info(f"获取客户端 {client_name} 账户信息成功:")
            self.log_info(f"  用户: {account_info.display_name} (ID: {account_info.user_id})")
            self.log_info(f"  Premium: {'✅' if account_info.is_premium else '❌'}")
            self.log_info(f"  Caption限制: {account_info.caption_limit} 字符")
            if account_info.dc_id:
                self.log_info(f"  数据中心: DC{account_info.dc_id}")
            
            return account_info
            
        except Exception as e:
            self.log_error(f"获取客户端 {client_name} 账户信息失败: {e}")
            return None
    
    async def refresh_account_info(self, client: Client, client_name: str) -> Optional[AccountInfo]:
        """
        刷新指定客户端的账户信息
        
        Args:
            client: Pyrogram客户端
            client_name: 客户端名称
            
        Returns:
            AccountInfo: 更新后的账户信息
        """
        self.log_info(f"刷新客户端 {client_name} 账户信息...")
        return await self.get_account_info(client, client_name)
    
    def get_cached_account_info(self, client_name: str) -> Optional[AccountInfo]:
        """
        获取缓存的账户信息
        
        Args:
            client_name: 客户端名称
            
        Returns:
            AccountInfo: 缓存的账户信息，不存在时返回None
        """
        return self.accounts_info.get(client_name)
    
    def is_premium_user(self, client_name: str) -> bool:
        """
        检查指定客户端是否为Premium用户
        
        Args:
            client_name: 客户端名称
            
        Returns:
            bool: 是否为Premium用户
        """
        account_info = self.get_cached_account_info(client_name)
        return account_info.is_premium if account_info else False
    
    def get_caption_limit(self, client_name: str) -> int:
        """
        获取指定客户端的Caption长度限制
        
        Args:
            client_name: 客户端名称
            
        Returns:
            int: Caption长度限制（普通用户1024，Premium用户4096）
        """
        account_info = self.get_cached_account_info(client_name)
        return account_info.caption_limit if account_info else 1024
    
    async def get_all_accounts_info(self, clients: Dict[str, Client]) -> Dict[str, AccountInfo]:
        """
        获取所有客户端的账户信息
        
        Args:
            clients: 客户端字典
            
        Returns:
            Dict[str, AccountInfo]: 所有账户信息
        """
        self.log_info("获取所有客户端账户信息...")
        
        results = {}
        for client_name, client in clients.items():
            account_info = await self.get_account_info(client, client_name)
            if account_info:
                results[client_name] = account_info
        
        # 统计信息
        total_clients = len(results)
        premium_clients = sum(1 for info in results.values() if info.is_premium)
        
        self.log_info(f"账户信息获取完成: {total_clients} 个客户端")
        self.log_info(f"Premium用户: {premium_clients} 个")
        self.log_info(f"普通用户: {total_clients - premium_clients} 个")
        
        return results
    
    def get_accounts_summary(self) -> Dict[str, Any]:
        """
        获取账户信息摘要
        
        Returns:
            Dict[str, Any]: 账户信息摘要
        """
        total_accounts = len(self.accounts_info)
        premium_accounts = sum(1 for info in self.accounts_info.values() if info.is_premium)
        
        return {
            "total_accounts": total_accounts,
            "premium_accounts": premium_accounts,
            "regular_accounts": total_accounts - premium_accounts,
            "accounts": {name: info.to_dict() for name, info in self.accounts_info.items()}
        }
    
    def log_accounts_summary(self):
        """记录账户信息摘要"""
        summary = self.get_accounts_summary()
        
        self.log_info("📊 账户信息摘要:")
        self.log_info(f"  总账户数: {summary['total_accounts']}")
        self.log_info(f"  Premium账户: {summary['premium_accounts']} 个")
        self.log_info(f"  普通账户: {summary['regular_accounts']} 个")
        
        if summary['total_accounts'] > 0:
            self.log_info("  账户详情:")
            for name, info in summary['accounts'].items():
                premium_status = "✅ Premium" if info['is_premium'] else "❌ 普通"
                self.log_info(f"    {name}: {info['display_name']} ({premium_status})")


# 全局账户信息管理器实例
account_info_manager = AccountInfoManager()


def get_account_info_manager() -> AccountInfoManager:
    """获取全局账户信息管理器实例"""
    return account_info_manager
