from .state import GlobalState
from .mcp_client import ProduceMCPClient
from logs import get_logger
import re

logger = get_logger("production")

class ProductionNode():
    def __init__(self):
        self.produce_client = ProduceMCPClient()

    def production_node(self, global_state: GlobalState) -> GlobalState:
        logger.info(f"执行生产管理")
        
        cmd = global_state["input_cmd"]
        logger.info(f"处理生产命令: {cmd}")
        
        try:
            # 根据命令类型调用相应的MCP工具
            if "生产" in cmd or "建造" in cmd:
                # 提取单位类型和数量
                unit_match = re.search(r'(步兵|工程师|狗|坦克|基地车|发电厂|兵营|战车工厂)', cmd)
                quantity_match = re.search(r'(\d+)', cmd)
                
                unit_type = unit_match.group(1) if unit_match else "步兵"
                quantity = int(quantity_match.group(1)) if quantity_match else 1
                
                wait_id = self.produce_client.produce(unit_type, quantity)
                logger.info(f"生产{quantity}个{unit_type}，任务ID: {wait_id}")
                
            elif "队列" in cmd or "查询生产" in cmd:
                # 提取队列类型
                queue_type_map = {
                    "建筑": "Building",
                    "防御": "Defense", 
                    "步兵": "Infantry",
                    "车辆": "Vehicle",
                    "飞机": "Aircraft",
                    "海军": "Naval"
                }
                
                queue_type = "Infantry"  # 默认
                for chinese, english in queue_type_map.items():
                    if chinese in cmd:
                        queue_type = english
                        break
                
                queue_info = self.produce_client.query_production_queue(queue_type)
                logger.info(f"查询{queue_type}队列结果: {queue_info}")
                
            elif "检查" in cmd and ("可生产" in cmd or "能否生产" in cmd):
                # 提取单位类型
                unit_match = re.search(r'(步兵|工程师|狗|坦克|基地车|发电厂|兵营|战车工厂)', cmd)
                unit_type = unit_match.group(1) if unit_match else "步兵"
                
                can_produce = self.produce_client.can_produce(unit_type)
                logger.info(f"检查{unit_type}可生产性结果: {can_produce}")
                
            elif "暂停" in cmd or "取消" in cmd or "继续" in cmd:
                # 管理生产队列
                action_map = {"暂停": "pause", "取消": "cancel", "继续": "resume"}
                action = "pause"
                for chinese, english in action_map.items():
                    if chinese in cmd:
                        action = english
                        break
                
                queue_type = "Infantry"  # 默认，实际应该从命令中提取
                success = self.produce_client.manage_production(queue_type, action)
                logger.info(f"管理生产队列({action})结果: {success}")
            
            else:
                logger.info(f"未识别的生产命令: {cmd}")
            
            global_state["state"] = global_state["next_state"]
            
        except Exception as e:
            logger.error(f"生产管理执行失败: {e}")
            
        return global_state
