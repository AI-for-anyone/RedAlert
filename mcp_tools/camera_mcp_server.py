from .OpenRA_Copilot_Library import GameAPI
from .OpenRA_Copilot_Library.models import Location, TargetsQueryParam, Actor,MapQueryResult
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP
from typing import Optional

# 单例 GameAPI 客户端
camera_api = GameAPI(host="localhost", port=7445, language="zh")
#mcp实例
camera_mcp = FastMCP()


# —— 相机控制 ——
@camera_mcp.tool(name="camera_move_to", description="将镜头移动到指定坐标")
def camera_move_to(x: int, y: int) -> str:
    camera_api.move_camera_by_location(Location(x, y))
    return "ok"

@camera_mcp.tool(name="camera_move_dir", description="按方向移动镜头")
def camera_move_dir(direction: str, distance: int) -> str:
    camera_api.move_camera_by_direction(direction, distance)
    return "ok"

@camera_mcp.tool(name="move_camera_to",description="将镜头移动到指定 Actor 的位置"
)
def move_camera_to(actor_id: int) -> str:
    """
    Args:
        actor_id (int): 目标 Actor 的 ID
    Returns:
        str: 操作完成返回 "ok"
    """
    camera_api.move_camera_to(Actor(actor_id))
    return "ok"


def main():
    camera_mcp.settings.log_level = "critical"
    camera_mcp.settings.host = "0.0.0.0"
    camera_mcp.settings.port = 8000
    camera_mcp.run(transport="sse")

if __name__ == "__main__":
    main()