import os
import json
import time
from typing import List, Dict, Any, Optional
import asyncio

from prompt import classify_prompt
from .state import GlobalState, WorkflowState, WorkflowType, NextCommand
from .token_logger import token_logger
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from langgraph.graph import END
from logs import get_logger

logger = get_logger("plan")

class PlanNode:
    def __init__(self):
        self._llm = None
        self._prompt = """你是一个AI助手，负责分析用户命令并生成执行计划。

请分析用户输入的命令，生成包含串行和并行执行的任务计划。

可用的助手节点：
- 地图视角控制: 控制游戏视角移动、缩放
- 生产管理: 管理单位生产、建筑建造  
- 单位控制: 控制单位移动、攻击
- 信息查询: 查询游戏状态、资源信息

输出格式为JSON数组，包含执行阶段：
```json
[
  {
    "stage": 1,
    "type": "serial",  // 串行执行
    "tasks": [
      {"assistant": "地图视角控制", "task": "移动到目标区域"},
      {"assistant": "信息查询", "task": "查看敌方单位"}
    ]
  },
  {
    "stage": 2, 
    "type": "parallel", // 并行执行
    "tasks": [
      {"assistant": "生产管理", "task": "生产步兵"},
      {"assistant": "单位控制", "task": "派遣侦察兵"}
    ]
  }
]
```

请根据任务的逻辑依赖关系合理安排串行和并行执行。
"""
        self._initialized = False
    
    async def initialize(self):
        """异步初始化计划节点"""
        if self._initialized:
            return
        
        try:
            self._llm = ChatOpenAI(
                model=os.getenv("CLASSIFY_MODEL"), 
                api_key=os.getenv("CLASSIFY_API_KEY"), 
                base_url=os.getenv("CLASSIFY_API_BASE"),
                extra_body={
                    "thinking": {
                        "type": "disabled"  # 关闭深度思考
                    }
                }
            )
            self._initialized = True
            logger.info("计划节点初始化完成")
        except Exception as e:
            logger.error(f"计划节点初始化失败: {e}")
            raise

    def _parse_plan_response(self, response_content: str) -> List[Dict[str, Any]]:
        """解析计划响应的 JSON 格式"""
        try:
            # 尝试直接解析 JSON
            stages = json.loads(response_content)
            
            # 验证格式
            if not isinstance(stages, list):
                raise ValueError("响应不是数组格式")
            
            for stage in stages:
                if not isinstance(stage, dict):
                    raise ValueError("阶段格式不正确")
                
                required_keys = ["stage", "type", "tasks"]
                for key in required_keys:
                    if key not in stage:
                        raise ValueError(f"阶段缺少必需字段: {key}")
                
                if stage["type"] not in ["serial", "parallel"]:
                    raise ValueError(f"无效的执行类型: {stage['type']}")
                
                if not isinstance(stage["tasks"], list) or len(stage["tasks"]) == 0:
                    raise ValueError("tasks字段必须是非空数组")
                
                for task in stage["tasks"]:
                    if not isinstance(task, dict) or "assistant" not in task or "task" not in task:
                        raise ValueError("任务格式不正确，缺少 assistant 或 task 字段")
            
            return stages
            
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试提取 JSON 部分
            try:
                # 查找 JSON 数组的开始和结束
                start = response_content.find('[')
                end = response_content.rfind(']') + 1
                
                if start != -1 and end != 0:
                    json_str = response_content[start:end]
                    stages = json.loads(json_str)
                    
                    # 递归验证
                    return self._parse_plan_response(json_str)
                else:
                    raise ValueError("未找到有效的 JSON 数组")
                    
            except Exception as e:
                raise ValueError(f"解析计划响应失败: {e}")

    def _determine_workflow_type(self, assistant: str) -> str:
        """根据助手类型确定工作流类型"""
        match assistant:
            case "地图视角控制":
                return WorkflowType.CAMERA_CONTROL.value
            case "生产管理":
                return WorkflowType.PRODUCTION.value
            case "单位控制":
                return WorkflowType.UNIT_CONTROL.value
            case "信息查询":
                return WorkflowType.INTELLIGENCE.value
            case _:
                logger.error(f"无法识别的助手类型: {assistant}")
                return WorkflowType.INTELLIGENCE.value  # 默认返回信息查询

    async def _execute_single_task(self, state: GlobalState, task: Dict[str, str]) -> Dict[str, Any]:
        """执行单个任务，调用对应的节点"""
        from .camera import CameraNode
        from .production import ProductionNode  
        from .unit_control import UnitControlNode
        from .intelligence import IntelligenceNode
        
        workflow_type = self._determine_workflow_type(task['assistant'])
        logger.info(f"执行任务: [{task['assistant']}] {task['task']} -> {workflow_type}")
        
        # 更新状态中的任务信息
        task_state = state.copy()
        task_state["input_cmd"] = task["task"]
        task_state["cmd_type"] = workflow_type
        
        try:
            # 根据工作流类型调用对应节点
            if workflow_type == WorkflowType.CAMERA_CONTROL.value:
                # 这里需要访问图中的节点实例，暂时模拟执行
                result = f"相机控制执行完成: {task['task']}"
            elif workflow_type == WorkflowType.PRODUCTION.value:
                result = f"生产管理执行完成: {task['task']}"
            elif workflow_type == WorkflowType.UNIT_CONTROL.value:
                result = f"单位控制执行完成: {task['task']}"
            elif workflow_type == WorkflowType.INTELLIGENCE.value:
                result = f"信息查询执行完成: {task['task']}"
            else:
                result = f"未知任务类型执行完成: {task['task']}"
            
            return {
                "task": task,
                "workflow_type": workflow_type,
                "status": "completed",
                "result": result,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"任务执行失败: {e}")
            return {
                "task": task,
                "workflow_type": workflow_type,
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }

    async def _execute_stage(self, state: GlobalState, stage: Dict[str, Any]) -> Dict[str, Any]:
        """执行一个阶段的任务"""
        stage_type = stage["type"]
        tasks = stage["tasks"]
        
        logger.info(f"开始执行阶段 {stage['stage']} ({stage_type}): {len(tasks)} 个任务")
        
        if stage_type == "serial":
            # 串行执行
            results = []
            for i, task in enumerate(tasks):
                logger.info(f"串行执行任务 {i+1}/{len(tasks)}: [{task['assistant']}] {task['task']}")
                result = await self._execute_single_task(state, task)
                results.append(result)
            
            return {"type": "serial", "results": results}
            
        else:  # parallel
            # 并行执行
            logger.info(f"并行执行 {len(tasks)} 个任务")
            
            # 并行执行所有任务
            results = await asyncio.gather(*[
                self._execute_single_task(state, task) for task in tasks
            ])
            
            return {"type": "parallel", "results": results}

    def plan_node(self, global_state: GlobalState) -> Command:
        """计划节点主逻辑"""
        
        # 初始化计划状态
        if "execution_plan" not in global_state or global_state["execution_plan"] is None:
            logger.info(f"开始分析命令生成执行计划: {global_state['input_cmd']}")
            
            # 生成执行计划
            messages = [
                {"role": "system", "content": self._prompt},
                {"role": "user", "content": global_state["input_cmd"]}
            ]

            # 记录 LLM 调用耗时
            start_time = time.time()
            response = self._llm.invoke(messages)
            end_time = time.time()
            
            elapsed_time = end_time - start_time
            duration_ms = elapsed_time * 1000
            
            # 记录token使用
            try:
                tokens = response.response_metadata.get("token_usage").get("total_tokens")
            except Exception as e:
                logger.error(f"记录token使用失败: {e}")
                tokens = 0
            
            token_logger.log_usage("plan", "llm", tokens, duration_ms)
            logger.debug(f"LLM 计划耗时: {elapsed_time:.2f} 秒，response: {response}")
            
            # 解析执行计划
            try:
                execution_plan = self._parse_plan_response(response.content)
                
                logger.info(f"生成执行计划: {len(execution_plan)} 个阶段")
                for stage in execution_plan:
                    logger.info(f"  阶段 {stage['stage']} ({stage['type']}): {len(stage['tasks'])} 个任务")
                
                return Command(
                    update={
                        "execution_plan": execution_plan,
                        "current_stage": 0,
                        "stage_results": [],
                        "state": WorkflowState.EXECUTING
                    },
                    goto="execute_plan"
                )
                
            except ValueError as e:
                logger.error(f"计划解析错误: {e}")
                logger.debug(f"原始响应: {response.content}")
                return Command(
                    update={
                        "result": f"计划生成失败: {e}",
                        "state": WorkflowState.ERROR
                    },
                    goto=END
                )
        
        # 如果已有计划，直接进入执行
        return Command(
            update={
                "state": WorkflowState.EXECUTING
            },
            goto="execute_plan"
        )

    async def execute_plan_node(self, global_state: GlobalState) -> Command:
        """执行计划节点"""
        execution_plan = global_state.get("execution_plan", [])
        current_stage = global_state.get("current_stage", 0)
        stage_results = global_state.get("stage_results", [])
        
        # 检查是否所有阶段都已完成
        if current_stage >= len(execution_plan):
            logger.info("所有阶段执行完成")
            
            # 汇总结果
            total_tasks = sum(len(result["results"]) for result in stage_results)
            summary = f"执行完成，共 {len(execution_plan)} 个阶段，{total_tasks} 个任务"
            
            return Command(
                update={
                    "result": summary,
                    "state": WorkflowState.COMPLETED
                },
                goto="cleanup_run"
            )
        
        # 执行当前阶段
        current_stage_data = execution_plan[current_stage]
        logger.info(f"执行阶段 {current_stage + 1}/{len(execution_plan)}")
        
        try:
            stage_result = await self._execute_stage(global_state, current_stage_data)
            stage_results.append(stage_result)
            
            return Command(
                update={
                    "current_stage": current_stage + 1,
                    "stage_results": stage_results
                },
                goto="execute_plan"
            )
            
        except Exception as e:
            logger.error(f"阶段执行失败: {e}")
            return Command(
                update={
                    "result": f"阶段 {current_stage + 1} 执行失败: {e}",
                    "state": WorkflowState.ERROR
                },
                goto=END
            )
