from typing import List
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.types import Command
from langgraph.graph import END
from .state import GlobalState, WorkflowState
from .base_node import BaseNode
from .mcp_manager import mcp_manager
from config.config import WorkflowType, config
from logs import get_logger
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from prompt import unit_control_prompt
from typing import Any
import json

logger = get_logger("unit_control")

class UnitControlNode(BaseNode):
    def __init__(self):
        super().__init__("unit_control", WorkflowType.UNIT_CONTROL)

    async def initialize(self):
        """初始化节点"""
        try:
            # 从配置获取LLM配置
            llm_config = config.get_llm_config(self.workflow_type)
            if not llm_config:
                raise ValueError(f"未找到 {self.workflow_type.value} 的LLM配置")

            self.prompt_params = config._prompt_params()
            
            # 初始化LLM
            self._model = ChatOpenAI(
                model=llm_config.model, 
                api_key=llm_config.api_key, 
                base_url=llm_config.base_url,
                extra_body={
                    "thinking": {
                        "type": "disabled"  # 关闭深度思考
                    }
                }
            )
            
            # 获取相关工具
            self._tools = self._get_node_tools()
            
            if self._tools:
                # 绑定工具到模型
                self._model_with_tools = self._model.bind_tools(self._tools)
                # 创建工具节点
                self._tool_node = ToolNode(self._tools)
                logger.info(f"{self.node_name} 节点初始化成功，使用模型 {llm_config.model}，绑定 {len(self._tools)} 个工具")
                logger.debug(f"{self.node_name} 节点工具列表: {[tool.name for tool in self._tools]}")
            else:
                self._model_with_tools = self._model
                logger.info(f"{self.node_name} 节点初始化成功，使用模型 {llm_config.model}，无工具绑定")
                
        except Exception as e:
            logger.error(f"{self.node_name} 节点初始化失败: {e}")
            raise

    def _get_node_tools(self) -> List:
        """获取单位控制和战斗相关的MCP工具"""
        unit_tools = mcp_manager.get_tools_by_server("unit")
        fight_tools = mcp_manager.get_tools_by_server("fight")
        base_tools = mcp_manager.get_tools_by_server("base")
        return unit_tools + fight_tools + base_tools
    
    def _get_system_prompt(self) -> str:
        """获取单位控制系统提示词"""
        return ""

    async def _get_system_prompt_async(self) -> str:
        """异步获取包含实时信息的系统提示词"""
        def _get_tool(name: str) -> BaseTool:
            for tool in self._tools:
                if tool.name == name:
                    return tool
            return None
        
        map_tool, unit_tool = _get_tool("map_query"), _get_tool("unit_info_query")
        if map_tool is None or unit_tool is None:
            logger.warning("未找到 map_query 或 unit_info_query 工具，使用默认提示词")
            return self._get_system_prompt()
        
        try:
            map_info = await map_tool.ainvoke({})
            unit_status = await unit_tool.ainvoke({})
        except Exception as e:
            logger.error(f"获取工具信息失败: {e}")
            return self._get_system_prompt()

        prompt = unit_control_prompt.format(
            map_info = map_info,
            unit_status = unit_status,
            ALL_ACTORS = self.prompt_params["ALL_ACTORS"],
            ALL_DIRECTIONS = self.prompt_params["ALL_DIRECTIONS"],
            ALL_GROUPS = self.prompt_params["ALL_GROUPS"],
            ALL_BUILDINGS = self.prompt_params["ALL_BUILDINGS"],
            ALL_UNITS = self.prompt_params["ALL_UNITS"] 
        )
        
        logger.debug(f"单位控制系统提示词: {prompt}")   
        return prompt
    
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


    async def unit_control_node(self, global_state: GlobalState) -> GlobalState:
        """单位控制节点"""
        logger.info("执行单位控制-start")
        
        try:
            # 获取当前任务
            current_task_index = global_state.get("classify_plan_index", 1) - 1
            current_task = None
            if current_task_index >= 0 and current_task_index < len(global_state.get("classify_plan_cmds", [])):
                current_task = global_state["classify_plan_cmds"][current_task_index].task
            
            logger.info(f"单位控制任务: {current_task}")
            
            # 使用LLM和工具执行任务
            result = await self.execute_with_tools_with_base_info(current_task)
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
