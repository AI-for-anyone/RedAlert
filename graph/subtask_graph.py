"""
动态串并行子任务执行器
基于 LangGraph 实现复杂子任务的串行和并行混合执行
"""
import operator
import asyncio
from typing import TypedDict, Literal, List, Dict, Any, Optional, Annotated
from langgraph.graph import StateGraph, START, END
from logs import get_logger
from .blackboard import blackboard, ns

logger = get_logger("subtask_graph")

# 阶段定义：serial 顺序执行；parallel 并行执行
class Stage(TypedDict):
    kind: Literal["serial", "parallel"]
    actions: List[Dict[str, Any]]  # 每个 action 是一个原子任务的参数包

class SubtaskState(TypedDict):
    """子任务状态"""
    plan: List[Stage]  # 执行计划
    stage_idx: int     # 当前阶段索引
    serial_cursor: int # 串行执行指针
    # 聚合结果，使用 Annotated + reducer 让并发 merge
    results: Annotated[List[Any], operator.add]
    run_id: Optional[str]  # 运行ID，用于黑板交互
    action: Optional[Dict[str, Any]]  # 当前执行的动作（Send分支使用）

async def plan_subtasks(state: SubtaskState) -> SubtaskState:
    """生成子任务执行计划"""
    logger.info("开始生成子任务执行计划")
    
    # 如果没有现成计划，动态生成
    if not state.get("plan"):
        # 这里可以基于 LLM 或规则引擎动态生成计划
        # 示例：第1阶段并行生产3个单位；第2阶段串行下达两条编队命令
        state["plan"] = [
            {
                "kind": "parallel", 
                "actions": [
                    {"type": "produce", "unit": "rifle", "count": 1},
                    {"type": "produce", "unit": "rifle", "count": 1}, 
                    {"type": "produce", "unit": "dog", "count": 1}
                ]
            },
            {
                "kind": "serial", 
                "actions": [
                    {"type": "move", "to": [10, 20], "units": "group1"},
                    {"type": "attack", "target": "enemy_oil", "units": "group1"}
                ]
            },
        ]
        state["stage_idx"] = 0
        state["serial_cursor"] = 0
        state["results"] = []
        
        logger.info(f"生成执行计划: {len(state['plan'])} 个阶段")
        for i, stage in enumerate(state["plan"]):
            logger.info(f"  阶段 {i}: {stage['kind']} - {len(stage['actions'])} 个动作")
    
    # 如果有 run_id，记录计划到黑板
    if state.get("run_id"):
        await blackboard.set(ns(state["run_id"], "subtask_plan"), state["plan"])
        logger.debug(f"计划已记录到黑板: run_id={state['run_id']}")
    
    return state

def _done(state: SubtaskState) -> bool:
    """检查是否所有阶段都已完成"""
    return state["stage_idx"] >= len(state["plan"])

async def dispatch_stage(state: SubtaskState):
    """阶段调度器 - 根据阶段类型进行分发"""
    if _done(state):
        logger.info("所有阶段执行完成")
        return state
    
    stage = state["plan"][state["stage_idx"]]
    stage_type = stage["kind"]
    actions = stage["actions"]
    
    logger.info(f"调度阶段 {state['stage_idx']}: {stage_type} - {len(actions)} 个动作")
    
    if stage_type == "parallel":
        # 并行执行所有动作
        logger.info(f"并行执行 {len(actions)} 个任务")
        parallel_results = []
        
        # 使用asyncio.gather来并行执行
        async def execute_action(action):
            logger.info(f"执行并行动作: {action}")
            try:
                if action.get("type") == "produce":
                    result = {"ok": True, "action": action, "message": f"生产 {action.get('unit')} 成功"}
                elif action.get("type") == "move":
                    result = {"ok": True, "action": action, "message": f"移动到 {action.get('to')} 成功"}
                elif action.get("type") == "attack":
                    result = {"ok": True, "action": action, "message": f"攻击 {action.get('target')} 成功"}
                else:
                    result = {"ok": True, "action": action, "message": "未知动作类型"}
                logger.info(f"动作执行成功: {result['message']}")
                return result
            except Exception as e:
                result = {"ok": False, "action": action, "error": str(e)}
                logger.error(f"动作执行失败: {e}")
                return result
        
        # 并行执行所有动作
        try:
            parallel_results = await asyncio.gather(*[execute_action(action) for action in actions])
        except Exception as e:
            logger.error(f"并行执行失败: {e}")
            parallel_results = [{"ok": False, "action": {}, "error": str(e)}]
        
        # 将结果添加到状态
        if "results" not in state:
            state["results"] = []
        state["results"].extend(parallel_results)
        
        # 进入下个阶段
        state["stage_idx"] += 1
        state["serial_cursor"] = 0
        
        return state
    else:
        # 串行：推进到 execute_serial
        logger.info("进入串行执行模式")
        return state

# 移除了do_one和join_parallel函数，因为并行执行现在在dispatch_stage中直接处理

