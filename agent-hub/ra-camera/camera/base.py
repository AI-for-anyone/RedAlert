"""
Base node class for LLM-powered nodes with MCP tool integration
"""
import time
from typing import Dict, Any, List
from abc import ABC, abstractmethod
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode

class BaseNode(ABC):
    """基础节点类，提供LLM和MCP工具集成"""
    def __init__(self, node_name: str):
        self.node_name = node_name
        self._model = None
        self._model_with_tools = None
        self._tool_node = None
        self._tools = []
    
    async def initialize(
        self, 
        model: str, 
        api_key: str, 
        base_url: str
    ):
        """初始化节点"""
        try:
            # 从配置获取LLM配置
            llm_config = config.get_llm_config(self.workflow_type)
            
            # 初始化LLM
            self._model = ChatOpenAI(
                model=model, 
                api_key=api_key, 
                base_url=base_url,
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
                print(f"{self.node_name} 节点初始化成功，使用模型 {llm_config.model}，绑定 {len(self._tools)} 个工具")
            else:
                self._model_with_tools = self._model
                print(f"{self.node_name} 节点初始化成功，使用模型 {llm_config.model}，无工具绑定")

            self.tokens_usage = 0
                
        except Exception as e:
            print(f"{self.node_name} 节点初始化失败: {e}")
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
        
        response = await self._model_with_tools.ainvoke(messages)
        
        # 简单记录token使用
        try:
            tokens = response.response_metadata.get("token_usage").get("total_tokens")
        except Exception as e:
            print(f"记录token使用失败: {e}")
            tokens = 0
        
        self.tokens_usage += tokens
        print(f"{self.node_name} tokens_usage: {self.tokens_usage}")
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
