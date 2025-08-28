"""
协程任务管理器(运行在单线程中)
支持嵌套任务组、任务终止、状态查询和结果查询
"""
import asyncio
import uuid
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from datetime import datetime
import traceback
import inspect
import json
from contextlib import asynccontextmanager



class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 正在执行
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed"        # 执行失败
    CANCELLED = "cancelled"  # 已取消


class Task:
    """单个任务的封装"""
    
    def __init__(self, coro: Callable[..., Any], task_id: Optional[str] = None, name: Optional[str] = None):
        """
        初始化任务
        
        Args:
            coro: 协程对象
            task_id: 任务ID，如果不提供则自动生成
            name: 任务名称
        """
        self.id: str = task_id or str(uuid.uuid4())
        self.name: str = name or f"Task-{self.id[:8]}"
        self.coro: Callable[..., Any] = coro  # 原始协程对象
        self.status: TaskStatus = TaskStatus.PENDING
        self.result: Any = None
        self.error: Optional[Exception] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self._asyncio_task: Optional[asyncio.Task] = None
        self.group_id: Optional[str] = None  # 所属任务组ID

        
    async def run(self) -> Any:
        """执行任务"""
        self.status = TaskStatus.RUNNING
        self.start_time = datetime.now()
        
        try:
            # 执行协程
            self.result = await self.coro
            self.status = TaskStatus.COMPLETED
        except asyncio.CancelledError:
            self.status = TaskStatus.CANCELLED
            self.end_time = datetime.now()
            raise
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.error = e
            self.end_time = datetime.now()
            raise
        else:
            self.end_time = datetime.now()
            return self.result
            
    def cancel(self) -> bool:
        """取消任务"""
        if self._asyncio_task and not self._asyncio_task.done():
            canceled = self._asyncio_task.cancel()
            if canceled:
                self.status = TaskStatus.CANCELLED
                self.end_time = datetime.now()
                return True
            else:
                return False
        return False
        
    def get_asyncio_task(self) -> Optional[asyncio.Task]:
        """获取内部asyncio任务对象"""
        return self._asyncio_task
        
    def set_asyncio_task(self, task: asyncio.Task) -> None:
        """设置内部asyncio任务对象
        
        Args:
            task: 要设置的asyncio任务对象
        """
        self._asyncio_task = task
    
    def get_info(self) -> Dict[str, Any]:
        """获取任务信息"""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "result": self.result,
            "error": str(self.error) if self.error else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "group_id": self.group_id
        }


