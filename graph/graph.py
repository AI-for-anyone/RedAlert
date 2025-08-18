from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, Literal
from enum import Enum

from .state import GlobalState, WorkflowType
from .classify import ClassifyNode
from .camera import CameraNode
from .production import ProductionNode
from .unit_control import UnitControlNode
from .intelligence import IntelligenceNode
from logs import get_logger
from config.config import check_mcp_servers

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
        self._init_graph()
    
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
        
    
    def run(self):
        match self._mode:
            case "stdio":
                self._run_stdio()
            case "sse":
                self._run_sse()
            case "http":
                self._run_http()
            case _:
                raise ValueError(f"不支持的模式: {self._mode}")
    
    def _run_stdio(self):
        logger.info("运行 stdio 模式，输入 /bye 退出")
        while True:
            user_input = input("User: ")
            if user_input == "/bye":
                break
            result = self._compiled_graph.invoke({"input_cmd": user_input})
            logger.info(f"cmd: [{user_input}], state: {result['state'].value}")
    
    def _run_sse(self):
        logger.info("运行 sse 模式")
        pass
    
    def _run_http(self):
        logger.info("运行 http 模式")
        pass

def main(mode="stdio"):
    graph = Graph(mode)
    graph.run()

if __name__ == "__main__":
    main()