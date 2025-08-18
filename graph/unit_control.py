from typing import List
from langgraph.types import Command
from langgraph.graph import END
from .state import GlobalState, WorkflowState
from .base_node import BaseNode
from .mcp_manager import mcp_manager
from config.config import WorkflowType
from logs import get_logger

logger = get_logger("unit_control")

class UnitControlNode(BaseNode):
    def __init__(self):
        super().__init__("unit_control", WorkflowType.UNIT_CONTROL)

    def _get_node_tools(self) -> List:
        """获取单位控制和战斗相关的MCP工具"""
        unit_tools = mcp_manager.get_tools_by_server("unit")
        fight_tools = mcp_manager.get_tools_by_server("fight")
        return unit_tools + fight_tools
    
    def _get_system_prompt(self) -> str:
        """获取单位控制系统提示词"""
        return """你是红色警戒游戏的单位控制助手。你可以使用以下工具来控制游戏中的单位：

主要功能：
1. 移动单位到指定坐标
2. 攻击指定目标
3. 查询和选择单位
4. 占领建筑
5. 修复单位
6. 停止单位行动
7. 编组和部署单位

请根据用户的指令，自主选择合适的工具来完成单位控制任务。
例如：
- "移动单位1到坐标(100,200)" -> 使用move_units工具
- "单位1攻击目标2" -> 使用attack_target工具
- "查询屏幕内的盟军步兵" -> 使用query_actor工具
- "修复单位1" -> 使用repair_units工具
- "停止所有单位" -> 使用stop_units工具

请直接执行用户的指令，无需过多解释。"""

    async def unit_control_node(self, global_state: GlobalState) -> Command:
        """单位控制节点"""
        logger.info("执行单位控制")
        
        try:
            # 获取当前任务
            current_task_index = global_state.get("classify_plan_index", 0) - 1
            current_task = None
            if current_task_index >= 0 and current_task_index < len(global_state.get("classify_plan_cmds", [])):
                current_task = global_state["classify_plan_cmds"][current_task_index].task
            
            task_input = current_task or global_state["input_cmd"]
            
            # 使用LLM和工具执行任务
            result = await self.execute_with_tools(task_input)
            logger.info(f"单位控制执行结果: {result}")
            
            return Command(
                update={
                    "state": WorkflowState.EXECUTING,
                    "result": result
                },
                goto="classify"
            )
            
        except Exception as e:
            logger.error(f"单位控制执行失败: {e}")
            return Command(
                update={
                    "state": WorkflowState.ERROR,
                    "result": f"单位控制执行失败: {e}"
                },
                goto=END
            )
