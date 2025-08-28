from OpenRA_Copilot_Library import AsyncGameAPI
from OpenRA_Copilot_Library.models import Location, TargetsQueryParam, NewTargetsQueryParam, Actor,MapQueryResult
from typing import List, Dict, Any ,Tuple
from mcp.server.fastmcp import FastMCP
from typing import Optional
import asyncio
import json

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logs import get_logger, setup_logging, LogConfig, LogLevel

from task_scheduler import TaskManager, Task

logger = get_logger("info_mcp_server")

# 单例 GameAPI 客户端
info_api = AsyncGameAPI(host="localhost", port=7445, language="zh")
#mcp实例
info_mcp = FastMCP()

@info_mcp.tool(name="get_game_state", description="返回玩家资源、电力和可见单位列表")
async def get_game_state() -> Dict[str, Any]:
    # 1) 玩家基础信息
    info = await info_api.player_base_info_query()
    # 2) 屏幕内可见单位
    units = await info_api.query_actor(
        NewTargetsQueryParam(
            type=[], faction=["任意"], range="screen", restrain=[{"visible": True}]
        )
    )
    visible = [
        {
            "actor_id": u.actor_id,
            "type": u.type,
            "faction": u.faction,
            "position": {"x": u.position.x, "y": u.position.y},
        }
        for u in units if u.faction != "中立"
    ]

    return {
        "cash": info.Cash,
        "resources": info.Resources,
        "power": info.Power,
        "visible_units": visible
    }


# —— 路径寻路 ——
@info_mcp.tool(name="find_path", description="为单位寻找路径")
async def find_path(actor_ids: List[int], dest_x: int, dest_y: int, method: str) -> List[Dict[str,int]]:
    '''为Actor找到到目标的路径
    Args:
        actors (List[Actor]): 要移动的Actor列表
        destination (Location): 目标位置
        method (str): 寻路方法，必须在 {"最短路"，"左路"，"右路"} 中

    Returns:
        List[Location]: 路径点列表，第0个是目标点，最后一个是Actor当前位置，相邻的点都是八方向相连的点

    Raises:
        GameAPIError: 当寻路失败时
    '''
    actors = [Actor(i) for i in actor_ids]
    path = await info_api.find_path(actors, Location(dest_x, dest_y), method)
    return [{"x": p.x, "y": p.y} for p in path]

@info_mcp.tool(name="get_actor_by_id",description="根据 Actor ID 获取单个单位的信息，如果不存在则返回 None"
)
async def get_actor_by_id(actor_id: int) -> Optional[Dict[str, Any]]:
    """
    Args:
        actor_id (int): 要查询的 Actor ID
    Returns:
        Dict: 包含 actor_id, type, faction, position, hpPercent 的字典
        None: 如果该 ID 对应的 Actor 不存在
    """
    actor = await info_api.get_actor_by_id(actor_id)
    if actor is None:
        return None

    return {
        "actor_id": actor.actor_id,
        "type": actor.type,
        "faction": actor.faction,
        "position": {"x": actor.position.x, "y": actor.position.y},
        "hpPercent": getattr(actor, "hp_percent", None)
    }

@info_mcp.tool(name="update_actor",description="根据 actor_id 更新该单位的信息，并返回其最新状态")
async def update_actor(actor_id: int) -> Optional[Dict[str, Any]]:
    """
    Args:
        actor_id (int): 要更新的 Actor ID
    Returns:
        Dict: 最新的 Actor 信息（如果成功），否则 None
    """
    actor = Actor(actor_id)
    success = await info_api.update_actor(actor)
    if not success:
        return None

    return {
        "actor_id": actor.actor_id,
        "type": actor.type,
        "faction": actor.faction,
        "position": {"x": actor.position.x, "y": actor.position.y},
        "hpPercent": getattr(actor, "hp_percent", None)
    }


@info_mcp.tool(name="visible_query",description="查询指定坐标是否在视野中")
async def visible_query(x: int, y: int) -> bool:
    """
    Args:
        x (int): 地图坐标 X
        y (int): 地图坐标 Y
    Returns:
        bool: 如果该点可见返回 True，否则 False
    """
    return await info_api.visible_query(Location(x, y))



@info_mcp.tool(name="explorer_query",description="查询指定坐标是否已探索")
async def explorer_query(x: int, y: int) -> bool:
    """
    Args:
        x (int): 地图坐标 X
        y (int): 地图坐标 Y
    Returns:
        bool: 如果该点已探索返回 True，否则 False
    """
    return await info_api.explorer_query(Location(x, y))


