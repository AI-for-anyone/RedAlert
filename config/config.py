"""
RedAlert AI Copilot 配置文件
包含 LLM 配置、Prompt 配置、MCP 服务器配置等
"""
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from typing import Any

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

class WorkflowType(Enum):
    """工作流类型枚举"""
    CLASSIFY = "classify"           # 任务分类
    CAMERA_CONTROL = "camera"       # 地图视角控制
    PRODUCTION = "production"       # 生产管理
    UNIT_CONTROL = "unit_control"   # 单位控制
    RESOURCE = "resource"           # 资源管理
    INTELLIGENCE = "intelligence"   # 信息管理

@dataclass
class LLMConfig:
    """LLM 配置"""
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 30

@dataclass
class PromptConfig:
    """Prompt 配置"""
    name: str
    file_path: Path
    description: str
    workflow_type: WorkflowType

@dataclass
class MCPServerConfig:
    """MCP 服务器配置"""
    name: str
    host: str = "127.0.0.1"
    port: int = 8000
    path: str = "/sse"
    transport: str = "sse"
    description: str = ""
    
    @property
    def url(self) -> str:
        """获取完整的 MCP 服务器 URL"""
        return f"http://{self.host}:{self.port}{self.path}"

class Config:
    """主配置类"""
    
    def __init__(self):
        self._load_env_vars()
        self._setup_llm_configs()
        self._setup_prompt_configs()
        self._setup_mcp_servers()
    
    def _load_env_vars(self):
        """加载环境变量"""
        # 从 .env 文件加载
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())
    
    def _setup_llm_configs(self):
        """设置 LLM 配置"""
        self.llm_configs: Dict[WorkflowType, LLMConfig] = {
            # 任务分类 - 使用快速响应的模型
            WorkflowType.CLASSIFY: LLMConfig(
                base_url=os.getenv("CLASSIFY_API_BASE", "https://api.deepseek.com"),
                api_key=os.getenv("CLASSIFY_API_KEY", ""),
                model=os.getenv("CLASSIFY_MODEL", "deepseek-chat"),
                temperature=0.1,  # 低温度，确保分类准确
                max_tokens=1024
            ),
            
            # 地图视角控制 - 需要精确的空间理解
            WorkflowType.CAMERA_CONTROL: LLMConfig(
                base_url=os.getenv("CAMERA_API_BASE", "https://api.deepseek.com"),
                api_key=os.getenv("CAMERA_API_KEY", ""),
                model=os.getenv("CAMERA_MODEL", "deepseek-chat"),
                temperature=0.3,
                max_tokens=2048
            ),
            
            # 生产管理 - 需要逻辑推理
            WorkflowType.PRODUCTION: LLMConfig(
                base_url=os.getenv("PRODUCTION_API_BASE", "https://api.deepseek.com"),
                api_key=os.getenv("PRODUCTION_API_KEY", ""),
                model=os.getenv("PRODUCTION_MODEL", "deepseek-chat"),
                temperature=0.5,
                max_tokens=3072
            ),
            
            # 单位控制 - 需要实时决策
            WorkflowType.UNIT_CONTROL: LLMConfig(
                base_url=os.getenv("UNIT_CONTROL_API_BASE", "https://api.deepseek.com"),
                api_key=os.getenv("UNIT_CONTROL_API_KEY", ""),
                model=os.getenv("UNIT_CONTROL_MODEL", "deepseek-chat"),
                temperature=0.0,
                max_tokens=8192
            ),
            
            # 信息管理 - 需要准确的信息处理
            WorkflowType.INTELLIGENCE: LLMConfig(
                base_url=os.getenv("INTELLIGENCE_API_BASE", "https://api.deepseek.com"),
                api_key=os.getenv("INTELLIGENCE_API_KEY", ""),
                model=os.getenv("INTELLIGENCE_MODEL", "deepseek-chat"),
                temperature=0.2,
                max_tokens=2048
            )
        }
    
    def _setup_prompt_configs(self):
        """设置 Prompt 配置"""
        prompt_dir = PROJECT_ROOT / "prompt"
        
        self.prompt_configs: Dict[WorkflowType, PromptConfig] = {
            WorkflowType.CLASSIFY: PromptConfig(
                name="classify_prompt",
                file_path=prompt_dir / "classify_prompt.md",
                description="任务分类提示词",
                workflow_type=WorkflowType.CLASSIFY
            ),
            
            WorkflowType.CAMERA_CONTROL: PromptConfig(
                name="camera_prompt",
                file_path=prompt_dir / "camera_prompt.md",
                description="地图视角控制提示词",
                workflow_type=WorkflowType.CAMERA_CONTROL
            ),
            
            WorkflowType.PRODUCTION: PromptConfig(
                name="production_prompt",
                file_path=prompt_dir / "production_prompt.md",
                description="生产管理提示词",
                workflow_type=WorkflowType.PRODUCTION
            ),
            
            WorkflowType.UNIT_CONTROL: PromptConfig(
                name="unit_control_prompt",
                file_path=prompt_dir / "unit_control_prompt.md",
                description="单位控制提示词",
                workflow_type=WorkflowType.UNIT_CONTROL
            ),
            
            WorkflowType.INTELLIGENCE: PromptConfig(
                name="intelligence_prompt",
                file_path=prompt_dir / "intelligence_prompt.md",
                description="信息管理提示词",
                workflow_type=WorkflowType.INTELLIGENCE
            )
        }
    
    def _setup_mcp_servers(self):
        """设置 MCP 服务器配置"""
        # MCP 服务器工具模式配置
        self.server_tool_patterns: Dict[str, List[str]] = {
            "camera": ["camera", "move_camera", "视角"],
            "fight": ["attack", "occupy", "repair", "stop", "战斗", "army"],
            "info": ["get_game_state", "map_query", "find_path", "player_base", "screen_info", "visible", "explorer"],
            "produce": ["produce", "can_produce", "query_production", "manage_production", "ensure_can_produce", "ensure_can_build", "生产", "deploy_mcv", "get_player_base_info"],
            "unit": ["move_units", "query_actor", "select_units", "form_group", "deploy_units", "单位"],
            "base": ["map_query", "unit_info_query"],
        }
        
        self.mcp_servers: Dict[str, MCPServerConfig] = {

            # 相机控制 MCP 服务器
            "camera": MCPServerConfig(
                name="camera",
                host="127.0.0.1",
                port=8000,
                path="/mcp",
                transport="streamable_http",
                description="相机控制服务器"
            ),
            # 战斗控制 MCP 服务器
            "fight": MCPServerConfig(
                name="fight",
                host="127.0.0.1",
                port=8001,
                path="/mcp",
                transport="streamable_http",
                description="战斗控制服务器"
            ),
            # 信息查询 MCP 服务器
            "info": MCPServerConfig(
                name="info",
                host="127.0.0.1",
                port=8002,
                path="/mcp",
                transport="streamable_http",
                description="游戏信息查询服务器"
            ),
            # 生产管理 MCP 服务器
            "produce": MCPServerConfig(
                name="produce",
                host="127.0.0.1",
                port=8003,
                path="/mcp",
                transport="streamable_http",
                description="生产管理服务器"
            ),
            # 单位控制 MCP 服务器
            "unit": MCPServerConfig(
                name="unit",
                host="127.0.0.1",
                port=8004,
                path="/mcp",
                transport="streamable_http",
                description="单位控制服务器"
            ),
        }
    
    def get_llm_config(self, workflow_type: WorkflowType) -> Optional[LLMConfig]:
        """获取指定工作流的 LLM 配置"""
        return self.llm_configs.get(workflow_type)
    
    def get_prompt_config(self, workflow_type: WorkflowType) -> Optional[PromptConfig]:
        """获取指定工作流的 Prompt 配置"""
        return self.prompt_configs.get(workflow_type)
    
    def get_mcp_server(self, server_name: str) -> Optional[MCPServerConfig]:
        """获取指定的 MCP 服务器配置"""
        return self.mcp_servers.get(server_name)
    
    def load_prompt(self, workflow_type: WorkflowType) -> str:
        """加载指定工作流的提示词内容"""
        prompt_config = self.get_prompt_config(workflow_type)
        if not prompt_config:
            return ""
        
        try:
            return prompt_config.file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"加载提示词失败 {prompt_config.file_path}: {e}")
            return ""
    
    def validate_config(self) -> List[str]:
        """验证配置完整性"""
        errors = []
        
        # 检查 API Key
        for workflow_type, llm_config in self.llm_configs.items():
            if not llm_config.api_key:
                errors.append(f"{workflow_type.value} LLM 缺少 API Key")
        
        # 检查提示词文件
        for workflow_type, prompt_config in self.prompt_configs.items():
            if not prompt_config.file_path.exists():
                errors.append(f"提示词文件不存在: {prompt_config.file_path}")
        
        return errors

