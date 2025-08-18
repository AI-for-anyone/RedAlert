from dataclasses import dataclass
from collections import deque
from OpenRA_Copilot_Library import AsyncGameAPI
from OpenRA_Copilot_Library.models import Location, NewTargetsQueryParam, Actor
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP
import asyncio
from monitor import update_actors_free_status, get_actors_status, get_monitor, get_all_enemy_actors_status

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logs import logger, get_logger, setup_logging, LogConfig, LogLevel
from task_scheduler import submit_task, wait_for_task

logger = get_logger("fight_mcp_server")

# 单例 GameAPI 客户端
fight_api = AsyncGameAPI(host="localhost", port=7445, language="zh")
#mcp实例
fight_mcp = FastMCP()

from model import ALL_INFANTRIES, ALL_TANKS, ALL_AIR

@fight_mcp.tool(name="army_attack", description="控制己方战斗单位攻击指定地点")
async def army_attack(
    source: NewTargetsQueryParam, 
    target: Location,
    perfer_attack_target: List[str] = []
) -> None:
    """
    Args:
        source (NewTargetsQueryParam): 执行攻击的对象
        target (Location): 被攻击的目标
        perfer_attack_target (List[str]): 优先攻击的目标类型列表
    Raises:
        GameAPIError: 当攻击命令执行失败时
    """
    try:
        actors = await fight_api.query_actor(source)
        logger.debug("army_attack-己方战斗单位: {0}".format(str([ac.actor_id for ac in actors])))
        await fight_api.move_units_by_location(target=source, location=target, attack_move=True)

        while True:
            actors = await fight_api.query_actor(source)
            logger.debug("army_attack-己方战斗单位: {0}".format(str([ac.actor_id for ac in actors])))
            center = get_center_location(actors)
            logger.debug("army_attack-己方战斗单位中心点: {0}".format(str(center)))
            dis = center.manhattan_distance(target)
            if dis < 20:
                break
            await asyncio.sleep(0.5)

    
        for perfer_attack_target in perfer_attack_target:
            while True:
                actors = await fight_api.query_actor(source)
                logger.debug("army_attack-己方战斗单位: {0}".format(str([ac.actor_id for ac in actors])))
                
                query = NewTargetsQueryParam(
                    type=[perfer_attack_target], 
                    faction=["敌方"], 
                    restrain=[{"visible": True}]
                )
                logger.debug("army_attack-查询目标: {0}".format(str(query)))
                # 查询目标
                targets = await fight_api.query_actor(query)
                logger.debug("army_attack-敌方目标: {0}".format(str([ac.actor_id for ac in targets])))
                if targets is None or len(targets) == 0:
                    logger.debug("army_attack-没有找到敌方目标: {0}".format(str(perfer_attack_target)))
                    break
                await fight_api.attack_target(attacker=source, target=NewTargetsQueryParam(actor_id=[ac.actor_id for ac in targets]))
                await asyncio.sleep(1)


        # update_actors_free_status(actors)   # 更新单位状态
        
    except Exception as e:
        logger.error("ARMY_ATTACK_ERROR", "控制己方战斗单位攻击指定目标时发生错误: {0}".format(str(e)))
        raise Exception("控制己方战斗单位攻击指定目标时发生错误: {0}".format(str(e)))

# 计算List[Actor]中心点
def get_center_location(actors: List[Actor]) -> Location:
    if actors is None or len(actors) == 0:
        return Location(0, 0)
    center_x = sum(u.position.x for u in actors) / len(actors)
    center_y = sum(u.position.y for u in actors) / len(actors)
    return Location(center_x, center_y)

# 军队聚团
@fight_mcp.tool(name="army_gather", description="军队聚团")
async def army_gather(source: NewTargetsQueryParam) -> None:
    # 查看所有单位
    units = await fight_api.query_actor(source)
    if units is None or len(units) == 0:
        return
    logger.debug("army_gather-军队: {0}".format(str([ac.actor_id for ac in units])))

    # 计算中心点位置
    center = get_center_location(units)
    logger.debug("army_gather-军队聚团: {0}".format(str(center)))
    try:
        await fight_api.move_units_by_location(target=source, location=center, attack_move=False)
    except Exception as e:
        raise logger.error("ARMY_ATTACK_ERROR", "控制己方战斗单位聚团时发生错误: {0}".format(str(e)))

def main():
    fight_mcp.settings.log_level = "critical"
    fight_mcp.settings.host = "0.0.0.0"
    fight_mcp.settings.port = 8001
    fight_mcp.run(transport="streamable-http")

async def main_async():
    m = get_monitor()
    await m.start(show=False)

    """主异步函数"""
    setup_logging(LogConfig(level=LogLevel.DEBUG))

    map_query = await fight_api.map_query()
    print(map_query.MapHeight, map_query.MapWidth)
    left = Location(x=0, y=map_query.MapWidth/2)

    task = await submit_task(army_attack,
        source=NewTargetsQueryParam(type=["雅克战机"], faction=["己方"], restrain=[{"visible": True}]),
        target=left,
        perfer_attack_target=["发电厂", "建造厂"]
    )

    await wait_for_task(task)

if __name__ == "__main__":
    main()
    # asyncio.run(main_async())    
    
