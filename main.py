import asyncio
import socket
import threading
import time
# from mcp_tools import unit_mcp_server, info_mcp_server, camera_mcp_server, fight_mcp_server, produce_mcp_server
from graph.graph import main as graph_main
from logs import get_logger, setup_logging, LogConfig, LogLevel

#将.env导入环境变量
from dotenv import load_dotenv
load_dotenv()

logger = get_logger("main")


def _init_logger(level, enable_console_logging: bool = False):
    setup_logging(LogConfig(level=LogLevel(level), enable_console_logging=enable_console_logging))

async def main_async():
    #处理命令行参数
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, default="stdio", help="运行模式: stdio, sse, http, gradio")
    parser.add_argument("--log-level", type=str, default="INFO", help="日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    args = parser.parse_args()

    # 在 Gradio 模式下开启控制台日志，避免终端“无回显”的观感
    _init_logger(args.log_level, enable_console_logging=(args.mode == "gradio"))
    
    logger.info("启动AI")
    
    # 若为 Gradio 模式，启动可视化界面
    if args.mode == "gradio":
        from ui.gradio_ui import launch
        print("Starting Gradio UI on http://127.0.0.1:7860 ...")
        launch()
        return

    # 启动 graph (异步)
    await graph_main(mode=args.mode)

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")