# 全局配置实例
config = Config()

# 便捷访问函数
def get_llm_config(workflow_type: WorkflowType) -> Optional[LLMConfig]:
    """获取 LLM 配置"""
    return config.get_llm_config(workflow_type)

def get_prompt(workflow_type: WorkflowType) -> str:
    """获取提示词内容"""
    return config.load_prompt(workflow_type)

def get_mcp_server(server_name: str) -> Optional[MCPServerConfig]:
    """获取 MCP 服务器配置"""
    return config.get_mcp_server(server_name)

def get_server_tool_patterns() -> Dict[str, List[str]]:
    """获取服务器工具模式配置"""
    return config.server_tool_patterns

def list_mcp_servers() -> Dict[str, str]:
    """列出所有 MCP 服务器"""
    return {name: server.url for name, server in config.mcp_servers.items()}

def get_mcp_server_status() -> Dict[str, Dict[str, Any]]:
    """获取所有MCP服务器状态信息"""
    import requests
    status_info = {}
    
    for name, server in config.mcp_servers.items():
        try:
            response = requests.get(f"http://{server.host}:{server.port}/health", timeout=3)
            is_online = response.status_code == 200
        except:
            is_online = False
            
        status_info[name] = {
            "url": server.url,
            "host": server.host,
            "port": server.port,
            "description": server.description,
            "online": is_online
        }
    
    return status_info

