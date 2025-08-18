from OpenRA_Copilot_Library import GameAPI
from OpenRA_Copilot_Library.models import Location, TargetsQueryParam, Actor,MapQueryResult
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP
from typing import Optional

# 单例 GameAPI 客户端
produce_api = GameAPI(host="localhost", port=7445, language="zh")
#mcp实例
produce_mcp = FastMCP()


@produce_mcp.tool(name="produce",description="生产指定类型和数量的单位，返回生产任务 ID")
def produce(unit_type: str, quantity: int) -> int:
    '''生产指定数量的Actor

    Args:
        unit_type (str): Actor类型
        quantity (int): 生产数量
        auto_place_building (bool, optional): 是否在生产完成后使用随机位置自动放置建筑，仅对建筑类型有效

    Returns:
        int: 生产任务的 waitId
        None: 如果任务创建失败
    '''
    wait_id = produce_api.produce(unit_type, quantity, auto_place_building=True)
    return wait_id or -1


@produce_mcp.tool(name="can_produce", description="检查是否可生产某类型单位")
def can_produce(unit_type: str) -> bool:
    '''检查是否可以生产指定类型的Actor

    Args:
        unit_type (str): Actor类型，必须在 {ALL_UNITS} 中

    Returns:
        bool: 是否可以生产

    '''
    return produce_api.can_produce(unit_type)


# @RAMCP.tool(name="produce_wait", description="发起并等待生产完成")
# def produce_wait(unit_type: str, quantity: int, auto_place: bool = True) -> bool:
#     '''生产指定数量的Actor并等待生产完成
#
#     Args:
#         unit_type (str): Actor类型
#         quantity (int): 生产数量
#         auto_place_building (bool, optional): 是否在生产完成后使用随机位置自动放置建筑，仅对建筑类型有效
#
#     Raises:
#         GameAPIError: 当生产或等待过程中发生错误时
#     '''
#     try:
#         api.produce_wait(unit_type, quantity, auto_place)
#         return True
#     except Exception:
#         return False

# @RAMCP.tool(name="is_ready",description="检查指定生产任务是否已完成")
# def is_ready(wait_id: int) -> bool:
#     """
#     Args:
#         wait_id (int): 生产任务的 ID
#     Returns:
#         bool: 生产任务是否已完成
#     """
#     return api.is_ready(wait_id)

# @RAMCP.tool(name="wait",description="等待指定生产任务完成，或超时返回 False")
# def wait(wait_id: int, max_wait_time: float = 20.0) -> bool:
#     """
#     Args:
#         wait_id (int): 生产任务的 ID
#         max_wait_time (float): 最大等待时间（秒），默认 20.0
#     Returns:
#         bool: 是否在指定时间内完成（False 表示超时）
#     """
#     return api.wait(wait_id, max_wait_time)


@produce_mcp.tool(name="query_production_queue",description="查询指定类型的生产队列")
def query_production_queue(queue_type: str) -> Dict[str, Any]:
    '''查询指定类型的生产队列

    Args:
        queue_type (str): 队列类型，必须是以下值之一：
            'Building'
            'Defense'
            'Infantry'
            'Vehicle'
            'Aircraft'
            'Naval'

    Returns:
        dict: 包含队列信息的字典，格式如下：
            {
                "queue_type": "队列类型",
                "queue_items": [
                    {
                        "name": "项目内部名称",
                        "chineseName": "项目中文名称",
                        "remaining_time": 剩余时间,
                        "total_time": 总时间,
                        "remaining_cost": 剩余花费,
                        "total_cost": 总花费,
                        "paused": 是否暂停,
                        "done": 是否完成,
                        "progress_percent": 完成百分比,
                        "owner_actor_id": 所属建筑的ActorID,
                        "status": "项目状态，可能的值：
                            'completed' - 已完成
                            'paused' - 已暂停
                            'in_progress' - 正在建造（队列中第一个项目）
                            'waiting' - 等待中（队列中其他项目）"
                    },
                    ...
                ],
                "has_ready_item": 是否有已就绪的项目
            }

    Raises:
        GameAPIError: 当查询生产队列失败时
    '''
    return produce_api.query_production_queue(queue_type)


# @RAMCP.tool(name="place_building",description="放置生产队列中已就绪的建筑")
# def place_building(queue_type: str, x: Optional[int] = None, y: Optional[int] = None) -> str:
#     """
#     Args:
#         queue_type (str): 队列类型，必须是 'Building', 'Defense', 'Infantry', 'Vehicle', 'Aircraft', 或 'Naval'
#         x (Optional[int]): 建筑放置 X 坐标（如不提供则自动选址）
#         y (Optional[int]): 建筑放置 Y 坐标（如不提供则自动选址）
#     Returns:
#         str: 操作完成时返回 "ok"
#     """
#     loc = Location(x, y) if x is not None and y is not None else None
#     api.place_building(queue_type, loc)
#     return "ok"

@produce_mcp.tool(name="manage_production",description="管理生产队列中的项目（暂停、取消或继续）")
def manage_production(queue_type: str, action: str) -> str:
    """
    Args:
        queue_type (str): 队列类型，必须是 'Building', 'Defense', 'Infantry', 'Vehicle', 'Aircraft' 或 'Naval'
        action (str): 操作类型，必须是 'pause', 'cancel' 或 'resume'
    Returns:
        str: 操作完成时返回 "ok"
    """
    produce_api.manage_production(queue_type, action)
    return "ok"


@produce_mcp.tool(name="ensure_can_build_wait",description="确保指定建筑已存在，若不存在则递归建造其所有依赖并等待完成")
def ensure_can_build_wait(building_name: str) -> bool:
    """
    Args:
        building_name (str): 建筑名称（中文）
    Returns:
        bool: 是否已拥有该建筑或成功建造完成
    """
    return produce_api.ensure_can_build_wait(building_name)


# @RAMCP.tool(name="ensure_building_wait",description="内部接口：确保指定建筑及其依赖已建造并等待完成")
# def ensure_building_wait(building_name: str) -> bool:
#     """
#     Args:
#         building_name (str): 建筑名称（中文）
#     Returns:
#         bool: 是否成功建造并等待完成
#     """
#     return api.ensure_building_wait_buildself(building_name)


@produce_mcp.tool(name="ensure_can_produce_unit",description="确保能生产指定单位（会自动补齐依赖建筑并等待完成）")
def ensure_can_produce_unit(unit_name: str) -> bool:
    """
    Args:
        unit_name (str): 要生产的单位名称（中文）
    Returns:
        bool: 是否已准备好生产该单位
    """
    return produce_api.ensure_can_produce_unit(unit_name)


@produce_mcp.tool(name="deploy_mcv_and_wait",description="展开自己的基地车并等待指定时间")
def deploy_mcv_and_wait(wait_time: float = 1.0) -> str:
    """
    Args:
        wait_time (float): 展开后的等待时间（秒），默认 1.0
    """
    produce_api.deploy_mcv_and_wait(wait_time)
    return "ok"


def main():
    produce_mcp.settings.log_level = "critical"
    produce_mcp.settings.host = "0.0.0.0"
    produce_mcp.settings.port = 8003
    produce_mcp.run(transport="streamable-http")

if __name__ == "__main__":
    main()