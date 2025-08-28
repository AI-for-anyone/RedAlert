import asyncio
import uuid
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, Literal
from enum import Enum

from task_scheduler import Task, TaskManager, TaskGroup, TaskStatus
from .blackboard import init_blackboard, blackboard, ns, clear_run_state

from .state import GlobalState, WorkflowType
from .plan import PlanNode
from .camera import CameraNode
from .production import ProductionNode
from .unit_control import UnitControlNode
from .intelligence import IntelligenceNode
from .subtask_graph import build_subtask_graph, execute_subtask
from .mcp_manager import mcp_manager
from logs import get_logger
from config.config import check_mcp_servers
from aioconsole import ainput

logger = get_logger("graph")

class Graph:
    def __init__(self, mode="stdio"):
        self._mode : str = mode
        self._check_dependencies()
        self._plan_node = PlanNode()
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
            # 初始化共享黑板系统
            await init_blackboard()
            logger.info("共享黑板系统初始化完成")
            
            # 初始化MCP管理器和所有节点
            await mcp_manager.initialize()
            await self._plan_node.initialize()
            await self._camera_node.initialize()
            await self._production_node.initialize()
            await self._unit_control_node.initialize()
            await self._intelligence_node.initialize()
            self._initialized = True
            logger.info("所有节点初始化完成")
        except Exception as e:
            logger.error(f"节点初始化失败: {e}")
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
        self._graph.add_node("plan", self._plan_node.plan_node)
        self._graph.add_node("execute_plan", self._plan_node.execute_plan_node)
        self._graph.add_node(WorkflowType.CAMERA_CONTROL.value, self._camera_node.camera_node)
        self._graph.add_node(WorkflowType.PRODUCTION.value, self._production_node.production_node)
        self._graph.add_node(WorkflowType.UNIT_CONTROL.value, self._unit_control_node.unit_control_node)
        self._graph.add_node(WorkflowType.INTELLIGENCE.value, self._intelligence_node.intelligence_node)
        
        # 添加子任务系统节点
        self._graph.add_node("subtask", self._run_complex_subtask)
        self._graph.add_node("init_run", self._init_run_state)
        self._graph.add_node("cleanup_run", self._cleanup_run_state)

        # 使用新的计划驱动的边
        self._graph.add_edge(START, "init_run")  # 先初始化运行状态
        self._graph.add_edge("init_run", "plan")  # 初始化后进入计划阶段
        
        # 计划阶段控制执行流程，不需要无条件边
        # execute_plan 节点会循环执行直到所有阶段完成
        
        # 保留子任务系统支持
        self._graph.add_edge("subtask", "plan")  # 子任务完成后回到计划重新评估
        
        # 清理资源并结束
        self._graph.add_edge("cleanup_run", END)

        self._compiled_graph = self._graph.compile()
    
    async def _init_run_state(self, state: GlobalState) -> GlobalState:
        """初始化运行状态"""
        if not state.get("run_id"):
            state["run_id"] = str(uuid.uuid4())
            logger.info(f"分配运行ID: {state['run_id']}")
        
        # 初始化子任务相关字段
        state["subtask_enabled"] = state.get("subtask_enabled", False)
        state["subtask_plan"] = state.get("subtask_plan", [])
        state["subtask_results"] = state.get("subtask_results", [])
        state["blackboard_keys"] = state.get("blackboard_keys", [])
        state["metadata"] = state.get("metadata", {})
        
        # 在黑板中记录运行状态
        try:
            await blackboard.set(ns(state["run_id"], "status"), "running")
            await blackboard.set(ns(state["run_id"], "start_time"), asyncio.get_event_loop().time())
            await blackboard.set(ns(state["run_id"], "input_cmd"), state.get("input_cmd", ""))
            logger.debug(f"运行状态已记录到黑板: {state['run_id']}")
        except Exception as e:
            logger.warning(f"记录运行状态到黑板失败: {e}")
        
        return state
    
    async def _cleanup_run_state(self, state: GlobalState) -> GlobalState:
        """清理运行状态"""
        run_id = state.get("run_id")
        if not run_id:
            return state
        
        try:
            # 更新运行状态为完成
            await blackboard.set(ns(run_id, "status"), "completed")
            await blackboard.set(ns(run_id, "end_time"), asyncio.get_event_loop().time())
            
            # 清理该运行的所有黑板数据
            cleared_count = await clear_run_state(run_id)
            logger.info(f"清理运行状态: {run_id}, 删除 {cleared_count} 个键")
            
        except Exception as e:
            logger.error(f"清理运行状态失败: {e}")
        
        return state
    
    async def _run_complex_subtask(self, state: GlobalState) -> GlobalState:
        """桥接节点：执行复杂子任务"""
        run_id = state.get("run_id")
        if not run_id:
            logger.warning("子任务执行：缺少运行ID")
            state["result"] = "子任务执行失败：缺少运行ID"
            return state
        
        logger.info(f"开始执行复杂子任务: {run_id}")
        
        try:
            # 从状态或黑板获取子任务计划
            subtask_plan = state.get("subtask_plan")
            if not subtask_plan:
                # 尝试从黑板获取
                subtask_plan, _ = await blackboard.get_with_version(ns(run_id, "subtask_plan"))
            
            if not subtask_plan:
                # 如果没有现成计划，基于输入命令生成默认计划
                input_cmd = state.get("input_cmd", "")
                subtask_plan = self._generate_default_plan(input_cmd)
                logger.info(f"生成默认子任务计划: {len(subtask_plan)} 个阶段")
            
            # 执行子任务
            result = await execute_subtask(plan=subtask_plan, run_id=run_id)
            
            # 更新状态
            state["subtask_results"] = result.get("results", [])
            state["result"] = f"子任务完成: 执行了 {len(state['subtask_results'])} 步操作"
            
            logger.info(f"子任务执行完成: {state['result']}")
            
        except Exception as e:
            logger.error(f"子任务执行失败: {e}")
            state["result"] = f"子任务执行失败: {str(e)}"
        
        return state
    
    def _generate_default_plan(self, input_cmd: str) -> list:
        """根据输入命令生成默认执行计划"""
        cmd_lower = input_cmd.lower()
        
        if "生产" in cmd_lower or "建造" in cmd_lower:
            return [
                {
                    "kind": "parallel",
                    "actions": [
                        {"type": "produce", "unit": "rifle", "count": 2},
                        {"type": "produce", "unit": "engineer", "count": 1}
                    ]
                }
            ]
        elif "攻击" in cmd_lower or "战斗" in cmd_lower:
            return [
                {
                    "kind": "serial",
                    "actions": [
                        {"type": "move", "to": [100, 100], "units": "all"},
                        {"type": "attack", "target": "enemy_base", "units": "all"}
                    ]
                }
            ]
        else:
            # 默认混合计划
            return [
                {
                    "kind": "parallel",
                    "actions": [
                        {"type": "produce", "unit": "rifle", "count": 1}
                    ]
                },
                {
                    "kind": "serial",
                    "actions": [
                        {"type": "move", "to": [50, 50], "units": "group1"}
                    ]
                }
            ]
        
    
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
        task_manager = await TaskManager.get_instance()
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