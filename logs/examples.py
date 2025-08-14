"""
日志模块使用示例
演示如何在RedAlert项目中使用日志功能
"""

import time
from .logger import get_logger, setup_logging, LogConfig, LogLevel
from .utils import log_execution_time, LogContext, create_module_logger


def basic_usage_example():
    """基本使用示例"""
    # 获取日志记录器
    logger = get_logger("example")
    
    # 记录不同级别的日志
    logger.debug("这是调试信息")
    logger.info("这是一般信息")
    logger.warning("这是警告信息")
    logger.error("这是错误信息")
    logger.critical("这是严重错误信息")


def custom_config_example():
    """自定义配置示例"""
    # 创建自定义配置
    config = LogConfig(
        level=LogLevel.DEBUG,
        format="[%(asctime)s] %(name)s.%(funcName)s:%(lineno)d - %(levelname)s - %(message)s",
        enable_color=True,
        log_filename="custom.log"
    )
    
    # 设置全局配置
    setup_logging(config)
    
    logger = get_logger("custom_example")
    logger.info("使用自定义配置的日志")


@log_execution_time("performance")
def slow_function():
    """带性能监控的函数示例"""
    time.sleep(0.1)  # 模拟耗时操作
    return "操作完成"


def context_manager_example():
    """上下文管理器示例"""
    logger = get_logger("context_example")
    
    with LogContext("context_example", "数据处理操作"):
        # 模拟一些操作
        logger.info("正在处理数据...")
        time.sleep(0.05)
        logger.info("数据处理中...")


def exception_handling_example():
    """异常处理示例"""
    logger = get_logger("exception_example")
    
    try:
        # 模拟一个会出错的操作
        result = 1 / 0
    except Exception as e:
        logger.exception("发生了除零错误")
        logger.error(f"错误详情: {e}")


def module_logger_example():
    """模块专用日志记录器示例"""
    # 为当前模块创建日志记录器
    logger = create_module_logger(__name__)
    
    logger.info("这是模块专用的日志记录器")
    logger.debug("模块调试信息")


class ExampleClass:
    """示例类，展示类中的日志使用"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.logger.info("ExampleClass 实例已创建")
    
    def do_something(self):
        """执行某些操作"""
        self.logger.info("开始执行操作")
        try:
            # 模拟操作
            self.logger.debug("操作步骤1完成")
            self.logger.debug("操作步骤2完成")
            self.logger.info("操作成功完成")
        except Exception as e:
            self.logger.error(f"操作失败: {e}")
            raise


def graph_integration_example():
    """与Graph模块集成的示例"""
    # 为graph模块创建专用日志记录器
    graph_logger = get_logger("graph")
    
    graph_logger.info("Graph模块初始化")
    graph_logger.debug("加载图节点配置")
    graph_logger.info("Graph模块启动完成")


def mcp_server_integration_example():
    """与MCP Server集成的示例"""
    # 为mcp_server模块创建专用日志记录器
    mcp_logger = get_logger("mcp_server")
    
    mcp_logger.info("MCP Server启动")
    mcp_logger.debug("监听端口: 8000")
    mcp_logger.info("MCP Server就绪")


if __name__ == "__main__":
    print("=== 日志模块使用示例 ===\n")
    
    print("1. 基本使用示例:")
    basic_usage_example()
    
    print("\n2. 自定义配置示例:")
    custom_config_example()
    
    print("\n3. 性能监控示例:")
    result = slow_function()
    print(f"函数返回: {result}")
    
    print("\n4. 上下文管理器示例:")
    context_manager_example()
    
    print("\n5. 异常处理示例:")
    exception_handling_example()
    
    print("\n6. 模块日志记录器示例:")
    module_logger_example()
    
    print("\n7. 类中使用示例:")
    example_obj = ExampleClass()
    example_obj.do_something()
    
    print("\n8. Graph集成示例:")
    graph_integration_example()
    
    print("\n9. MCP Server集成示例:")
    mcp_server_integration_example()
    
    print("\n=== 示例完成 ===")
