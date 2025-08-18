import os
import json
import time
from typing import List, Dict, Any

from prompt import classify_prompt
from .state import GlobalState, WorkflowState, WorkflowType, NextCommand
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from langgraph.graph import END
from logs import get_logger

logger = get_logger("classify")

class ClassifyNode:
    def __init__(self):
        self._llm = None
        self._prompt = classify_prompt
        self._initialized = False
    
    async def initialize(self):
        """异步初始化分类节点"""
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
            logger.info("分类节点初始化完成")
        except Exception as e:
            logger.error(f"分类节点初始化失败: {e}")
            raise

    def _parse_classify_response(self, response_content: str) -> List[Dict[str, str]]:
        """解析分类响应的 JSON 格式"""
        try:
            # 尝试直接解析 JSON
            tasks = json.loads(response_content)
            
            # 验证格式
            if not isinstance(tasks, list):
                raise ValueError("响应不是数组格式")
            
            for task in tasks:
                if not isinstance(task, dict) or "assistant" not in task or "task" not in task:
                    raise ValueError("任务格式不正确，缺少 assistant 或 task 字段")
            
            return tasks
            
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试提取 JSON 部分
            try:
                # 查找 JSON 数组的开始和结束
                start = response_content.find('[')
                end = response_content.rfind(']') + 1
                
                if start != -1 and end != 0:
                    json_str = response_content[start:end]
                    tasks = json.loads(json_str)
                    
                    # 验证格式
                    for task in tasks:
                        if not isinstance(task, dict) or "assistant" not in task or "task" not in task:
                            raise ValueError("任务格式不正确")
                    
                    return tasks
                else:
                    raise ValueError("未找到有效的 JSON 数组")
                    
            except Exception as e:
                raise ValueError(f"解析分类响应失败: {e}")

    def classify_node(self, global_state: GlobalState) -> Command:
        global_state["classify_plan_cmds"] = global_state.get("classify_plan_cmds", [])
        logger.debug(f"global_state: {global_state}")
        if len(global_state["classify_plan_cmds"]) == 0:
            # 第一次进入分类规划
            global_state["classify_plan_index"] = 0
            
            """分类用户输入的任务"""
            messages = [
                {"role": "system", "content": self._prompt},
                {"role": "user", "content": global_state["input_cmd"]}
            ]

            # 记录 LLM 调用耗时
            start_time = time.time()
            response = self._llm.invoke(messages)
            end_time = time.time()
            
            elapsed_time = end_time - start_time
            logger.debug(f"LLM 分类耗时: {elapsed_time:.2f} 秒，response: {response}")
            
            # 解析 JSON 响应
            try:
                tasks = self._parse_classify_response(response.content)
                
                # 提取任务列表
                task_list = [NextCommand(assistant=task["assistant"], task=task["task"]) for task in tasks]
                global_state["classify_plan_cmds"] = task_list
                
                logger.debug(f"分类结果: {len(tasks)} 个任务")
                for i, task in enumerate(tasks):
                    logger.debug(f"  {i+1}. [{task['assistant']}] {task['task']}")
                
            except ValueError as e:
                logger.error(f"分类解析错误: {e}")
                logger.debug(f"原始响应: {response.content}")
                raise e

        global_state["classify_plan_index"] = global_state.get("classify_plan_index", 0)
        # 获取当前要执行的任务
        if global_state["classify_plan_index"] >= len(global_state["classify_plan_cmds"]):
            return Command(
                update={
                    "state": WorkflowState.COMPLETED
                },
                goto=END
            )
        next_task = global_state["classify_plan_cmds"][global_state["classify_plan_index"]].assistant
        logger.info(f"next_task: {next_task}")
        
        # 这里应该根据任务内容确定工作流类型
        # 简化处理，可以根据任务内容关键词判断
        workflow_type = self._determine_workflow_type(next_task)
        
        return Command(
            update={
                "classify_plan_index": global_state["classify_plan_index"] + 1,
                "classify_plan_cmds": global_state["classify_plan_cmds"],
                "state": WorkflowState.CLASSIFYING
            },
            goto=workflow_type
        )
    
    def _determine_workflow_type(self, task: str) -> WorkflowType:
        """根据任务内容确定工作流类型"""
        match task.lower():
            case "地图视角控制":
                return WorkflowType.CAMERA_CONTROL.value
            case "生产管理":
                return WorkflowType.PRODUCTION.value
            case "单位控制":
                return WorkflowType.UNIT_CONTROL.value
            case "信息查询":
                return WorkflowType.INTELLIGENCE.value
            case _:
                logger.error(f"无法识别的任务类型: {task}")
                return END
        
