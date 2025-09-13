"""
RedAlert AI Copilot 配置文件
包含 LLM 配置、Prompt 配置、MCP 服务器配置等
"""
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from typing import Any, Final, Mapping, Tuple
from types import MappingProxyType

# 项目根目录
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
# 提示词目录常量
PROMPT_DIR: Final[Path] = PROJECT_ROOT / "prompt"

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

# 作为只读映射暴露
PROMPT_PARAMS: Final[Mapping[str, Tuple[str, ...]]] = MappingProxyType({
    "ALL_ACTORS": ALL_ACTORS,
    "ALL_DIRECTIONS": ALL_DIRECTIONS,
    "ALL_GROUPS": ALL_GROUPS,
    "ALL_BUILDINGS": ALL_BUILDINGS,
    "ALL_UNITS": ALL_UNITS,
})

# MCP 默认常量
MCP_DEFAULT_HOST: Final[str] = "127.0.0.1"
MCP_DEFAULT_PATH: Final[str] = "/mcp"
MCP_DEFAULT_TRANSPORT: Final[str] = "streamable_http"

# 服务器工具模式（只读映射 + 不可变序列）
SERVER_TOOL_PATTERNS: Final[Mapping[str, Tuple[str, ...]]] = MappingProxyType({
    "camera": ("move_camera_to", "camera_move_dir", "camera_move_to"),
    "fight": (
        "army_gather", "army_designated_attack", "army_attack_direction", "army_attack_location",
        "army_attack_target_direction", "army_attack_target_location", "army", "army_move"
    ),
    "info": (
        "get_game_state", "find_path", "get_actor_by_id", "update_actor", "visible_query", "explorer_query",
        "get_unexplored_nearby_positions", "unit_attribute_query", "unit_info_query", "map_query",
        "player_base_info_query", "screen_info_query", "query_actor", "get_ungrouped_actors", "get_groups", "control_point_query"
    ),
    "produce": (
        "produce", "can_produce", "query_production", "manage_production", "ensure_can_produce",
        "ensure_can_build", "生产", "deploy_mcv", "get_player_base_info",  "recycle_mcv" , "deploy_mcv_and_wait", "clean_queue"
    ),
    "unit": ("group_units", "move_units", "move_units_by_direction", "set_rally_point", "recycle_mcv", "investigation", "occupy_cp"),
    "base": ("map_query", "unit_info_query", "control_point_query"),
    "ai_assistant": ( "player_base_info_query", "query_production_queue", 
        "produce",  "ensure_can_produce", "unit_info_query", "do_nothing",
        "ensure_can_build", "deploy_mcv", "double_mine_start")
})

class WorkflowType(Enum):
    """工作流类型枚举"""
    CLASSIFY = "classify"           # 任务分类
    CAMERA_CONTROL = "camera"       # 地图视角控制
    PRODUCTION = "production"       # 生产管理
    UNIT_CONTROL = "unit_control"   # 单位控制
    RESOURCE = "resource"           # 资源管理
    INTELLIGENCE = "intelligence"   # 信息管理
    AI_ASSISTANT = "ai_assistant"   # AI 助手

