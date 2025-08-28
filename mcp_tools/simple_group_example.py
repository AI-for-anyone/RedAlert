"""
简化编组管理模块使用示例
"""
import asyncio
import logging
from group import GroupMgr

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def my_task(group_mgr: GroupMgr, group_id: int, task_name: str, duration: int = 5):
    """用户自己的任务函数"""
    print(f"{task_name} 开始执行...")
    
    # 获取信号量
    semaphore = group_mgr.get_group_semaphore(group_id)
    if not semaphore:
        print(f"编组 {group_id} 没有信号量，任务退出")
        return
    
    # 使用信号量
    async with semaphore:
        for i in range(duration):
            # 检查是否需要取消
            if group_mgr.should_group_cancel(group_id):
                print(f"{task_name} 检测到取消信号，正在退出...")
                break
            
            await asyncio.sleep(1)
            print(f"{task_name} 执行中... {i+1}/{duration}")
    
    print(f"{task_name} 执行完成")
    
    # 任务完成后释放信号量
    await group_mgr.release_group_semaphore(group_id)

async def main():
    """主函数演示简化的编组管理功能"""
    print("=== 简化编组管理模块演示 ===\n")
    
    # 创建编组管理器
    group_mgr = GroupMgr(min_id=1, max_id=5)
    
    print("1. 查看初始状态:")
    status = group_mgr.get_all_groups_status()
    for group_id, info in status.items():
        print(f"  编组 {group_id}: 空闲={info['is_idle']}, 有信号量={info['has_semaphore']}")
    
    print(f"\n空闲编组: {group_mgr.get_idle_groups()}")
    
    print("\n2. 为编组1创建信号量并启动任务:")
    # 创建信号量
    semaphore = await group_mgr.create_group_semaphore(1, 1)
    print(f"编组1信号量创建成功: {semaphore is not None}")
    
    # 启动任务（用户自己管理）
    task1 = asyncio.create_task(my_task(group_mgr, 1, "任务1", 8))
    
    await asyncio.sleep(2)
    
    print("\n3. 查看编组状态:")
    status = group_mgr.get_all_groups_status()
    for group_id, info in status.items():
        if info['has_semaphore']:
            print(f"  编组 {group_id}: 空闲={info['is_idle']}, 有信号量={info['has_semaphore']}")
    
    print("\n4. 为编组1分配新任务（会取消当前任务）:")
    # 取消当前任务
    await group_mgr.cancel_group_task(1)
    
    # 创建新信号量
    new_semaphore = await group_mgr.create_group_semaphore(1, 1)
    print(f"编组1新信号量创建成功: {new_semaphore is not None}")
    
    # 启动新任务
    task2 = asyncio.create_task(my_task(group_mgr, 1, "新任务", 3))
    
    print("\n5. 演示编组2的任务:")
    # 为编组2创建信号量并启动任务
    await group_mgr.create_group_semaphore(2, 1)
    task3 = asyncio.create_task(my_task(group_mgr, 2, "编组2任务", 6))
    
    # 等待2秒后手动取消
    await asyncio.sleep(2)
    print("\n手动取消编组2的任务:")
    await group_mgr.cancel_group_task(2)
    
    # 等待所有任务完成
    await asyncio.gather(task1, task2, task3, return_exceptions=True)
    
    print("\n6. 最终状态:")
    status = group_mgr.get_all_groups_status()
    for group_id, info in status.items():
        print(f"  编组 {group_id}: 空闲={info['is_idle']}, 有信号量={info['has_semaphore']}")
    
    print(f"\n空闲编组: {group_mgr.get_idle_groups()}")

if __name__ == "__main__":
    asyncio.run(main())
