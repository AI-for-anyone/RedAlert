from dataclasses import dataclass
from collections import deque

from openai.types.beta import assistant
from OpenRA_Copilot_Library import AsyncGameAPI
from OpenRA_Copilot_Library.models import Location, NewTargetsQueryParam, Actor
from typing import List, Dict, Any, Optional, AsyncIterator
from mcp.server.fastmcp import FastMCP
import asyncio
import time
from monitor import update_actors_free_status, get_actors_status, get_monitor, get_all_enemy_actors_status
import model
from task_scheduler import TaskManager, TaskStatus, Task

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logs import logger, get_logger, setup_logging, LogConfig, LogLevel

logger = get_logger("fight_mcp_server")

# 单例 GameAPI 客户端
fight_api = AsyncGameAPI(host="localhost", port=7445, language="zh")
#mcp实例
fight_mcp = FastMCP()

from group import GroupMgr
_group_mgr = GroupMgr()

from model import ALL_INFANTRIES, ALL_TANKS, ALL_AIR, ALL_DIRECTIONS, ALL_BUILDING, FIGHT_UNITS

# 计算List[Actor]中心点
def get_center_location(actors: List[Actor]) -> Location:
    if actors is None or len(actors) == 0:
        return Location(0, 0)
    center_x = sum(u.position.x for u in actors) / len(actors)
    center_y = sum(u.position.y for u in actors) / len(actors)
    return Location(center_x, center_y)

# 收集军队
@fight_mcp.tool(name="army_gather", description="使军队聚团")
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

@fight_mcp.tool(name="army_move", description="指定某个编组移动到指定位置")
async def army_move(group_id: int, target: Location) -> bool:
    '''
    Args:
        group_id (int): 指定的编组ID
        target (Location): 目标位置
    Returns:
        bool: 操作是否成功
    '''
    logger.info("army_move-开始控制己方战斗编组{0}移动到指定位置{1}".format(group_id, target))
    _group_mgr.start_new_task(group_id)

    await fight_api.move_units_by_location(target=NewTargetsQueryParam(group_id=group_id), location=target, attack_move=False)
    return True

# 攻击
@fight_mcp.tool(name="army_attack_direction", description="指定某个编组往某个方向攻击见到的所有敌人")
async def army_attack_direction(
    group_id: int, 
    direction: str = "", 
    distance: int = 15
) -> Dict[str, Any]:
    '''
    Args:
        group_id (int): 指定的编组ID
        direction (str): 移动方向，必须在 {"左上", "上", "右上", "左", "右", "左下", "下", "右下"} 中
        distance (int): 移动距离
    '''
    logger.info("army_attack_direction-开始控制己方战斗编组{}攻击指定方向{}".format(group_id, direction))
    _group_mgr.start_new_task(group_id)
    
    await army_advanced_attack(
        _group_mgr.get_event(group_id),
        source=NewTargetsQueryParam(group_id=group_id),
        direction=direction,
        distance=distance
    )
    logger.info("army_attack_direction-控制己方战斗单位攻击指定目标成功")
    return {"result": "ok"}

@fight_mcp.tool(name="army_attack_location", description="指定某个编组往某个位置攻击见到的所有敌人, 可以指定优先攻击目标")
async def army_attack_location(
    group_id: int, 
    location: Location,
    perfer_attack_target: List[str] = []
) -> Dict[str, Any]:
    '''
    Args:
        group_id (int): 指定的编组ID
        location (Location): 攻击位置
        perfer_attack_target (List[str]): 优先攻击的目标类型列表
    '''
    logger.info("army_attack_location-控制己方战斗单位攻击指定位置{0}".format(location))

    perfer_attack_target:Dict[str, float] = {}
    for target in perfer_attack_target:
        perfer_attack_target[target] = 100.0

    _group_mgr.start_new_task(group_id)

    await army_advanced_attack(
        _group_mgr.get_event(group_id),
        source=NewTargetsQueryParam(group_id=group_id),
        location=location,
        target_type=perfer_attack_target
    )
    logger.info("army_attack_location-控制己方战斗单位攻击指定位置成功")
    return {"result": "ok"}

# 攻击指定目标
@fight_mcp.tool(name="army_attack_target_direction", description="指定某个编组往某个方向攻击见到的特定敌人")
async def army_attack_target_direction(
    group_id: int, 
    direction: str = "",
    distance: int = 15,
    target_type: List[str] = []
) -> Dict[str, Any]:
    '''
    Args:
        group_id (int): 指定的编组ID
        direction (str): 移动方向，必须在 {ALL_DIRECTIONS} 中
        distance (int): 移动距离
        target_type (List[str]): 攻击的目标类型列表
    '''
    _group_mgr.start_new_task(group_id)

    await army_advanced_attack(
        _group_mgr.get_event(group_id),
        source=NewTargetsQueryParam(group_id=group_id),
        direction=direction,
        distance=distance,
        target_type=target_type
    )
    logger.info("army_attack_target_direction-控制己方战斗单位攻击指定方向成功")
    return {"result": "ok"}

