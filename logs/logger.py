"""
日志记录器实现
提供统一的日志记录接口和功能
"""

import logging
import logging.handlers
import os
import sys
from typing import Optional, Dict, Any
from .config import LogConfig, LogLevel, DEFAULT_CONFIG


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
        'RESET': '\033[0m'        # 重置
    }
    
    def format(self, record):
        """格式化日志记录"""
        if hasattr(record, 'levelname') and record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


class Logger:
    """日志记录器类"""
    
    _instances: Dict[str, 'Logger'] = {}
    _config: LogConfig = DEFAULT_CONFIG
    
    def __init__(self, name: str, config: Optional[LogConfig] = None):
        """
        初始化日志记录器
        
        Args:
            name: 日志记录器名称
            config: 日志配置，如果为None则使用默认配置
        """
        self.name = name
        self.config = config or self._config
        self._logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """设置日志记录器"""
        # 清除现有的处理器
        self._logger.handlers.clear()
        
        # 设置日志级别
        level = getattr(logging, self.config.level.value)
        self._logger.setLevel(level)
        
        # 检查模块特定级别
        if self.name in self.config.module_levels:
            module_level = getattr(logging, self.config.module_levels[self.name].value)
            self._logger.setLevel(module_level)
        
        # 添加文件处理器
        if self.config.enable_file_logging:
            self._add_file_handler()
        
        # 添加控制台处理器
        if self.config.enable_console_logging:
            self._add_console_handler()
        
        # 防止重复日志
        self._logger.propagate = False
    
    def _add_file_handler(self):
        """添加文件处理器"""
        # 确保日志目录存在
        os.makedirs(self.config.log_dir, exist_ok=True)
        
        # 创建轮转文件处理器
        file_handler = logging.handlers.RotatingFileHandler(
            filename=self.config.log_file_path,
            maxBytes=self.config.max_file_size,
            backupCount=self.config.backup_count,
            encoding='utf-8'
        )
        
        # 设置格式
        formatter = logging.Formatter(
            fmt=self.config.format,
            datefmt=self.config.date_format
        )
        file_handler.setFormatter(formatter)
        
        # 设置级别
        level = getattr(logging, self.config.level.value)
        file_handler.setLevel(level)
        
        self._logger.addHandler(file_handler)
    
    def _add_console_handler(self):
        """添加控制台处理器"""
        console_handler = logging.StreamHandler(sys.stdout)
        
        # 选择格式化器
        if self.config.enable_color and sys.stdout.isatty():
            formatter = ColoredFormatter(
                fmt=self.config.format,
                datefmt=self.config.date_format
            )
        else:
            formatter = logging.Formatter(
                fmt=self.config.format,
                datefmt=self.config.date_format
            )
        
        console_handler.setFormatter(formatter)
        
        # 设置级别
        level = getattr(logging, self.config.console_level.value)
        console_handler.setLevel(level)
        
        self._logger.addHandler(console_handler)
    
    def debug(self, message: str, *args, **kwargs):
        """记录DEBUG级别日志"""
        self._logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """记录INFO级别日志"""
        self._logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """记录WARNING级别日志"""
        self._logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """记录ERROR级别日志"""
        self._logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """记录CRITICAL级别日志"""
        self._logger.critical(message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        """记录异常信息"""
        self._logger.exception(message, *args, **kwargs)
    
    def log_function_call(self, func_name: str, args: tuple = None, kwargs: dict = None):
        """记录函数调用"""
        args_str = f"args={args}" if args else ""
        kwargs_str = f"kwargs={kwargs}" if kwargs else ""
        params = ", ".join(filter(None, [args_str, kwargs_str]))
        self.debug(f"调用函数: {func_name}({params})")
    
    def log_performance(self, operation: str, duration: float, **context):
        """记录性能信息"""
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        self.info(f"性能统计: {operation} 耗时 {duration:.3f}s {context_str}")
    
    @classmethod
    def set_global_config(cls, config: LogConfig):
        """设置全局日志配置"""
        cls._config = config
        # 重新配置所有已存在的日志记录器
        for logger in cls._instances.values():
            logger.config = config
            logger._setup_logger()


def get_logger(name: str, config: Optional[LogConfig] = None) -> Logger:
    """
    获取日志记录器实例（单例模式）
    
    Args:
        name: 日志记录器名称
        config: 日志配置
    
    Returns:
        Logger实例
    """
    if name not in Logger._instances:
        Logger._instances[name] = Logger(name, config)
    return Logger._instances[name]


def setup_logging(config: LogConfig):
    """
    设置全局日志配置
    
    Args:
        config: 日志配置
    """
    Logger.set_global_config(config)
