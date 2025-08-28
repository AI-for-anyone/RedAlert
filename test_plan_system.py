#!/usr/bin/env python3
"""
测试新的计划系统功能
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, List

from graph.plan import PlanNode
from graph.state import GlobalState, WorkflowState
from logs import get_logger

logger = get_logger("test_plan")

class TestResults:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
    
    def add_test(self, name: str, passed: bool, message: str = "", duration: float = 0.0):
        """添加测试结果"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.results.append({
            "name": name,
            "passed": passed,
            "message": message,
            "duration": duration,
            "status": status
        })
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        
        logger.info(f"{status} | {name} | {duration:.3f}s | {message}")

async def test_plan_node_initialization():
    """测试计划节点初始化"""
    results = TestResults()
    
    start_time = time.time()
    try:
        plan_node = PlanNode()
        await plan_node.initialize()
        results.add_test("计划节点初始化", True, "初始化成功", time.time() - start_time)
    except Exception as e:
        results.add_test("计划节点初始化", False, f"初始化失败: {e}", time.time() - start_time)
        return results
    
    return results, plan_node

async def test_plan_generation():
    """测试计划生成功能"""
    results = TestResults()
    
    # 初始化节点
    plan_node = PlanNode()
    await plan_node.initialize()
    
    # 测试用例
    test_cases = [
        {
            "name": "简单生产命令",
            "command": "生产10个步兵单位",
            "expected_stages": 1
        },
        {
            "name": "复合作战命令", 
            "command": "先移动视角到敌方基地，然后查看敌方单位信息，同时生产坦克和派遣侦察兵",
            "expected_stages": 2  # 预期至少2个阶段
        },
        {
            "name": "复杂战术命令",
            "command": "移动到北部战区，生产防空单位，派遣工程师修复建筑，查询资源状态",
            "expected_stages": 1  # 可能是并行执行
        }
    ]
    
    for test_case in test_cases:
        start_time = time.time()
        try:
            # 创建测试状态
            test_state = {
                "input_cmd": test_case["command"],
                "state": WorkflowState.INIT,
                "run_id": str(uuid.uuid4()),
                "execution_plan": None,
                "current_stage": None,
                "stage_results": None
            }
            
            # 调用计划节点
            command = plan_node.plan_node(test_state)
            
            # 应用Command的更新到test_state
            if hasattr(command, 'update') and command.update:
                test_state.update(command.update)
            
            # 验证结果
            assert "execution_plan" in test_state, "execution_plan字段缺失"
            assert test_state["execution_plan"] is not None, "execution_plan为空"
            assert len(test_state["execution_plan"]) >= test_case["expected_stages"], f"阶段数不足: 期望>={test_case['expected_stages']}, 实际{len(test_state['execution_plan'])}"
            assert command.goto == "execute_plan", f"路由错误: 期望execute_plan, 实际{command.goto}"
            
            # 验证计划结构
            execution_plan = test_state["execution_plan"]
            for stage in execution_plan:
                assert "stage" in stage
                assert "type" in stage
                assert "tasks" in stage
                assert stage["type"] in ["serial", "parallel"]
                assert len(stage["tasks"]) > 0
                
                for task in stage["tasks"]:
                    assert "assistant" in task
                    assert "task" in task
            
            plan_info = f"{len(execution_plan)} 阶段，{sum(len(s['tasks']) for s in execution_plan)} 任务"
            results.add_test(f"计划生成-{test_case['name']}", True, plan_info, time.time() - start_time)
            
        except Exception as e:
            import traceback
            error_details = f"生成失败: {e}\n{traceback.format_exc()}"
            results.add_test(f"计划生成-{test_case['name']}", False, error_details, time.time() - start_time)
    
    return results

async def test_plan_execution():
    """测试计划执行功能"""
    results = TestResults()
    
    # 初始化节点
    plan_node = PlanNode()
    await plan_node.initialize()
    
    start_time = time.time()
    try:
        # 创建测试计划
        test_plan = [
            {
                "stage": 1,
                "type": "serial",
                "tasks": [
                    {"assistant": "地图视角控制", "task": "移动到目标区域"},
                    {"assistant": "信息查询", "task": "查看敌方单位"}
                ]
            },
            {
                "stage": 2,
                "type": "parallel",
                "tasks": [
                    {"assistant": "生产管理", "task": "生产步兵"},
                    {"assistant": "单位控制", "task": "派遣侦察兵"}
                ]
            }
        ]
        
        # 创建测试状态
        test_state = {
            "input_cmd": "测试复合命令",
            "execution_plan": test_plan,
            "current_stage": 0,
            "stage_results": [],
            "state": WorkflowState.EXECUTING,
            "run_id": str(uuid.uuid4())
        }
        
        # 执行所有阶段
        total_stages = len(test_plan)
        executed_stages = 0
        
        while test_state["current_stage"] < total_stages:
            command = await plan_node.execute_plan_node(test_state)
            
            # 手动应用Command的更新到test_state
            if hasattr(command, 'update') and command.update:
                test_state.update(command.update)
            
            executed_stages += 1
            
            if command.goto == "cleanup_run":
                break
                
            # 安全检查：防止无限循环
            if executed_stages > total_stages * 2:
                raise Exception("执行超时，可能陷入无限循环")
        
        # 验证执行结果
        assert executed_stages == total_stages
        assert len(test_state["stage_results"]) == total_stages
        
        # 验证串行阶段结果
        serial_result = test_state["stage_results"][0]
        assert serial_result["type"] == "serial"
        assert len(serial_result["results"]) == 2
        
        # 验证并行阶段结果  
        parallel_result = test_state["stage_results"][1]
        assert parallel_result["type"] == "parallel"
        assert len(parallel_result["results"]) == 2
        
        results.add_test("计划执行-多阶段", True, f"执行了 {executed_stages} 个阶段", time.time() - start_time)
        
    except Exception as e:
        results.add_test("计划执行-多阶段", False, f"执行失败: {e}", time.time() - start_time)
    
    return results

