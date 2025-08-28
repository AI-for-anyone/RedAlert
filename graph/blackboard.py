"""
共享黑板系统 - 支持跨运行图的状态共享和热更新
基于 asyncio 实现异步、线程安全的键值存储
"""
import asyncio
from typing import Any, Dict, Optional, Tuple, Callable
from logs import get_logger

logger = get_logger("blackboard")

class _KeyData:
    """键数据封装类"""
    __slots__ = ("lock", "cond", "version", "value")
    
    def __init__(self):
        self.lock = asyncio.Lock()
        self.cond = asyncio.Condition()
        self.version = 0
        self.value = None

class Blackboard:
    """全局共享黑板 - 单例模式"""
    _instance = None
    _global_lock = asyncio.Lock()  # 保护 _data 的结构性访问

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data: Dict[str, _KeyData] = {}
            cls._instance._initialized = False
        return cls._instance

    async def initialize(self):
        """初始化黑板系统"""
        if not self._initialized:
            logger.info("初始化共享黑板系统")
            self._initialized = True

    async def _ensure_key(self, key: str) -> _KeyData:
        """确保键存在，如不存在则创建"""
        async with self._global_lock:
            if key not in self._data:
                self._data[key] = _KeyData()
                logger.debug(f"创建新键: {key}")
            return self._data[key]

    async def get(self, key: str, default: Any = None) -> Any:
        """获取键值"""
        kd = await self._ensure_key(key)
        async with kd.lock:
            result = default if kd.value is None else kd.value
            logger.debug(f"获取键值: {key} = {result}")
            return result

    async def get_with_version(self, key: str) -> Tuple[Any, int]:
        """获取键值和版本号"""
        kd = await self._ensure_key(key)
        async with kd.lock:
            logger.debug(f"获取键值和版本: {key} = {kd.value}, v{kd.version}")
            return kd.value, kd.version

    async def set(self, key: str, value: Any) -> int:
        """设置键值"""
        kd = await self._ensure_key(key)
        async with kd.lock:
            kd.value = value
            kd.version += 1
            ver = kd.version
            logger.debug(f"设置键值: {key} = {value}, v{ver}")
        
        # 广播在锁外进行，避免阻塞
        async with kd.cond:
            kd.cond.notify_all()
        return ver

    async def update(self, key: str, fn: Callable[[Any], Any]) -> Tuple[Any, int]:
        """原子更新键值 - fn(old_value) -> new_value"""
        kd = await self._ensure_key(key)
        async with kd.lock:
            old_value = kd.value
            kd.value = fn(old_value)
            kd.version += 1
            val, ver = kd.value, kd.version
            logger.debug(f"更新键值: {key} = {old_value} -> {val}, v{ver}")
        
        async with kd.cond:
            kd.cond.notify_all()
        return val, ver

    async def wait_for_change(self, key: str, last_version: int, timeout: Optional[float] = None) -> Tuple[Any, int]:
        """等待键值变更"""
        kd = await self._ensure_key(key)
        
        async with kd.cond:
            # 先检查是否已经有新版本
            async with kd.lock:
                if kd.version > last_version:
                    logger.debug(f"键值已变更: {key}, v{last_version} -> v{kd.version}")
                    return kd.value, kd.version
            
            # 等待变更通知
            try:
                if timeout is None:
                    await kd.cond.wait()
                    logger.debug(f"收到变更通知: {key}")
                else:
                    await asyncio.wait_for(kd.cond.wait(), timeout=timeout)
                    logger.debug(f"收到变更通知 (超时={timeout}s): {key}")
            except asyncio.TimeoutError:
                logger.debug(f"等待变更超时: {key}, timeout={timeout}s")
                # 超时返回当前值与版本，不视为错误
                pass
            
            async with kd.lock:
                return kd.value, kd.version

    async def clear_namespace(self, prefix: str) -> int:
        """删除所有以 prefix 开头的键"""
        async with self._global_lock:
            keys = [k for k in self._data.keys() if k.startswith(prefix)]
            count = len(keys)
            for k in keys:
                del self._data[k]
            logger.info(f"清理命名空间: {prefix}*, 删除 {count} 个键")
            return count

    async def list_keys(self, prefix: str = "") -> Dict[str, Tuple[Any, int]]:
        """列出所有匹配前缀的键值和版本"""
        result = {}
        async with self._global_lock:
            keys = [k for k in self._data.keys() if k.startswith(prefix)]
            
        for key in keys:
            value, version = await self.get_with_version(key)
            result[key] = (value, version)
        
        logger.debug(f"列出键值: 前缀={prefix}, 找到 {len(result)} 个键")
        return result

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        async with self._global_lock:
            exists = key in self._data
            logger.debug(f"检查键存在: {key} = {exists}")
            return exists

    async def delete(self, key: str) -> bool:
        """删除指定键"""
        async with self._global_lock:
            if key in self._data:
                del self._data[key]
                logger.debug(f"删除键: {key}")
                return True
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """获取黑板统计信息"""
        async with self._global_lock:
            stats = {
                "total_keys": len(self._data),
                "keys": list(self._data.keys()),
                "memory_usage": sum(len(str(kd.value)) for kd in self._data.values() if kd.value is not None)
            }
            logger.debug(f"黑板统计: {stats}")
            return stats

# 全局黑板实例
blackboard = Blackboard()

def ns(run_id: str, name: str) -> str:
    """命名空间工具函数: run:<run_id>:<name>"""
    return f"run:{run_id}:{name}"

def global_ns(name: str) -> str:
    """全局命名空间: global:<name>"""
    return f"global:{name}"

# 便捷函数
async def get_run_state(run_id: str, key: str, default: Any = None) -> Any:
    """获取运行状态"""
    return await blackboard.get(ns(run_id, key), default)

async def set_run_state(run_id: str, key: str, value: Any) -> int:
    """设置运行状态"""
    return await blackboard.set(ns(run_id, key), value)

async def update_run_state(run_id: str, key: str, fn: Callable[[Any], Any]) -> Tuple[Any, int]:
    """更新运行状态"""
    return await blackboard.update(ns(run_id, key), fn)

async def wait_for_run_change(run_id: str, key: str, last_version: int, timeout: Optional[float] = None) -> Tuple[Any, int]:
    """等待运行状态变更"""
    return await blackboard.wait_for_change(ns(run_id, key), last_version, timeout)

async def clear_run_state(run_id: str) -> int:
    """清理运行状态"""
    return await blackboard.clear_namespace(f"run:{run_id}:")

# 初始化函数
async def init_blackboard():
    """初始化共享黑板系统"""
    await blackboard.initialize()
    logger.info("共享黑板系统初始化完成")
