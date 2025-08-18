from typing import List
from langgraph.types import Command
from langgraph.graph import END
from .state import GlobalState, WorkflowState
from .base_node import BaseNode
from .mcp_manager import mcp_manager
from config.config import WorkflowType
from logs import get_logger

logger = get_logger("intelligence")

class IntelligenceNode(BaseNode):
    def __init__(self):
        super().__init__("intelligence", WorkflowType.INTELLIGENCE)

    def _get_node_tools(self) -> List:
        """获取信息查询相关的MCP工具"""
        return mcp_manager.get_tools_by_server("info")
    
    def _get_system_prompt(self) -> str:
        """获取信息查询系统提示词"""
        return """你是红色警戒游戏的信息管理助手。你可以使用以下工具来查询游戏信息：

主要功能：
1. 查询游戏状态（资源、电力等）
2. 查询地图信息
3. 寻路规划
4. 查询玩家基地信息
5. 查询屏幕信息
6. 检查坐标可见性和探索状态

请根据用户的指令，自主选择合适的工具来完成信息查询任务。
例如：
- "查询游戏状态" -> 使用get_game_state工具
- "查询地图信息" -> 使用map_query工具
- "为单位1寻找到(100,200)的路径" -> 使用find_path工具
- "查询玩家基地信息" -> 使用player_base_info_query工具
- "检查坐标(50,60)是否可见" -> 使用visible_query工具

请直接执行用户的指令，无需过多解释。"""

    async def intelligence_node(self, global_state: GlobalState) -> Command:
        """信息管理节点"""
        logger.info("执行信息管理")
        
        try:
            # 获取当前任务
            current_task_index = global_state.get("classify_plan_index", 0) - 1
            current_task = None
            if current_task_index >= 0 and current_task_index < len(global_state.get("classify_plan_cmds", [])):
                current_task = global_state["classify_plan_cmds"][current_task_index].task
            
            task_input = current_task or global_state["input_cmd"]
            
            # 使用LLM和工具执行任务
            result = await self.execute_with_tools(task_input)
            logger.info(f"信息管理执行结果: {result}")
            
            return Command(
                update={
                    "state": WorkflowState.EXECUTING,
                    "result": result
                },
                goto="classify"
            )
            
        except Exception as e:
            logger.error(f"信息管理执行失败: {e}")
            return Command(
                update={
                    "state": WorkflowState.ERROR,
                    "result": f"信息管理执行失败: {e}"
                },
                goto=END
            )
