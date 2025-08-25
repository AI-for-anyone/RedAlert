from OpenRA_Copilot_Library import AsyncGameAPI
from OpenRA_Copilot_Library.models import Location, TargetsQueryParam, NewTargetsQueryParam, Actor
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP
from typing import Optional
import json



# 单例 GameAPI 客户端
unit_api = AsyncGameAPI(host="localhost", port=7445, language="zh")
#mcp实例
unit_mcp = FastMCP()

# 编组
@unit_mcp.tool(name="group_units", description="将指定单位编组")
async def group_units(source: NewTargetsQueryParam, group_id: int) -> str:
    '''
    Args:
        source (NewTargetsQueryParam): 要编组的单位
        group_id (int): 群组 ID
    '''
    # 查询单位
    units = await unit_api.query_actor(source)
    if units is None or len(units) == 0:
        return "no actors"
    await unit_api.form_group(units, group_id)
    return "ok"



# 移动
@unit_mcp.tool(name="move_units",description="移动指定单位到指定坐标")
async def move_units(source: NewTargetsQueryParam, target: Location) -> str:
    '''
    Args:
        source (NewTargetsQueryParam): 要移动的单位
        target (Location): 目标位置
    '''
    await unit_api.move_units_by_location(target=source, location=target, attack_move=False)
    
    return "ok"

@unit_mcp.tool(name="move_units_by_direction", description="以指定单位的中心为起点，按方向移动一批单位")
async def move_units_by_direction(source: NewTargetsQueryParam, direction: str, distance: int) -> str:
    '''
    Args:
        source (NewTargetsQueryParam): 要移动的单位
        direction (str): 移动方向，必须在 {"左上", "上", "右上", "左", "右", "左下", "下", "右下"} 中
        distance (int): 移动距离
    '''
    units = await unit_api.query_actor(source)
    if units is None or len(units) == 0:
        return "no actors"
    await unit_api.move_units_by_direction(units, direction, distance)
    return "ok"

@unit_mcp.tool(name="set_rally_point",description="为指定建筑设置集结点")
async def set_rally_point(source: NewTargetsQueryParam, x: int, y: int) -> str:
    """
    Args:
        source (NewTargetsQueryParam): 要设置集结点的建筑
        x (int): 集结点 X 坐标
        y (int): 集结点 Y 坐标
    Returns:
        str: 操作完成返回 "ok"
    """
    actors = [Actor(i) for i in actor_ids]
    await unit_api.set_rally_point(actors, Location(x, y))
    return "ok"

def main():
    unit_mcp.settings.log_level = "critical"
    unit_mcp.settings.host = "0.0.0.0"
    unit_mcp.settings.port = 8004
    unit_mcp.run(transport="streamable-http")

if __name__ == "__main__":
    main()
