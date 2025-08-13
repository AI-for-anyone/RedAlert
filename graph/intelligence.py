from .state import GlobalState


class IntelligenceNode():
    def __init__(self):
        pass

    def intelligence_node(self, global_state: GlobalState) -> GlobalState:
        print("执行信息管理,当前GlobalState:", global_state)
        return global_state
