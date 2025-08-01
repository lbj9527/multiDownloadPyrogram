"""
会话管理器
管理Telegram会话文件
"""
from pathlib import Path
from typing import List, Optional
from utils.logging_utils import LoggerMixin

class SessionManager(LoggerMixin):
    """会话管理器"""
    
    def __init__(self, session_directory: str = "sessions"):
        self.session_directory = Path(session_directory)
        self.session_directory.mkdir(exist_ok=True)
    
    def get_available_sessions(self, session_names: List[str]) -> List[str]:
        """
        获取可用的会话文件
        
        Args:
            session_names: 期望的会话名称列表
            
        Returns:
            实际可用的会话名称列表
        """
        available_sessions = []
        
        for session_name in session_names:
            session_file = self.session_directory / f"{session_name}.session"
            if session_file.exists():
                available_sessions.append(session_name)
                self.log_debug(f"找到会话文件: {session_file}")
            else:
                self.log_warning(f"会话文件不存在: {session_file}")
        
        self.log_info(f"可用会话: {len(available_sessions)}/{len(session_names)}")
        return available_sessions
    
    def validate_session_files(self, session_names: List[str]) -> bool:
        """
        验证会话文件是否完整
        
        Args:
            session_names: 会话名称列表
            
        Returns:
            是否所有会话文件都存在且有效
        """
        all_valid = True
        
        for session_name in session_names:
            session_file = self.session_directory / f"{session_name}.session"
            
            if not session_file.exists():
                self.log_error(f"会话文件不存在: {session_file}")
                all_valid = False
                continue
            
            # 检查文件大小（会话文件不应该为空）
            if session_file.stat().st_size == 0:
                self.log_error(f"会话文件为空: {session_file}")
                all_valid = False
                continue
            
            self.log_debug(f"会话文件有效: {session_file}")
        
        if all_valid:
            self.log_info("所有会话文件验证通过")
        else:
            self.log_error("部分会话文件验证失败")
        
        return all_valid
    
    def get_session_file_path(self, session_name: str) -> Path:
        """获取会话文件路径"""
        return self.session_directory / f"{session_name}.session"
    
    def list_all_session_files(self) -> List[str]:
        """列出所有会话文件"""
        session_files = []
        
        for file_path in self.session_directory.glob("*.session"):
            session_name = file_path.stem  # 去掉.session后缀
            session_files.append(session_name)
        
        return sorted(session_files)
    
    def cleanup_invalid_sessions(self, valid_session_names: List[str]) -> int:
        """
        清理无效的会话文件
        
        Args:
            valid_session_names: 有效的会话名称列表
            
        Returns:
            清理的文件数量
        """
        all_sessions = self.list_all_session_files()
        cleaned_count = 0
        
        for session_name in all_sessions:
            if session_name not in valid_session_names:
                session_file = self.get_session_file_path(session_name)
                try:
                    session_file.unlink()
                    self.log_info(f"已清理无效会话文件: {session_file}")
                    cleaned_count += 1
                except Exception as e:
                    self.log_error(f"清理会话文件失败 {session_file}: {e}")
        
        return cleaned_count
