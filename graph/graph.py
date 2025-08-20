import asyncio
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, Literal
from enum import Enum

from task_scheduler import Task, TaskManager, TaskGroup, TaskStatus

from .state import GlobalState, WorkflowType
from .classify import ClassifyNode
from .camera import CameraNode
from .production import ProductionNode
from .unit_control import UnitControlNode
from .intelligence import IntelligenceNode
from .mcp_manager import mcp_manager
from logs import get_logger
from config.config import check_mcp_servers
from aioconsole import ainput

logger = get_logger("graph")

class Graph:
    def __init__(self, mode="stdio"):
        self._mode : str = mode
        self._check_dependencies()
        self._classify_node = ClassifyNode()
        self._camera_node = CameraNode()
        self._production_node = ProductionNode()
        self._unit_control_node = UnitControlNode()
        self._intelligence_node = IntelligenceNode()
        self._initialized = False
        self._init_graph()
    
    async def initialize(self):
        """异步初始化MCP管理器和所有节点"""
        if self._initialized:
            return
        
        try:
            # 初始化MCP管理器
            await mcp_manager.initialize()
            logger.info("MCP管理器初始化完成")
            
            # 初始化所有节点
            await self._classify_node.initialize()
            await self._camera_node.initialize()
            await self._production_node.initialize()
            await self._unit_control_node.initialize()
            await self._intelligence_node.initialize()
            
            self._initialized = True
            logger.info("所有节点初始化完成")
            
        except Exception as e:
            logger.error(f"图初始化失败: {e}")
            raise
    
    def _check_dependencies(self):
        """检查MCP服务器依赖"""
        offline_servers = check_mcp_servers()
        if offline_servers:
            logger.warning(f"以下MCP服务器离线: {', '.join(offline_servers)}")
        else:
            logger.info("所有MCP服务器连接正常")

    def _init_graph(self):
        self._graph = StateGraph(GlobalState)

        # 使用字符串作为节点名，传递绑定的方法
        self._graph.add_node(WorkflowType.CLASSIFY.value, self._classify_node.classify_node)
        self._graph.add_node(WorkflowType.CAMERA_CONTROL.value, self._camera_node.camera_node)
        self._graph.add_node(WorkflowType.PRODUCTION.value, self._production_node.production_node)
        self._graph.add_node(WorkflowType.UNIT_CONTROL.value, self._unit_control_node.unit_control_node)
        self._graph.add_node(WorkflowType.INTELLIGENCE.value, self._intelligence_node.intelligence_node)

        # 使用字符串作为边的节点名
        self._graph.add_edge(START, WorkflowType.CLASSIFY.value)
        self._graph.add_edge(WorkflowType.CAMERA_CONTROL.value, WorkflowType.CLASSIFY.value)
        self._graph.add_edge(WorkflowType.PRODUCTION.value, WorkflowType.CLASSIFY.value)
        self._graph.add_edge(WorkflowType.UNIT_CONTROL.value, WorkflowType.CLASSIFY.value)
        self._graph.add_edge(WorkflowType.INTELLIGENCE.value, WorkflowType.CLASSIFY.value)

        self._compiled_graph = self._graph.compile()
        
    
    async def run(self):
        # 确保初始化完成
        await self.initialize()
        
        match self._mode:
            case "stdio":
                await self._run_stdio()
            case "sse":
                await self._run_sse()
            case "http":
                await self._run_http()
            case _:
                raise ValueError(f"不支持的模式: {self._mode}")
    
    async def _run_stdio(self):
        logger.info("运行 stdio 模式，输入 /bye 退出")
        task_manager = TaskManager()
        while True:
            user_input = await ainput("\n-------------\nUser: ")
            if user_input == "/bye":
                break
            try:
                # task = asyncio.create_task(self._compiled_graph.ainvoke({"input_cmd": user_input}), name=user_input)
                task = await task_manager.create_task(self._compiled_graph.ainvoke({"input_cmd": user_input}), name=user_input)
                task_handle = await task_manager.submit_task(task.id)
                logger.info(f"cmd: [{user_input}] | task: {task.name}")
            except Exception as e:
                logger.error(f"执行命令失败: {e}")
    
    async def _run_sse(self):
        logger.info("运行 sse 模式")
        pass
    
    async def _run_http(self):
        logger.info("运行 http 模式")
        pass
    
    async def close(self):
        """关闭资源"""
        try:
            await mcp_manager.close()
            logger.info("图资源已关闭")
        except Exception as e:
            logger.error(f"关闭图资源失败: {e}")

async def main(mode="stdio"):
    graph = Graph(mode)
    try:
        await graph.run()
    finally:
        await graph.close()

if __name__ == "__main__":
    main()