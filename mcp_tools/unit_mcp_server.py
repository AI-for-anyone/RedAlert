from OpenRA_Copilot_Library import GameAPI
from OpenRA_Copilot_Library.models import Location, TargetsQueryParam, Actor,MapQueryResult
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP
from typing import Optional


# 单例 GameAPI 客户端
unit_api = GameAPI(host="localhost", port=7445, language="zh")
#mcp实例
unit_mcp = FastMCP()


@unit_mcp.tool(name="visible_units", description="根据条件查询可见单位")
def visible_units(type: List[str],faction: str,range: str,restrain: List[dict]) -> List[Dict[str, Any]]:
    # 修复单值传入错误
    if isinstance(type, str):
        type = [type]
    if isinstance(restrain, dict):  # 有时也会传成一个字典
        restrain = [restrain]
    elif isinstance(restrain, bool):  # LLM 有时会给布尔值
        restrain = []

    params = TargetsQueryParam(type=type, faction=faction, range=range, restrain=restrain)
    units = unit_api.query_actor(params)
    return [
        {
            "actor_id": u.actor_id,
            "type": u.type,
            "faction": u.faction,
            "position": {"x": u.position.x, "y": u.position.y},
            "hpPercent": getattr(u, "hp_percent", None)
        }
        for u in units
    ]

@unit_mcp.tool(name="move_units",description="移动一批单位到指定坐标")
def move_units(actor_ids: List[int], x: int, y: int, attack_move: bool = False) -> str:
    #     Args:
    #     actors(List[Actor]): 要移动的Actor列表
    #     location(Location): 目标位置
    #     attack_move(bool): 是否为攻击性移动
    actors = [Actor(i) for i in actor_ids]
    loc = Location(x, y)
    unit_api.move_units_by_location(actors, loc, attack_move=attack_move)
    return "ok"


# —— 单位移动 ——
@unit_mcp.tool(name="move_units_by_location", description="把一批单位移动到指定坐标")
def move_units_by_location(actor_ids: List[int], x: int, y: int, attack_move: bool = False) -> str:
    '''移动单位到指定位置

    Args:
        actors (List[Actor]): 要移动的Actor列表
        location (Location): 目标位置
        attack_move (bool): 是否为攻击性移动

    Raises:
        GameAPIError: 当移动命令执行失败时
    '''
    actors = [Actor(i) for i in actor_ids]
    unit_api.move_units_by_location(actors, Location(x, y), attack_move)
    return "ok"

@unit_mcp.tool(name="move_units_by_direction", description="按方向移动一批单位")
def move_units_by_direction(actor_ids: List[int], direction: str, distance: int) -> str:
    actors = [Actor(i) for i in actor_ids]
    unit_api.move_units_by_direction(actors, direction, distance)
    return "ok"

@unit_mcp.tool(name="move_units_by_path", description="沿指定路径移动一批单位")
def move_units_by_path(actor_ids: List[int], path: List[Dict[str, int]]) -> str:
    '''
    沿指定路径移动一批单位。

    Args:
        actor_ids (List[int]): 要移动的单位 ID 列表。
        path (List[Dict[str, int]]): 路径点列表，每个点为 {"x": int, "y": int} 形式。

    Returns:
        str: "ok" 表示移动命令已发送成功。

    Raises:
        GameAPIError: 当移动命令执行失败时。
    '''
    actors = [Actor(i) for i in actor_ids]
    locs = [Location(p["x"], p["y"]) for p in path]
    unit_api.move_units_by_path(actors, locs)
    return "ok"


# —— 查询与选择 ——
@unit_mcp.tool(name="select_units", description="选中符合条件的单位")
def select_units(type: List[str], faction: str, range: str, restrain: List[dict]) -> str:
    '''选中符合条件的Actor，指的是游戏中的选中操作

    Args:
        query_params (TargetsQueryParam): 查询参数

    Raises:
        GameAPIError: 当选择单位失败时
    '''
    unit_api.select_units(TargetsQueryParam(type=type, faction=faction, range=range, restrain=restrain))
    return "ok"

@unit_mcp.tool(name="form_group", description="为一批单位编组")
def form_group(actor_ids: List[int], group_id: int) -> str:
    '''将Actor编成编组

            Args:
                actors (List[Actor]): 要分组的Actor列表
                group_id (int): 群组 ID

            Raises:
                GameAPIError: 当编组失败时
            '''
    actors = [Actor(i) for i in actor_ids]
    unit_api.form_group(actors, group_id)
    return "ok"

@unit_mcp.tool(name="query_actor", description="查询单位列表")
def query_actor(type: List[str], faction: str, range: str, restrain: List[dict]) -> List[Dict[str, Any]]:
    '''查询符合条件的Actor，获取Actor应该使用的接口

    Args:
        query_params (TargetsQueryParam): 查询参数

    Returns:
        List[Actor]: 符合条件的Actor列表

    Raises:
        GameAPIError: 当查询Actor失败时
    '''
    params = TargetsQueryParam(type=type, faction=faction, range=range, restrain=restrain)
    actors = unit_api.query_actor(params)
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


@unit_mcp.tool(name="deploy_units",description="展开或部署指定单位列表")
def deploy_units(actor_ids: List[int]) -> str:
    """
    Args:
        actor_ids (List[int]): 要展开的单位 ID 列表
    Returns:
        str: 操作完成返回 "ok"
    """
    actors = [Actor(i) for i in actor_ids]
    unit_api.deploy_units(actors)
    return "ok"


@unit_mcp.tool(name="move_units_and_wait",description="移动一批单位到指定位置并等待到达或超时")
def move_units_and_wait(
    actor_ids: List[int],
    x: int,
    y: int,
    max_wait_time: float = 10.0,
    tolerance_dis: int = 1
) -> bool:
    """
    Args:
        actor_ids (List[int]): 要移动的单位 ID 列表
        x (int): 目标 X 坐标
        y (int): 目标 Y 坐标
        max_wait_time (float): 最大等待时间（秒），默认 10.0
        tolerance_dis (int): 到达判定的曼哈顿距离容差，默认 1
    Returns:
        bool: 是否在 max_wait_time 内全部到达（False 表示超时或卡住）
    """
    actors = [Actor(i) for i in actor_ids]
    return unit_api.move_units_by_location_and_wait(actors, Location(x, y), max_wait_time, tolerance_dis)


@unit_mcp.tool(name="set_rally_point",description="为指定建筑设置集结点")
def set_rally_point(actor_ids: List[int], x: int, y: int) -> str:
    """
    Args:
        actor_ids (List[int]): 要设置集结点的建筑 ID 列表
        x (int): 集结点 X 坐标
        y (int): 集结点 Y 坐标
    Returns:
        str: 操作完成返回 "ok"
    """
    actors = [Actor(i) for i in actor_ids]
    unit_api.set_rally_point(actors, Location(x, y))
    return "ok"


# @RAMCP.tool(name="deploy_mcv_and_wait",description="展开自己的基地车并等待指定时间")
# def deploy_mcv_and_wait(wait_time: float = 1.0) -> str:
#     """
#     Args:
#         wait_time (float): 展开后的等待时间（秒），默认 1.0
#     """
#     api.deploy_mcv_and_wait(wait_time)
#     return "ok"


def main():
    unit_mcp.settings.log_level = "critical"
    unit_mcp.settings.host = "0.0.0.0"
    unit_mcp.settings.port = 8004
    unit_mcp.run(transport="sse")

if __name__ == "__main__":
    main()