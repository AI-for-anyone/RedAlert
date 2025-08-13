import asyncio
import socket
import threading
import time
from mcp_tools import mcp_server
from graph import Graph

#将.env导入环境变量
from dotenv import load_dotenv
load_dotenv()

"""
main.py - 一键启动 MCP Server + Client 的入口脚本
用法:
    python main.py

- 自动启动本地服务（端口 8000）
- 启动 SSE 客户端连接服务
"""

def run_server():
    print("[启动] MCP Server")
    mcp_server.main()

if __name__ == "__main__":
    # 启动 server 的线程
    # server_thread = threading.Thread(target=run_server, daemon=True)
    # server_thread.start()

    # 启动 graph
    graph = Graph()
    graph.run()

    # 主线程等待子线程
    # server_thread.join()