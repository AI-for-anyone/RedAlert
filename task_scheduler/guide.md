# 任务调度器 (task_scheduler) 使用指南

`task_scheduler` 是一个基于 asyncio 的并发任务管理模块，提供了强大的任务调度、分组和监控功能。

## 基本概念

- **Task**: 单个异步任务的封装，管理任务状态和结果
- **TaskGroup**: 任务组，支持嵌套和批量操作
- **TaskManager**: 全局任务管理器，采用单例模式
- **TaskStatus**: 任务状态枚举（PENDING、RUNNING、COMPLETED、FAILED、CANCELLED）

## 快速入门

### 1. 初始化 TaskManager

```python
import asyncio
from task_scheduler import TaskManager

# 获取TaskManager单例（异步方法）
async def get_manager():
    manager = await TaskManager.get_instance()
    return manager

# 或在同步代码中获取实例（需要事件循环已启动）
manager = TaskManager.get_instance_sync()
```

### 2. 创建并提交单个任务

```python
async def example_task():
    # 模拟一些异步操作
    await asyncio.sleep(1)
    return "Task completed"

async def run_task():
    manager = await TaskManager.get_instance()
    
    # 创建任务
    task = await manager.create_task(example_task, name="MyTask")
    
    # 提交任务执行
    asyncio_task = await manager.submit_task(task.id)
    
    # 等待任务完成
    result = await asyncio_task
    print(f"Task result: {result}")
```

### 3. 使用任务组

```python
async def run_task_group():
    manager = await TaskManager.get_instance()
    
    # 创建任务组
    group = await manager.create_group(name="MyTaskGroup")
    
    # 添加多个任务到组
    task1 = await manager.create_task(example_task, name="Task1", group_id=group.id)
    task2 = await manager.create_task(example_task, name="Task2", group_id=group.id)
    
    # 提交整个任务组
    group_task = await manager.submit_group(group.id)
    
    # 等待所有任务完成
    results = await group_task
    print(f"Group results: {results}")
```

### 4. 嵌套任务组

```python
async def run_nested_groups():
    manager = await TaskManager.get_instance()
    
    # 创建父任务组
    parent_group = await manager.create_group(name="ParentGroup")
    
    # 创建子任务组
    child_group = await manager.create_group(name="ChildGroup", parent_group_id=parent_group.id)
    
    # 添加任务到子组
    await manager.create_task(example_task, name="NestedTask", group_id=child_group.id)
    
    # 提交父组会执行所有嵌套任务
    await manager.submit_group(parent_group.id)
```

## 高级功能

### 取消任务或任务组

```python
# 取消单个任务
await manager.cancel_task(task_id)

# 取消整个任务组（包括所有子任务和子组）
await manager.cancel_group(group_id)
```

### 查询任务状态和结果

```python
# 获取任务状态
status = manager.get_task_status(task_id)

# 获取任务结果（已完成的任务）
result = manager.get_task_result(task_id)

# 获取任务详细信息
task_info = manager.get_task_info(task_id)

# 获取任务组详细信息
group_info = manager.get_group_info(group_id)
```

### 等待所有任务完成

```python
# 等待所有任务完成（阻塞直到所有任务结束）
await manager.wait_all()
```

### 调试信息

```python
# 获取详细调试信息
debug_info = await manager.debug_info()

# 打印调试信息（同步方法）
manager.print_debug_info()
```

## 线程安全性

TaskManager 使用细粒度锁确保在并发环境中安全地访问共享数据结构：

- `_tasks_lock`: 保护任务字典
- `_groups_lock`: 保护任务组字典
- `_running_lock`: 保护运行中的任务集合

## 最佳实践

1. **使用任务组管理相关任务**：对相关任务进行分组，便于批量操作和状态管理
2. **处理异常**：任务失败时会存储异常，可通过 `task.error` 获取
3. **避免阻塞**：所有长时间运行的操作应在异步任务中执行
4. **使用 await**：确保使用 await 等待异步操作完成
5. **注意单例模式**：TaskManager 是单例，无需创建多个实例

## 注意事项

- 所有与 TaskManager 的交互应在异步环境中进行