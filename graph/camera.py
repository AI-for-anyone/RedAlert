from .state import GlobalState


class CameraNode():
    def __init__(self):
        pass

    def camera_node(self, global_state: GlobalState) -> GlobalState:
        print("执行地图视角控制,当前GlobalState:", global_state)
        return global_state