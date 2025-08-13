from .state import GlobalState


class UnitControlNode():
    def __init__(self):
        pass

    def unit_control_node(self, global_state: GlobalState) -> GlobalState:
        print("执行单位控制,当前GlobalState:", global_state)
        return global_state
