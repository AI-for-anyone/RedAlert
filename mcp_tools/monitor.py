from OpenRA_Copilot_Library import AsyncGameAPI
from OpenRA_Copilot_Library.models import NewTargetsQueryParam, Location, Actor
from typing import Dict, List, Deque    
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logs import get_logger
import asyncio
from collections import deque
from model import ALL_INFANTRIES, ALL_TANKS, ALL_AIR
from task_scheduler import TaskManager, Task

logger = get_logger("monitor")

class ActorItems:
    history_location: Deque[Location]
    actor: Actor
    is_free: bool = False
    max_history_size: int = 10
    target: List[int]
    target_type: List[str]
    def __init__(self, actor: Actor):
        self.actor = actor
        self.history_location = deque(maxlen=self.max_history_size)
    
    def __post_init__(self):
        """初始化后处理，确保 history_location 是固定长度的 deque"""
        if not isinstance(self.history_location, deque):
            self.history_location = deque(self.history_location, maxlen=self.max_history_size)
        else:
            # 如果已经是 deque，更新 maxlen
            temp_data = list(self.history_location)
            self.history_location = deque(temp_data, maxlen=self.max_history_size)
    
    def add_location(self, location: Location):
        """添加新位置，自动维护 FIFO 队列"""
        self.history_location.append(location)
    
    def get_recent_locations(self, count: int = None) -> List[Location]:
        """获取最近的位置记录"""
        if count is None:
            return list(self.history_location)
        return list(self.history_location)[-count:]

    # 判断是否空闲
    def update_free_state(self):
        stay = False
        if self.actor.type in ALL_AIR:
            if len(self.history_location) >= 10:
                # 分别计算location x y的方差
                x = [loc.x for loc in self.history_location]
                y = [loc.y for loc in self.history_location]
                x_var = sum((xi - sum(x)/len(x))**2 for xi in x)/len(x)
                y_var = sum((yi - sum(y)/len(y))**2 for yi in y)/len(y)
                # logger.debug("actor {0} x_var {1}, y_var {2}".format(self.actor.actor_id, x_var, y_var))
                if x_var < 10 and y_var < 10:
                    stay = True
        elif self.actor.type in ALL_INFANTRIES or self.actor.type in ALL_TANKS:
            # 取最近的位置，判断是否发生改变
            locations = self.get_recent_locations(3)
            if len(locations) >= 3 and locations[0] == locations[1] and locations[1] == locations[2]:
                stay = True
        if stay:
            if self.target is None or len(self.target) == 0:
                self.is_free = True
            else:
                self.is_free = False
    
# 全局单例实例
_monitor = None

