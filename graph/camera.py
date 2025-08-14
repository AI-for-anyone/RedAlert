from .state import GlobalState
from logs import get_logger

logger = get_logger("camera")
class CameraNode():
    def __init__(self):
        pass

    def camera_node(self, global_state: GlobalState) -> GlobalState:
        logger.info(f"执行地图视角控制,当前GlobalState: {global_state}")
        return global_state