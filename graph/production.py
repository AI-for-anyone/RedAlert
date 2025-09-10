from re import M
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
        return f"""你是红色警戒游戏的生产管理助手。你可以使用以下工具来管理单位和建筑的生产：

建筑队列生产成本:
| 单位 | 金钱 | 时间 | 电力 |
| --- | --- | --- | --- |
| 电厂 | 150 | 2 | 100 |
| 兵营 | 250 | 3 | -20 |
| 矿场 | 700 | 9 | -30 |
| 车间 | 1000 | 12 | -30 |
| 雷达 | 750 | 9 | -40 |
| 维修中心 | 600 | 8 | -30 |
| 核电 | 250 | 3 | 200 |
| 机场 | 200 | 3 | 200 |
| 科技中心 | 750 | 9 | -100 |
防御队列生产成本:
| 单位 | 金钱 | 时间 | 电力 |
| --- | --- | --- | --- |
| 火焰塔 | 300 | 4 | -20 |
| 电塔 | 600 | 8 | -100 |
| 防空塔 | 350 | 5 | -40 |
步兵队列生产成本:
| 单位 | 金钱 | 时间 | 电力 |
| --- | --- | --- | --- |
| 步兵 | 50 | 1 | 0 |
| 火箭兵 | 150 | 2 | 0 |
载具队列生产成本:
| 单位 | 金钱 | 时间 | 电力 |
| --- | --- | --- | --- |
| 矿车 | 550 | 7 | 0 |
| 防空车 | 300 | 4 | 0 |
| 重坦 | 575 | 7 | 0 |
| v2 | 450 | 6 | 0 |
| 猛犸 | 1000 | 12 | 0 |
飞机队列生产成本:
| 单位 | 金钱 | 时间 | 电力 |
| --- | --- | --- | --- |
| 雅克 | 675 | 9 | 0 |
| 米格 | 1000 | 12 | 0 |

主要功能：
1. 生产单位和建筑
2. 查询生产队列状态
3. 检查单位是否可生产
4. 管理生产队列（暂停、继续、取消）
5. 查询当前资源信息

请根据用户的指令，自主选择合适的工具来完成生产管理任务。
例如：
- "生产5个步兵" -> 使用produce工具
- "确保生产核电" -> 使用ensure_can_produce_unit工具
- "查询步兵队列" -> 使用query_production_queue工具
- "检查是否能生产坦克" -> 使用can_produce工具
- "暂停生产" -> 使用manage_production工具
- "部署基地车" -> 使用deploy_mcv_and_wait工具

约束:
- 不要模拟执行过程，执行工具调用
- 只有提及"确保"时才使用"ensure_"系列工具"""

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
            result = await self.execute_with_tools(task_input, max_iterations=1)
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
