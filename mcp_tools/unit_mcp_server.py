from OpenRA_Copilot_Library import AsyncGameAPI
from OpenRA_Copilot_Library.models import Location, TargetsQueryParam, NewTargetsQueryParam, Actor
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP
from typing import Optional
import json
import random



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

# 计算List[Actor]中心点
def get_center_location(actors: List[Actor]) -> Location:
    if actors is None or len(actors) == 0:
        return Location(0, 0)
    center_x = sum(u.position.x for u in actors) / len(actors)
    center_y = sum(u.position.y for u in actors) / len(actors)
    return Location(center_x, center_y)


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

    # 计算中心点位置
    before_center = get_center_location(units)

    relative_pos = Location(before_center.x, before_center.y)
    match direction:
        case "左上":
            relative_pos.x = max(relative_pos.x - int(distance * 1.41421), 0)
            relative_pos.y = max(relative_pos.y - int(distance * 1.41421), 0)
        case "上":
            relative_pos.y = max(relative_pos.y - distance, 0)
        case "右上":
            relative_pos.x = min(relative_pos.x + int(distance * 1.41421), 1024)
            relative_pos.y = max(relative_pos.y - int(distance * 1.41421), 0)
        case "左":
            relative_pos.x = max(relative_pos.x - distance, 0)
        case "右":
            relative_pos.x = min(relative_pos.x + distance, 1024)
        case "左下":
            relative_pos.x = max(relative_pos.x - int(distance * 1.41421), 0)
            relative_pos.y = min(relative_pos.y + int(distance * 1.41421), 1024)
        case "下":
            relative_pos.y = min(relative_pos.y + distance, 1024)
        case "右下":
            relative_pos.x = min(relative_pos.x + int(distance * 1.41421), 1024)
            relative_pos.y = min(relative_pos.y + int(distance * 1.41421), 1024)
        case _:
            return "direction error"
    
    await unit_api.move_units_by_location(target=source, location=relative_pos, attack_move=False)
    return "ok"

@unit_mcp.tool(name="set_rally_point",description="为出兵建筑设置集结点")
async def set_rally_point(x: int, y: int) -> str:
    """
    Args:
        x (int): 集结点 X 坐标
        y (int): 集结点 Y 坐标
    Returns:
        str: 操作完成返回 "ok"
    """
    await unit_api.set_rally_point(Location(x, y))
    return "ok"

@unit_mcp.tool(name="recycle_mcv",description="回收基地车")
async def recycle_mcv() -> str:
    """
    """
    # 查找建造厂
    factory = await unit_api.query_actor(NewTargetsQueryParam(type=['建造厂'], faction='自己'))
    if factory is None or len(factory) == 0:
        await unit_api.deploy_mcv_and_wait()  
        return "ok"

    await unit_api.deploy_units([Actor(actor_id=factory[0].actor_id)])
    return "ok"

@unit_mcp.tool(name="investigation",description="侦察")
async def investigation() -> str:
    """
    """
    unit = await unit_api.query_actor(NewTargetsQueryParam(type=['步兵'], faction='自己'))
    if unit is None or len(unit) == 0:
        return "no actors"
    
    map_info = await unit_api.map_query()
    for u in unit:
        # 全图随机一个坐标
        locations:List[Location] = [
            Location(random.randrange(0,map_info.MapWidth),random.randrange(0,map_info.MapHeight)),
            Location(random.randrange(0,map_info.MapWidth),random.randrange(0,map_info.MapHeight)),
            Location(random.randrange(0,map_info.MapWidth),random.randrange(0,map_info.MapHeight)),
            Location(random.randrange(0,map_info.MapWidth),random.randrange(0,map_info.MapHeight)),
            Location(random.randrange(0,map_info.MapWidth),random.randrange(0,map_info.MapHeight)),
            Location(random.randrange(0,map_info.MapWidth),random.randrange(0,map_info.MapHeight)),
            Location(random.randrange(0,map_info.MapWidth),random.randrange(0,map_info.MapHeight)),
            Location(random.randrange(0,map_info.MapWidth),random.randrange(0,map_info.MapHeight)),
            Location(random.randrange(0,map_info.MapWidth),random.randrange(0,map_info.MapHeight)),
            Location(random.randrange(0,map_info.MapWidth),random.randrange(0,map_info.MapHeight)),
            Location(random.randrange(0,map_info.MapWidth),random.randrange(0,map_info.MapHeight)),
            Location(random.randrange(0,map_info.MapWidth),random.randrange(0,map_info.MapHeight)),
            Location(random.randrange(0,map_info.MapWidth),random.randrange(0,map_info.MapHeight)),
            Location(random.randrange(0,map_info.MapWidth),random.randrange(0,map_info.MapHeight))
        ]
        await unit_api.move_units_by_path(actors=[Actor(actor_id=u.actor_id)],path=locations)
    return "ok"

def main():
    unit_mcp.settings.log_level = "critical"
    unit_mcp.settings.host = "0.0.0.0"
    unit_mcp.settings.port = 8004
    unit_mcp.run(transport="streamable-http")

if __name__ == "__main__":
    main()
