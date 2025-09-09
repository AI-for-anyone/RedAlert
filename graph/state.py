from enum import Enum
from typing import TypedDict, Literal, List

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
    AI_ASSISTANT = "ai_assistant"   # AI 助手

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