def check_mcp_servers() -> List[str]:
    """检查所有MCP服务器连接状态，返回离线服务器列表"""
    offline_servers = []
    
    for name, server in config.mcp_servers.items():
        try:
            pass
            # TODO: 检查MCP服务器连接状态
            # import requests
            # response = requests.get(f"http://{server.host}:{server.port}/health", timeout=3)
            # if response.status_code != 200:
            #     offline_servers.append(f"{name} ({server.url})")
        except Exception as e:
            offline_servers.append(f"{name} ({server.url}) - {str(e)}")
    
    return offline_servers

if __name__ == "__main__":
    # 配置验证
    errors = config.validate_config()
    if errors:
        print("配置错误:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("配置验证通过")
    
    # 显示配置信息
    print("\n=== LLM 配置 ===")
    for workflow_type, llm_config in config.llm_configs.items():
        print(f"{workflow_type.value}: {llm_config.model} (temp={llm_config.temperature})")
    
    print("\n=== MCP 服务器 ===")
    for name, server in config.mcp_servers.items():
        print(f"{name}: {server.url}")
    
    print("\n=== 提示词文件 ===")
    for workflow_type, prompt_config in config.prompt_configs.items():
        exists = "✓" if prompt_config.file_path.exists() else "✗"
        print(f"{workflow_type.value}: {prompt_config.file_path} {exists}")
