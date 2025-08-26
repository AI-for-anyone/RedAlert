from enum import Enum
from typing import TypedDict, Literal, List, Optional, Dict, Any, Annotated
import operator

# from graph import classify

class WorkflowState(Enum):
    """工作流状态枚举"""
    INIT = "init"
    CLASSIFYING = "classifying"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ERROR = "error"

class WorkflowType(Enum):
    """工作流类型枚举"""
    CLASSIFY = "classify"           # 任务分类
    CAMERA_CONTROL = "camera"       # 地图视角控制
    PRODUCTION = "production"       # 生产管理
    UNIT_CONTROL = "unit_control"   # 单位控制
    INTELLIGENCE = "intelligence"   # 信息管理

# class InputState(TypedDict):
#     input_cmd: str

# class OutputState(TypedDict):
#     result: str

class NextCommand:
    def __init__(self, assistant: str, task: str):
        self.assistant = assistant
        self.task = task

class GlobalState(TypedDict):
    input_cmd: Annotated[str, lambda x, y: y if y else x]  # Take the latest non-empty value
    result: Annotated[str, lambda x, y: y if y else x]  # Take the latest non-empty value
    classify_plan_index: Annotated[int, lambda x, y: y if y is not None else x]  # Take the latest non-None value
    classify_plan_cmds: Annotated[List[NextCommand], lambda x, y: y if y else x]  # Take the latest non-empty list
    state: Annotated[Literal[WorkflowState.INIT, WorkflowState.CLASSIFYING, WorkflowState.EXECUTING, WorkflowState.COMPLETED, WorkflowState.ERROR], lambda x, y: y if y else x]
    cmd_type: Annotated[Literal[WorkflowType.CAMERA_CONTROL, WorkflowType.PRODUCTION, WorkflowType.UNIT_CONTROL, WorkflowType.INTELLIGENCE], lambda x, y: y if y else x]
    # 新增字段用于支持子任务和跨运行图交互
    run_id: Annotated[Optional[str], lambda x, y: y if y is not None else x]  # 运行ID，用于标识和隔离不同的图运行实例
    subtask_enabled: Annotated[Optional[bool], lambda x, y: y if y is not None else x]  # 是否启用子任务模式
    subtask_plan: Annotated[Optional[List[Dict[str, Any]]], lambda x, y: y if y is not None else x]  # 子任务执行计划
    subtask_results: Annotated[Optional[List[Dict[str, Any]]], lambda x, y: y if y is not None else x]  # 子任务执行结果
    blackboard_keys: Annotated[Optional[List[str]], lambda x, y: y if y is not None else x]  # 关联的黑板键列表，用于清理
    parent_run_id: Annotated[Optional[str], lambda x, y: y if y is not None else x]  # 父运行ID，用于嵌套子任务
    metadata: Annotated[Optional[Dict[str, Any]], lambda x, y: y if y is not None else x]  # 额外的元数据