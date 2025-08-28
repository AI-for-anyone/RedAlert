import asyncio
from typing import Dict

class GroupMgr:
    """编组管理器 - 简化版"""
    def __init__(self):
        self._events: Dict[int, asyncio.Event] = {}
        for i in range(1, 11):  # 编组1-10
            self._events[i] = None
    
    def get_event(self, group_id: int) -> asyncio.Event:
        """获取编组的取消事件"""
        event = self._events.get(group_id)
        if event is None:
            event = asyncio.Event()
            self._events[group_id] = event
        return event
    
    def should_cancel(self, group_id: int) -> bool:
        """检查编组是否应该取消"""
        return self._events[group_id].is_set()
    
    def cancel_group(self, group_id: int):
        """取消编组任务"""
        self._events[group_id].set()
    
    def start_new_task(self, group_id: int):
        """开始新任务（会先取消当前任务）"""
        # 先取消当前任务
        if self._events[group_id] is not None:
            self._events[group_id].set()
        # 创建新的事件对象
        self._events[group_id] = asyncio.Event()