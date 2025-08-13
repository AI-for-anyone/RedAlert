from .state import GlobalState


class ProductionNode():
    def __init__(self):
        pass

    def production_node(self, global_state: GlobalState) -> GlobalState:
        print("执行生产管理,当前GlobalState:", global_state)
        return global_state
