import os
import json
from dotenv import load_dotenv
from typing import Optional, Final, Tuple, List, Mapping
from langchain_core.tools import BaseTool
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from types import MappingProxyType

from .prompt import llm_prompt
from .base import BaseNode
from .mcp_cli import mcp_manager

# Prompt 参数常量（不可变）
ALL_TOWER: Final[Tuple[str, ...]] = ("火焰塔", "特斯拉塔", "防空塔")
ALL_ACTORS: Final[Tuple[str, ...]] = ("敌方", "己方", "中立")
ALL_DIRECTIONS: Final[Tuple[str, ...]] = ("左上", "上", "右上", "左", "右", "左下", "下", "右下")
ALL_GROUPS: Final[Tuple[str, ...]] = tuple(str(i) for i in range(10))
ALL_BUILDINGS: Final[Tuple[str, ...]] = (
    "建造厂", "发电厂", "兵营", "矿场", "战车工厂", "雷达站", "维修厂", "核电站", "科技中心", "空军基地"
) + ALL_TOWER
ALL_UNITS: Final[Tuple[str, ...]] = (
    "步兵", "火箭兵", "防空车", "重型坦克", "V2火箭发射车", "超重型坦克", "雅克战机", "米格战机", "采矿车"
)

PROMPT_PARAMS: Final[Mapping[str, Tuple[str, ...]]] = MappingProxyType({
    "ALL_ACTORS": ALL_ACTORS,
    "ALL_DIRECTIONS": ALL_DIRECTIONS,
    "ALL_GROUPS": ALL_GROUPS,
    "ALL_BUILDINGS": ALL_BUILDINGS,
    "ALL_UNITS": ALL_UNITS,
})

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
        self.node_name = "unit_llm"
        self.config = config or LLMConfig()
        self._client = None
        super().__init__("unit")
    
    async def _initialize_client(self):
        try:
            await mcp_manager.initialize(
                enable_tools= ["select_units", "form_group", 
                "move_units_by_location", "move_units_by_direction", 
                "move_units_by_path", "move_units_by_location_and_wait", 
                "attack_target", "can_attack_target", "occupy_units", "repair_units", 
                "stop", "find_path", "set_rally_point"]            
            )
        except Exception as e:
            print(f"{self.node_name} 节点初始化失败: {e}")

        await self.initialize(
            self.config.model_name,
            self.config.api_key,
            self.config.api_url
        )

    async def initialize(self,
        model: str,
        api_key: str,
        base_url: str
    ):
        """初始化节点"""
        try:
            # 从配置获取LLM配置

            self.prompt_params = PROMPT_PARAMS
            
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
                print(f"{self.node_name} 节点初始化成功，使用模型 {model}，绑定 {len(self._tools)} 个工具")
                print(f"{self.node_name} 节点工具列表: {[tool.name for tool in self._tools]}")
            else:
                self._model_with_tools = self._model
                print(f"{self.node_name} 节点初始化成功，使用模型 {model}，无工具绑定")
                
        except Exception as e:
            print(f"{self.node_name} 节点初始化失败: {e}")
            raise

    
    def _get_node_tools(self) -> List:
        """获取单位控制相关的MCP工具"""
        return mcp_manager.get_tools()

    def _get_system_prompt(self) -> str:
        return ""
    
    async def _get_system_prompt_async(self) -> str:
        """异步获取包含实时信息的系统提示词"""
        def _get_tool(name: str) -> BaseTool:
            for tool in self._tools:
                if tool.name == name:
                    return tool
            return None
        
        map_tool, unit_tool, control_point_tool = _get_tool("map_query"), _get_tool("unit_info_query"), _get_tool("control_point_query")
        if map_tool is None or unit_tool is None or control_point_tool is None:
            print("未找到 map_query 或 unit_info_query 工具，使用默认提示词")
            return self._get_system_prompt()
        
        try:
            map_info = await map_tool.ainvoke({})
            unit_status = await unit_tool.ainvoke({})
            control_points = await control_point_tool.ainvoke({})
        except Exception as e:
            print(f"获取工具信息失败: {e}")
            return self._get_system_prompt()

        control_points = json.loads(control_points)
        cps = []
        for cp in control_points.keys():
            cps.append({"x": control_points[cp][0], "y": control_points[cp][1]})
        cps.sort(key=lambda x: (x["x"], x["y"]))

        control_points_info = ""
        index = 1
        for cp in cps:
            control_points_info += f"据点{index}: ({cp["x"]}, {cp["y"]})\n"
            index += 1

        print(f"控制点信息: {control_points_info}")

        prompt = llm_prompt.format(
            map_info = map_info,
            unit_status = unit_status,
            control_point_info = control_points_info,
            ALL_ACTORS = self.prompt_params["ALL_ACTORS"],
            ALL_DIRECTIONS = self.prompt_params["ALL_DIRECTIONS"],
            ALL_GROUPS = self.prompt_params["ALL_GROUPS"],
            ALL_BUILDINGS = self.prompt_params["ALL_BUILDINGS"],
            ALL_UNITS = self.prompt_params["ALL_UNITS"] 
        )
        
        print(f"单位控制系统提示词: {prompt}")   
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


    async def node(self, input: str) -> str:
        """单位控制节点"""
        print("执行单位控制-start")
        
        try:
            # 使用LLM和工具执行任务
            result = await self.execute_with_tools_with_base_info(input)
            print(f"单位控制执行结果: {result}")
            
            return result
            
        except Exception as e:
            print(f"单位控制执行失败: {e}")
            return f"单位控制执行失败: {e}"

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
