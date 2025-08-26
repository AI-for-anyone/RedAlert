from enum import Enum
from typing import TypedDict, Literal, List, Optional, Dict, Any

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
    input_cmd: str
    result: str
    classify_plan_index: int
    classify_plan_cmds: List[NextCommand]
    state: Literal[WorkflowState.INIT, WorkflowState.CLASSIFYING, WorkflowState.EXECUTING, WorkflowState.COMPLETED, WorkflowState.ERROR]
    cmd_type: Literal[WorkflowType.CAMERA_CONTROL, WorkflowType.PRODUCTION, WorkflowType.UNIT_CONTROL, WorkflowType.INTELLIGENCE]
    # 新增字段用于支持子任务和跨运行图交互
    run_id: Optional[str]  # 运行ID，用于标识和隔离不同的图运行实例
    subtask_enabled: Optional[bool]  # 是否启用子任务模式
    subtask_plan: Optional[List[Dict[str, Any]]]  # 子任务执行计划
    subtask_results: Optional[List[Dict[str, Any]]]  # 子任务执行结果
    blackboard_keys: Optional[List[str]]  # 关联的黑板键列表，用于清理
    parent_run_id: Optional[str]  # 父运行ID，用于嵌套子任务
    metadata: Optional[Dict[str, Any]]  # 额外的元数据