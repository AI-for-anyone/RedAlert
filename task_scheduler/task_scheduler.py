"""
基于asyncio的并发管理模块
实现单例模式的任务调度器，提供并发控制和资源管理功能
"""

import asyncio
import threading
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logs
import time
from contextlib import asynccontextmanager


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """任务信息数据类"""
    task_id: str
    name: str
    status: TaskStatus
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[Exception] = None


class ConcurrencyManager:
    """
    基于asyncio的并发管理器 - 单例模式
    提供任务调度、并发控制、资源管理等功能
    """
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        """单例模式实现"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, max_concurrent_tasks: int = 100, enable_logging: bool = True):
        """
        初始化并发管理器
        
        Args:
            max_concurrent_tasks: 最大并发任务数
            enable_logging: 是否启用日志
        """
        if self._initialized:
            return
            
        self.max_concurrent_tasks = max_concurrent_tasks
        self.enable_logging = enable_logging
        
        # 任务管理
        self._tasks: Dict[str, asyncio.Task] = {}
        self._task_info: Dict[str, TaskInfo] = {}
        self._task_counter = 0
        
        # 并发控制
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._running_tasks: Set[str] = set()
        
        # 事件循环管理
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # 回调函数
        self._task_callbacks: Dict[str, List[Callable]] = {
            'on_start': [],
            'on_complete': [],
            'on_error': [],
            'on_cancel': []
        }
        
        # 日志配置
        if self.enable_logging:
            self._setup_logging()
        
        self._initialized = True
        
    def _setup_logging(self):
        print("设置日志")
        """设置日志"""
        self.logger = logs.get_logger("task_scheduler")
        self.logger.info("设置日志成功")
    
    def _log(self, level: str, message: str):
        """记录日志"""
        match level.upper():
            case "DEBUG":
                self.logger.debug(message)
            case "INFO":
                self.logger.info(message)
            case "WARNING":
                self.logger.warning(message)
            case "ERROR":
                self.logger.error(message)
            case "CRITICAL":
                self.logger.critical(message)
    
    async def _ensure_loop(self):
        """确保事件循环存在"""
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.get_running_loop()
            self._semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
    
    def _generate_task_id(self, task_name: str) -> str:
        """生成任务ID"""
        self._task_counter += 1
        return f"task_{self._task_counter}_{task_name}_{int(time.time() * 1000)}"
    
    async def submit_task(
        self, 
        coro: Callable,
        *args,
        task_name: Optional[str] = None,
        task_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        提交异步任务
        
        Args:
            coro: 协程函数
            *args: 位置参数
            task_name: 任务名称
            task_id: 自定义任务ID
            **kwargs: 关键字参数
            
        Returns:
            str: 任务ID
        """
        await self._ensure_loop()
        
        if task_name is None:
            task_name = getattr(coro, '__name__', str(coro))

        if task_id is None:
            task_id = self._generate_task_id(task_name)
        
        # 创建任务信息
        task_info = TaskInfo(
            task_id=task_id,
            name=task_name,
            status=TaskStatus.PENDING,
            created_at=time.time()
        )
        self._task_info[task_id] = task_info
        
        # 创建并启动任务
        task = asyncio.create_task(
            self._execute_task(task_id, coro, *args, **kwargs)
        )
        self._tasks[task_id] = task
        
        self._log('info', f"Task submitted: {task_id} ({task_name})")
        return task_id
    
    async def _execute_task(self, task_id: str, coro: Callable, *args, **kwargs):
        """执行任务的内部方法"""
        task_info = self._task_info[task_id]
        
        try:
            # 等待获取信号量（并发控制）
            async with self._semaphore:
                # 更新任务状态
                task_info.status = TaskStatus.RUNNING
                task_info.started_at = time.time()
                self._running_tasks.add(task_id)
                
                # 执行开始回调
                await self._execute_callbacks('on_start', task_id, task_info)
                
                self._log('info', f"Task started: {task_id}")
                
                # 执行实际任务
                if asyncio.iscoroutinefunction(coro):
                    result = await coro(*args, **kwargs)
                else:
                    result = coro(*args, **kwargs)
                
                # 任务完成
                task_info.status = TaskStatus.COMPLETED
                task_info.completed_at = time.time()
                task_info.result = result
                
                self._log('info', f"Task completed: {task_id}")
                
                # 执行完成回调
                await self._execute_callbacks('on_complete', task_id, task_info)
                
                return result
                
        except asyncio.CancelledError:
            task_info.status = TaskStatus.CANCELLED
            task_info.completed_at = time.time()
            self._log('info', f"Task cancelled: {task_id}")
            await self._execute_callbacks('on_cancel', task_id, task_info)
            raise
            
        except Exception as e:
            task_info.status = TaskStatus.FAILED
            task_info.completed_at = time.time()
            task_info.error = e
            self._log('error', f"Task failed: {task_id} - {str(e)}")
            await self._execute_callbacks('on_error', task_id, task_info)
            raise
            
        finally:
            self._running_tasks.discard(task_id)
    
    async def _execute_callbacks(self, event: str, task_id: str, task_info: TaskInfo):
        """执行回调函数"""
        for callback in self._task_callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task_id, task_info)
                else:
                    callback(task_id, task_info)
            except Exception as e:
                self._log('error', f"Callback error for {event}: {str(e)}")
    
    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """
        等待指定任务完成
        
        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）
            
        Returns:
            任务结果
        """
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self._tasks[task_id]
        try:
            return await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            self._log('warning', f"Task {task_id} timed out")
            raise
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消指定任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功取消
        """
        if task_id not in self._tasks:
            return False
        
        task = self._tasks[task_id]
        if not task.done():
            task.cancel()
            self._log('info', f"Task cancelled: {task_id}")
            return True
        return False
    
    async def wait_all_tasks(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        等待所有任务完成
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            Dict[str, Any]: 任务ID到结果的映射
        """
        if not self._tasks:
            return {}
        
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*self._tasks.values(), return_exceptions=True),
                timeout=timeout
            )
            
            return {
                task_id: result 
                for task_id, result in zip(self._tasks.keys(), results)
            }
        except asyncio.TimeoutError:
            self._log('warning', "wait_all_tasks timed out")
            raise
    
    async def cancel_all_tasks(self) -> int:
        """
        取消所有任务
        
        Returns:
            int: 被取消的任务数量
        """
        cancelled_count = 0
        for task_id, task in self._tasks.items():
            if not task.done():
                task.cancel()
                cancelled_count += 1
                self._log('info', f"Task cancelled: {task_id}")
        
        self._log('info', f"Cancelled {cancelled_count} tasks")
        return cancelled_count
    
    def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务信息"""
        return self._task_info.get(task_id)
    
    def get_all_tasks_info(self) -> Dict[str, TaskInfo]:
        """获取所有任务信息"""
        return self._task_info.copy()
    
    def get_running_tasks(self) -> Set[str]:
        """获取正在运行的任务ID集合"""
        return self._running_tasks.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_tasks = len(self._task_info)
        status_counts = {}
        for status in TaskStatus:
            status_counts[status.value] = sum(
                1 for info in self._task_info.values() 
                if info.status == status
            )
        
        return {
            'total_tasks': total_tasks,
            'running_tasks': len(self._running_tasks),
            'max_concurrent': self.max_concurrent_tasks,
            'status_counts': status_counts
        }
    
    def add_callback(self, event: str, callback: Callable):
        """
        添加回调函数
        
        Args:
            event: 事件类型 ('on_start', 'on_complete', 'on_error', 'on_cancel')
            callback: 回调函数
        """
        if event in self._task_callbacks:
            self._task_callbacks[event].append(callback)
        else:
            raise ValueError(f"Invalid event type: {event}")
    
    def remove_callback(self, event: str, callback: Callable):
        """移除回调函数"""
        if event in self._task_callbacks:
            try:
                self._task_callbacks[event].remove(callback)
            except ValueError:
                pass
    
    @asynccontextmanager
    async def task_group(self, max_concurrent: Optional[int] = None):
        """
        任务组上下文管理器
        
        Args:
            max_concurrent: 组内最大并发数
        """
        old_semaphore = self._semaphore
        if max_concurrent is not None:
            await self._ensure_loop()
            self._semaphore = asyncio.Semaphore(max_concurrent)
        
        group_tasks = []
        try:
            yield group_tasks
            if group_tasks:
                await asyncio.gather(*group_tasks, return_exceptions=True)
        finally:
            self._semaphore = old_semaphore
    
    async def cleanup(self):
        """清理资源"""
        self._log('info', "Starting cleanup...")
        
        # 取消所有任务
        await self.cancel_all_tasks()
        
        # 等待所有任务完成或被取消
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        
        # 清理数据
        self._tasks.clear()
        self._task_info.clear()
        self._running_tasks.clear()
        
        self._log('info', "Cleanup completed")
    
    def __del__(self):
        """析构函数"""
        if hasattr(self, '_loop') and self._loop and not self._loop.is_closed():
            try:
                asyncio.run_coroutine_threadsafe(self.cleanup(), self._loop)
            except:
                pass


# 全局单例实例
_concurrency_manager = None


def get_concurrency_manager(**kwargs) -> ConcurrencyManager:
    """
    获取并发管理器单例实例
    
    Args:
        **kwargs: 初始化参数（仅在首次调用时生效）
        
    Returns:
        ConcurrencyManager: 并发管理器实例
    """
    global _concurrency_manager
    if _concurrency_manager is None:
        _concurrency_manager = ConcurrencyManager(**kwargs)
    return _concurrency_manager


# 便捷函数
async def submit_task(coro: Callable, *args, **kwargs) -> str:
    """提交任务的便捷函数"""
    manager = get_concurrency_manager()
    return await manager.submit_task(coro, *args, **kwargs)


async def wait_for_task(task_id: str, timeout: Optional[float] = None) -> Any:
    """等待任务的便捷函数"""
    manager = get_concurrency_manager()
    return await manager.wait_for_task(task_id, timeout)


async def cancel_task(task_id: str) -> bool:
    """取消任务的便捷函数"""
    manager = get_concurrency_manager()
    return await manager.cancel_task(task_id)


def get_task_info(task_id: str) -> Optional[TaskInfo]:
    """获取任务信息的便捷函数"""
    manager = get_concurrency_manager()
    return manager.get_task_info(task_id)


def get_stats() -> Dict[str, Any]:
    """获取统计信息的便捷函数"""
    manager = get_concurrency_manager()
    return manager.get_stats()