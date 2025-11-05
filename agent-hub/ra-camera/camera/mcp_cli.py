"""
MCP Client Manager using MultiServerMCPClient
"""
from typing import Final, List, Any, Dict
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel, create_model

MCP_DEFAULT_TRANSPORT: Final[str] = "streamable_http"

class MCPManager:
    """MCP客户端管理器，使用MultiServerMCPClient统一管理多个MCP服务器"""
    
    def __init__(self, host: str = "localhost"):
        self._client = None
        self._tools = None
        self._raw_tools = None
        self._host = host
        self._path = "/mcp"
        self._server_configs = {
            "camera": {
                "url": f"http://{self._host}:8000{self._path}",
                "transport": MCP_DEFAULT_TRANSPORT
            },
            # 战斗控制 MCP 服务器
            "fight": {
                "url": f"http://{self._host}:8001{self._path}",
                "transport": MCP_DEFAULT_TRANSPORT
            },
            # 信息查询 MCP 服务器
            "info": {
                "url": f"http://{self._host}:8002{self._path}",
                "transport": MCP_DEFAULT_TRANSPORT
            },
            # 生产管理 MCP 服务器
            "produce": {
                "url": f"http://{self._host}:8003{self._path}",
                "transport": MCP_DEFAULT_TRANSPORT
            },
            # 单位控制 MCP 服务器
            "unit": {
                "url": f"http://{self._host}:8004{self._path}",
                "transport": MCP_DEFAULT_TRANSPORT
            }
        }
    
    async def initialize(self, enable_tools: List[str]):
        """初始化MCP客户端"""
        try:
            print(f"使用配置初始化MCP客户端: {list(self._server_configs.keys())}")
            print(f"服务器配置详情: {self._server_configs}")
            
            self._client = MultiServerMCPClient(self._server_configs)
            print("MultiServerMCPClient 创建成功，开始获取工具...")
            
            self._raw_tools = await self._client.get_tools()
            print(f"获取到原始工具数量: {len(self._raw_tools)}")
            
            self._tools = []
            
            # 过滤
            for tool in self._raw_tools:
                tool_name = tool.name if hasattr(tool, 'name') else str(tool)
                if tool_name in enable_tools:
                    self._tools.append(tool)

            print(f"成功初始化MCP客户端，获取到 {len(self._tools)} 个工具")
            return self._tools
        except Exception as e:
            print(f"初始化MCP客户端失败: {e}")
            print(f"错误类型: {type(e).__name__}")
            print(f"服务器配置: {self._server_configs}")
            import traceback
            traceback.print_exc()
            raise
    
    def get_tools(self) -> List:
        """获取所有可用工具"""
        if self._tools is None:
            raise RuntimeError("MCP客户端未初始化，请先调用 initialize()")
        return self._tools

# 全局MCP管理器实例
mcp_manager = MCPManager("172.19.160.1")