from mofa.agent_build.base.base_agent import MofaAgent, run_agent
import threading
import queue
import time
from typing import Dict, Any

from classify.llm import get_llm_client, LLMClient

node_name = "ra-classify"

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


def command_consumer():
    """消费者线程：从队列中取出命令并处理"""
    global running, llm_client
    
    while running:
        try:
            # 从队列中获取命令，超时时间为1秒
            command_data = command_queue.get(timeout=1)
            
            if command_data:
                process_command(command_data)
                command_queue.task_done()
                
        except queue.Empty:
            # 队列为空，继续循环
            continue
        except Exception as e:
            print(f"消费者线程异常: {str(e)}")
            time.sleep(1)


def process_command(command_data: Dict[str, Any]):
    """处理单个命令"""
    try:
        command = command_data['command']
        agent = command_data['agent']
        timestamp = command_data['timestamp']
        
        agent.write_log(message=f"[{timestamp}]:{node_name} 开始处理命令: {command}")
        
        # 使用LLM处理命令
        if llm_client:
            task = llm_client.node(command)
            next_node = _determine_next_node(task["assistant"])
            cmd = task["task"]
            agent.write_log(message=f"{node_name} LLM响应: {task}")
        else:
            agent.write_log(message=f"{node_name} LLM未初始化，无法处理命令", level='WARNING')
        
        # 下一步
        if next_node == "END":
            agent.write_log(message=f"{node_name} 命令失败")
        
        agent.send_output(
            agent_output_name=next_node,
            agent_result=cmd
        )
        
        agent.write_log(message=f"{node_name} 数据发送完成: agent_output_name={next_node}, agent_result={cmd}")
        
    except Exception as e:
        error_message = f"处理命令时发生异常: {str(e)}"
        if 'agent' in command_data:
            command_data['agent'].write_log(message=error_message, level='ERROR')
        else:
            print(error_message)

def _determine_next_node(task: str) -> str:
        """根据任务内容确定工作流类型"""
        match task.lower():
            case "地图视角控制":
                return "ra-camera"
            case "生产管理":
                return "ra-produce"
            case "单位控制":
                return "ra-unit"
            case "信息查询":
                return "ra-info"
            case "ai助手":
                return "ra-ai_assistant"
            case _:
                logger.error(f"无法识别的任务类型: {task}")
                return "END"


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