async def test_serial_vs_parallel_execution():
    """测试串行和并行执行的差异"""
    results = TestResults()
    
    # 初始化节点
    plan_node = PlanNode()
    await plan_node.initialize()
    
    # 测试串行执行
    start_time = time.time()
    try:
        serial_plan = [{
            "stage": 1,
            "type": "serial", 
            "tasks": [
                {"assistant": "信息查询", "task": "任务1"},
                {"assistant": "信息查询", "task": "任务2"},
                {"assistant": "信息查询", "task": "任务3"}
            ]
        }]
        
        test_state = {
            "execution_plan": serial_plan,
            "current_stage": 0,
            "stage_results": [],
            "run_id": str(uuid.uuid4())
        }
        
        serial_start = time.time()
        command = await plan_node.execute_plan_node(test_state)
        # 应用状态更新
        if hasattr(command, 'update') and command.update:
            test_state.update(command.update)
        serial_duration = time.time() - serial_start
        
        results.add_test("串行执行", True, f"3个任务耗时 {serial_duration:.3f}s", time.time() - start_time)
        
    except Exception as e:
        results.add_test("串行执行", False, f"执行失败: {e}", time.time() - start_time)
    
    # 测试并行执行
    start_time = time.time()
    try:
        parallel_plan = [{
            "stage": 1,
            "type": "parallel",
            "tasks": [
                {"assistant": "信息查询", "task": "任务1"},
                {"assistant": "信息查询", "task": "任务2"}, 
                {"assistant": "信息查询", "task": "任务3"}
            ]
        }]
        
        test_state = {
            "execution_plan": parallel_plan,
            "current_stage": 0,
            "stage_results": [],
            "run_id": str(uuid.uuid4())
        }
        
        parallel_start = time.time()
        command = await plan_node.execute_plan_node(test_state)
        # 应用状态更新
        if hasattr(command, 'update') and command.update:
            test_state.update(command.update)
        parallel_duration = time.time() - parallel_start
        
        results.add_test("并行执行", True, f"3个任务耗时 {parallel_duration:.3f}s", time.time() - start_time)
        
    except Exception as e:
        results.add_test("并行执行", False, f"执行失败: {e}", time.time() - start_time)
    
    return results

async def test_error_handling():
    """测试错误处理"""
    results = TestResults()
    
    # 初始化节点
    plan_node = PlanNode()
    await plan_node.initialize()
    
    # 测试无效JSON响应处理
    start_time = time.time()
    try:
        # 测试解析错误处理
        invalid_responses = [
            "这不是JSON",
            '{"invalid": "structure"}',
            '[{"missing": "fields"}]',
            '[]'  # 空数组
        ]
        
        exceptions_caught = 0
        for invalid_response in invalid_responses:
            try:
                plan_node._parse_plan_response(invalid_response)
                # 如果没有抛出异常，则测试失败
                results.add_test("错误处理-无效JSON", False, f"响应'{invalid_response[:20]}...'应该抛出解析异常", time.time() - start_time)
                return results
            except ValueError as e:
                # 正确抛出了解析异常
                exceptions_caught += 1
                continue
        
        results.add_test("错误处理-无效JSON", True, "正确处理了解析错误", time.time() - start_time)
        
    except Exception as e:
        results.add_test("错误处理-无效JSON", False, f"测试失败: {e}", time.time() - start_time)
    
    return results

async def main():
    """主测试函数"""
    logger.info("开始计划系统测试")
    logger.info("=" * 50)
    
    all_results = []
    
    # 运行所有测试模块
    test_modules = [
        ("计划节点初始化", test_plan_node_initialization),
        ("计划生成功能", test_plan_generation), 
        ("计划执行功能", test_plan_execution),
        ("串行并行对比", test_serial_vs_parallel_execution),
        ("错误处理", test_error_handling)
    ]
    
    for module_name, test_func in test_modules:
        logger.info(f"\n测试模块: {module_name}")
        logger.info("=" * 40)
        
        try:
            if module_name == "计划节点初始化":
                module_results, _ = await test_func()
            else:
                module_results = await test_func()
            
            all_results.append(module_results)
            logger.info(f"模块 {module_name}: {module_results.passed}/{module_results.passed + module_results.failed} 通过")
            
        except Exception as e:
            logger.error(f"测试模块 {module_name} 执行失败: {e}")
            # 创建失败结果
            failed_results = TestResults()
            failed_results.add_test(f"{module_name}-执行", False, f"模块执行异常: {e}")
            all_results.append(failed_results)
    
    # 汇总结果
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    success_rate = total_passed / (total_passed + total_failed) * 100 if (total_passed + total_failed) > 0 else 0
    
    logger.info("\n" + "=" * 60)
    logger.info(f"测试摘要: {total_passed}/{total_passed + total_failed} 通过 ({total_failed} 失败)")
    logger.info("=" * 60)
    
    if total_failed > 0:
        logger.info("\n失败的测试:")
        for results in all_results:
            for result in results.results:
                if not result["passed"]:
                    logger.info(f"  ❌ {result['name']}: {result['message']}")
    
    logger.info(f"\n成功率: {success_rate:.1f}%")
    
    return 0 if total_failed == 0 else 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
