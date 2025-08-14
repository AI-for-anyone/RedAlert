from .state import GlobalState
from logs import get_logger

logger = get_logger("intelligence")
class IntelligenceNode():
    def __init__(self):
        pass

    def intelligence_node(self, global_state: GlobalState) -> GlobalState:
        logger.info(f"执行信息管理,当前GlobalState: {global_state}")
        return global_state
