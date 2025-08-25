from OpenRA_Copilot_Library import AsyncGameAPI
from OpenRA_Copilot_Library.models import Location, TargetsQueryParam, Actor,MapQueryResult
from typing import List, Dict, Any, Tuple
from mcp.server.fastmcp import FastMCP
from typing import Optional
from utils import unify_unit_name, unify_queue_name
import logging

logger = logging.getLogger(__name__)

# 单例 GameAPI 客户端
produce_api = AsyncGameAPI(host="localhost", port=7445, language="zh")
#mcp实例
produce_mcp = FastMCP()

# 生产单位的成本信息
cost_map = {
    unify_unit_name("发电厂"): {"cost": 150, "time": 2, "power": 100},
    unify_unit_name("兵营"): {"cost": 250, "time": 3, "power": -20},
    unify_unit_name("矿场"): {"cost": 700, "time": 9, "power": -30},
    unify_unit_name("车间"): {"cost": 1000, "time": 12, "power": -30},
    unify_unit_name("雷达"): {"cost": 750, "time": 9, "power": -40},
    unify_unit_name("维修中心"): {"cost": 600, "time": 8, "power": -30},
    unify_unit_name("核电站"): {"cost": 250, "time": 3, "power": 200},
    unify_unit_name("机场"): {"cost": 200, "time": 3, "power": 200},
    unify_unit_name("科技中心"): {"cost": 750, "time": 9, "power": -100},
    unify_unit_name("火焰塔"): {"cost": 300, "time": 4, "power": -20},
    unify_unit_name("电塔"): {"cost": 600, "time": 8, "power": -100},
    unify_unit_name("防空塔"): {"cost": 350, "time": 5, "power": -40},
    unify_unit_name("步兵"): {"cost": 50, "time": 1, "power": 0},
    unify_unit_name("火箭兵"): {"cost": 150, "time": 2, "power": 0},
    unify_unit_name("矿车"): {"cost": 550, "time": 7, "power": 0},
    unify_unit_name("防空车"): {"cost": 300, "time": 4, "power": 0},
    unify_unit_name("重坦"): {"cost": 575, "time": 7, "power": 0},
    unify_unit_name("v2"): {"cost": 450, "time": 6, "power": 0},
    unify_unit_name("猛犸"): {"cost": 1000, "time": 12, "power": 0},
    unify_unit_name("雅克"): {"cost": 675, "time": 9, "power": 0},
    unify_unit_name("米格"): {"cost": 1000, "time": 12, "power": 0},
}

def get_cost(unit_type: str) -> Dict[str, int]:
    return cost_map.get(unify_unit_name(unit_type), None)

async def get_produce_remain_resource() -> Tuple[int, int]:
    '''
    获取生产完成后剩余的资源
    Returns:
        Tuple[int, int]: (money, power)
    '''
    base_info = await produce_api.player_base_info_query()
    money = power = 0
    for queue_type in ['Building', 'Defense', 'Infantry', 'Vehicle', 'Aircraft']:
        queue_info = await produce_api.query_production_queue(unify_queue_name(queue_type))
        items = queue_info.get('queue_items', None)
        if items is None:
            raise ValueError(f"未找到 {queue_type} 的生产队列信息")
        for item in items:
            if item.get('done', False) or item.get('paused', False):
                continue
            name = item.get('chineseName', None)
            if name is None:
                raise ValueError(f"未找到 item 的中文名称")
            cost = get_cost(name)
            if cost is None:
                raise ValueError(f"未找到 {name} 的生产成本信息")
            power += cost.get('power', 0)
            money += cost.get('cost', 0)
    return (base_info.Cash + base_info.Resources - money, base_info.PowerProvided - base_info.PowerDrained + power)


# @produce_mcp.tool(name="get_player_base_info", description="返回玩家资源信息")
# async def get_player_base_info() -> Dict[str, Any]:
#     """返回玩家资源信息"""
#     info = await produce_api.player_base_info_query()
#     return {"cash":info.Cash, "resources":info.Resources, "powerDrained": info.PowerDrained, "powerProvided": info.PowerProvided}


@produce_mcp.tool(name="produce", description="生产指定类型和数量的单位，返回生产任务 ID")
async def produce(unit_type: str, quantity: int = 1, auto_place: bool = True) -> int:
    '''生产指定数量的Actor

    Args:
        unit_type (str): Actor类型
        quantity (int): 生产数量
        auto_place (bool, optional): 是否在生产完成后使用随机位置自动放置建筑，仅对建筑类型有效

    Returns:
        int: 生产任务的 waitId
        None: 如果任务创建失败
    '''

    wait_id = await produce_api.produce(unify_unit_name(unit_type), quantity, auto_place_building=auto_place)
    return wait_id or -1


@produce_mcp.tool(name="can_produce", description="检查是否可生产某类型单位")
async def can_produce(unit_type: str, quantity: int = 1, permit_resource_shortage: bool = False, permit_power_shortage: bool = False) -> bool:
    '''检查是否可以生产指定类型的Actor

    Args:
        unit_type (str): Actor类型，必须在 {ALL_UNITS} 中
        quantity (int): 生产数量
        permit_resource_shortage (bool, optional): 是否允许资源短缺
        permit_power_shortage (bool, optional): 是否允许电力短缺
    Returns:
        bool: 是否可以生产
    '''
    
    produce_able = await produce_api.can_produce(unify_unit_name(unit_type))
    if permit_power_shortage and permit_resource_shortage:
        return produce_able
    
    cost = get_cost(unit_type)
    if cost is None:
        raise ValueError(f"未找到 {unit_type} 的生产成本信息")
    remain_money = remain_power = 0
    if not permit_power_shortage or not permit_resource_shortage:
        remain_money, remain_power = await get_produce_remain_resource()
        logger.info(f"当前电力: {remain_power}, 当前资源: {remain_money}")
    if not permit_power_shortage and remain_power + quantity * cost.get('power', 0) < 0:
        logger.info("电力不足")
        return False
    if not permit_resource_shortage and remain_money - quantity * cost.get('cost', 0) < 0:
        logger.info("资源不足")
        return False
    return True
    

@produce_mcp.tool(name="produce_wait", description="发起并等待生产完成")
async def produce_wait(unit_type: str, quantity: int = 1, auto_place: bool = True) -> bool:
    '''生产指定数量的Actor并等待生产完成

    Args:
        unit_type (str): Actor类型
        quantity (int): 生产数量
        auto_place (bool, optional): 是否在生产完成后使用随机位置自动放置建筑，仅对建筑类型有效

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