# 攻击指定位置
@fight_mcp.tool(name="army_attack_target_location", description="指定某个编组往某个位置攻击见到的特定敌人")
async def army_attack_target_location(
    group_id: int, 
    location: Location,
    target_type: List[str] = []
) -> Dict[str, Any]:
    '''
    Args:
        group_id (int): 指定的编组ID
        location (Location): 攻击位置
        target_type (List[str]): 攻击的目标类型列表
    '''
    _group_mgr.start_new_task(group_id)

    await army_advanced_attack(
        _group_mgr.get_event(group_id),
        source=NewTargetsQueryParam(group_id=group_id),
        location=location,
        target_type=target_type
    )
    logger.info("army_attack_target_location-控制己方战斗单位攻击指定位置成功")
    return {"result": "ok"}


async def formation_adjustment(
    units: List[Actor],
    after_center: Location
):
    tanks: List[Actor] = []
    others: List[Actor] = []
    for unit in units:
        if unit.type in ["重型坦克", "超重型坦克"]:
            tanks.append(unit)
        else:
            others.append(unit)

    if len(tanks) == 0 or len(others) == 0:
        await fight_api.move_units_by_location(NewTargetsQueryParam(actor_id=[ac.actor_id for ac in units]), after_center)
        return

    tank_center = get_center_location(tanks)
    other_center = get_center_location(others)

    if after_center.euclidean_distance(tank_center) > after_center.euclidean_distance(other_center):
        logger.debug("formation_adjustment-坦克前进，其他聚团")
        await fight_api.move_units_by_location(NewTargetsQueryParam(actor_id=[ac.actor_id for ac in tanks]), after_center)
        await fight_api.move_units_by_location(NewTargetsQueryParam(actor_id=[ac.actor_id for ac in others]), other_center)
        await asyncio.sleep(1)
        await fight_api.move_units_by_location(NewTargetsQueryParam(actor_id=[ac.actor_id for ac in units]), after_center)
    else:
        logger.debug("formation_adjustment-全部前进")
        await fight_api.move_units_by_location(NewTargetsQueryParam(actor_id=[ac.actor_id for ac in units]), after_center)

    