class TaskGroup:
    """任务组，支持嵌套"""
    
    def __init__(self, group_id: Optional[str] = None, name: Optional[str] = None, parent_group: Optional['TaskGroup'] = None):
        """
        初始化任务组
        
        Args:
            group_id: 任务组ID
            name: 任务组名称
            parent_group: 父任务组
        """
        self.id: str = group_id or str(uuid.uuid4())
        self.name: str = name or f"Group-{self.id[:8]}"
        self.parent_group: Optional['TaskGroup'] = parent_group
        self.tasks: Dict[str, Task] = {}
        self.sub_groups: Dict[str, TaskGroup] = {}
        self.status: TaskStatus = TaskStatus.PENDING
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
    def add_task(self, task: Task) -> None:
        """添加任务到组"""
        task.group_id = self.id
        self.tasks[task.id] = task
        
    def remove_task(self, task_id: str) -> bool:
        """从组中移除任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False
        
    def add_sub_group(self, group: 'TaskGroup') -> None:
        """添加子任务组"""
        group.parent_group = self
        self.sub_groups[group.id] = group
        
    def remove_sub_group(self, group_id: str) -> bool:
        """移除子任务组"""
        if group_id in self.sub_groups:
            self.sub_groups[group_id].parent_group = None
            del self.sub_groups[group_id]
            return True
        return False
        
    async def run(self) -> List[Any]:
        """运行任务组中的所有任务"""
        self.status = TaskStatus.RUNNING
        self.start_time = datetime.now()
        
        try:
            # 收集所有任务（包括子组的任务）
            all_coroutines = []
            task_refs = []
            
            # 添加当前组的任务
            for task in self.tasks.values():
                task_refs.append(task)
                all_coroutines.append(task.run())
                
            # 递归运行子组
            for sub_group in self.sub_groups.values():
                all_coroutines.append(sub_group.run())
                
            # 并发执行所有任务
            results: List[Any] = []
            if all_coroutines:
                results = await asyncio.gather(*all_coroutines, return_exceptions=True)

                # 检查是否有取消的任务（检查所有嵌套任务）
                has_cancellation = any(t.status == TaskStatus.CANCELLED for t in self.get_all_tasks())
                if has_cancellation:
                    self.status = TaskStatus.CANCELLED
                else:
                    # 检查是否有失败的任务（检查所有嵌套任务）
                    has_failure = any(t.status == TaskStatus.FAILED for t in self.get_all_tasks())
                    if has_failure:
                        # fixme 子任务失败直接标记了任务组失败
                        self.status = TaskStatus.FAILED
                    else:
                        self.status = TaskStatus.COMPLETED
            else:
                self.status = TaskStatus.COMPLETED
                
        except asyncio.CancelledError:
            self.status = TaskStatus.CANCELLED
            # 取消所有子任务
            await self.cancel_all()
            raise
        except Exception:
            self.status = TaskStatus.FAILED
            raise
        finally:
            self.end_time = datetime.now()
            return results
            
    async def cancel_all(self) -> None:
        """取消组内所有任务"""
        # 取消当前组的任务
        for task in self.tasks.values():
            canceled = task.cancel()
            if not canceled:
                pass

        # 递归取消子组的任务
        cancel_tasks = []
        for sub_group in self.sub_groups.values():
            cancel_tasks.append(sub_group.cancel_all())
            
        if cancel_tasks:
            await asyncio.gather(*cancel_tasks, return_exceptions=True)
            
        # 设置组自身的状态
        self.status = TaskStatus.CANCELLED
        self.end_time = datetime.now()
            
    def get_all_tasks(self) -> List[Task]:
        """获取组内所有任务（包括子组）"""
        all_tasks: List[Task] = list(self.tasks.values())
        
        for sub_group in self.sub_groups.values():
            all_tasks.extend(sub_group.get_all_tasks())
            
        return all_tasks
    
    def get_info(self) -> Dict[str, Any]:
        """获取任务组信息"""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "parent_group_id": self.parent_group.id if self.parent_group else None,
            "tasks": [task.get_info() for task in self.tasks.values()],
            "sub_groups": [group.get_info() for group in self.sub_groups.values()],
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None
        }


class TaskManager:
    """协程任务管理器（单例模式）"""
    
    # 单例实例
    _instance = None
    # 初始化标志
    _initialized = False
    # 保护单例创建的锁
    _instance_lock = asyncio.Lock()
    
    def __new__(cls):
        # 使用__new__方法实现单例
        return cls.get_instance()
    
    @classmethod
    async def get_instance(cls):
        """获取TaskManager单例实例（异步方法）
        
        Returns:
            TaskManager: 单例实例
        """
        if cls._instance is None:
            async with cls._instance_lock:
                # 创建实例
                cls._instance = super(TaskManager, cls).__new__(cls)
        
        # 确保只初始化一次
        if not cls._initialized:
            async with cls._instance_lock:
                await cls._instance._initialize()
                cls._initialized = True
        
        return cls._instance
    
    @classmethod
    def get_instance_sync(cls):
        """获取TaskManager单例实例（同步方法）
        
        注意：这个方法应该只在确保事件循环已经运行的情况下使用
        如果实例未初始化，则会创建实例但不会调用异步初始化
        
        Returns:
            TaskManager: 单例实例
        """
        if cls._instance is None:
            # 在同步上下文中，我们只能创建实例但不能异步初始化
            cls._instance = super(TaskManager, cls).__new__(cls)
            # 设置一个标志，表明需要初始化
            cls._initialized = False
            
        return cls._instance
    
    def __init__(self):
        """初始化方法，在单例模式下实际不会执行多次初始化"""
        # 实际初始化移动到_initialize异步方法中
        pass
        
    async def _initialize(self):
        """真正的异步初始化方法"""
        self.tasks: Dict[str, Task] = {}
        self.groups: Dict[str, TaskGroup] = {}
        self.running_tasks: Set[str] = set()
        # 细粒度锁，分别保护不同的数据结构
        self._tasks_lock: asyncio.Lock = asyncio.Lock()  # 保护任务字典
        self._groups_lock: asyncio.Lock = asyncio.Lock()  # 保护任务组字典
        self._running_lock: asyncio.Lock = asyncio.Lock()  # 保护运行中的任务集合
        
    @asynccontextmanager
    async def _lock_multiple(self, *locks: List[asyncio.Lock]):
        """同时获取多个锁的上下文管理器
        
        Args:
            *locks: 要获取的锁列表
        """
        # 按固定顺序获取锁，避免死锁
        sorted_locks: List[asyncio.Lock] = sorted(locks, key=id)
        acquired_locks: List[asyncio.Lock] = []
        try:
            for lock in sorted_locks:
                await lock.acquire()
                acquired_locks.append(lock)
            yield
        finally:
            for lock in reversed(acquired_locks):
                lock.release()
    
    async def create_task(self, coro: Callable[..., Any], task_id: Optional[str] = None, name: Optional[str] = None, group_id: Optional[str] = None) -> Task:
        """
        创建任务
        
        Args:
            coro: 协程对象
            task_id: 任务ID
            name: 任务名称
            group_id: 要加入的任务组ID
            
        Returns:
            创建的任务对象
        """
        # 创建任务对象 (无需锁)
        task = Task(coro, task_id, name)
        
        if group_id is not None:
            # 需要同时访问任务和任务组，使用多重锁
            async with self._lock_multiple(self._tasks_lock, self._groups_lock):
                self.tasks[task.id] = task
                # 如果指定了任务组，将任务加入组
                if group_id in self.groups:
                    self.groups[group_id].add_task(task)
        else:
            # 仅添加任务，只需要任务锁
            async with self._tasks_lock:
                self.tasks[task.id] = task
                
        return task
            
    async def create_group(self, group_id: Optional[str] = None, name: Optional[str] = None, parent_group_id: Optional[str] = None) -> TaskGroup:
        """
        创建任务组
        
        Args:
            group_id: 任务组ID
            name: 任务组名称
            parent_group_id: 父任务组ID
            
        Returns:
            创建的任务组对象
        """
        async with self._groups_lock:
            parent_group = None
            if parent_group_id and parent_group_id in self.groups:
                parent_group = self.groups[parent_group_id]
                
            group = TaskGroup(group_id, name, parent_group)
            self.groups[group.id] = group
            
            # 如果有父组，将其添加到父组中
            if parent_group:
                parent_group.add_sub_group(group)
                
            return group
            
    async def submit_task(self, task_id: str) -> asyncio.Task[Any]:
        """
        提交任务执行
        
        Args:
            task_id: 任务ID
            
        Returns:
            asyncio.Task对象
        """
        # 查找和验证任务（需要任务锁）
        async with self._tasks_lock:
            if task_id not in self.tasks:
                raise ValueError(f"Task {task_id} not found")
                
            task = self.tasks[task_id]
            if task.status != TaskStatus.PENDING:
                raise ValueError(f"Task {task_id} is not in PENDING status")
        
        # 添加到运行列表（需要运行锁）
        async with self._running_lock:
            self.running_tasks.add(task_id)
            
        # 创建异步任务（无需锁）
        async def run_wrapper() -> Any:
            try:
                return await task.run()
            except Exception:
                raise
            finally:
                # 确保任务结束时从运行列表中移除（只需运行锁）
                async with self._running_lock:
                    self.running_tasks.discard(task_id)
                    
        # 创建并保存对asyncio任务的引用（需要任务锁）
        async with self._tasks_lock:
            task.set_asyncio_task(asyncio.create_task(run_wrapper()))
            return task._asyncio_task
            
    async def submit_group(self, group_id: str) -> asyncio.Task[Any]:
        """
        提交任务组执行
        
        Args:
            group_id: 任务组ID
            
        Returns:
            asyncio.Task对象
        """
        # 查找和验证任务组（需要组锁）
        async with self._groups_lock:
            if group_id not in self.groups:
                raise ValueError(f"Group {group_id} not found")
                
            group = self.groups[group_id]
            if group.status != TaskStatus.PENDING:
                raise ValueError(f"Group {group_id} is not in PENDING status")
            
            # 获取组内所有任务（无需修改，只是读取）
            all_tasks = group.get_all_tasks()
        
        # 将组内所有任务添加到运行集合（需要运行锁）
        async with self._running_lock:
            for task in all_tasks:
                self.running_tasks.add(task.id)
                
        # 创建异步任务（无需锁）
        async def run_wrapper() -> List[Any]:
            try:
                return await group.run()
            except Exception:
                raise
            finally:
                # 从运行列表中移除所有任务（只需运行锁）
                async with self._running_lock:
                    for task in all_tasks:
                        self.running_tasks.discard(task.id)
                            
        # 创建异步任务（无需锁）
        group_task = asyncio.create_task(run_wrapper())
        
        # 将group_task保存到组内每个任务的_asyncio_task引用（需要任务锁）
        async with self._tasks_lock:
            for task in all_tasks:
                if task.id in self.tasks:
                    self.tasks[task.id].set_asyncio_task(group_task)
                    
        return group_task
            
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功取消
        """
        # 查找任务（需要任务锁）
        async with self._tasks_lock:
            if task_id not in self.tasks:
                return False
                
            task = self.tasks[task_id]
            canceled = task.cancel()
            
        # 如果取消成功，从运行列表中移除（需要运行锁）
        if canceled:
            async with self._running_lock:
                self.running_tasks.discard(task_id)
                
        return canceled
            
    async def cancel_group(self, group_id: str) -> bool:
        """
        取消任务组
        
        Args:
            group_id: 任务组ID
            
        Returns:
            是否成功取消
        """
        # 查找任务组并取消（需要组锁）
        async with self._groups_lock:
            if group_id not in self.groups:
                return False
                
            group = self.groups[group_id]
            # 获取所有任务，这里只是读取
            all_tasks_in_group = group.get_all_tasks()
            
        # 取消任务组（不在锁内执行可能耗时的操作）
        await group.cancel_all()
        
        # 更新组状态（需要组锁）
        async with self._groups_lock:
            if group_id in self.groups:  # 再次检查，防止在await期间被删除
                group = self.groups[group_id]
                group.status = TaskStatus.CANCELLED
                group.end_time = datetime.now()
            
        # 从运行列表中移除（需要运行锁）
        async with self._running_lock:
            for task in all_tasks_in_group:
                self.running_tasks.discard(task.id)
                
        return True
            
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态，如果任务不存在返回None
        """
        if task_id in self.tasks:
            return self.tasks[task_id].status
        return None
        
    def get_task_result(self, task_id: str) -> Any:
        """
        获取任务结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务结果
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
            
        task = self.tasks[task_id]
        if task.status == TaskStatus.COMPLETED:
            return task.result
        elif task.status == TaskStatus.FAILED:
            raise task.error
        else:
            return None
            
    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务详细信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务信息字典
        """
        if task_id in self.tasks:
            return self.tasks[task_id].get_info()
        return None
        
    def get_group_info(self, group_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务组详细信息
        
        Args:
            group_id: 任务组ID
            
        Returns:
            任务组信息字典
        """
        if group_id in self.groups:
            return self.groups[group_id].get_info()
        return None
        
    def get_all_tasks_info(self) -> List[Dict[str, Any]]:
        """获取所有任务信息"""
        return [task.get_info() for task in self.tasks.values()]
        
    def get_all_groups_info(self) -> List[Dict[str, Any]]:
        """获取所有任务组信息"""
        return [group.get_info() for group in self.groups.values()]
        
    def get_running_tasks(self) -> List[str]:
        """获取正在运行的任务ID列表"""
        return list(self.running_tasks)

    async def debug_info(self, include_task_details: bool = True, include_group_details: bool = True) -> Dict[str, Any]:
        """获取任务管理器的详细调试信息，包括所有任务、任务组和锁的状态
        
        Args:
            include_task_details: 是否包含所有任务的详细信息
            include_group_details: 是否包含所有任务组的详细信息
            
        Returns:
            包含所有调试信息的字典
        """
        # 获取锁状态信息
        locks_info = {
            "tasks_lock": {
                "locked": self._tasks_lock.locked(),
                "holders": self._get_lock_holders(self._tasks_lock)
            },
            "groups_lock": {
                "locked": self._groups_lock.locked(),
                "holders": self._get_lock_holders(self._groups_lock)
            },
            "running_lock": {
                "locked": self._running_lock.locked(),
                "holders": self._get_lock_holders(self._running_lock)
            }
        }
        
        # 基本统计信息
        stats = {
            "total_tasks": len(self.tasks),
            "running_tasks_count": len(self.running_tasks),
            "total_groups": len(self.groups),
            "tasks_by_status": self._count_tasks_by_status(),
        }
        
        # 构建调试信息字典
        debug_data = {
            "locks": locks_info,
            "stats": stats,
            "running_tasks": list(self.running_tasks),
        }
        
        # 添加任务详情（可选）
        if include_task_details:
            debug_data["tasks"] = {task_id: task.get_info() for task_id, task in self.tasks.items()}
            
        # 添加任务组详情（可选）
        if include_group_details:
            debug_data["groups"] = {group_id: group.get_info() for group_id, group in self.groups.items()}
            
        return debug_data
    
    def _get_lock_holders(self, lock: asyncio.Lock) -> List[Dict[str, Any]]:
        """尝试获取正在持有锁的任务信息
        
        Args:
            lock: 要检查的锁对象
            
        Returns:
            持有该锁的任务信息列表
        """
        # 如果锁没有被持有，返回空列表
        if not lock.locked():
            return []
            
        # 获取当前运行中的任务信息
        holders = []
        for task_id in self.running_tasks:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                asyncio_task = task.get_asyncio_task()
                if asyncio_task:
                    # 检查任务的栈以查找锁的获取操作
                    try:
                        # 获取任务的当前栈帧，但inspect.getstack在最新版本中已废弃
                        # 改为使用更简单的检测方法
                        if hasattr(asyncio_task, '_coro') and asyncio_task._coro.cr_frame:
                            frame = asyncio_task._coro.cr_frame
                            while frame:
                                # 检查帧中是否有对当前锁的引用
                                for var_name, var_val in frame.f_locals.items():
                                    if isinstance(var_val, asyncio.Lock) and id(var_val) == id(lock):
                                        holders.append({
                                            "task_id": task_id,
                                            "task_name": task.name,
                                            "function": frame.f_code.co_name
                                        })
                                        break
                                frame = frame.f_back
                    except (ValueError, AttributeError):
                        # 访问内部属性可能失败，因为任务可能已经完成或被取消
                        pass
        
        # 如果未能识别持有锁的任务，提供一个占位符
        if not holders and lock.locked():
            holders.append({"info": "锁被持有，但无法确定持有者"})
            
        return holders
    
    def _count_tasks_by_status(self) -> Dict[str, int]:
        """统计各状态的任务数量"""
        status_counts = {status.value: 0 for status in TaskStatus}
        
        for task in self.tasks.values():
            status_counts[task.status.value] += 1
            
        return status_counts
            
    def print_debug_info(self, include_task_details: bool = False, include_group_details: bool = False) -> None:
        """打印任务管理器的调试信息
        
        Args:
            include_task_details: 是否包含所有任务的详细信息
            include_group_details: 是否包含所有任务组的详细信息
        """
        async def _get_and_print():
            info = await self.debug_info(include_task_details, include_group_details)
            print(json.dumps(info, indent=2, ensure_ascii=False))
            
        # 创建一个事件循环来执行异步函数
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果已经在事件循环中，创建一个新任务
            asyncio.create_task(_get_and_print())
        else:
            # 否则，运行直到完成
            loop.run_until_complete(_get_and_print())
            
    @classmethod
    def reset_instance(cls):
        """重置单例实例（仅用于测试）"""
        cls._instance = None
        cls._initialized = False
        
    async def wait_all(self) -> None:
        """等待所有任务完成"""
        # 收集所有需要等待的任务（只需任务锁读取，不需要修改）
        async with self._tasks_lock:
            tasks_to_wait: List[asyncio.Task[Any]] = []
            for task in self.tasks.values():
                asyncio_task = task.get_asyncio_task()
                if asyncio_task and not asyncio_task.done() and task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                    tasks_to_wait.append(asyncio_task)
        
        # 等待任务完成（无需锁，这是异步操作）
        if tasks_to_wait:
            await asyncio.gather(*tasks_to_wait, return_exceptions=True)
    