class Monitor:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Monitor, cls).__new__(cls)
        return cls._instance
    
    def __init__(self,collection_interval: float = 0.5,show_interval: float = 1):
        if not Monitor._initialized:
            self.our_actors: Dict[int, ActorItems] = {}
            self.enemy_actors: Dict[int, ActorItems] = {}
            self.monitor_api = AsyncGameAPI(host="localhost", port=7445, language="zh")
            self.collection_interval = collection_interval
            self.show_interval = show_interval
            self._lock = asyncio.Lock()  # 添加异步锁保护共享数据
            self.task_manager = TaskManager()
            Monitor._initialized = True
    
    async def start(self, show: bool = True):
        logger.info("Monitor-开始监控")
        self.collect_actors_task = await self.task_manager.submit_task(self.collect_actors_info)
        if show:
            self.show_task = await self.task_manager.submit_task(self.show)

    def get_enemy_actors_status(self) -> List[Actor]:
        return [actor.actor for actor in self.enemy_actors.values()]

    def get_actors_status(self, actor_ids: List[int]) -> List[ActorItems]:
        if actor_ids is None or len(actor_ids) == 0:
            return []
        return [self.our_actors.get(actor_id) for actor_id in actor_ids]
    
    async def show(self):
        while True:
            async with self._lock:  # 获取锁保护读操作
                logger.info("-----------------------show-开始显示单位信息-----------------------")
                for actor in self.our_actors.values():
                    logger.info("actor[{0}:{1}]({2},{3})=[{4}]".format(actor.actor.actor_id, actor.actor.type, actor.actor.position, actor.is_free, actor.actor.__format__("")))
                logger.info("-----------------------show-结束显示单位信息-----------------------")
            await asyncio.sleep(self.show_interval)
    
    async def update_actors_free_status(self, actors: List[Actor]):
        async with self._lock:
            for actor in actors:
                if actor.actor_id in self.our_actors:
                    # 清空历史位置
                    self.our_actors[actor.actor_id].history_location.clear()
                    self.our_actors[actor.actor_id].is_free = False

    async def collect_actors_info(self):
        """监控单位信息的协程"""
        logger.debug("collect_actors_info-开始收集单位信息")
        while True:
            try:
                # 先获取数据，减少锁持有时间
                our_actors = await self.monitor_api.query_actor(NewTargetsQueryParam(faction="己方", restrain=[{"visible": True}]))
                enemy_actors = await self.monitor_api.query_actor(NewTargetsQueryParam(faction="敌方", restrain=[{"visible": True}]))
                our_units = await self.monitor_api.unit_attribute_query(NewTargetsQueryParam(faction="己方", restrain=[{"visible": True}]))
                try:
                    enemy_units = await self.monitor_api.unit_attribute_query(NewTargetsQueryParam(faction="敌方", restrain=[{"visible": True}]))
                except Exception as e:
                    logger.warning("collect_actors_info-获取敌方单位属性失败: {e}")
                    enemy_units = []
                
                # 获取锁进行写操作
                async with self._lock:
                    for actor in our_actors:
                        if actor.actor_id not in self.our_actors:
                            self.our_actors[actor.actor_id] = ActorItems(actor=actor)
                        self.our_actors[actor.actor_id].add_location(actor.position)
                    for actor in enemy_actors:
                        if actor.actor_id not in self.enemy_actors:
                            self.enemy_actors[actor.actor_id] = ActorItems(actor=actor)
                            self.enemy_actors[actor.actor_id].add_location(actor.position)
                    
                    for unit in our_units:
                        if unit is not None and unit.get("id") in self.our_actors.keys():
                            self.our_actors[unit.get("id")].target = unit.get("target")
                            target_type = []
                            for target_id in unit.get("target", []):
                                target_type.append(self.enemy_actors[target_id].type)
                            self.our_actors[unit.get("id")].target_type = target_type
                            self.our_actors[unit.get("id")].update_free_state()

                    for unit in enemy_units:
                        if unit is not None and unit.get("id") in self.enemy_actors.keys():
                            self.enemy_actors[unit.get("id")].target = unit.get("target")
                            target_type = []
                            for target_id in unit.get("target", []):
                                target_type.append(self.our_actors[target_id].type)
                            self.enemy_actors[unit.get("id")].target_type = target_type
                            self.enemy_actors[unit.get("id")].update_free_state()
            except Exception as e:
                logger.error(f"collect_actors_info发生错误: {e}")
            await asyncio.sleep(self.collection_interval)

# 便捷函数：获取 Monitor 单例实例
def get_monitor() -> Monitor:
    global _monitor
    if _monitor is None:
        _monitor = Monitor()
    return _monitor

async def update_actors_free_status(actors: List[Actor]):
    monitor = get_monitor()
    await monitor.update_actors_free_status(actors)

def get_actors_status(actor_ids: List[int])-> List[ActorItems]:
    monitor = get_monitor()
    return monitor.get_actors_status(actor_ids)

def get_all_enemy_actors_status()-> List[Actor]:
    monitor = get_monitor()
    return monitor.get_enemy_actors_status()

async def test():
    monitor = get_monitor()
    await monitor.start()

if __name__ == "__main__":
    asyncio.run(test()) 
