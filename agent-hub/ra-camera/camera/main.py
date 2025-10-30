from unittest import async_case
from mofa.agent_build.base.base_agent import MofaAgent, run_agent
import threading
import queue
import time
import asyncio
from typing import Dict, Any

from .llm import get_llm_client, LLMClient

node_name = "ra-camera"

llm_client: LLMClient|None = None
command_queue: queue.Queue = queue.Queue()
running = True

def command_producer(agent: MofaAgent):
    """生产者线程：接收命令并放入队列"""
    global running
    
    while running:
        try:
            # 接收命令参数
            user_input = agent.receive_parameter('command')
            if user_input:
                command_data = {
                    'command': user_input,
                    'timestamp': time.time(),
                    'agent': agent
                }
                command_queue.put(command_data)
                agent.write_log(message=f"{node_name} 命令已加入队列: {user_input}")
            
            time.sleep(0.1)  # 避免过度占用CPU
            
        except Exception as e:
            error_message = f"生产者线程异常: {str(e)}"
            agent.write_log(message=error_message, level='ERROR')
            time.sleep(1)  # 出错时等待一秒再重试

async def camera_deal():
    """消费者线程：从队列中取出命令并处理"""
    global running, llm_client

    await llm_client._initialize_client()
    
    while running:
        try:
            # 从队列中获取命令，超时时间为1秒
            command_data = command_queue.get(timeout=1)
            
            if command_data:
                result = await llm_client.node(command_data)
                command_queue.task_done()

                
        except queue.Empty:
            # 队列为空，继续循环
            continue
        except Exception as e:
            print(f"消费者线程异常: {str(e)}")
            time.sleep(1)

def command_consumer():
    asyncio.run(camera_deal())

@run_agent
def run(agent: MofaAgent):
    """主运行函数，启动生产者和消费者线程"""
    global running
    
    try:
        agent.write_log(message=f"{node_name} 启动队列处理系统")
        
        # 启动消费者线程
        consumer_thread = threading.Thread(target=command_consumer, daemon=True)
        consumer_thread.start()
        agent.write_log(message=f"{node_name} 消费者线程已启动")
        
        # 启动生产者线程（在主线程中运行）
        agent.write_log(message=f"{node_name} 生产者线程开始运行")
        command_producer(agent)
        
    except KeyboardInterrupt:
        agent.write_log(message=f"{node_name} 收到中断信号，正在停止...")
        running = False
    except Exception as e:
        error_message = f"运行时发生异常: {str(e)}"
        agent.write_log(message=error_message, level='ERROR')
        running = False
    finally:
        running = False
        agent.write_log(message=f"{node_name} 系统已停止")

def _init():
    global llm_client

    try:
        # 初始化llm
        llm_client = get_llm_client()
        
    except Exception as e:
        print(f"LLM初始化失败: {str(e)}")
        raise

def main():
    # 初始化LLM客户端
    _init()

    agent = MofaAgent(agent_name=node_name)
    
    try:
        run(agent=agent)
    except KeyboardInterrupt:
        print(f"\n{node_name} 收到中断信号，正在关闭...")
        global running
        running = False
    finally:
        # 等待队列中的任务完成
        if not command_queue.empty():
            print(f"等待队列中剩余 {command_queue.qsize()} 个任务完成...")
            command_queue.join()
        print(f"{node_name} 已完全停止")

if __name__ == "__main__":
    main()