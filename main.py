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

"""
main.py - 一键启动 MCP Server + Client 的入口脚本
用法:
    python main.py

- 自动启动本地服务
- 自动启动本地服务
- 启动 SSE 客户端连接服务
"""

# def run_server():
#     print("[启动] MCP Server")
#     unit_thread = threading.Thread(target=unit_mcp_server.main, daemon=True)
#     info_thread = threading.Thread(target=info_mcp_server.main, daemon=True)
#     camera_thread = threading.Thread(target=camera_mcp_server.main, daemon=True)
#     fight_thread = threading.Thread(target=fight_mcp_server.main, daemon=True)
#     produce_thread = threading.Thread(target=produce_mcp_server.main, daemon=True)
#     unit_thread.start()
#     info_thread.start()
#     camera_thread.start()
#     fight_thread.start()
#     produce_thread.start()


def _init_logger(level):
    setup_logging(LogConfig(level=LogLevel(level)))

async def main_async():
    #处理命令行参数
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, default="stdio", help="运行模式: stdio, sse, http")
    parser.add_argument("--log-level", type=str, default="INFO", help="日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    args = parser.parse_args()

    _init_logger(args.log_level)
    
    logger.info("启动 MCP Server + Client")
    
    # run_server()
    
    # 等待MCP服务器启动
    # await asyncio.sleep(2)

    # 启动 graph (异步)
    await graph_main(mode=args.mode)

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")