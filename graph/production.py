from .state import GlobalState
from logs import get_logger

logger = get_logger("production")
class ProductionNode():
    def __init__(self):
        pass

    def production_node(self, global_state: GlobalState) -> GlobalState:
        logger.info(f"执行生产管理")
        return global_state
