from typing import List
from langgraph.types import Command
from langgraph.graph import END
from .state import GlobalState, WorkflowState
from .base_node import BaseNode
from .mcp_manager import mcp_manager
from config.config import WorkflowType
from logs import get_logger

logger = get_logger("camera")

class CameraNode(BaseNode):
    def __init__(self):
        super().__init__("camera", WorkflowType.CAMERA_CONTROL)

    def _get_node_tools(self) -> List:
        """获取相机控制相关的MCP工具"""
        return mcp_manager.get_tools_by_server("camera")
    
    def _get_system_prompt(self) -> str:
        """获取相机控制系统提示词"""
        return """你是红色警戒游戏的相机控制助手。你可以使用以下工具来控制游戏视角：

主要功能：
1. 移动相机到指定坐标
2. 按方向移动相机
3. 跟随指定单位/Actor

请根据用户的指令，自主选择合适的工具来完成相机控制任务。
例如：
- "移动相机到坐标(100, 200)" -> 使用camera_move_to工具
- "向北移动相机50距离" -> 使用camera_move_dir工具
- "跟随Actor 123" -> 使用move_camera_to工具

请直接执行用户的指令，无需过多解释。"""

    async def camera_node(self, global_state: GlobalState) -> Command:
        """相机控制节点"""
        logger.info("执行相机控制")
        
        try:
            # 获取当前任务
            current_task_index = global_state.get("classify_plan_index", 0) - 1
            current_task = None
            if current_task_index >= 0 and current_task_index < len(global_state.get("classify_plan_cmds", [])):
                current_task = global_state["classify_plan_cmds"][current_task_index].task
            
            task_input = current_task or global_state["input_cmd"]
            
            # 使用LLM和工具执行任务
            result = await self.execute_with_tools(task_input)
            logger.info(f"相机控制执行结果: {result}")
            
            return Command(
                update={
                    "state": WorkflowState.EXECUTING,
                    "result": result
                },
                goto="classify"
            )
            
        except Exception as e:
            logger.error(f"相机控制执行失败: {e}")
            return Command(
                update={
                    "state": WorkflowState.ERROR,
                    "result": f"相机控制执行失败: {e}"
                },
                goto=END
            )