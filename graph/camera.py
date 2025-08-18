from .state import GlobalState
from .mcp_client import CameraMCPClient
from logs import get_logger
import re

logger = get_logger("camera")

class CameraNode():
    def __init__(self):
        self.camera_client = CameraMCPClient()

    def camera_node(self, global_state: GlobalState) -> GlobalState:
        logger.info(f"执行地图视角控制,当前GlobalState: {global_state}")
        
        cmd = global_state["input_cmd"]
        logger.info(f"处理相机控制命令: {cmd}")
        
        try:
            # 根据命令类型调用相应的MCP工具
            if "移动镜头" in cmd or "移动相机" in cmd:
                # 尝试提取坐标信息
                coords = re.findall(r'(\d+)[,，]\s*(\d+)', cmd)
                if coords:
                    x, y = int(coords[0][0]), int(coords[0][1])
                    success = self.camera_client.move_camera_to(x, y)
                    logger.info(f"相机移动到({x}, {y})结果: {success}")
                else:
                    # 默认坐标
                    success = self.camera_client.move_camera_to(100, 100)
                    logger.info(f"相机移动到默认位置结果: {success}")
                    
            elif "跟随" in cmd or "镜头跟随" in cmd:
                # 尝试提取Actor ID
                actor_ids = re.findall(r'(\d+)', cmd)
                if actor_ids:
                    actor_id = int(actor_ids[0])
                    success = self.camera_client.move_camera_to_actor(actor_id)
                    logger.info(f"相机跟随Actor {actor_id}结果: {success}")
                else:
                    logger.warning("未找到有效的Actor ID，使用默认ID 1")
                    success = self.camera_client.move_camera_to_actor(1)
                    logger.info(f"相机跟随默认Actor结果: {success}")
                    
            elif "方向移动" in cmd:
                # 提取方向和距离
                direction_match = re.search(r'(上|下|左|右|北|南|东|西)', cmd)
                distance_match = re.search(r'(\d+)', cmd)
                
                direction = direction_match.group(1) if direction_match else "北"
                distance = int(distance_match.group(1)) if distance_match else 50
                
                success = self.camera_client.move_camera_by_direction(direction, distance)
                logger.info(f"相机向{direction}移动{distance}格结果: {success}")
            else:
                logger.info(f"未识别的相机控制命令: {cmd}")
            
            global_state["state"] = global_state["next_state"]
            
        except Exception as e:
            logger.error(f"相机控制执行失败: {e}")
            
        return global_state