async def execute_serial(state: SubtaskState):
    """串行执行器"""
    if _done(state):
        logger.info("串行执行：所有阶段完成")
        return state
    
    stage = state["plan"][state["stage_idx"]]
    if stage["kind"] != "serial":
        logger.info("串行执行：当前阶段非串行，跳过")
        return state
    
    actions = stage["actions"]
    cursor = state["serial_cursor"]
    
    if cursor >= len(actions):
        # 本串行阶段完成，进入下个阶段
        logger.info(f"串行阶段 {state['stage_idx']} 完成")
        state["stage_idx"] += 1
        state["serial_cursor"] = 0
        return state
    
    # 执行当前 action（顺序执行，不用 Send）
    action = actions[cursor]
    logger.info(f"执行串行动作 {cursor}: {action}")
    
    # 检查是否需要从黑板获取计划更新
    if state.get("run_id"):
        try:
            updated_plan, _ = await blackboard.get_with_version(ns(state["run_id"], "subtask_plan"))
            if updated_plan and updated_plan != state["plan"]:
                state["plan"] = updated_plan
                logger.info("从黑板更新了执行计划")
                # 重新检查当前阶段是否还有效
                if state["stage_idx"] >= len(state["plan"]):
                    return state
                stage = state["plan"][state["stage_idx"]]
                actions = stage["actions"]
                if cursor >= len(actions):
                    state["stage_idx"] += 1
                    state["serial_cursor"] = 0
                    return state
                action = actions[cursor]
        except Exception as e:
            logger.warning(f"从黑板获取计划更新失败: {e}")
    
    try:
        if action.get("type") == "produce":
            result = {"ok": True, "action": action, "message": f"生产 {action.get('unit')} 成功"}
        elif action.get("type") == "move":
            result = {"ok": True, "action": action, "message": f"移动到 {action.get('to')} 成功"}
        elif action.get("type") == "attack":
            result = {"ok": True, "action": action, "message": f"攻击 {action.get('target')} 成功"}
        else:
            result = {"ok": True, "action": action, "message": "未知动作类型"}
        
        logger.info(f"串行动作执行成功: {result['message']}")
    except Exception as e:
        result = {"ok": False, "action": action, "error": str(e)}
        logger.error(f"串行动作执行失败: {e}")
    
    # 记录结果
    if "results" not in state:
        state["results"] = []
    state["results"].append(result)
    
    # 推进指针
    state["serial_cursor"] = cursor + 1
    
    return state

def should_continue_from_dispatch(state: SubtaskState) -> str:
    """从 dispatch 节点的条件分支"""
    if _done(state):
        return "end"
    
    stage = state["plan"][state["stage_idx"]]
    if stage["kind"] == "serial":
        return "serial"
    else:
        return "dispatch"  # 并行已在dispatch中处理，继续下个阶段

def should_continue_from_serial(state: SubtaskState) -> str:
    """从 execute_serial 节点的条件分支"""
    if _done(state):
        return "end"
    
    # 检查当前阶段是否完成
    stage = state["plan"][state["stage_idx"]]
    if stage["kind"] == "serial" and state["serial_cursor"] < len(stage["actions"]):
        return "continue_serial"  # 继续串行执行
    else:
        return "next_stage"  # 进入下个阶段

def build_subtask_graph():
    """构建子任务执行图"""
    logger.info("构建子任务执行图")
    
    g = StateGraph(SubtaskState)
    
    # 添加节点
    g.add_node("plan", plan_subtasks)
    g.add_node("dispatch", dispatch_stage)
    g.add_node("execute_serial", execute_serial)
    
    # 基本流程
    g.add_edge(START, "plan")
    g.add_edge("plan", "dispatch")
    
    # 条件分支：从 dispatch 根据阶段类型分发
    g.add_conditional_edges(
        "dispatch",
        should_continue_from_dispatch,
        {
            "serial": "execute_serial",
            "dispatch": "dispatch",  # 并行完成后继续调度
            "end": END
        }
    )
    
    # 串行阶段循环：execute_serial -> dispatch（循环直到阶段完成）
    g.add_conditional_edges(
        "execute_serial",
        should_continue_from_serial,
        {
            "continue_serial": "execute_serial",  # 继续串行执行
            "next_stage": "dispatch",  # 进入下个阶段
            "end": END
        }
    )
    
    compiled = g.compile()
    logger.info("子任务执行图构建完成")
    return compiled

# 便捷函数
async def execute_subtask(plan: Optional[List[Stage]] = None, run_id: Optional[str] = None) -> Dict[str, Any]:
    """执行子任务"""
    logger.info(f"开始执行子任务: run_id={run_id}")
    
    subtask_graph = build_subtask_graph()
    
    # 构造初始状态
    initial_state = {
        "plan": plan or [],
        "stage_idx": 0,
        "serial_cursor": 0,
        "results": [],
        "run_id": run_id
    }
    
    try:
        result = await subtask_graph.ainvoke(initial_state)
        logger.info(f"子任务执行完成: {len(result.get('results', []))} 个结果")
        return result
    except Exception as e:
        logger.error(f"子任务执行失败: {e}")
        raise

# 计划生成器示例
def create_production_plan(units: List[Dict[str, Any]]) -> List[Stage]:
    """创建生产计划"""
    return [
        {
            "kind": "parallel",
            "actions": [{"type": "produce", **unit} for unit in units]
        }
    ]

def create_attack_plan(targets: List[Dict[str, Any]]) -> List[Stage]:
    """创建攻击计划"""
    return [
        {
            "kind": "serial",
            "actions": [{"type": "attack", **target} for target in targets]
        }
    ]

def create_mixed_plan(production_units: List[Dict[str, Any]], attack_targets: List[Dict[str, Any]]) -> List[Stage]:
    """创建混合计划：先并行生产，后串行攻击"""
    stages = []
    
    if production_units:
        stages.append({
            "kind": "parallel",
            "actions": [{"type": "produce", **unit} for unit in production_units]
        })
    
    if attack_targets:
        stages.append({
            "kind": "serial", 
            "actions": [{"type": "attack", **target} for target in attack_targets]
        })
    
    return stages
