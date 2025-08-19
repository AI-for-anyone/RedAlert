from OpenRA_Copilot_Library import AsyncGameAPI
from OpenRA_Copilot_Library.models import Location, TargetsQueryParam, Actor,MapQueryResult
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP
from typing import Optional
from utils import unify_unit_name, unify_queue_name

# 单例 GameAPI 客户端
produce_api = AsyncGameAPI(host="localhost", port=7445, language="zh")
#mcp实例
produce_mcp = FastMCP()

# 生产单位的成本信息
cost_map = {
    "电厂": {"cash": 150, "time": 2, "power": 100},
    "兵营": {"cash": 250, "time": 3, "power": -20},
    "矿场": {"cash": 700, "time": 9, "power": -30},
    "车间": {"cash": 1000, "time": 12, "power": -30},
    "雷达": {"cash": 750, "time": 9, "power": -40},
    "维修中心": {"cash": 600, "time": 8, "power": -30},
    "核电": {"cash": 250, "time": 3, "power": 200},
    "机场": {"cash": 200, "time": 3, "power": 200},
    "科技中心": {"cash": 750, "time": 9, "power": -100},
    "火焰塔": {"cash": 300, "time": 4, "power": -20},
    "电塔": {"cash": 600, "time": 8, "power": -100},
    "防空塔": {"cash": 350, "time": 5, "power": -40},
    "步兵": {"cash": 50, "time": 1, "power": 0},
    "火箭兵": {"cash": 150, "time": 2, "power": 0},
    "矿车": {"cash": 550, "time": 7, "power": 0},
    "防空车": {"cash": 300, "time": 4, "power": 0},
    "重坦": {"cash": 575, "time": 7, "power": 0},
    "v2": {"cash": 450, "time": 6, "power": 0},
    "猛犸": {"cash": 1000, "time": 12, "power": 0},
    "雅克": {"cash": 675, "time": 9, "power": 0},
    "米格": {"cash": 1000, "time": 12, "power": 0},
}


def get_produce_cost(unit_type: str) -> (Dict[str, Any],bool):
    '''获取生产单位的成本信息


    Args:
        unit_type (str): Actor类型
    Returns:
        dict: 包含生产成本信息的字典
        bool: 是否获取到
    '''
    unit_type = unify_unit_name(unit_type)
    return cost_map.get(unit_type, {}), unit_type in cost_map


@produce_mcp.tool(name="get_resource_info", description="返回玩家资源信息")
async def get_resource_info() -> Dict[str, Any]:
    
    info = await produce_api.player_base_info_query()
    return info


@produce_mcp.tool(name="produce", description="生产指定类型和数量的单位，返回生产任务 ID")
async def produce(unit_type: str, quantity: int) -> int:
    '''生产指定数量的Actor

    Args:
        unit_type (str): Actor类型
        quantity (int): 生产数量
        auto_place_building (bool, optional): 是否在生产完成后使用随机位置自动放置建筑，仅对建筑类型有效

    Returns:
        int: 生产任务的 waitId
        None: 如果任务创建失败
    '''

    wait_id = await produce_api.produce(unify_unit_name(unit_type), quantity, auto_place_building=True)
    return wait_id or -1


@produce_mcp.tool(name="can_produce", description="检查是否可生产某类型单位")
async def can_produce(unit_type: str) -> bool:
    '''检查是否可以生产指定类型的Actor

    Args:
        unit_type (str): Actor类型，必须在 {ALL_UNITS} 中
    Returns:
        bool: 是否可以生产
    '''
    return await produce_api.can_produce(unify_unit_name(unit_type), quantity)


@produce_mcp.tool(name="produce_wait", description="发起并等待生产完成")
async def produce_wait(unit_type: str, quantity: int, auto_place: bool = True) -> bool:
    '''生产指定数量的Actor并等待生产完成

    Args:
        unit_type (str): Actor类型
        quantity (int): 生产数量
        auto_place_building (bool, optional): 是否在生产完成后使用随机位置自动放置建筑，仅对建筑类型有效

    Raises:
        GameAPIError: 当生产或等待过程中发生错误时
    '''
    try:
        await produce_api.produce_wait(unit_type, quantity, auto_place)
        return True
    except Exception:
        return False

@produce_mcp.tool(name="is_ready",description="检查指定生产任务是否已完成")
async def is_ready(wait_id: int) -> bool:
    """
    Args:
        wait_id (int): 生产任务的 ID
    Returns:
        bool: 生产任务是否已完成
    """
    return await produce_api.is_ready(wait_id)

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
async def query_production_queue(queue_type: str) -> Dict[str, Any]:
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
    return await produce_api.query_production_queue(unify_queue_name(queue_type))

@produce_mcp.tool(name="place_building",description="放置生产队列中已就绪的建筑")
async def place_building(queue_type: str, x: Optional[int] = None, y: Optional[int] = None) -> str:
    """
    Args:
        queue_type (str): 队列类型，必须是 'Building', 'Defense', 'Infantry', 'Vehicle', 'Aircraft', 或 'Naval'
        x (Optional[int]): 建筑放置 X 坐标（如不提供则自动选址）
        y (Optional[int]): 建筑放置 Y 坐标（如不提供则自动选址）
    Returns:
        str: 操作完成时返回 "ok"
    """
    loc = Location(x, y) if x is not None and y is not None else None
    await produce_api.place_building(unify_queue_name(queue_type), loc)
    return "ok"

@produce_mcp.tool(name="manage_production",description="管理生产队列中的项目（暂停、取消或继续）")
async def manage_production(queue_type: str, action: str) -> str:
    """
    Args:
        queue_type (str): 队列类型，必须是 'Building', 'Defense', 'Infantry', 'Vehicle', 'Aircraft' 或 'Naval'
        action (str): 操作类型，必须是 'pause', 'cancel' 或 'resume'
    Returns:
        str: 操作完成时返回 "ok"
    """
    await produce_api.manage_production(unify_queue_name(queue_type), action)
    return "ok"


@produce_mcp.tool(name="ensure_can_build_wait",description="确保指定建筑已存在，若不存在则递归建造其所有依赖并等待完成")
async def ensure_can_build_wait(building_name: str) -> bool:
    """
    Args:
        building_name (str): 建筑名称（中文）
    Returns:
        bool: 是否已拥有该建筑或成功建造完成
    """
    return await produce_api.ensure_can_build_wait(unify_unit_name(building_name))


@produce_mcp.tool(name="ensure_can_produce_unit",description="确保能生产指定单位（会自动补齐依赖建筑并等待完成）")
async def ensure_can_produce_unit(unit_name: str) -> bool:
    """
    Args:
        unit_name (str): 要生产的单位名称（中文）
    Returns:
        bool: 是否已准备好生产该单位
    """
    return await produce_api.ensure_can_produce_unit(unify_unit_name(unit_name))


@produce_mcp.tool(name="deploy_mcv_and_wait",description="展开/部署自己的基地车并等待指定时间")
async def deploy_mcv_and_wait(wait_time: float = 1.0) -> str:
    """
    Args:
        wait_time (float): 展开后的等待时间（秒），默认 1.0
    """
    await produce_api.deploy_mcv_and_wait(wait_time)
    return "ok"




def main():
    produce_mcp.settings.log_level = "debug"
    produce_mcp.settings.host = "0.0.0.0"
    produce_mcp.settings.port = 8003
    produce_mcp.run(transport="streamable-http")

if __name__ == "__main__":
    main()