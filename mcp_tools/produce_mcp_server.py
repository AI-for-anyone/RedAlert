from OpenRA_Copilot_Library import AsyncGameAPI
from OpenRA_Copilot_Library.models import Location, TargetsQueryParam, Actor,MapQueryResult
from typing import List, Dict, Any, Tuple
from mcp.server.fastmcp import FastMCP
from typing import Optional
import asyncio
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
    return cost_map.get(unify_unit_name(unit_type), {"cost": 999999, "time": 999999, "power": 999999})

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

@produce_mcp.tool(name="deploy_mcv_and_wait",description="展开/部署自己的基地车并等待指定时间")
async def deploy_mcv_and_wait(wait_time: float = 1.0) -> str:
    """
    Args:
        wait_time (float): 展开后的等待时间（秒），默认 1.0
    """
    await produce_api.deploy_mcv_and_wait(wait_time)
    return "ok"

@produce_mcp.tool(name="double_mine_start",description="使用固定开局：双矿开局")
async def double_mine_start():
    '''
    使用双矿开局
    '''
    produce_list: List[Tuple[str, int, bool]] = [
        ("发电厂", 1, True),
        ("矿场", 2, True),
        ("发电厂", 2, True),
        ("兵营", 1, True),
        ("步兵", 10, False),
        ("战车工厂", 1, True),
        ("雷达站", 1, True),
        ("矿车", 2, False),
        ("维修工厂", 1, True),
        ("科技中心", 1, True),
        ("空军基地", 1, True),
    ]
    await produce_api.deploy_mcv_and_wait(1.0)
    for unit_type, quantity, wait_flag in produce_list:
        loop_times = 0
        while loop_times < 100:
            loop_times += 1
            # 首先检测是否能生产
            if not await produce_api.can_produce(unit_type):
                await produce_api.ensure_can_build(unit_type)
                await asyncio.sleep(0.1)
                continue

            # 判断是否有足够资源
            base_info = await produce_api.player_base_info_query()
            try:
                cost = get_cost(unit_type).get('cost')
                power = get_cost(unit_type).get('power')
            except Exception:
                logger.error(f"未找到 {unit_type} 的生产成本信息")
                return f"未找到 {unit_type} 的生产成本信息"
            while base_info.Cash < quantity * cost or base_info.Power + quantity * power < 0:
                await asyncio.sleep(0.1)
                continue

            if wait_flag:
                await produce_api.produce_wait(unit_type, quantity)
                break
            else:
                await produce_api.produce(unit_type, quantity)
                break
        if loop_times >= 100:
            logger.error(f"生产 {unit_type} 失败")
            return f"生产 {unit_type} 失败"

def main():
    produce_mcp.settings.log_level = "debug"
    produce_mcp.settings.host = "0.0.0.0"
    produce_mcp.settings.port = 8003
    produce_mcp.run(transport="streamable-http")

async def test():
    await double_mine_start()

if __name__ == "__main__":
    # asyncio.run(test())
    main()