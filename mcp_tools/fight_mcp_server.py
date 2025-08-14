from OpenRA_Copilot_Library import GameAPI
from OpenRA_Copilot_Library.models import Location, TargetsQueryParam, Actor,MapQueryResult
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP
from typing import Optional


# 单例 GameAPI 客户端
fight_api = GameAPI(host="localhost", port=7445, language="zh")
#mcp实例
fight_mcp = FastMCP()

# —— 攻击与占领 ——
@fight_mcp.tool(name="attack", description="发起一次攻击")
def attack(attacker_id: int, target_id: int) -> bool:
    '''攻击指定目标

    Args:
        attacker (Actor): 发起攻击的Actor
        target (Actor): 被攻击的目标

    Returns:
        bool: 是否成功发起攻击(如果目标不可见，或者不可达，或者攻击者已经死亡，都会返回false)

    Raises:
        GameAPIError: 当攻击命令执行失败时
    '''
    atk = Actor(attacker_id); tgt = Actor(target_id)
    return fight_api.attack_target(atk, tgt)

@fight_mcp.tool(name="occupy", description="占领目标")
def occupy(occupiers: List[int], targets: List[int]) -> str:
    '''占领目标

    Args:
        occupiers (List[Actor]): 执行占领的Actor列表
        targets (List[Actor]): 被占领的目标列表

    Raises:
        GameAPIError: 当占领行动失败时
    '''
    occ = [Actor(i) for i in occupiers]
    tgt = [Actor(i) for i in targets]
    fight_api.occupy_units(occ, tgt)
    return "ok"


@fight_mcp.tool(name="occupy_units",description="占领指定目标单位")
def occupy_units(occupier_ids: List[int], target_ids: List[int]) -> str:
    """
    Args:
        occupier_ids (List[int]): 发起占领的单位 ID 列表
        target_ids (List[int]): 被占领的目标单位 ID 列表
    Returns:
        str: 操作完成返回 "ok"
    """
    occupiers = [Actor(i) for i in occupier_ids]
    targets = [Actor(i) for i in target_ids]
    fight_api.occupy_units(occupiers, targets)
    return "ok"



@fight_mcp.tool(name="attack_target",description="由指定单位发起对目标单位的攻击")
def attack_target(attacker_id: int, target_id: int) -> bool:
    """
    Args:
        attacker_id (int): 发起攻击的单位 ID
        target_id (int): 被攻击的目标单位 ID
    Returns:
        bool: 是否成功发起攻击
    """
    attacker = Actor(attacker_id)
    target = Actor(target_id)
    return fight_api.attack_target(attacker, target)


@fight_mcp.tool(name="can_attack_target",description="检查指定单位是否可以攻击目标单位")
def can_attack_target(attacker_id: int, target_id: int) -> bool:
    """
    Args:
        attacker_id (int): 攻击者的单位 ID
        target_id (int): 目标单位的 ID
    Returns:
        bool: 如果攻击者可以攻击目标（目标可见），返回 True，否则 False
    """
    attacker = Actor(attacker_id)
    target = Actor(target_id)
    return fight_api.can_attack_target(attacker, target)


@fight_mcp.tool(name="repair_units",description="修复一批单位")
def repair_units(actor_ids: List[int]) -> str:
    """
    Args:
        actor_ids (List[int]): 要修复的单位 ID 列表
    Returns:
        str: 操作完成返回 "ok"
    """
    actors = [Actor(i) for i in actor_ids]
    fight_api.repair_units(actors)
    return "ok"


@fight_mcp.tool(name="stop_units",description="停止一批单位当前行动")
def stop_units(actor_ids: List[int]) -> str:
    """
    Args:
        actor_ids (List[int]): 要停止的单位 ID 列表
    Returns:
        str: 操作完成返回 "ok"
    """
    actors = [Actor(i) for i in actor_ids]
    fight_api.stop(actors)
    return "ok"


def main():
    fight_mcp.settings.log_level = "critical"
    fight_mcp.settings.host = "0.0.0.0"
    fight_mcp.settings.port = 8001
    fight_mcp.run(transport="sse")

if __name__ == "__main__":
    main()