import os
import json
from dotenv import load_dotenv
from typing import Optional
from langchain_openai import ChatOpenAI
from typing import List

from .prompt import llm_prompt
from .base import BaseNode
from .mcp_cli import mcp_manager

class LLMConfig:
    """LLM配置类，从.env文件读取配置信息"""
    
    def __init__(self, env_path: str = ".env"):
        """
        初始化LLM配置
        
        Args:
            env_path: .env文件路径，默认为当前目录下的.env
        """
        # 加载.env文件
        load_dotenv(env_path)
        
        # 从环境变量读取配置
        self.api_key = os.getenv("LLM_API_KEY")
        self.api_url = os.getenv("LLM_API_URL")
        self.model_name = os.getenv("LLM_MODEL_NAME", "gpt-3.5-turbo")
        
        # 验证必需的配置
        if not self.api_key:
            raise ValueError("LLM_API_KEY not found in environment variables")
        if not self.api_url:
            raise ValueError("LLM_API_URL not found in environment variables")


class LLMClient(BaseNode):
    """LLM客户端类"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        初始化LLM客户端
        
        Args:
            config: LLM配置对象，如果为None则使用默认配置
        """
        self.node_name = "ai_assistant_llm"
        self.config = config or LLMConfig()
        self._client = None
        super().__init__("ai_assistant")
    
    async def _initialize_client(self):
        try:
            await mcp_manager.initialize(
                enable_tools= ["query_actor", "get_actor_by_id", "update_actor", "map_query", "screen_info_query", "player_base_info_query", "visible_query", "explorer_query", "unit_attribute_query"]            
            )
        except Exception as e:
            print(f"{self.node_name} 节点初始化失败: {e}")

        self.initialize(
            self.config.model_name,
            self.config.api_key,
            self.config.api_url
        )
    
    def _get_node_tools(self) -> List:
        """获取信息查询相关的MCP工具"""
        return mcp_manager.get_tools()

    def _get_system_prompt(self) -> str:
        return llm_prompt
    
    async def node(self, task_input: str) -> str:
        print("执行信息查询")

        # 使用LLM和工具执行任务
        try:
            result = await self.execute_with_tools(task_input)
            print(f"信息查询执行结果: {result}")
            return f"{self.node_name} result: {result}"

        except Exception as e:
            print(f"信息查询执行失败: {e}")
            return f"{self.node_name} error: {e}"

def initialize_llm(env_path: str = ".env") -> LLMClient:
    """
    初始化LLM客户端的便捷函数
    
    Args:
        env_path: .env文件路径
        
    Returns:
        初始化的LLM客户端
    """
    config = LLMConfig(env_path)
    return LLMClient(config)

# 全局LLM客户端实例
_llm_client: Optional[LLMClient] = None

def get_llm_client() -> LLMClient:
    """
    获取全局LLM客户端实例
    
    Returns:
        LLM客户端实例
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = initialize_llm()
    return _llm_client
