from .state import GlobalState
from logs import get_logger

logger = get_logger("unit_control")
class UnitControlNode():
    def __init__(self):
        pass

    def unit_control_node(self, global_state: GlobalState) -> GlobalState:
        logger.info(f"执行单位控制,当前GlobalState: {global_state}")
        return global_state
