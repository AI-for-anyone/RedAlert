from .state import GlobalState
from .mcp_client import InfoMCPClient
from logs import get_logger
import re

logger = get_logger("intelligence")

class IntelligenceNode():
    def __init__(self):
        self.info_client = InfoMCPClient()

    def intelligence_node(self, global_state: GlobalState) -> GlobalState:
        logger.info(f"执行信息管理,当前GlobalState: {global_state}")
        
        cmd = global_state["input_cmd"]
        logger.info(f"处理信息查询命令: {cmd}")
        
        try:
            # 根据命令类型调用相应的MCP工具
            if "游戏状态" in cmd or "资源" in cmd or "电力" in cmd:
                # 获取游戏状态
                game_state = self.info_client.get_game_state()
                logger.info(f"游戏状态查询结果: 金钱{game_state.get('cash', 0)}, 资源{game_state.get('resources', 0)}, 电力{game_state.get('power', 0)}")
                logger.info(f"可见单位数量: {len(game_state.get('visible_units', []))}")
                
            elif "地图" in cmd:
                # 查询地图信息
                map_info = self.info_client.map_query()
                logger.info(f"地图查询结果: 宽度{map_info.get('width', 0)}, 高度{map_info.get('height', 0)}")
                
            elif "路径" in cmd or "寻路" in cmd:
                # 提取单位ID、目标坐标和寻路方法
                actor_ids = [int(x) for x in re.findall(r'单位(\d+)', cmd)]
                coords = re.findall(r'(\d+)[,，]\s*(\d+)', cmd)
                
                method = "最短路"
                if "左路" in cmd:
                    method = "左路"
                elif "右路" in cmd:
                    method = "右路"
                
                if not actor_ids:
                    actor_ids = [1]
                if coords:
                    dest_x, dest_y = int(coords[0][0]), int(coords[0][1])
                else:
                    dest_x, dest_y = 100, 100
                
                path = self.info_client.find_path(actor_ids, dest_x, dest_y, method)
                logger.info(f"为单位{actor_ids}寻找到目标({dest_x}, {dest_y})的{method}，路径长度: {len(path)}")
                
            elif "玩家信息" in cmd or "基地信息" in cmd:
                # 查询玩家基地信息
                base_info = self.info_client.player_base_info_query()
                logger.info(f"玩家基地信息: 金钱{base_info.get('cash', 0)}, 已用电力{base_info.get('powerDrained', 0)}/{base_info.get('power', 0)}")
                
            elif "屏幕信息" in cmd:
                # 查询屏幕信息
                screen_info = self.info_client.screen_info_query()
                screen_min = screen_info.get('screenMin', {})
                screen_max = screen_info.get('screenMax', {})
                logger.info(f"屏幕信息: 范围({screen_min.get('x', 0)}, {screen_min.get('y', 0)}) 到 ({screen_max.get('x', 0)}, {screen_max.get('y', 0)})")
                
            elif "可见性" in cmd or "可见" in cmd:
                # 查询坐标可见性
                coords = re.findall(r'(\d+)[,，]\s*(\d+)', cmd)
                if coords:
                    x, y = int(coords[0][0]), int(coords[0][1])
                else:
                    x, y = 100, 100
                
                is_visible = self.info_client.visible_query(x, y)
                logger.info(f"坐标({x}, {y})可见性查询结果: {is_visible}")
                
            elif "探索" in cmd or "已探索" in cmd:
                # 查询坐标探索状态
                coords = re.findall(r'(\d+)[,，]\s*(\d+)', cmd)
                if coords:
                    x, y = int(coords[0][0]), int(coords[0][1])
                else:
                    x, y = 100, 100
                
                is_explored = self.info_client.explorer_query(x, y)
                logger.info(f"坐标({x}, {y})探索状态查询结果: {is_explored}")
                
            else:
                logger.info(f"未识别的信息查询命令: {cmd}")
                
            global_state["state"] = global_state["next_state"]
            
        except Exception as e:
            logger.error(f"信息管理执行失败: {e}")
            
        return global_state
