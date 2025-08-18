import requests
import json
from logs import get_logger
from typing import Any, Dict
from config.config import get_mcp_server

logger = get_logger("mcp_client")

class MCPClient:
    """MCP客户端基类，用于与MCP服务器通信"""
    
    def __init__(self, server_name: str):
        self.server_config = get_mcp_server(server_name)
        if not self.server_config:
            raise ValueError(f"未找到MCP服务器配置: {server_name}")
        self.base_url = f"http://{self.server_config.host}:{self.server_config.port}"
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        """
        调用MCP工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        if arguments is None:
            arguments = {}
            
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            response = requests.post(f"{self.base_url}{self.server_config.path}", json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if "error" in result:
                    logger.error(f"MCP工具调用错误: {result['error']}")
                    return None
                    
                # 解析结果
                content = result.get("result", {}).get("content", [])
                if content and len(content) > 0:
                    text_result = content[0].get("text", "")
                    # 尝试解析JSON格式的结果
                    try:
                        return json.loads(text_result)
                    except (json.JSONDecodeError, ValueError):
                        return text_result
                return None
            else:
                logger.error(f"MCP HTTP请求失败: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"MCP调用超时: {tool_name}")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"MCP连接失败: {self.base_url}")
            return None
        except Exception as e:
            logger.error(f"MCP调用异常: {tool_name} - {e}")
            return None
    
    def is_connected(self) -> bool:
        """检查与MCP服务器的连接状态"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False


class CameraMCPClient(MCPClient):
    """相机控制MCP客户端"""
    
    def __init__(self):
        super().__init__("camera")
    
    def move_camera_to(self, x: int, y: int) -> bool:
        """移动相机到指定坐标"""
        result = self.call_tool("camera_move_to", {"x": x, "y": y})
        return result == "ok"
    
    def move_camera_by_direction(self, direction: str, distance: int) -> bool:
        """按方向移动相机"""
        result = self.call_tool("camera_move_dir", {"direction": direction, "distance": distance})
        return result == "ok"
    
    def move_camera_to_actor(self, actor_id: int) -> bool:
        """移动相机到指定Actor位置"""
        result = self.call_tool("move_camera_to", {"actor_id": actor_id})
        return result == "ok"


class FightMCPClient(MCPClient):
    """战斗MCP客户端"""
    
    def __init__(self):
        super().__init__("fight")
    
    def attack_target(self, attacker_id: int, target_id: int) -> bool:
        """攻击指定目标"""
        result = self.call_tool("attack_target", {"attacker_id": attacker_id, "target_id": target_id})
        return result is not None and result is not False
    
    def occupy_units(self, occupier_ids: list, target_ids: list) -> bool:
        """占领目标单位"""
        result = self.call_tool("occupy_units", {"occupier_ids": occupier_ids, "target_ids": target_ids})
        return result == "ok"
    
    def repair_units(self, actor_ids: list) -> bool:
        """修复单位"""
        result = self.call_tool("repair_units", {"actor_ids": actor_ids})
        return result == "ok"
    
    def stop_units(self, actor_ids: list) -> bool:
        """停止单位当前行动"""
        result = self.call_tool("stop_units", {"actor_ids": actor_ids})
        return result == "ok"


class InfoMCPClient(MCPClient):
    """信息查询MCP客户端"""
    
    def __init__(self):
        super().__init__("info")
    
    def get_game_state(self) -> Dict[str, Any]:
        """获取游戏状态"""
        return self.call_tool("get_game_state") or {}
    
    def map_query(self) -> Dict[str, Any]:
        """查询地图信息"""
        return self.call_tool("map_query") or {}
    
    def find_path(self, actor_ids: list, dest_x: int, dest_y: int, method: str = "最短路") -> list:
        """寻路"""
        result = self.call_tool("find_path", {
            "actor_ids": actor_ids, 
            "dest_x": dest_x, 
            "dest_y": dest_y, 
            "method": method
        })
        return result or []
    
    def player_base_info_query(self) -> Dict[str, Any]:
        """查询玩家基地信息"""
        return self.call_tool("player_base_info_query") or {}
    
    def screen_info_query(self) -> Dict[str, Any]:
        """查询屏幕信息"""
        return self.call_tool("screen_info_query") or {}
    
    def visible_query(self, x: int, y: int) -> bool:
        """查询坐标可见性"""
        result = self.call_tool("visible_query", {"x": x, "y": y})
        return result is True
    
    def explorer_query(self, x: int, y: int) -> bool:
        """查询坐标探索状态"""
        result = self.call_tool("explorer_query", {"x": x, "y": y})
        return result is True


class ProduceMCPClient(MCPClient):
    """生产MCP客户端"""
    
    def __init__(self):
        super().__init__("produce")
    
    def produce(self, unit_type: str, quantity: int) -> int:
        """生产单位"""
        result = self.call_tool("produce", {"unit_type": unit_type, "quantity": quantity})
        return result if isinstance(result, int) else -1
    
    def can_produce(self, unit_type: str) -> bool:
        """检查是否可生产"""
        result = self.call_tool("can_produce", {"unit_type": unit_type})
        return result is True
    
    def query_production_queue(self, queue_type: str) -> Dict[str, Any]:
        """查询生产队列"""
        return self.call_tool("query_production_queue", {"queue_type": queue_type}) or {}
    
    def manage_production(self, queue_type: str, action: str) -> bool:
        """管理生产队列"""
        result = self.call_tool("manage_production", {"queue_type": queue_type, "action": action})
        return result == "ok"


class UnitMCPClient(MCPClient):
    """单位控制MCP客户端"""
    
    def __init__(self):
        super().__init__("unit")
    
    def move_units(self, actor_ids: list, x: int, y: int, attack_move: bool = False) -> bool:
        """移动单位"""
        result = self.call_tool("move_units", {
            "actor_ids": actor_ids, 
            "x": x, 
            "y": y, 
            "attack_move": attack_move
        })
        return result == "ok"
    
    def query_actor(self, type_list: list, faction: str, range_param: str, restrain: list) -> list:
        """查询单位"""
        result = self.call_tool("query_actor", {
            "type": type_list,
            "faction": faction, 
            "range": range_param,
            "restrain": restrain
        })
        return result or []
    
    def select_units(self, type_list: list, faction: str, range_param: str, restrain: list) -> bool:
        """选中单位"""
        result = self.call_tool("select_units", {
            "type": type_list,
            "faction": faction,
            "range": range_param, 
            "restrain": restrain
        })
        return result == "ok"
    
    def form_group(self, actor_ids: list, group_id: int) -> bool:
        """编组单位"""
        result = self.call_tool("form_group", {"actor_ids": actor_ids, "group_id": group_id})
        return result == "ok"
    
    def deploy_units(self, actor_ids: list) -> bool:
        """展开单位"""
        result = self.call_tool("deploy_units", {"actor_ids": actor_ids})
        return result == "ok"