@info_mcp.tool(name="get_unexplored_nearby_positions",description="获取当前位置附近尚未探索的坐标列表")
async def get_unexplored_nearby_positions(
    map_result: Dict[str, Any],
    current_x: int,
    current_y: int,
    max_distance: int
) -> List[Dict[str, int]]:
    """
    Args:
        map_result (dict): map_query 返回的地图信息字典
        current_x (int): 当前 X 坐标
        current_y (int): 当前 Y 坐标
        max_distance (int): 曼哈顿距离范围
    Returns:
        List[dict]: 未探索位置的列表，每项包含 'x' 和 'y'
    """
    # 将 dict 转回 MapQueryResult
    mq = MapQueryResult(
        MapWidth=map_result["width"],
        MapHeight=map_result["height"],
        Height=map_result["heightMap"],
        IsVisible=map_result["visible"],
        IsExplored=map_result["explored"],
        Terrain=map_result["terrain"],
        ResourcesType=map_result["resourcesType"],
        Resources=map_result["resources"]
    )
    # 调用底层方法
    locs = info_api.get_unexplored_nearby_positions(
        mq,
        Location(current_x, current_y),
        max_distance
    )
    # 序列化为 JSON-friendly 格式
    return [{"x": loc.x, "y": loc.y} for loc in locs]


@info_mcp.tool(name="unit_attribute_query",description="查询指定单位的属性及其攻击范围内的目标")
async def unit_attribute_query(actor_ids: List[int]) -> Dict[str, Any]:
    """
    Args:
        actor_ids (List[int]): 要查询的单位 ID 列表
    Returns:
        dict: 每个单位的属性信息，包括其攻击范围内的目标列表
    """
    target = NewTargetsQueryParam(actor_id=actor_ids)
    return await info_api.unit_attribute_query(target)

