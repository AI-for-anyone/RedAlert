"""
日志工具模块
提供日志相关的实用工具函数
"""

import functools
import time
from typing import Callable, Any
from .logger import get_logger


def log_execution_time(logger_name: str = "performance"):
    """
    装饰器：记录函数执行时间
    
    Args:
        logger_name: 日志记录器名称
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = get_logger(logger_name)
            start_time = time.time()
            
            try:
                logger.log_function_call(func.__name__, args, kwargs)
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.log_performance(
                    operation=func.__name__,
                    duration=duration,
                    status="success"
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.log_performance(
                    operation=func.__name__,
                    duration=duration,
                    status="error",
                    error=str(e)
                )
                logger.exception(f"函数 {func.__name__} 执行出错: {e}")
                raise
        
        return wrapper
    return decorator


def log_method_calls(logger_name: str = None):
    """
    类装饰器：记录类中所有方法的调用
    
    Args:
        logger_name: 日志记录器名称，如果为None则使用类名
    """
    def decorator(cls):
        class_logger_name = logger_name or cls.__name__
        logger = get_logger(class_logger_name)
        
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if callable(attr) and not attr_name.startswith('_'):
                setattr(cls, attr_name, log_execution_time(class_logger_name)(attr))
        
        return cls
    return decorator


class LogContext:
    """日志上下文管理器"""
    
    def __init__(self, logger_name: str, operation: str, level: str = "INFO"):
        """
        初始化日志上下文
        
        Args:
            logger_name: 日志记录器名称
            operation: 操作名称
            level: 日志级别
        """
        self.logger = get_logger(logger_name)
        self.operation = operation
        self.level = level.lower()
        self.start_time = None
    
    def __enter__(self):
        """进入上下文"""
        self.start_time = time.time()
        getattr(self.logger, self.level)(f"开始执行: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        duration = time.time() - self.start_time
        
        if exc_type is None:
            getattr(self.logger, self.level)(
                f"完成执行: {self.operation} (耗时: {duration:.3f}s)"
            )
        else:
            self.logger.error(
                f"执行失败: {self.operation} (耗时: {duration:.3f}s) - {exc_val}"
            )
        
        return False  # 不抑制异常


def create_module_logger(module_name: str):
    """
    为模块创建专用日志记录器的便捷函数
    
    Args:
        module_name: 模块名称（通常使用 __name__）
    
    Returns:
        Logger实例
    """
    return get_logger(module_name)
