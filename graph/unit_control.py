from typing import List
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
        return unit_tools + fight_tools
    
    def _get_system_prompt(self) -> str:
        """获取单位控制系统提示词"""
        return unit_control_prompt.format(
            map_info = "",
            unit_status = ""
        )

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
            result = await self.execute_with_tools(current_task)
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
