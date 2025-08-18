from typing import List
from langgraph.types import Command
from langgraph.graph import END
from .state import GlobalState, WorkflowState
from .base_node import BaseNode
from .mcp_manager import mcp_manager
from config.config import WorkflowType
from logs import get_logger

logger = get_logger("production")

class ProductionNode(BaseNode):
    def __init__(self):
        super().__init__("production", WorkflowType.PRODUCTION)

    def _get_node_tools(self) -> List:
        """获取生产相关的MCP工具"""
        return mcp_manager.get_tools_by_server("produce")
    
    def _get_system_prompt(self) -> str:
        """获取生产管理系统提示词"""
        return """你是红色警戒游戏的生产管理助手。你可以使用以下工具来管理单位和建筑的生产：

主要功能：
1. 生产单位和建筑
2. 查询生产队列状态
3. 检查单位是否可生产
4. 管理生产队列（暂停、继续、取消）
5. 确保建筑存在后再生产

请根据用户的指令，自主选择合适的工具来完成生产管理任务。
例如：
- "生产5个步兵" -> 使用produce工具
- "查询步兵队列" -> 使用query_production_queue工具
- "检查是否能生产坦克" -> 使用can_produce工具
- "暂停生产" -> 使用manage_production工具

请直接执行用户的指令，无需过多解释。"""

    async def production_node(self, global_state: GlobalState) -> Command:
        """生产管理节点"""
        logger.info("执行生产管理")
        
        try:
            # 获取当前任务
            current_task_index = global_state.get("classify_plan_index", 0) - 1
            current_task = None
            if current_task_index >= 0 and current_task_index < len(global_state.get("classify_plan_cmds", [])):
                current_task = global_state["classify_plan_cmds"][current_task_index].task
            
            task_input = current_task or global_state["input_cmd"]
            
            # 使用LLM和工具执行任务
            result = await self.execute_with_tools(task_input)
            logger.info(f"生产管理执行结果: {result}")
            
            return Command(
                update={
                    "state": WorkflowState.EXECUTING,
                    "result": result
                },
                goto="classify"
            )
            
        except Exception as e:
            logger.error(f"生产管理执行失败: {e}")
            return Command(
                update={
                    "state": WorkflowState.ERROR,
                    "result": f"生产管理执行失败: {e}"
                },
                goto=END
            )
