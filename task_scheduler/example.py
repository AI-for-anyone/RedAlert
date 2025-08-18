"""
并发管理模块使用示例
演示如何使用基于asyncio的单例并发管理器
"""

import asyncio
import random
from task_scheduler import get_concurrency_manager, submit_task, wait_for_task, get_stats


async def sample_task(task_name: str, duration: float) -> str:
    """示例异步任务"""
    print(f"Task {task_name} started, will run for {duration:.2f} seconds")
    await asyncio.sleep(duration)
    result = f"Task {task_name} completed after {duration:.2f} seconds"
    print(result)
    return result


async def failing_task(task_name: str) -> str:
    """会失败的示例任务"""
    print(f"Failing task {task_name} started")
    await asyncio.sleep(1)
    raise Exception(f"Task {task_name} failed intentionally")


async def main():
    """主函数演示并发管理器的使用"""
    
    # 获取并发管理器实例（单例模式）
    manager = get_concurrency_manager(max_concurrent_tasks=3, enable_logging=True)
    
    print("=== 并发管理器示例 ===\n")
    
    # 1. 提交多个任务
    print("1. 提交多个并发任务...")
    task_ids = []
    
    for i in range(5):
        duration = random.uniform(1, 3)
        task_id = await submit_task(
            sample_task, 
            f"Task-{i+1}", 
            duration,
            task_name=f"SampleTask-{i+1}"
        )
        task_ids.append(task_id)
    
    # 2. 提交一个会失败的任务
    print("\n2. 提交一个会失败的任务...")
    failing_task_id = await manager.submit_task(
        failing_task,
        "FailingTask",
        task_name="FailingTask"
    )
    task_ids.append(failing_task_id)
    
    # 3. 查看统计信息
    print("\n3. 查看当前统计信息:")
    stats = get_stats()
    print(f"总任务数: {stats['total_tasks']}")
    print(f"运行中任务数: {stats['running_tasks']}")
    print(f"最大并发数: {stats['max_concurrent']}")
    print(f"状态统计: {stats['status_counts']}")
    
    # 4. 等待部分任务完成
    print("\n4. 等待第一个任务完成...")
    try:
        result = await wait_for_task(task_ids[0], timeout=5)
        print(f"第一个任务结果: {result}")
    except Exception as e:
        print(f"等待任务时出错: {e}")
    
    # 5. 取消一个任务
    if len(task_ids) > 1:
        print(f"\n5. 取消任务 {task_ids[1]}...")
        cancelled = await manager.cancel_task(task_ids[1])
        print(f"任务取消成功: {cancelled}")
    
    # 6. 等待所有任务完成
    print("\n6. 等待所有剩余任务完成...")
    try:
        results = await manager.wait_all_tasks(timeout=10)
        print("所有任务完成!")
        for task_id, result in results.items():
            if isinstance(result, Exception):
                print(f"任务 {task_id} 失败: {result}")
            else:
                print(f"任务 {task_id} 成功: {result}")
    except asyncio.TimeoutError:
        print("等待任务超时")
    
    # 7. 查看最终统计信息
    print("\n7. 最终统计信息:")
    final_stats = get_stats()
    print(f"总任务数: {final_stats['total_tasks']}")
    print(f"运行中任务数: {final_stats['running_tasks']}")
    print(f"状态统计: {final_stats['status_counts']}")
    
    # 8. 查看所有任务信息
    print("\n8. 所有任务详细信息:")
    all_tasks = manager.get_all_tasks_info()
    for task_id, task_info in all_tasks.items():
        print(f"任务 {task_id}:")
        print(f"  名称: {task_info.name}")
        print(f"  状态: {task_info.status.value}")
        print(f"  创建时间: {task_info.created_at}")
        if task_info.started_at:
            print(f"  开始时间: {task_info.started_at}")
        if task_info.completed_at:
            print(f"  完成时间: {task_info.completed_at}")
            duration = task_info.completed_at - task_info.created_at
            print(f"  总耗时: {duration:.2f}秒")
        if task_info.error:
            print(f"  错误: {task_info.error}")
        print()


async def callback_example():
    """演示回调函数的使用"""
    print("\n=== 回调函数示例 ===\n")
    
    manager = get_concurrency_manager()
    
    # 定义回调函数
    def on_task_start(task_id: str, task_info):
        print(f"🚀 回调: 任务 {task_id} ({task_info.name}) 开始执行")
    
    def on_task_complete(task_id: str, task_info):
        print(f"✅ 回调: 任务 {task_id} ({task_info.name}) 执行完成")
    
    def on_task_error(task_id: str, task_info):
        print(f"❌ 回调: 任务 {task_id} ({task_info.name}) 执行失败: {task_info.error}")
    
    # 添加回调函数
    manager.add_callback('on_start', on_task_start)
    manager.add_callback('on_complete', on_task_complete)
    manager.add_callback('on_error', on_task_error)
    
    # 提交任务
    task_id1 = await manager.submit_task(sample_task, "CallbackTask1", 2.0)
    task_id2 = await manager.submit_task(failing_task, "CallbackFailTask")
    
    # 等待任务完成
    await manager.wait_all_tasks()
    
    print("回调函数示例完成")


async def task_group_example():
    """演示任务组的使用"""
    print("\n=== 任务组示例 ===\n")
    
    manager = get_concurrency_manager()
    
    # 使用任务组限制并发数
    async with manager.task_group(max_concurrent=2) as group:
        print("在任务组中提交任务（最大并发数=2）...")
        
        tasks = []
        for i in range(4):
            task = asyncio.create_task(sample_task(f"GroupTask-{i+1}", 5))
            tasks.append(task)
            group.append(task)
        
        print("等待任务组中的所有任务完成...")
    
    print("任务组示例完成")


if __name__ == "__main__":
    async def run_all_examples():
        """运行所有示例"""
        await main()
        await callback_example()
        await task_group_example()
        
        # 清理资源
        manager = get_concurrency_manager()
        await manager.cleanup()
        print("\n所有示例完成，资源已清理")
    
    # 运行示例
    asyncio.run(run_all_examples())
