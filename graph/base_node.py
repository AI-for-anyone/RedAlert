"""
Base node class for LLM-powered nodes with MCP tool integration
"""
import os
import time
from typing import Dict, Any, List
from abc import ABC, abstractmethod
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from langgraph.graph import MessagesState
from .mcp_manager import mcp_manager
from .state import GlobalState, WorkflowState
from .token_logger import token_logger
from config.config import config, WorkflowType
from logs import get_logger

logger = get_logger("base_node")

class BaseNode(ABC):
    """基础节点类，提供LLM和MCP工具集成"""
    
    def __init__(self, node_name: str, workflow_type: WorkflowType = None):
        self.node_name = node_name
        self.workflow_type = workflow_type or self._get_workflow_type_by_name(node_name)
        self._model = None
        self._model_with_tools = None
        self._tool_node = None
        self._tools = []
        
    def _get_workflow_type_by_name(self, node_name: str) -> WorkflowType:
        """根据节点名称获取工作流类型"""
        mapping = {
            "production": WorkflowType.PRODUCTION,
            "camera": WorkflowType.CAMERA_CONTROL,
            "unit_control": WorkflowType.UNIT_CONTROL,
            "intelligence": WorkflowType.INTELLIGENCE
        }
        return mapping.get(node_name, WorkflowType.CLASSIFY)
    
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
            else:
                self._model_with_tools = self._model
                logger.info(f"{self.node_name} 节点初始化成功，使用模型 {llm_config.model}，无工具绑定")
                
        except Exception as e:
            logger.error(f"{self.node_name} 节点初始化失败: {e}")
            raise
    
    @abstractmethod
    def _get_node_tools(self) -> List:
        """获取节点相关的工具，子类需要实现"""
        pass
    
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """获取系统提示词，子类需要实现"""
        pass
    
    def _should_continue(self, messages) -> str:
        """判断是否需要继续调用工具"""
        if not messages:
            return "end"
        
        last_message = messages[-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        return "end"
    
    async def _call_model(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """调用模型"""
        if self._model_with_tools is None:
            raise RuntimeError(f"{self.node_name} 节点未初始化")
        
        start_time = time.time()
        response = await self._model_with_tools.ainvoke(messages)
        duration_ms = (time.time() - start_time) * 1000
        
        # 简单记录token使用
        try:
            tokens = response.response_metadata.get("token_usage").get("total_tokens")
        except Exception as e:
            logger.error(f"记录token使用失败: {e}")
            tokens = 0
        
        token_logger.log_usage(self.node_name, "llm", tokens, duration_ms)
        return {"messages": [response]}
    
    async def _call_tools(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """调用工具"""
        if self._tool_node is None:
            raise RuntimeError(f"{self.node_name} 节点工具未初始化")
        
        # 构建消息状态
        state = {"messages": messages}
        logger.info(f"调用工具: {messages[-1].tool_calls}")
        result = await self._tool_node.ainvoke(state)
        logger.info(f"调用工具结果: {result}")
        return result
    
    async def execute_with_tools(self, user_input: str, max_iterations: int = 5) -> str:
        """使用工具执行任务"""
        # 构建初始消息
        messages = [
            {"role": "system", "content": self._get_system_prompt()},
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
