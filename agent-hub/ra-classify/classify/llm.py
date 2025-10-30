import os
import json
from dotenv import load_dotenv
from typing import Optional
from langchain_openai import ChatOpenAI
from typing import Dict

from .prompt import prompt_str

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
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "1000"))
        
        # 验证必需的配置
        if not self.api_key:
            raise ValueError("LLM_API_KEY not found in environment variables")
        if not self.api_url:
            raise ValueError("LLM_API_URL not found in environment variables")


class LLMClient:
    """LLM客户端类"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        初始化LLM客户端
        
        Args:
            config: LLM配置对象，如果为None则使用默认配置
        """
        self.config = config or LLMConfig()
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化LLM客户端"""
        try:
            self._llm = ChatOpenAI(
                model=self.config.model_name, 
                api_key=self.config.api_key, 
                base_url=self.config.api_url,
                extra_body={
                    "thinking": {
                        "type": "disabled"  # 关闭深度思考
                    }
                }
            )
            
            print(f"LLM客户端初始化成功")
            print(f"API URL: {self.config.api_url}")
            print(f"Model: {self.config.model_name}")

            self._prompt = prompt_str
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize LLM client: {str(e)}")
    
    def node(self, input:str) -> Dict[str, str]:
        messages = [
            {"role": "system", "content": self._prompt},
            {"role": "user", "content": input}
        ]

        response = self._llm.invoke(messages)

        # 简单记录token使用
        try:
            tokens = response.response_metadata.get("token_usage").get("total_tokens")
        except Exception as e:
            print(f"记录token使用失败: {e}")
            tokens = 0
        
        print("tokens: {tokens}")

        # 解析 JSON 响应
        try:
            task = self._parse_classify_response(response.content)
        except ValueError as e:
            print(f"分类解析错误: {e}")
            print(f"原始响应: {response.content}")
            raise e

        return task

    def _parse_classify_response(self, response_content: str)->Dict[str, str]:
        """解析分类响应的 JSON 格式"""
        try:
            # 尝试直接解析 JSON
            task = json.loads(response_content)
            
            # 验证格式

            if not isinstance(task, dict) or "assistant" not in task or "task" not in task:
                raise ValueError("任务格式不正确，缺少 assistant 或 task 字段")
            
            return task
            
        except json.JSONDecodeError:
            raise ValueError("未找到有效的 JSON 结构")
                    

        


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