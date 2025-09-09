from typing import List
from langgraph.types import Command
from langgraph.graph import END
from .state import GlobalState, WorkflowState
from .base_node import BaseNode
from .mcp_manager import mcp_manager
from config.config import WorkflowType
from logs import get_logger
from prompt import ai_assistant_prompt
from langchain_core.tools import BaseTool
from dataclasses import dataclass

# 玩家基础信息查询返回结构体，Cash 和 Resources 的和是玩家持有的金钱，Power 是剩余电力。
@dataclass
class PlayerBaseInfo:
    Cash: int  # 玩家持有的现金。
    Resources: int  # 玩家持有的资源。
    Power: int  # 玩家当前剩余电力。
    PowerDrained: int  # 玩家消耗的电力。
    PowerProvided: int  # 玩家提供的电力。

logger = get_logger("ai_assistant")

class AIAssistantNode(BaseNode):
    def __init__(self):
        super().__init__("ai_assistant", WorkflowType.AI_ASSISTANT)

    def _get_node_tools(self) -> List:
        """获取生产相关的MCP工具"""
        return mcp_manager.get_tools_by_server("ai_assistant")
    
    def _get_system_prompt(self) -> str:
        """获取提示词"""
        pt = ai_assistant_prompt.format(
            unit_status="",
            resource="",
            power=""
        )
        return pt
    
    async def _get_system_prompt_async(self) -> str:
        import json
        """获取提示词"""
        def _get_tool(name: str) -> BaseTool:
            for tool in self._tools:
                if tool.name == name:
                    return tool
            return None
        
        unit_tool = _get_tool("unit_info_query")
        base_tool = _get_tool("player_base_info_query")
        produce_tool = _get_tool("query_production_queue")
        if  unit_tool is None:
            logger.warning("未找到 unit_info_query 工具，使用默认提示词")
            return self._get_system_prompt()
        if base_tool is None:
            logger.warning("未找到 player_base_info_query 工具，使用默认提示词")
            return self._get_system_prompt()
        if produce_tool is None:
            logger.warning("未找到 query_production_queue 工具，使用默认提示词")
            return self._get_system_prompt()
        logger.info(f"工具ready")
        
        try:
            unit_status = await unit_tool.ainvoke({})
            base_info = await base_tool.ainvoke({})
            
            # 获取各种生产队列信息
            building_queue = await produce_tool.ainvoke({"queue_type": "Building"})
            infantry_queue = await produce_tool.ainvoke({"queue_type": "Infantry"})
            vehicle_queue = await produce_tool.ainvoke({"queue_type": "Vehicle"})
            aircraft_queue = await produce_tool.ainvoke({"queue_type": "Aircraft"})
        except Exception as e:
            logger.error(f"获取工具信息失败: {e}")
            return self._get_system_prompt()

        # 写的是shit
        unit = dict()
        unit_status = json.loads(unit_status)
        our_unit = unit_status["our"]
        for i in our_unit.keys():
            unit[i] = our_unit[i].get("count", 0)

        infantry_unit = json.loads(infantry_queue)
        for i in infantry_unit.keys():
            if i not in unit.keys():
                unit[i] = 0
            unit[i] += infantry_unit[i]
        
        vehicle_unit = json.loads(vehicle_queue)
        for i in vehicle_unit.keys():
            if i not in unit.keys():
                unit[i] = 0
            unit[i] += vehicle_unit[i]
        
        aircraft_unit = json.loads(aircraft_queue)
        for i in aircraft_unit.keys():
            if i not in unit.keys():
                unit[i] = 0
            unit[i] += aircraft_unit[i]
            

        logger.info(f"unit_status: {unit}")
        logger.info(f"base_info: {base_info}")
        logger.info(f"building_queue: {building_queue}")

        # 反序列化base_info为PlayerBaseInfo对象
        
        # 如果base_info是字符串，先解析JSON
        if isinstance(base_info, str):
            base_info_dict = json.loads(base_info)
        else:
            base_info_dict = base_info
            
        player_info = PlayerBaseInfo(
            Cash=base_info_dict.get("cash", 0),
            Resources=base_info_dict.get("resources", 0), 
            Power=base_info_dict.get("power", 0),
            PowerDrained=base_info_dict.get("powerDrained", 0),
            PowerProvided=base_info_dict.get("powerProvided", 0)
        )
        
        logger.debug(f"反序列化后的玩家信息: Cash={player_info.Cash}, Resources={player_info.Resources}, Power={player_info.Power}, PowerDrained={player_info.PowerDrained}, PowerProvided={player_info.PowerProvided}")

        pt = ai_assistant_prompt.format(
            unit_status=unit,
            resource=player_info.Resources,
            power=player_info.Power,
            building_queue=building_queue
        )

        logger.debug(f"AI 助手提示词: {pt}")
        return pt

    async def ai_assistant_node(self, global_state: GlobalState) -> Command:
        """AI 助手节点"""
        logger.info("执行AI 助手")
        
        try:
            loop_times = 0
            while True:
                # 获取当前任务
                task_input = "帮助玩家进行运营"
                
                # 使用LLM和工具执行任务
                result = await self.execute_with_tools_with_base_info(task_input, max_iterations=1)
                logger.info(f"AI 助手执行结果: {result}")
                loop_times += 1
                logger.info(f"AI 助手循环次数: {loop_times}")
                
            
        except Exception as e:
            logger.error(f"AI 助手执行失败: {e}")

        return Command(
            update={
                "state": WorkflowState.ERROR,
                "result": f"AI 助手执行结束"
            },
            goto=END
        )

    async def execute_with_tools_with_base_info(self, user_input: str, max_iterations: int = 5) -> str:
        """使用工具执行任务"""
        _sys_prompt = await self._get_system_prompt_async()
        # 构建初始消息
        messages = [
            {"role": "system", "content": _sys_prompt},
            {"role": "user", "content": user_input}
        ]
        
        iteration = 0
        while iteration < max_iterations:
            # 调用模型
            model_result = await self._call_model(messages)
            messages.extend(model_result["messages"])
            
            # 检查是否需要调用工具
            if self._should_continue(messages) == "tools":
                # 调用工具
                tool_result = await self._call_tools(messages)
                messages.extend(tool_result.get("messages", []))
                iteration += 1
            else:
                break
        
        # 返回最后的响应
        return messages[-1].content if messages else "执行完成"
