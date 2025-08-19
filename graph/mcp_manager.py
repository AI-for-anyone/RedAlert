"""
MCP Client Manager using MultiServerMCPClient
"""
import os
from typing import Dict, Any, List
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.chat_models import init_chat_model
from config.config import config
from logs import get_logger

logger = get_logger("mcp_manager")

class MCPManager:
    """MCP客户端管理器，使用MultiServerMCPClient统一管理多个MCP服务器"""
    
    def __init__(self):
        self._client = None
        self._tools = None
        self._server_configs = self._get_server_configs()
    
    def _get_server_configs(self) -> Dict[str, Dict[str, Any]]:
        """从配置文件获取MCP服务器配置"""
        server_configs = {}
        
        for server_name, server_config in config.mcp_servers.items():
            # 根据传输方式构建配置
            if server_config.transport == "sse":
                # SSE 传输方式
                server_configs[server_name] = {
                    "url": f"http://{server_config.host}:{server_config.port}{server_config.path}",
                    "transport": "sse"  # langchain-mcp-adapters 使用的传输方式
                }
            else:
                # 其他传输方式
                server_configs[server_name] = {
                    "url": server_config.url,
                    "transport": server_config.transport
                }
        
        return server_configs
    
    async def initialize(self):
        """初始化MCP客户端"""
        try:
            logger.info(f"使用配置初始化MCP客户端: {list(self._server_configs.keys())}")
            self._client = MultiServerMCPClient(self._server_configs)
            self._tools = await self._client.get_tools()
            logger.info(f"成功初始化MCP客户端，获取到 {len(self._tools)} 个工具")
            
            # 打印工具信息用于调试
            for tool in self._tools:
                tool_name = tool.name if hasattr(tool, 'name') else str(tool)
                logger.debug(f"可用工具: {tool_name}")
                
            return self._tools
        except Exception as e:
            logger.error(f"初始化MCP客户端失败: {e}")
            logger.error(f"服务器配置: {self._server_configs}")
            raise
    
    def get_tools(self) -> List:
        """获取所有可用工具"""
        if self._tools is None:
            raise RuntimeError("MCP客户端未初始化，请先调用 initialize()")
        return self._tools
    
    def get_tools_by_server(self, server_name: str) -> List:
        """根据服务器名称过滤工具"""
        if self._tools is None:
            raise RuntimeError("MCP客户端未初始化，请先调用 initialize()")
        
        # 过滤属于指定服务器的工具
        server_tools = []
        for tool in self._tools:
            # 根据工具名称前缀或其他标识来判断属于哪个服务器
            tool_name = tool.name if hasattr(tool, 'name') else str(tool)
            if self._is_tool_from_server(tool_name, server_name):
                server_tools.append(tool)
        
        return server_tools
    
    def _is_tool_from_server(self, tool_name: str, server_name: str) -> bool:
        """判断工具是否属于指定服务器"""
        # 根据工具名称模式匹配服务器
        # 从配置文件获取工具模式配置
        server_tool_patterns = config.server_tool_patterns
        
        patterns = server_tool_patterns.get(server_name, [])
        return any(pattern in tool_name.lower() for pattern in patterns)
    
    async def close(self):
        """关闭MCP客户端连接"""
        # if self._client:
        #     try:
        #         await self._client.close()
        #         logger.info("MCP客户端连接已关闭")
        #     except Exception as e:
        #         logger.error(f"关闭MCP客户端失败: {e}")

# 全局MCP管理器实例
mcp_manager = MCPManager()