# 智能攻击
async def army_advanced_attack(
    cancel_evt: asyncio.Event,
    source: NewTargetsQueryParam, 
    direction: str = "", 
    location: Location|None = None, 
    distance: int = 15,
    perfer_type_priority: Dict[str, float]|None = None,
    target_type: List[str]|None = None,
) -> None:
    '''
    Args:
        source (NewTargetsQueryParam): 指定单位要攻击的单位
        direction (str): 攻击方向，必须在 {"左上", "上", "右上", "左", "右", "左下", "下", "右下"} 中
        location (Location): 攻击位置
        distance (int): 攻击距离
    '''
    try:
        # 获取所有攻击单位
        units = await fight_api.query_actor(source)
        # 过滤
        units = [ac for ac in units if ac.type in ALL_INFANTRIES or ac.type in ALL_TANKS or ac.type in ALL_AIR]
        if units is None or len(units) == 0:
            logger.info("army_attack-没有找到己方战斗单位: {0}".format(str(source)))
            return

        # 计算中心点位置
        before_center = get_center_location(units)
        logger.debug("army_attack-己方战斗单位中心点: {0}".format(str(before_center)))

        if location is None:
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
                    logger.info("方向{0}不在{1}中".format(str(direction), ALL_DIRECTIONS))
                    return
        else:
            relative_pos = location
        
        # move units to relative_pos
        await fight_api.move_units_by_location(NewTargetsQueryParam(actor_id=[ac.actor_id for ac in units]), relative_pos)
        
        async def _attack_direction(cancel_evt: asyncio.Event):
            our_units: Dict[int, model.own_unit] = {}
            for u in units:
                our_units[u.actor_id] = model.own_unit(u.actor_id, u.type, u.position, u.hp, u.max_hp)
            enemy_units: Dict[int, model.enemy_unit] = {}

            enemy_type = []
            if target_type is not None and len(target_type) > 0:
                enemy_type = target_type
            else:
                enemy_type = FIGHT_UNITS + ALL_BUILDING + ["采矿车"]
                
            while not cancel_evt.is_set():
                # center
                new_actors = await fight_api.query_actor(NewTargetsQueryParam(actor_id=[actor_id for actor_id in our_units.keys()]))
                if new_actors is None or len(new_actors) == 0:
                    logger.info("没有己方目标")
                    break
                center = get_center_location(new_actors)

                new_units: Dict[int, model.own_unit] = {}
                for new_actor in new_actors:
                    new_units[new_actor.actor_id] = our_units[new_actor.actor_id]
                    new_units[new_actor.actor_id].hp = new_actor.hp
                    new_units[new_actor.actor_id].location = new_actor.position
                our_units = new_units

                # 查看所有敌人
                try:
                    enemy_actors = await fight_api.query_actor(NewTargetsQueryParam(
                        faction="敌方", 
                        type=enemy_type,
                        restrain=[{"distance": 15}],
                        location=center
                    ))  
                except Exception as e:
                    logger.info("ATTACK_DIRECTION_ERROR-查询敌方单位失败: {0}".format(str(e)))
                    enemy_actors = None
                if enemy_actors is None or len(enemy_actors) == 0:
                    logger.debug("没有敌方目标")
                    if center.manhattan_distance(relative_pos) < 7:
                        logger.info("己方单位已到达目标位置")
                        break
                    # 这里调整阵型
                    await formation_adjustment(units, relative_pos)
                    await asyncio.sleep(1)
                    continue
                logger.debug("attack_direction-敌方目标: {0}".format(str([[ac.actor_id, ac.type] for ac in enemy_actors])))

                # 记录所有敌方单位
                new_enemy_units: Dict[int, model.enemy_unit] = {}
                for enemy_actor in enemy_actors:
                    if enemy_actor.actor_id in enemy_units.keys():
                        new_enemy_units[enemy_actor.actor_id] = enemy_units[enemy_actor.actor_id]
                        new_enemy_units[enemy_actor.actor_id].hp = enemy_actor.hp
                        new_enemy_units[enemy_actor.actor_id].location = enemy_actor.position
                    else:
                        new_enemy_units[enemy_actor.actor_id] = model.enemy_unit(
                            enemy_actor.actor_id, 
                            enemy_actor.type, 
                            enemy_actor.position, 
                            enemy_actor.hp, 
                            enemy_actor.max_hp, 
                            assigned_attack_units=[]
                        )
                    new_enemy_units[enemy_actor.actor_id].assigned_attack_units = [u for u in new_enemy_units[enemy_actor.actor_id].assigned_attack_units if u in our_units.keys()]
                enemy_units = new_enemy_units

                # 每个单位分配目标
                for own_unit in our_units.values():
                    # 残血后退
                    if own_unit.hp < own_unit.max_hp * 0.5 and not own_unit.retreated:
                        own_unit.retreated = True
                        if own_unit.target is not None:
                            if own_unit.target in enemy_units.keys():
                                try:
                                    enemy_units[own_unit.target].assigned_attack_units.remove(own_unit.actor_id)
                                except Exception:
                                    logger.error("ATTACK_DIRECTION_ERROR-删除敌方单位已分配单位出错, {0}-{1}".format(str(enemy_units[own_unit.target].assigned_attack_units), str(own_unit)))
                            own_unit.target = None
                        try:
                            await fight_api.move_units_by_location(
                                target=NewTargetsQueryParam(actor_id=[own_unit.actor_id]),
                                location=before_center,
                                attack_move=False
                            )
                        except Exception as e:
                            logger.error("ATTACK_DIRECTION_ERROR-移动单位失败: {0}".format(str(e)))
                        continue

                    # 如果有目标
                    if own_unit.target is not None and own_unit.target in enemy_units.keys():
                        continue
                    
                    # 如果没有目标
                    best_target = [0, 0.0] # [target_actor_id, priority]
                    for enemy_unit in enemy_units.values():
                        try:
                            score = model.effective_damage_score(own_unit, enemy_unit, our_units, perfer_type_priority)
                        except Exception as e:
                            logger.warning("ATTACK_DIRECTION_ERROR-计算己方单位对敌方单位的优先级时发生错误")
                            score = 0
                        logger.debug("attack_direction-己方单位{0}对敌方单位{1}的优先级: {2}".format(str(own_unit.actor_id), str(enemy_unit.actor_id), str(score)))
                        if score > best_target[1]:
                            best_target = [enemy_unit.actor_id, score]
                    
                    if best_target[0] != 0:
                        own_unit.target = best_target[0]
                        enemy_units[best_target[0]].assigned_attack_units.append(own_unit.actor_id)
                
                # 按照优先级分配目标
                for enemy_unit in enemy_units.values():
                    if len(enemy_unit.assigned_attack_units) > 0:
                        await fight_api.attack_target(NewTargetsQueryParam(actor_id=enemy_unit.assigned_attack_units), NewTargetsQueryParam(actor_id=[enemy_unit.actor_id]))
                await asyncio.sleep(1)
            if cancel_evt.is_set():
                logger.info("army_attack-中止")
                return
        try:
            await asyncio.wait_for(_attack_direction(cancel_evt), timeout=180)
        except asyncio.TimeoutError:
            logger.warning("ATTACK_DIRECTION_TIMEOUT 控制指定单位攻击指定方向超时，已自动退出")
            return

    except Exception as e:
        raise logger.error("ATTACK_DIRECTION_ERROR-控制指定单位攻击指定方向时发生错误: {0}".format(str(e)))

def main():
    setup_logging(LogConfig(level=LogLevel.DEBUG, enable_console_logging=True))
    fight_mcp.settings.log_level = "debug"
    fight_mcp.settings.host = "0.0.0.0"
    fight_mcp.settings.port = 8001
    fight_mcp.run(transport="streamable-http")
    
if __name__ == "__main__":
    main()
