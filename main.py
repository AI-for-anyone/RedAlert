import asyncio
import socket
import threading
import time
from mcp_tools import mcp_server, mcp_client

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

def wait_for_server(host: str, port: int, timeout=10):
    """等待 server 启动"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                print("[✔] MCP Server 已就绪")
                return True
        except OSError:
            print("[...] 等待 MCP Server 启动中...")
            time.sleep(1)
    raise RuntimeError("等待 MCP Server 启动失败，超时退出")


def run_client():
    wait_for_server("127.0.0.1", 8000)
    print("[启动] MCP Client")
    asyncio.run(mcp_client.main("http://127.0.0.1:8000/sse"))

if __name__ == "__main__":
    # 启动 server 的线程
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 启动 client 的线程
    client_thread = threading.Thread(target=run_client, daemon=True)
    client_thread.start()

    # 主线程等待子线程
    server_thread.join()
    client_thread.join()