@dataclass
class LLMConfig:
    """LLM 配置"""
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 30
    model_provider: str = "openai"

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

    def _prompt_params(self):
        """获取提示词参数"""
        return PROMPT_PARAMS
    
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
                max_tokens=1024,
                model_provider=os.getenv("CLASSIFY_MODEL_PROVIDER", "deepseek")
            ),
            
            # 地图视角控制 - 需要精确的空间理解
            WorkflowType.CAMERA_CONTROL: LLMConfig(
                base_url=os.getenv("CAMERA_API_BASE", "https://api.deepseek.com"),
                api_key=os.getenv("CAMERA_API_KEY", ""),
                model=os.getenv("CAMERA_MODEL", "deepseek-chat"),
                temperature=0.3,
                max_tokens=2048,
                model_provider=os.getenv("CAMERA_MODEL_PROVIDER", "deepseek")
            ),
            
            # 生产管理 - 需要逻辑推理
            WorkflowType.PRODUCTION: LLMConfig(
                base_url=os.getenv("PRODUCTION_API_BASE", "https://api.deepseek.com"),
                api_key=os.getenv("PRODUCTION_API_KEY", ""),
                model=os.getenv("PRODUCTION_MODEL", "deepseek-chat"),
                temperature=0.5,
                max_tokens=3072,
                model_provider=os.getenv("PRODUCTION_MODEL_PROVIDER", "deepseek")
            ),
            
            # 单位控制 - 需要实时决策
            WorkflowType.UNIT_CONTROL: LLMConfig(
                base_url=os.getenv("UNIT_CONTROL_API_BASE", "https://api.deepseek.com"),
                api_key=os.getenv("UNIT_CONTROL_API_KEY", ""),
                model=os.getenv("UNIT_CONTROL_MODEL", "deepseek-chat"),
                temperature=0.0,
                max_tokens=8192,
                model_provider=os.getenv("UNIT_CONTROL_MODEL_PROVIDER", "deepseek")
            ),
            
            # 信息管理 - 需要准确的信息处理
            WorkflowType.INTELLIGENCE: LLMConfig(
                base_url=os.getenv("INTELLIGENCE_API_BASE", "https://api.deepseek.com"),
                api_key=os.getenv("INTELLIGENCE_API_KEY", ""),
                model=os.getenv("INTELLIGENCE_MODEL", "deepseek-chat"),
                temperature=0.2,
                max_tokens=2048,
                model_provider=os.getenv("INTELLIGENCE_MODEL_PROVIDER", "deepseek")
            ),
            
            # AI助手 - 需要智能的决策
            WorkflowType.AI_ASSISTANT: LLMConfig(
                base_url=os.getenv("AI_ASSISTANT_API_BASE", "https://api.deepseek.com"),
                api_key=os.getenv("AI_ASSISTANT_API_KEY", ""),
                model=os.getenv("AI_ASSISTANT_MODEL", "deepseek-chat"),
                temperature=0.2,
                max_tokens=2048,
                model_provider=os.getenv("AI_ASSISTANT_MODEL_PROVIDER", "deepseek")
            )
        }
    
    def _setup_prompt_configs(self):
        """设置 Prompt 配置"""
        prompt_dir = PROMPT_DIR
        
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
        # MCP 服务器工具模式配置（只读）
        self.server_tool_patterns = SERVER_TOOL_PATTERNS
        
        self.mcp_servers: Dict[str, MCPServerConfig] = {

            # 相机控制 MCP 服务器
            "camera": MCPServerConfig(
                name="camera",
                host=MCP_DEFAULT_HOST,
                port=8000,
                path=MCP_DEFAULT_PATH,
                transport=MCP_DEFAULT_TRANSPORT,
                description="相机控制服务器"
            ),
            # 战斗控制 MCP 服务器
            "fight": MCPServerConfig(
                name="fight",
                host=MCP_DEFAULT_HOST,
                port=8001,
                path=MCP_DEFAULT_PATH,
                transport=MCP_DEFAULT_TRANSPORT,
                description="战斗控制服务器"
            ),
            # 信息查询 MCP 服务器
            "info": MCPServerConfig(
                name="info",
                host=MCP_DEFAULT_HOST,
                port=8002,
                path=MCP_DEFAULT_PATH,
                transport=MCP_DEFAULT_TRANSPORT,
                description="游戏信息查询服务器"
            ),
            # 生产管理 MCP 服务器
            "produce": MCPServerConfig(
                name="produce",
                host=MCP_DEFAULT_HOST,
                port=8003,
                path=MCP_DEFAULT_PATH,
                transport=MCP_DEFAULT_TRANSPORT,
                description="生产管理服务器"
            ),
            # 单位控制 MCP 服务器
            "unit": MCPServerConfig(
                name="unit",
                host=MCP_DEFAULT_HOST,
                port=8004,
                path=MCP_DEFAULT_PATH,
                transport=MCP_DEFAULT_TRANSPORT,
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

def get_server_tool_patterns() -> Mapping[str, Tuple[str, ...]]:
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
