"""
启动所有 MCP 服务器的统一入口
"""
import subprocess
import time
import sys
import os
from pathlib import Path
import asyncio

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logs import get_logger, setup_logging, LogConfig, LogLevel

logger = get_logger("mcp_server")

def start_all_servers():
    """启动所有 MCP 服务器"""
    # 获取当前目录和 Python 解释器路径
    current_dir = Path(__file__).parent
    python_exe = sys.executable
    
    # 服务器配置
    servers = [
        ("unit_mcp_server.py", "Unit", 8004),
        ("info_mcp_server.py", "Info", 8002),
        ("camera_mcp_server.py", "Camera", 8000),
        ("fight_mcp_server.py", "Fight", 8001),
        ("produce_mcp_server.py", "Produce", 8003)
    ]
    
    processes = []
    
    try:
        # 启动所有服务器
        print("[启动] MCP Server")
        for server_file, server_name, port in servers:
            server_path = current_dir / server_file
            try:
                logger.info(f"启动 {server_name} MCP 服务器 (端口 {port})")
                
                # 使用独立进程启动，避免事件循环冲突
                process = subprocess.Popen(
                    [python_exe, str(server_path)],
                    cwd=str(current_dir),
                    stdout=None,
                    stderr=None,
                    text=True,
                    encoding='utf-8'
                )
                processes.append((process, server_name))
                time.sleep(0)  # 错开启动时间
            except Exception as e:
                logger.error(f"{server_name} MCP 服务器启动失败: {e}")
        
        logger.info("所有 MCP 服务器已启动")
        
        # 保持主进程运行并监控子进程
        while True:
            time.sleep(5)
            # 检查进程状态
            for process, name in processes:
                if process.poll() is not None:
                    logger.error(f"{name} MCP 服务器已退出")
                    
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭所有服务器...")
        # 终止所有子进程
        for process, name in processes:
            if process.poll() is None:
                logger.info(f"正在关闭 {name} MCP 服务器")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
    except Exception as e:
        logger.error("启动 MCP 服务器时发生错误: {0}".format(str(e)))
    
    

if __name__ == "__main__":
    setup_logging(LogConfig(level=LogLevel.DEBUG))
    start_all_servers()