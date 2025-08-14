"""
日志配置模块
定义日志的配置参数和格式
"""

import os
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogConfig:
    """日志配置类"""
    # 基本配置
    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    
    # 文件输出配置
    enable_file_logging: bool = True
    log_dir: str = "logs"
    log_filename: str = "redalert.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    # 控制台输出配置
    enable_console_logging: bool = True
    console_level: Optional[LogLevel] = None  # 如果为None，使用主level
    
    # 彩色输出配置
    enable_color: bool = True
    
    # 模块特定配置
    module_levels: dict = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.module_levels is None:
            self.module_levels = {}
        
        if self.console_level is None:
            self.console_level = self.level
    
    @property
    def log_file_path(self) -> str:
        """获取完整的日志文件路径"""
        return os.path.join(self.log_dir, self.log_filename)


# 默认配置
DEFAULT_CONFIG = LogConfig()

# 开发环境配置
DEV_CONFIG = LogConfig(
    level=LogLevel.DEBUG,
    enable_console_logging=True,
    enable_color=True,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
)

# 生产环境配置
PROD_CONFIG = LogConfig(
    level=LogLevel.INFO,
    enable_console_logging=False,
    enable_color=False,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s"
)
