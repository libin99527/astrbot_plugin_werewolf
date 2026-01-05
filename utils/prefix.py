"""命令前缀工具"""

# 全局命令前缀，由插件初始化时设置
_command_prefix: str = "/"


def set_command_prefix(prefix: str) -> None:
    """设置命令前缀"""
    global _command_prefix
    _command_prefix = prefix


def get_command_prefix() -> str:
    """获取命令前缀"""
    return _command_prefix


def cmd(command: str) -> str:
    """返回带前缀的命令字符串
    
    例如: cmd("创建房间") -> "/创建房间" 或 "#创建房间"
    """
    return f"{_command_prefix}{command}"
