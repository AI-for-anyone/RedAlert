# GameAPI 接口文档

本文档整理了从 `move_camera_by_location` 开始的所有 GameAPI 接口，按功能分类组织。

## 目录
- [相机控制](#相机控制)
- [生产管理](#生产管理)
- [单位移动](#单位移动)
- [单位操作](#单位操作)
- [战斗相关](#战斗相关)
- [查询接口](#查询接口)
- [地图和视野](#地图和视野)
- [生产队列管理](#生产队列管理)
- [高级辅助功能](#高级辅助功能)

---

## 相机控制

### 1. move_camera_by_location
```python
def move_camera_by_location(self, location: Location) -> None
```
**功能**: 根据给定的位置移动相机
- **参数**: 
  - `location (Location)`: 要移动到的位置
- **异常**: `GameAPIError` - 当移动相机失败时

### 2. move_camera_by_direction
```python
def move_camera_by_direction(self, direction: str, distance: int) -> None
```
**功能**: 向某个方向移动相机
- **参数**: 
  - `direction (str)`: 移动的方向，必须在 {ALL_DIRECTIONS} 中
  - `distance (int)`: 移动的距离
- **异常**: `GameAPIError` - 当移动相机失败时

### 3. move_camera_to
```python
def move_camera_to(self, actor: Actor) -> None
```
**功能**: 将相机移动到指定Actor位置
- **参数**: 
  - `actor (Actor)`: 目标Actor
- **异常**: `GameAPIError` - 当移动相机失败时

---

## 生产管理

### 4. can_produce
```python
def can_produce(self, unit_type: str) -> bool
```
**功能**: 检查是否可以生产指定类型的Actor
- **参数**: 
  - `unit_type (str)`: Actor类型，必须在 {ALL_UNITS} 中
- **返回**: `bool` - 是否可以生产
- **异常**: `GameAPIError` - 当查询生产能力失败时

### 5. produce
```python
def produce(self, unit_type: str, quantity: int, auto_place_building: bool = False) -> Optional[int]
```
**功能**: 生产指定数量的Actor
- **参数**: 
  - `unit_type (str)`: Actor类型
  - `quantity (int)`: 生产数量
  - `auto_place_building (bool, optional)`: 是否在生产完成后使用随机位置自动放置建筑，仅对建筑类型有效
- **返回**: `int` - 生产任务的 waitId；`None` - 如果任务创建失败
- **异常**: `GameAPIError` - 当生产命令执行失败时

### 6. produce_wait
```python
def produce_wait(self, unit_type: str, quantity: int, auto_place_building: bool = True) -> None
```
**功能**: 生产指定数量的Actor并等待生产完成
- **参数**: 
  - `unit_type (str)`: Actor类型
  - `quantity (int)`: 生产数量
  - `auto_place_building (bool, optional)`: 是否在生产完成后使用随机位置自动放置建筑，仅对建筑类型有效
- **异常**: `GameAPIError` - 当生产或等待过程中发生错误时

### 7. is_ready
```python
def is_ready(self, wait_id: int) -> bool
```
**功能**: 检查生产任务是否完成
- **参数**: 
  - `wait_id (int)`: 生产任务的 ID
- **返回**: `bool` - 是否完成
- **异常**: `GameAPIError` - 当查询任务状态失败时

### 8. wait
```python
def wait(self, wait_id: int, max_wait_time: float = 20.0) -> bool
```
**功能**: 等待生产任务完成
- **参数**: 
  - `wait_id (int)`: 生产任务的 ID
  - `max_wait_time (float)`: 最大等待时间，默认为 20 秒
- **返回**: `bool` - 是否成功完成等待（false表示超时）
- **异常**: `GameAPIError` - 当等待过程中发生错误时

---

## 单位移动

### 9. move_units_by_location
```python
def move_units_by_location(self, actors: List[Actor], location: Location, attack_move: bool = False) -> None
```
**功能**: 移动单位到指定位置
- **参数**: 
  - `actors (List[Actor])`: 要移动的Actor列表
  - `location (Location)`: 目标位置
  - `attack_move (bool)`: 是否为攻击性移动
- **异常**: `GameAPIError` - 当移动命令执行失败时

### 10. move_units_by_direction
```python
def move_units_by_direction(self, actors: List[Actor], direction: str, distance: int) -> None
```
**功能**: 向指定方向移动单位
- **参数**: 
  - `actors (List[Actor])`: 要移动的Actor列表
  - `direction (str)`: 移动方向
  - `distance (int)`: 移动距离
- **异常**: `GameAPIError` - 当移动命令执行失败时

### 11. move_units_by_path
```python
def move_units_by_path(self, actors: List[Actor], path: List[Location]) -> None
```
**功能**: 沿路径移动单位
- **参数**: 
  - `actors (List[Actor])`: 要移动的Actor列表
  - `path (List[Location])`: 移动路径
- **异常**: `GameAPIError` - 当移动命令执行失败时

### 12. move_units_by_location_and_wait
```python
def move_units_by_location_and_wait(self, actors: List[Actor], location: Location, max_wait_time: float = 10.0, tolerance_dis: int = 1) -> bool
```
**功能**: 移动一批Actor到指定位置，并等待(或直到超时)
- **参数**: 
  - `actors (List[Actor])`: 要移动的Actor列表
  - `location (Location)`: 目标位置
  - `max_wait_time (float)`: 最大等待时间(秒)
  - `tolerance_dis (int)`: 容忍的距离误差，Actor：格子，Actor越多一般就得设得越大
- **返回**: `bool` - 是否在max_wait_time内到达(若中途卡住或超时则False)

---

## 单位操作

### 13. select_units
```python
def select_units(self, query_params: TargetsQueryParam) -> None
```
**功能**: 选中符合条件的Actor，指的是游戏中的选中操作
- **参数**: 
  - `query_params (TargetsQueryParam)`: 查询参数
- **异常**: `GameAPIError` - 当选择单位失败时

### 14. form_group
```python
def form_group(self, actors: List[Actor], group_id: int) -> None
```
**功能**: 将Actor编成编组
- **参数**: 
  - `actors (List[Actor])`: 要分组的Actor列表
  - `group_id (int)`: 群组 ID
- **异常**: `GameAPIError` - 当编组失败时

### 15. deploy_units
```python
def deploy_units(self, actors: List[Actor]) -> None
```
**功能**: 部署/展开 Actor
- **参数**: 
  - `actors (List[Actor])`: 要部署/展开的Actor列表
- **异常**: `GameAPIError` - 当部署单位失败时

### 16. occupy_units
```python
def occupy_units(self, occupiers: List[Actor], targets: List[Actor]) -> None
```
**功能**: 占领目标
- **参数**: 
  - `occupiers (List[Actor])`: 执行占领的Actor列表
  - `targets (List[Actor])`: 被占领的目标列表
- **异常**: `GameAPIError` - 当占领行动失败时

### 17. repair_units
```python
def repair_units(self, actors: List[Actor]) -> None
```
**功能**: 修复Actor
- **参数**: 
  - `actors (List[Actor])`: 要修复的Actor列表，可以是载具或者建筑，修理载具需要修建修理中心
- **异常**: `GameAPIError` - 当修复命令执行失败时

### 18. stop
```python
def stop(self, actors: List[Actor]) -> None
```
**功能**: 停止Actor当前行动
- **参数**: 
  - `actors (List[Actor])`: 要停止的Actor列表
- **异常**: `GameAPIError` - 当停止命令执行失败时

### 19. set_rally_point
```python
def set_rally_point(self, actors: list[Actor], target_location: Location) -> None
```
**功能**: 设置建筑的集结点
- **参数**: 
  - `actors (list[Actor])`: 要设置集结点的建筑列表
  - `target_location (Location)`: 集结点目标位置
- **异常**: `GameAPIError` - 当设置集结点失败时

---

## 战斗相关

### 20. attack_target
```python
def attack_target(self, attacker: Actor, target: Actor) -> bool
```
**功能**: 攻击指定目标
- **参数**: 
  - `attacker (Actor)`: 发起攻击的Actor
  - `target (Actor)`: 被攻击的目标
- **返回**: `bool` - 是否成功发起攻击(如果目标不可见，或者不可达，或者攻击者已经死亡，都会返回false)
- **异常**: `GameAPIError` - 当攻击命令执行失败时

### 21. can_attack_target
```python
def can_attack_target(self, attacker: Actor, target: Actor) -> bool
```
**功能**: 检查是否可以攻击目标
- **参数**: 
  - `attacker (Actor)`: 攻击者
  - `target (Actor)`: 目标
- **返回**: `bool` - 是否可以攻击
- **异常**: `GameAPIError` - 当检查攻击能力失败时

---

## 查询接口

### 22. query_actor
```python
def query_actor(self, query_params: TargetsQueryParam) -> List[Actor]
```
**功能**: 查询符合条件的Actor，获取Actor应该使用的接口
- **参数**: 
  - `query_params (TargetsQueryParam)`: 查询参数
- **返回**: `List[Actor]` - 符合条件的Actor列表
- **异常**: `GameAPIError` - 当查询Actor失败时

### 23. get_actor_by_id
```python
def get_actor_by_id(self, actor_id: int) -> Optional[Actor]
```
**功能**: 获取指定 ID 的Actor，这是根据ActorID获取Actor的接口，只有已知ActorID是才能调用这个接口
- **参数**: 
  - `actor_id (int)`: Actor ID
- **返回**: `Actor` - 对应的Actor；`None` - 如果Actor不存在
- **异常**: `GameAPIError` - 当获取Actor失败时

### 24. update_actor
```python
def update_actor(self, actor: Actor) -> bool
```
**功能**: 更新Actor信息，如果时间改变了，需要调用这个来更新Actor的各种属性（位置等）
- **参数**: 
  - `actor (Actor)`: 要更新的Actor
- **返回**: `bool` - 如果Actor已死，会返回false，否则返回true
- **异常**: `GameAPIError` - 当更新Actor信息失败时

### 25. find_path
```python
def find_path(self, actors: List[Actor], destination: Location, method: str) -> List[Location]
```
**功能**: 为Actor找到到目标的路径
- **参数**: 
  - `actors (List[Actor])`: 要移动的Actor列表
  - `destination (Location)`: 目标位置
  - `method (str)`: 寻路方法，必须在 {"最短路"，"左路"，"右路"} 中
- **返回**: `List[Location]` - 路径点列表，第0个是目标点，最后一个是Actor当前位置，相邻的点都是八方向相连的点
- **异常**: `GameAPIError` - 当寻路失败时

### 26. unit_attribute_query
```python
def unit_attribute_query(self, actors: List[Actor]) -> dict
```
**功能**: 查询Actor的属性和攻击范围内目标
- **参数**: 
  - `actors (List[Actor])`: 要查询的Actor列表
- **返回**: `dict` - Actor属性信息，包括攻击范围内的目标
- **异常**: `GameAPIError` - 当查询Actor属性失败时

### 27. unit_range_query (已弃用)
```python
def unit_range_query(self, actors: List[Actor]) -> List[int]
```
**功能**: 获取这些传入Actor攻击范围内的所有Target (已弃用，请使用unit_attribute_query)
- **参数**: 
  - `actors (List[Actor])`: 要查询的Actor列表
- **返回**: `List[int]` - 攻击范围内的目标ID列表

### 28. map_query
```python
def map_query(self) -> MapQueryResult
```
**功能**: 查询地图信息
- **返回**: `MapQueryResult` - 地图查询结果
- **异常**: `GameAPIError` - 当查询地图信息失败时

### 29. player_base_info_query
```python
def player_base_info_query(self) -> PlayerBaseInfo
```
**功能**: 查询玩家基地信息
- **返回**: `PlayerBaseInfo` - 玩家基地信息
- **异常**: `GameAPIError` - 当查询玩家基地信息失败时

### 30. screen_info_query
```python
def screen_info_query(self) -> ScreenInfoResult
```
**功能**: 查询当前玩家看到的屏幕信息
- **返回**: `ScreenInfoResult` - 屏幕信息查询结果
- **异常**: `GameAPIError` - 当查询屏幕信息失败时

---

## 地图和视野

### 31. visible_query
```python
def visible_query(self, location: Location) -> bool
```
**功能**: 查询位置是否可见
- **参数**: 
  - `location (Location)`: 要查询的位置
- **返回**: `bool` - 是否可见
- **异常**: `GameAPIError` - 当查询可见性失败时

### 32. explorer_query
```python
def explorer_query(self, location: Location) -> bool
```
**功能**: 查询位置是否已探索
- **参数**: 
  - `location (Location)`: 要查询的位置
- **返回**: `bool` - 是否已探索
- **异常**: `GameAPIError` - 当查询探索状态失败时

---

## 生产队列管理

### 33. query_production_queue
```python
def query_production_queue(self, queue_type: str) -> dict
```
**功能**: 查询指定类型的生产队列
- **参数**: 
  - `queue_type (str)`: 队列类型，必须是以下值之一：
    - 'Building' - 建筑
    - 'Defense' - 防御
    - 'Infantry' - 士兵
    - 'Vehicle' - 载具
    - 'Aircraft' - 飞机
    - 'Naval' - 海军
- **返回**: `dict` - 包含队列信息的字典，格式详见源码注释
- **异常**: `GameAPIError` - 当查询生产队列失败时

### 34. place_building
```python
def place_building(self, queue_type: str, location: Location = None) -> None
```
**功能**: 放置建造队列顶端已就绪的建筑
- **参数**: 
  - `queue_type (str)`: 队列类型，可选值：'Building', 'Defense', 'Infantry', 'Vehicle', 'Aircraft', 'Naval'
  - `location (Location, optional)`: 放置建筑的位置，如果不指定则使用自动选择的位置
- **异常**: `GameAPIError` - 当放置建筑失败时

### 35. manage_production
```python
def manage_production(self, queue_type: str, action: str) -> None
```
**功能**: 管理生产队列中的项目（暂停/取消/继续）
- **参数**: 
  - `queue_type (str)`: 队列类型，可选值：'Building', 'Defense', 'Infantry', 'Vehicle', 'Aircraft', 'Naval'
  - `action (str)`: 操作类型，必须是 'pause', 'cancel', 或 'resume'
- **异常**: `GameAPIError` - 当管理生产队列失败时

---

## 高级辅助功能

### 36. deploy_mcv_and_wait
```python
def deploy_mcv_and_wait(self, wait_time: float = 1.0) -> None
```
**功能**: 展开自己的基地车并等待一小会
- **参数**: 
  - `wait_time (float)`: 展开后的等待时间(秒)，默认为1秒，已经够了，一般不用改

### 37. ensure_can_build_wait
```python
def ensure_can_build_wait(self, building_name: str) -> bool
```
**功能**: 确保能生产某个建筑，如果不能会尝试生产所有前置建筑，并等待生产完成
- **参数**: 
  - `building_name (str)`: 建筑名称(中文)
- **返回**: `bool` - 是否已经拥有该建筑或成功生产

### 38. ensure_can_produce_unit
```python
def ensure_can_produce_unit(self, unit_name: str) -> bool
```
**功能**: 确保能生产某个Actor(会自动生产其所需建筑并等待完成)
- **参数**: 
  - `unit_name (str)`: Actor名称(中文)
- **返回**: `bool` - 是否成功准备好生产该Actor

### 39. get_unexplored_nearby_positions
```python
def get_unexplored_nearby_positions(self, map_query_result: MapQueryResult, current_pos: Location, max_distance: int) -> List[Location]
```
**功能**: 获取当前位置附近尚未探索的坐标列表
- **参数**: 
  - `map_query_result (MapQueryResult)`: 地图信息
  - `current_pos (Location)`: 当前Actor的位置
  - `max_distance (int)`: 距离范围(曼哈顿)
- **返回**: `List[Location]` - 未探索位置列表

---

## 依赖关系表

### 建筑依赖关系
```python
BUILDING_DEPENDENCIES = {
    "电厂": [],
    "兵营": ["电厂"],
    "矿场": ["电厂"],
    "车间": ["矿场"],
    "雷达": ["矿场"],
    "维修中心": ["车间"],
    "核电": ["雷达"],
    "科技中心": ["车间", "雷达"],
    "机场": ["雷达"]
}
```

### 单位依赖关系
```python
UNIT_DEPENDENCIES = {
    "步兵": ["兵营"],
    "火箭兵": ["兵营"],
    "工程师": ["兵营"],
    "手雷兵": ["兵营"],
    "矿车": ["车间"],
    "防空车": ["车间"],
    "装甲车": ["车间"],
    "重坦": ["车间", "维修中心"],
    "v2": ["车间", "雷达"],
    "猛犸坦克": ["车间", "维修中心", "科技中心"]
}
```

---

## 总结

本文档共整理了 **39个接口**，涵盖了游戏的各个方面：

- **相机控制**: 3个接口
- **生产管理**: 5个接口
- **单位移动**: 4个接口
- **单位操作**: 7个接口
- **战斗相关**: 2个接口
- **查询接口**: 9个接口
- **地图和视野**: 2个接口
- **生产队列管理**: 3个接口
- **高级辅助功能**: 4个接口

所有接口都提供了完整的参数说明、返回值说明和异常处理信息，便于开发者使用。
