from .state import GlobalState
from .mcp_client import UnitMCPClient, FightMCPClient
from logs import get_logger
import re

logger = get_logger("unit_control")

class UnitControlNode():
    def __init__(self):
        self.unit_client = UnitMCPClient()
        self.fight_client = FightMCPClient()

    def unit_control_node(self, global_state: GlobalState) -> GlobalState:
        logger.info(f"执行单位控制,当前GlobalState: {global_state}")
        
        cmd = global_state["input_cmd"]
        logger.info(f"处理单位控制命令: {cmd}")
        
        try:
            # 根据命令类型调用相应的MCP工具
            if "移动" in cmd:
                # 提取单位ID和目标坐标
                actor_ids = [int(x) for x in re.findall(r'单位(\d+)', cmd)]
                coords = re.findall(r'(\d+)[,，]\s*(\d+)', cmd)
                attack_move = "攻击移动" in cmd or "attack move" in cmd.lower()
                
                if not actor_ids:
                    actor_ids = [1]  # 默认单位ID
                if coords:
                    x, y = int(coords[0][0]), int(coords[0][1])
                else:
                    x, y = 100, 100  # 默认坐标
                
                success = self.unit_client.move_units(actor_ids, x, y, attack_move)
                logger.info(f"移动单位{actor_ids}到({x}, {y})，攻击移动: {attack_move}，结果: {success}")
                
            elif "攻击" in cmd:
                # 提取攻击者和目标ID
                attacker_match = re.search(r'单位(\d+)', cmd)
                target_match = re.search(r'目标(\d+)', cmd)
                
                attacker_id = int(attacker_match.group(1)) if attacker_match else 1
                target_id = int(target_match.group(1)) if target_match else 2
                
                success = self.fight_client.attack_target(attacker_id, target_id)
                logger.info(f"单位{attacker_id}攻击目标{target_id}，结果: {success}")
                
            elif "查询单位" in cmd or "查找单位" in cmd or "查看单位" in cmd:
                # 提取查询条件
                faction_map = {"盟军": "盟军", "苏军": "苏军", "中立": "中立", "敌军": "苏军"}
                faction = "盟军"  # 默认
                for chinese, english in faction_map.items():
                    if chinese in cmd:
                        faction = english
                        break
                
                # 提取单位类型
                unit_types = []
                if "步兵" in cmd:
                    unit_types.append("步兵")
                elif "坦克" in cmd:
                    unit_types.append("坦克")
                elif "建筑" in cmd:
                    unit_types.append("建筑")
                
                range_param = "screen"  # 默认屏幕范围
                if "全图" in cmd:
                    range_param = "all"
                elif "附近" in cmd:
                    range_param = "nearby"
                
                units = self.unit_client.query_actor(
                    unit_types, faction, range_param, [{"visible": True}]
                )
                logger.info(f"查询{faction}{unit_types}单位，范围{range_param}，结果: {len(units)}个单位")
                
            elif "占领" in cmd:
                # 提取占领者和目标ID
                occupier_ids = [int(x) for x in re.findall(r'单位(\d+)', cmd)]
                target_ids = [int(x) for x in re.findall(r'目标(\d+)', cmd)]
                
                if not occupier_ids:
                    occupier_ids = [1]
                if not target_ids:
                    target_ids = [2]
                
                success = self.fight_client.occupy_units(occupier_ids, target_ids)
                logger.info(f"单位{occupier_ids}占领目标{target_ids}，结果: {success}")
                
            elif "修复" in cmd:
                # 提取要修复的单位ID
                actor_ids = [int(x) for x in re.findall(r'单位(\d+)', cmd)]
                if not actor_ids:
                    actor_ids = [1]
                
                success = self.fight_client.repair_units(actor_ids)
                logger.info(f"修复单位{actor_ids}，结果: {success}")
                
            elif "停止" in cmd:
                # 提取要停止的单位ID
                actor_ids = [int(x) for x in re.findall(r'单位(\d+)', cmd)]
                if not actor_ids:
                    actor_ids = [1]
                
                success = self.fight_client.stop_units(actor_ids)
                logger.info(f"停止单位{actor_ids}行动，结果: {success}")
                
            elif "选中" in cmd or "选择" in cmd:
                # 选中单位
                unit_types = []
                if "步兵" in cmd:
                    unit_types.append("步兵")
                
                success = self.unit_client.select_units(
                    unit_types, "盟军", "screen", [{"visible": True}]
                )
                logger.info(f"选中{unit_types}单位，结果: {success}")
                
            elif "编组" in cmd or "分组" in cmd:
                # 编组单位
                actor_ids = [int(x) for x in re.findall(r'单位(\d+)', cmd)]
                group_match = re.search(r'组(\d+)', cmd)
                
                if not actor_ids:
                    actor_ids = [1]
                group_id = int(group_match.group(1)) if group_match else 1
                
                success = self.unit_client.form_group(actor_ids, group_id)
                logger.info(f"将单位{actor_ids}编为第{group_id}组，结果: {success}")
                
            elif "展开" in cmd or "部署" in cmd:
                # 展开单位
                actor_ids = [int(x) for x in re.findall(r'单位(\d+)', cmd)]
                if not actor_ids:
                    actor_ids = [1]
                
                success = self.unit_client.deploy_units(actor_ids)
                logger.info(f"展开单位{actor_ids}，结果: {success}")
            
            else:
                logger.info(f"未识别的单位控制命令: {cmd}")
                
            global_state["state"] = global_state["next_state"]
            
        except Exception as e:
            logger.error(f"单位控制执行失败: {e}")
            
        return global_state