@info_mcp.tool(name="unit_info_query",description="查询所有可见单位的信息")
async def unit_info_query() -> Dict[str, Any]:  
    logger.info("查询所有可见单位的信息")
    info = await info_api.query_actor(NewTargetsQueryParam(restrain=[{"visible": True}]))
    logger.debug(f"unit_info_query- {info}")
    our_dict:Dict[str, {List[Location], int}] = {}
    enemy_dict:Dict[str, {List[Location], int}] = {}
    for unit in info:
        if unit.type == "mpspawn":
            continue

        if unit.faction == "己方":
            if unit.type not in our_dict.keys():
                our_dict[unit.type] = {"locations": [], "count": 0}
            our_dict[unit.type]["locations"].append((unit.position.x, unit.position.y))
            our_dict[unit.type]["count"] += 1
        elif unit.faction == "敌方":
            if unit.type not in enemy_dict.keys():
                enemy_dict[unit.type] = {"locations": [], "count": 0}
            enemy_dict[unit.type]["locations"].append((unit.position.x, unit.position.y))
            enemy_dict[unit.type]["count"] += 1

    def get_center_location(locations: List[Tuple[int, int]]) -> Location:
        if not locations:
            return Location(0, 0)
        
        total_x = sum(x for x, _ in locations)
        total_y = sum(y for _, y in locations)
        
        return Location(total_x // len(locations), total_y // len(locations))
    
    for d in our_dict:
        our_dict[d]["center_locations"] = get_center_location(our_dict[d]["locations"])

    for d in enemy_dict:
        enemy_dict[d]["center_locations"] = get_center_location(enemy_dict[d]["locations"])

    result = {"our": our_dict, "enemy": enemy_dict}
    logger.debug(f"unit_info_query- {result}")
    # 将列表结果包装为字典格式
    return result


@info_mcp.tool(name="map_query",description="查询地图信息并返回序列化数据")
async def map_query() -> Dict[str, Any]:
    """
    Returns:
        dict: 包含地图宽度、高度、高程、可见性、探索状态、地形、资源类型和资源量的字典
    """
    result = await info_api.map_query()
    return {
        "左上角坐标": Location(0, 0),
        "右下角坐标": Location(result.MapWidth, result.MapHeight),
        "地图宽度": result.MapWidth,
        "地图高度": result.MapHeight
    }


@info_mcp.tool(name="player_base_info_query",description="查询玩家基地的资源、电力等基础信息")
async def player_base_info_query() -> Dict[str, Any]:
    """
    Returns:
        dict: 包含以下字段的玩家基地信息
            - cash: 当前金钱
            - resources: 资源数量
            - power: 总供电量
            - powerDrained: 已用电量
            - powerProvided: 可用电量
    """
    info = await info_api.player_base_info_query()
    return {
        "cash": info.Cash,
        "resources": info.Resources,
        "power": info.Power,
        "powerDrained": info.PowerDrained,
        "powerProvided": info.PowerProvided
    }

@info_mcp.tool(name="screen_info_query",description="查询当前屏幕信息")
async def screen_info_query() -> Dict[str, Any]:
    """
    Returns:
        dict: 包含以下字段的屏幕信息
            - screenMin: {x, y}
            - screenMax: {x, y}
            - isMouseOnScreen: bool
            - mousePosition: {x, y}
    """
    info = await info_api.screen_info_query()
    return {
        "screenMin": {"x": info.ScreenMin.x, "y": info.ScreenMin.y},
        "screenMax": {"x": info.ScreenMax.x, "y": info.ScreenMax.y},
        "isMouseOnScreen": info.IsMouseOnScreen,
        "mousePosition": {"x": info.MousePosition.x, "y": info.MousePosition.y}
    }

@info_mcp.tool(name="query_actor", description="查询单位列表")
async def query_actor(type: List[str], faction: str, range: str, restrain: List[dict]) -> List[Dict[str, Any]]:
    '''查询符合条件的Actor，获取Actor应该使用的接口

    Args:
        query_params (TargetsQueryParam): 查询参数

    Returns:
        List[Actor]: 符合条件的Actor列表

    Raises:
        GameAPIError: 当查询Actor失败时
    '''
    params = NewTargetsQueryParam(type=type, faction=faction, range=range, restrain=restrain)
    actors = await info_api.query_actor(params)
    return [
        {
            "actor_id": u.actor_id,
            "type": u.type,
            "faction": u.faction,
            "position": {"x": u.position.x, "y": u.position.y},
            "hpPercent": getattr(u, "hp_percent", None)
        }
        for u in actors
    ]


# 查看所有编组
@info_mcp.tool(name="get_groups", description="查看所有编组")
async def get_groups() -> List[Tuple[int, List[Tuple[int, str]]]]:
    '''
    Returns:
        List[Tuple[int, List[Tuple[int, str]]]]: 所有编组信息
    '''
    
    groups: List[Tuple[int, List[Tuple[int, str]]]] = []
    for group_id in range(1, 10):
        try:
            units = await info_api.query_actor(NewTargetsQueryParam(faction="己方", group_id=[group_id]))
        except Exception as e:
            logger.error("get_groups-查询编组失败: {0}".format(e))
            continue
        if units is None or len(units) == 0:
            continue
        groups.append((group_id, [(unit.actor_id, unit.type) for unit in units]))
    return groups

# 查看所有没有被编组的作战单位
@info_mcp.tool(name="get_ungrouped_actors", description="查看所有没有被编组的作战单位")
async def get_ungrouped_actors() -> List[Actor]:
    '''
    Returns:
        List[Actor]: 所有没有被编组的作战单位信息
    '''
    from model import FIGHT_UNITS
    all_actors = await info_api.query_actor(NewTargetsQueryParam(faction="己方",type=FIGHT_UNITS))
    logger.info(f"get_ungrouped_actors- {all_actors}")

    grouped_actors:List[Actor] = []
    
    try:
        units = await info_api.query_actor(NewTargetsQueryParam(faction="己方", group_id=[id for id in range(1, 10)]))
    except Exception as e:
        logger.error("get_ungrouped_actors-查询编组失败: {0}".format(e))
        units = []
    logger.info(f"get_ungrouped_actors- {units}")
    if units is None or len(units) == 0:
        return json.dumps([actor.__dict__ for actor in all_actors])
    grouped_actors.extend(units)

    ungrouped_actors = [actor for actor in all_actors if actor not in grouped_actors]
    return json.dumps([actor.__dict__ for actor in ungrouped_actors])

def main():
    info_mcp.settings.log_level = "debug"
    info_mcp.settings.host = "0.0.0.0"
    info_mcp.settings.port = 8002
    info_mcp.run(transport="streamable-http")

if __name__ == "__main__":
    main()