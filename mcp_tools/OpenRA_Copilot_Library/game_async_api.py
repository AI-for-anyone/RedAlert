import asyncio
import json
import uuid
from typing import List, Optional, Tuple, Dict, Any

from .models import *

# API版本常量
API_VERSION = "1.0"

class AsyncGameAPIError(Exception):
    """游戏API异常基类"""
    def __init__(self, code: str, message: str, details: Dict = None):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(f"{code}: {message}")

class AsyncGameAPI:
    '''游戏API接口类，用于与游戏服务器进行通信
    提供了一系列方法来与游戏服务器进行交互，包括Actor移动、生产、查询等功能。
    所有的通信都是通过socket连接完成的。'''

    MAX_RETRIES = 3
    RETRY_DELAY = 0.5

    @staticmethod
    async def is_server_running(host="localhost", port=7445, timeout=2.0) -> bool:
        '''检查游戏服务器是否已启动并可访问

        Args:
            host (str): 游戏服务器地址，默认为"localhost"。
            port (int): 游戏服务器端口，默认为 7445。
            timeout (float): 连接超时时间（秒），默认为 2.0 秒。

        Returns:
            bool: 服务器是否已启动并可访问
        '''
        try:
            request_data = {
                "apiVersion": API_VERSION,
                "requestId": str(uuid.uuid4()),
                "command": "ping",
                "params": {},
                "language": "zh"
            }

            # 使用asyncio创建异步连接
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )

            try:
                # 发送请求
                json_data = json.dumps(request_data)
                writer.write(json_data.encode('utf-8'))
                await writer.drain()

                # 接收响应
                chunks = []
                try:
                    while True:
                        chunk = await asyncio.wait_for(reader.read(4096), timeout=timeout)
                        if not chunk:
                            break
                        chunks.append(chunk)
                except asyncio.TimeoutError:
                    if not chunks:
                        return False

                data = b''.join(chunks).decode('utf-8')

                try:
                    response = json.loads(data)
                    if response.get("status", 0) > 0 and "data" in response:
                        return True
                    return False
                except json.JSONDecodeError:
                    return False

            finally:
                writer.close()
                await writer.wait_closed()

        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return False

        except Exception:
            return False

    def __init__(self, host, port=7445, language="zh"):
        self.server_address = (host, port)
        self.language = language
        '''初始化 GameAPI 类

        Args:
            host (str): 游戏服务器地址，本地就填"localhost"。
            port (int): 游戏服务器端口，默认为 7445。
            language (str): 接口返回语言，默认为 "zh"，支持 "zh" 和 "en"。
        '''

    def _generate_request_id(self) -> str:
        """生成唯一的请求ID"""
        return str(uuid.uuid4())

    async def _send_request(self, command: str, params: dict) -> dict:
        '''通过异步socket和Game交互，发送信息并接收响应

        Args:
            command (str): 要执行的命令
            params (dict): 命令相关的数据参数

        Returns:
            dict: 服务器返回的JSON响应数据

        Raises:
            AsyncGameAPIError: 当API调用出现错误时
            ConnectionError: 当连接服务器失败时
        '''
        request_id = self._generate_request_id()
        request_data = {
            "apiVersion": API_VERSION,
            "requestId": request_id,
            "command": command,
            "params": params,
            "language": self.language
        }

        retries = 0
        while retries < self.MAX_RETRIES:
            try:
                # 使用asyncio创建异步连接
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.server_address[0], self.server_address[1]),
                    timeout=10.0
                )

                try:
                    # 发送请求
                    json_data = json.dumps(request_data)
                    writer.write(json_data.encode('utf-8'))
                    await writer.drain()

                    # 接收响应
                    response_data = await self._receive_data_async(reader)

                    try:
                        response = json.loads(response_data)

                        # 验证响应格式
                        if not isinstance(response, dict):
                            raise AsyncGameAPIError("INVALID_RESPONSE",
                                             "服务器返回的响应格式无效")

                        # 检查请求ID匹配
                        if response.get("requestId") != request_id:
                            raise AsyncGameAPIError("REQUEST_ID_MISMATCH",
                                             "响应的请求ID不匹配")

                        # 处理错误响应
                        if response.get("status", 0) < 0:
                            error = response.get("error", {})
                            raise AsyncGameAPIError(
                                error.get("code", "UNKNOWN_ERROR"),
                                error.get("message", "未知错误"),
                                error.get("details")
                            )

                        return response

                    except json.JSONDecodeError:
                        raise AsyncGameAPIError("INVALID_JSON",
                                         "服务器返回的不是有效的JSON格式")

                finally:
                    # 确保连接被正确关闭
                    writer.close()
                    await writer.wait_closed()

            except asyncio.TimeoutError:
                retries += 1
                if retries >= self.MAX_RETRIES:
                    raise AsyncGameAPIError("CONNECTION_TIMEOUT",
                                     "连接服务器超时")
                await asyncio.sleep(self.RETRY_DELAY)

            except (ConnectionError, OSError) as e:
                retries += 1
                if retries >= self.MAX_RETRIES:
                    raise AsyncGameAPIError("CONNECTION_ERROR",
                                     "连接服务器失败: {0}".format(str(e)))
                await asyncio.sleep(self.RETRY_DELAY)

            except AsyncGameAPIError:
                raise

            except Exception as e:
                raise AsyncGameAPIError("UNEXPECTED_ERROR",
                                 "发生未预期的错误: {0}".format(str(e)))

    async def _receive_data_async(self, reader: asyncio.StreamReader) -> str:
        """从异步socket接收完整的响应数据"""
        chunks = []
        try:
            while True:
                # 使用asyncio.wait_for添加超时控制
                chunk = await asyncio.wait_for(reader.read(4096), timeout=10.0)
                if not chunk:
                    break
                chunks.append(chunk)
        except asyncio.TimeoutError:
            if not chunks:
                raise AsyncGameAPIError("TIMEOUT",
                                 "接收响应超时")
        return b''.join(chunks).decode('utf-8')

    def _handle_response(self, response: dict, error_msg: str) -> Any:
        """处理API响应，提取所需数据或抛出异常"""
        if response is None:
            raise AsyncGameAPIError("NO_RESPONSE",
                             "{0}".format(error_msg))
        return response.get("data") if "data" in response else response

    async def move_units_by_location(self, target: NewTargetsQueryParam, location: Location, attack_move: bool = False) -> None:
        '''移动单位到指定位置

        Args:
            target (NewTargetsQueryParam): 要移动的Actor列表
            location (Location): 目标位置
            attack_move (bool): 是否为攻击性移动

        Raises:
            AsyncGameAPIError: 当移动命令执行失败时
        '''
        try:
            response = await self._send_request('move_actor', {
                "targets": target.to_dict(),
                "location": location.to_dict(),
                "isAttackMove": 1 if attack_move else 0
            })
            self._handle_response(response, "移动单位失败")
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("MOVE_UNITS_ERROR", "移动单位时发生错误: {0}".format(str(e)))

    async def query_actor(self, query_params: NewTargetsQueryParam) -> List[Actor]:
        '''查询符合条件的Actor，获取Actor应该使用的接口

        Args:
            query_params (TargetsQueryParam): 查询参数

        Returns:
            List[Actor]: 符合条件的Actor列表

        Raises:
            AsyncGameAPIError: 当查询Actor失败时
        '''
        try:
            response = await self._send_request('query_actor', {
                "targets": query_params.to_dict()
            })
            result = self._handle_response(response, "查询Actor失败")

            actors = []
            actors_data = result.get("actors", [])

            for data in actors_data:
                try:

                    actor = Actor(data["id"])
                    position = Location(
                        data["position"]["x"],
                        data["position"]["y"]
                    )
                    hp_percent = data["hp"] * 100 // data["maxHp"] if data.get("maxHp", 0) > 0 else -1
                    actor.update_details(
                        data["type"],
                        data["faction"],
                        position,
                        hp_percent
                    )
                    actor.max_hp = data.get("maxHp", 0)
                    actor.hp = data.get("hp", 0)
                    actors.append(actor)
                except KeyError as e:
                    raise AsyncGameAPIError("INVALID_ACTOR_DATA", "Actor数据格式无效: {0}".format(str(e)))

            return actors

        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("QUERY_ACTOR_ERROR", "查询Actor时发生错误: {0}".format(str(e)))

    async def attack_target(self, attacker: NewTargetsQueryParam, target: NewTargetsQueryParam) -> bool:
        '''攻击指定目标

        Args:
            attacker (Actor): 发起攻击的Actor
            target (Actor): 被攻击的目标

        Returns:
            bool: 是否成功发起攻击(如果目标不可见，或者不可达，或者攻击者已经死亡，都会返回false)

        Raises:
            AsyncGameAPIError: 当攻击命令执行失败时
        '''
        try:
            response = await self._send_request('attack', {
                "attackers": attacker.to_dict(),
                "targets": target.to_dict()
            })
            result = self._handle_response(response, "攻击命令执行失败")
            if result is None:
                return True
            return result.get("status", 0) > 0
        except AsyncGameAPIError as e:
            if e.code == "COMMAND_EXECUTION_ERROR":
                return False
            raise
        except Exception as e:
            raise AsyncGameAPIError("ATTACK_ERROR", "攻击命令执行时发生错误: {0}".format(str(e)))

    async def unit_attribute_query(self, target: NewTargetsQueryParam) -> dict:
        '''查询Actor的属性和攻击范围内目标

        Args:
            target (NewTargetsQueryParam): 要查询的Actor列表

        Returns:
            dict: Actor属性信息，包括攻击范围内的目标

        Raises:
            AsyncGameAPIError: 当查询Actor属性失败时
        '''
        try:
            response = await self._send_request('unit_attribute_query', {
                "targets": target.to_dict()
            })
            res = self._handle_response(response, "查询Actor属性失败")
            if res is None :
                raise AsyncGameAPIError("ATTRIBUTE_QUERY_ERROR", "查询Actor属性失败")
            return res.get("attributes", [])
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("ATTRIBUTE_QUERY_ERROR", "查询Actor属性时发生错误: {0}".format(str(e)))
    async def map_query(self) -> MapQueryResult:
        '''查询地图信息

        Returns:
            MapQueryResult: 地图查询结果

        Raises:
            AsyncGameAPIError: 当查询地图信息失败时
        '''
        try:
            response = await self._send_request('map_query', {})
            result = self._handle_response(response, "查询地图信息失败")

            return MapQueryResult(
                MapWidth=result.get('MapWidth', 0),
                MapHeight=result.get('MapHeight', 0),
                Height=result.get('Height', [[]]),
                IsVisible=result.get('IsVisible', [[]]),
                IsExplored=result.get('IsExplored', [[]]),
                Terrain=result.get('Terrain', [[]]),
                ResourcesType=result.get('ResourcesType', [[]]),
                Resources=result.get('Resources', [[]])
            )
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("MAP_QUERY_ERROR", "查询地图信息时发生错误: {0}".format(str(e)))

    async def move_camera_by_location(self, location: Location) -> None:
        '''根据给定的位置移动相机'''
        try:
            response = await self._send_request('camera_move', {"location": location.to_dict()})
            self._handle_response(response, "移动相机失败")
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("CAMERA_MOVE_ERROR", "移动相机时发生错误: {0}".format(str(e)))

    async def move_camera_by_direction(self, direction: str, distance: int) -> None:
        '''向某个方向移动相机'''
        try:
            response = await self._send_request('camera_move', {
                "direction": direction,
                "distance": distance
            })
            self._handle_response(response, "移动相机失败")
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("CAMERA_MOVE_ERROR", "移动相机时发生错误: {0}".format(str(e)))

        '''检查是否可以生产指定类型的Actor'''
    async def can_produce(self, unit_type: str) -> bool:
        try:
            response = await self._send_request('query_can_produce', {
                "units": [{"unit_type": unit_type}]
            })
            result = self._handle_response(response, "查询生产能力失败")
            return result.get("canProduce", False)
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("PRODUCE_QUERY_ERROR", "查询生产能力时发生错误: {0}".format(str(e)))

    async def produce(self, unit_type: str, quantity: int, auto_place_building: bool = True) -> Optional[int]:
        '''生产指定数量的Actor，返回waitId'''
        try:
            response = await self._send_request('start_production', {
                "units": [{"unit_type": unit_type, "quantity": quantity}],
                "autoPlaceBuilding": auto_place_building
            })
            result = self._handle_response(response, "生产命令执行失败")
            return result.get("waitId")
        except AsyncGameAPIError as e:
            if e.code == "COMMAND_EXECUTION_ERROR":
                return None
            raise
        except Exception as e:
            raise AsyncGameAPIError("PRODUCTION_ERROR", "执行生产命令时发生错误: {0}".format(str(e)))

    async def produce_wait(self, unit_type: str, quantity: int, auto_place_building: bool = True) -> None:
        '''生产并等待完成'''
        try:
            wait_id = await self.produce(unit_type, quantity, auto_place_building)
            if wait_id is not None:
                await self.wait(wait_id, 20 * quantity)
            else:
                raise AsyncGameAPIError("PRODUCTION_FAILED", "生产任务创建失败")
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("PRODUCTION_WAIT_ERROR", "生产并等待过程中发生错误: {0}".format(str(e)))

    async def is_ready(self, wait_id: int) -> bool:
        '''检查生产任务是否完成'''
        try:
            response = await self._send_request('query_wait_info', {"waitId": wait_id})
            result = self._handle_response(response, "查询任务状态失败")
            return result.get("status", False)
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("WAIT_STATUS_ERROR", "查询任务状态时发生错误: {0}".format(str(e)))

    async def wait(self, wait_id: int, max_wait_time: float = 20.0) -> bool:
        '''等待生产任务完成，超时返回False'''
        try:
            wait_time = 0.0
            step_time = 0.1
            while True:
                response = await self._send_request('query_wait_info', {"waitId": wait_id})
                result = self._handle_response(response, "等待任务完成失败")

                if result.get("waitStatus") == "success":
                    return True

                await asyncio.sleep(step_time)
                wait_time += step_time
                if wait_time > max_wait_time:
                    return False

        except AsyncGameAPIError as e:
            if e.code == "COMMAND_EXECUTION_ERROR":
                return True
            raise
        except Exception as e:
            raise AsyncGameAPIError("WAIT_ERROR", "等待任务完成时发生错误: {0}".format(str(e)))

    async def move_units_by_direction(self, actors: List[Actor], direction: str, distance: int) -> None:
        '''向指定方向移动单位'''
        try:
            response = await self._send_request('move_actor', {
                "targets": {"actorId": [actor.actor_id for actor in actors]},
                "direction": direction,
                "distance": distance
            })
            self._handle_response(response, "移动单位失败")
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("MOVE_UNITS_ERROR", "移动单位时发生错误: {0}".format(str(e)))

    async def move_units_by_path(self, actors: List[Actor], path: List[Location]) -> None:
        '''沿路径移动单位'''
        if not path:
            return
        try:
            response = await self._send_request('move_actor', {
                "targets": {"actorId": [actor.actor_id for actor in actors]},
                "path": [point.to_dict() for point in path]
            })
            self._handle_response(response, "移动单位失败")
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("MOVE_UNITS_ERROR", "移动单位时发生错误: {0}".format(str(e)))

    async def select_units(self, query_params: TargetsQueryParam) -> None:
        '''选中符合条件的Actor（游戏中选中操作）'''
        try:
            response = await self._send_request('select_unit', {
                "targets": query_params.to_dict()
            })
            self._handle_response(response, "选择单位失败")
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("SELECT_UNITS_ERROR", "选择单位时发生错误: {0}".format(str(e)))

    async def form_group(self, actors: List[Actor], group_id: int) -> None:
        '''将Actor编成编组'''
        try:
            response = await self._send_request('form_group', {
                "targets": {"actorId": [actor.actor_id for actor in actors]},
                "groupId": group_id
            })
            self._handle_response(response, "编组失败")
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("FORM_GROUP_ERROR", "编组时发生错误: {0}".format(str(e)))

    async def find_path(self, actors: List[Actor], destination: Location, method: str) -> List[Location]:
        '''为Actor找到到目标的路径'''
        try:
            response = await self._send_request('query_path', {
                "targets": {"actorId": [actor.actor_id for actor in actors]},
                "destination": destination.to_dict(),
                "method": method
            })
            result = self._handle_response(response, "寻路失败")

            try:
                return [Location(step["x"], step["y"]) for step in result["path"]]
            except (KeyError, TypeError) as e:
                raise AsyncGameAPIError("INVALID_PATH_DATA", "路径数据格式无效: {0}".format(str(e)))
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("FIND_PATH_ERROR", "寻路时发生错误: {0}".format(str(e)))

    async def get_actor_by_id(self, actor_id: int) -> Optional[Actor]:
        '''获取指定 ID 的Actor'''
        actor = Actor(actor_id)
        try:
            if await self.update_actor(actor):
                return actor
            return None
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("GET_ACTOR_ERROR", "获取Actor时发生错误: {0}".format(str(e)))

    async def update_actor(self, actor: Actor) -> bool:
        '''更新Actor信息'''
        try:
            response = await self._send_request('query_actor', {
                "targets": {"actorId": [actor.actor_id]}
            })
            result = self._handle_response(response, "更新Actor信息失败")

            try:
                actor_data = result["actors"][0]
                position = Location(
                    actor_data["position"]["x"],
                    actor_data["position"]["y"]
                )
                hp_percent = actor_data["hp"] * 100 // actor_data["maxHp"] if actor_data.get("maxHp", 0) > 0 else -1
                actor.update_details(
                    actor_data["type"],
                    actor_data["faction"],
                    position,
                    hp_percent
                )
                return True
            except (IndexError, KeyError):
                return False
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("UPDATE_ACTOR_ERROR", "更新Actor信息时发生错误: {0}".format(str(e)))

    async def deploy_units(self, actors: List[Actor]) -> None:
        '''部署/展开 Actor'''
        try:
            response = await self._send_request('deploy', {
                "targets": {"actorId": [actor.actor_id for actor in actors]}
            })
            self._handle_response(response, "部署单位失败")
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("DEPLOY_UNITS_ERROR", "部署单位时发生错误: {0}".format(str(e)))

    async def move_camera_to(self, actor: Actor) -> None:
        '''将相机移动到指定Actor位置'''
        try:
            response = await self._send_request('view', {"actorId": actor.actor_id})
            self._handle_response(response, "移动相机失败")
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("CAMERA_MOVE_ERROR", "移动相机时发生错误: {0}".format(str(e)))

    async def occupy_units(self, occupiers: List[Actor], targets: List[Actor]) -> None:
        '''占领目标'''
        try:
            response = await self._send_request('occupy', {
                "occupiers": {"actorId": [actor.actor_id for actor in occupiers]},
                "targets": {"actorId": [target.actor_id for target in targets]}
            })
            self._handle_response(response, "占领行动失败")
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("OCCUPY_ERROR", "占领行动时发生错误: {0}".format(str(e)))

    async def can_attack_target(self, attacker: Actor, target: Actor) -> bool:
        '''检查是否可以攻击目标'''
        try:
            response = await self._send_request('query_actor', {
                "targets": {
                    "actorId": [target.actor_id],
                    "restrain": [{"visible": True}]
                }
            })
            result = self._handle_response(response, "检查攻击能力失败")
            return len(result.get("actors", [])) > 0
        except AsyncGameAPIError:
            return False
        except Exception as e:
            raise AsyncGameAPIError("CHECK_ATTACK_ERROR", "检查攻击能力时发生错误: {0}".format(str(e)))

    async def repair_units(self, actors: List[Actor]) -> None:
        '''修复Actor'''
        try:
            response = await self._send_request('repair', {
                "targets": {"actorId": [actor.actor_id for actor in actors]}
            })
            self._handle_response(response, "修复命令执行失败")
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("REPAIR_ERROR", "修复命令执行时发生错误: {0}".format(str(e)))

    async def stop(self, actors: List[Actor]) -> None:
        '''停止Actor当前行动'''
        try:
            response = await self._send_request('stop', {
                "targets": {"actorId": [actor.actor_id for actor in actors]}
            })
            self._handle_response(response, "停止命令执行失败")
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("STOP_ERROR", "停止命令执行时发生错误: {0}".format(str(e)))

    async def visible_query(self, location: Location) -> bool:
        '''查询位置是否可见'''
        try:
            response = await self._send_request('fog_query', {
                "pos": location.to_dict()
            })
            result = self._handle_response(response, "查询可见性失败")
            return result.get('IsVisible', False)
        except AsyncGameAPIError:
            return False
        except Exception as e:
            raise AsyncGameAPIError("VISIBILITY_QUERY_ERROR", "查询可见性时发生错误: {0}".format(str(e)))

    async def explorer_query(self, location: Location) -> bool:
        '''查询位置是否已探索'''
        try:
            response = await self._send_request('fog_query', {
                "pos": location.to_dict()
            })
            result = self._handle_response(response, "查询探索状态失败")
            return result.get('IsExplored', False)
        except AsyncGameAPIError:
            return False
        except Exception as e:
            raise AsyncGameAPIError("EXPLORER_QUERY_ERROR", "查询探索状态时发生错误: {0}".format(str(e)))

    async def query_production_queue(self, queue_type: str) -> dict:
        '''查询指定类型的生产队列'''
        if queue_type not in ['Building', 'Defense', 'Infantry', 'Vehicle', 'Aircraft', 'Naval']:
            raise AsyncGameAPIError(
                "INVALID_QUEUE_TYPE",
                "队列类型必须是以下值之一: 'Building', 'Defense', 'Infantry', 'Vehicle', 'Aircraft', 'Naval'")
        try:
            response = await self._send_request('query_production_queue', {
                "queueType": queue_type
            })
            return self._handle_response(response, "查询生产队列失败")
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("PRODUCTION_QUEUE_QUERY_ERROR", "查询生产队列时发生错误: {0}".format(str(e)))

    async def place_building(self, queue_type: str, location: Optional[Location] = None) -> None:
        '''放置建造队列顶端已就绪的建筑'''
        try:
            params: Dict[str, Any] = {
                "queueType": queue_type
            }
            if location:
                params["location"] = location.to_dict()
            response = await self._send_request('place_building', params)
            self._handle_response(response, "放置建筑失败")
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("PLACE_BUILDING_ERROR", "放置建筑时发生错误: {0}".format(str(e)))

    async def manage_production(self, queue_type: str, action: str) -> None:
        '''管理生产队列中的项目（暂停/取消/继续）'''
        if action not in ['pause', 'cancel', 'resume']:
            raise AsyncGameAPIError("INVALID_ACTION", "action参数必须是 'pause', 'cancel', 或 'resume'")
        try:
            params = {
                "queueType": queue_type,
                "action": action
            }
            response = await self._send_request('manage_production', params)
            self._handle_response(response, "管理生产队列失败")
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("MANAGE_PRODUCTION_ERROR", "管理生产队列时发生错误: {0}".format(str(e)))

    # ===== 依赖关系表 =====
    BUILDING_DEPENDENCIES = {
        "发电厂": [],
        "兵营": ["发电厂"],
        "矿场": ["发电厂"],
        "战车工厂": ["矿场"],
        "雷达站": ["矿场"],
        "维修厂": ["战车工厂"],
        "核电站": ["雷达站"],
        "科技中心": ["战车工厂", "雷达站"],
        "空军基地": ["雷达站"],
        "火焰塔": ["兵营"],
        "特斯拉塔": ["兵营", "战车工厂"],
        "防空塔": ["兵营", "雷达站"],
    }

    UNIT_DEPENDENCIES = {
        "步兵": ["兵营"],
        "火箭兵": ["兵营"],
        # "工程师": ["兵营"],
        # "手雷兵": ["兵营"],
        "采矿车": ["战车工厂"],
        "防空车": ["战车工厂"],
        # "装甲车": ["战车工厂"],
        "重型坦克": ["战车工厂", "维修厂"],
        "V2火箭发射车": ["战车工厂", "雷达站"],
        "超重型坦克": ["战车工厂", "维修厂", "科技中心"]
    }

    async def deploy_mcv_and_wait(self, wait_time: float = 1.0) -> None:
        '''展开自己的基地车并等待一小会'''
        mcv = await self.query_actor(NewTargetsQueryParam(type=['mcv'], faction='自己'))
        if not mcv:
            return
        await self.deploy_units(mcv)
        await asyncio.sleep(wait_time)

    async def ensure_can_build(self, building_name: str) -> bool:
        '''确保能生产某个建筑，如果不能会尝试生产所有前置建筑，并等待生产完成'''
        building_exists = await self.query_actor(TargetsQueryParam(type=[building_name], faction="自己"))
        if building_exists:
            return True
        deps = self.BUILDING_DEPENDENCIES.get(building_name, [])
        for dep in deps:
            if not await self.ensure_building_wait_buildself(dep):
                return False
        return True

    async def ensure_can_build_wait(self, building_name: str) -> bool:
        '''确保能生产某个建筑，如果不能会尝试生产所有前置建筑，并等待生产完成'''
        building_exists = await self.query_actor(TargetsQueryParam(type=[building_name], faction="自己"))
        if building_exists:
            return True
        deps = self.BUILDING_DEPENDENCIES.get(building_name, [])
        for dep in deps:
            if not await self.ensure_building_wait_buildself(dep):
                return False
        return await self.ensure_building_wait_buildself(building_name)

    async def ensure_building_wait_buildself(self, building_name: str) -> bool:
        '''非外部接口'''
        building_exists = await self.query_actor(TargetsQueryParam(type=[building_name], faction="自己"))
        if building_exists:
            return True
        deps = self.BUILDING_DEPENDENCIES.get(building_name, [])
        for dep in deps:
            await self.ensure_building_wait_buildself(dep)
        if await self.can_produce(building_name):
            wait_id = await self.produce(building_name, 1, True)
            if wait_id:
                await self.wait(wait_id)
                return True
        return False

    async def ensure_can_produce_unit(self, unit_name: str) -> bool:
        '''确保能生产某个Actor(会自动生产其所需建筑并等待完成)
        Args:
            unit_name (str): Actor名称(中文)
        Returns:
            bool: 是否成功准备好生产该Actor
        '''
        if await self.can_produce(unit_name):
            return True
        needed_buildings = self.UNIT_DEPENDENCIES.get(unit_name, [])
        for b in needed_buildings:
            await self.ensure_building_wait_buildself(b)
        if not await self.can_produce(unit_name):
            await asyncio.sleep(1)
        return await self.can_produce(unit_name)

    def get_unexplored_nearby_positions(self, map_query_result: MapQueryResult, current_pos: Location, max_distance: int) -> List[Location]:
        '''获取当前位置附近尚未探索的坐标列表'''
        neighbors: List[Location] = []
        for dx in range(-max_distance, max_distance + 1):
            for dy in range(-max_distance, max_distance + 1):
                if abs(dx) + abs(dy) > max_distance:
                    continue
                if dx == 0 and dy == 0:
                    continue
                x = current_pos.x + dx
                y = current_pos.y + dy
                if 0 <= x < map_query_result.MapWidth and 0 <= y < map_query_result.MapHeight:
                    if not map_query_result.IsExplored[x][y]:
                        neighbors.append(Location(x, y))
        return neighbors

    async def move_units_by_location_and_wait(self, actors: List[Actor], location: Location, max_wait_time: float = 10.0, tolerance_dis: int = 1) -> bool:
        '''移动一批Actor到指定位置，并等待(或直到超时)'''
        await self.move_units_by_location(actors, location)
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < max_wait_time:
            all_arrived = True
            for actor in actors:
                await self.update_actor(actor)
                if actor.position is None or actor.position.manhattan_distance(location) > tolerance_dis:
                    all_arrived = False
                    break
            if all_arrived:
                return True
            await asyncio.sleep(0.3)
        return False

    # 兼容旧方法：返回攻击范围内的所有Target ID
    async def unit_range_query(self, actors: List[Actor]) -> List[int]:
        '''获取这些传入Actor攻击范围内的所有Target (已弃用，请使用unit_attribute_query)'''
        try:
            result = await self.unit_attribute_query(actors)
            targets: List[int] = []
            for attr in result.get("attributes", []):
                targets.extend(attr.get("targets", []))
            return targets
        except Exception:
            return []

    async def player_base_info_query(self) -> PlayerBaseInfo:
        '''查询玩家基地信息'''
        try:
            response = await self._send_request('player_baseinfo_query', {})
            result = self._handle_response(response, "查询玩家基地信息失败")
            return PlayerBaseInfo(
                Cash=result.get('Cash', 0),
                Resources=result.get('Resources', 0),
                Power=result.get('Power', 0),
                PowerDrained=result.get('PowerDrained', 0),
                PowerProvided=result.get('PowerProvided', 0)
            )
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("BASE_INFO_QUERY_ERROR", "查询玩家基地信息时发生错误: {0}".format(str(e)))

    async def screen_info_query(self) -> ScreenInfoResult:
        '''查询当前玩家看到的屏幕信息'''
        try:
            response = await self._send_request('screen_info_query', {})
            result = self._handle_response(response, "查询屏幕信息失败")
            return ScreenInfoResult(
                ScreenMin=Location(
                    result['ScreenMin']['X'],
                    result['ScreenMin']['Y']
                ),
                ScreenMax=Location(
                    result['ScreenMax']['X'],
                    result['ScreenMax']['Y']
                ),
                IsMouseOnScreen=result.get('IsMouseOnScreen', False),
                MousePosition=Location(
                    result['MousePosition']['X'],
                    result['MousePosition']['Y']
                )
            )
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("SCREEN_INFO_QUERY_ERROR", "查询屏幕信息时发生错误: {0}".format(str(e)))

    async def set_rally_point(self, target_location: Location) -> None:
        '''设置建筑的集结点'''
        try:
            response = await self._send_request('set_rally_point', {
                "targets": {"type": ["兵营", "战车工厂", "空军基地"]},
                "location": target_location.to_dict()
            })
            self._handle_response(response, "设置集结点失败")
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("SET_RALLY_POINT_ERROR", "设置集结点时发生错误: {0}".format(str(e)))

    async def control_point_query(self) -> ControlPointQueryResult:
        '''查询控制点信息
        '''
        '''
        Args:
            None

        Returns:
            ControlPointQueryResult: 控制点信息查询结果

        Raises:
            GameAPIError: 当查询控制点信息失败时
        '''
        try:
            response = await self._send_request('query_control_points', {})
            result = self._handle_response(response, "查询控制点信息失败")
            return ControlPointQueryResult(
                ControlPoints=result.get('controlPoints', [])
            )
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("CONTROL_POINT_QUERY_ERROR", "查询控制点信息时发生错误: {0}".format(str(e)))

    async def match_info_query(self) -> MatchInfoQueryResult:
        '''查询比赛信息
        '''
        '''
        Args:
            None

        Returns:
            MatchInfoQueryResult: 比赛信息查询结果

        Raises:
            GameAPIError: 当查询比赛信息失败时
        '''
        try:
            response = await self._send_request('match_info_query', {})
            result = self._handle_response(response, "查询比赛信息失败")
            return MatchInfoQueryResult(
                SelfScore=result.get('selfScore', 0),
                EnemyScore=result.get('enemyScore', 0),
                RemainingTime=result.get('remainingTime', 0)
            )
        except AsyncGameAPIError:
            raise
        except Exception as e:
            raise AsyncGameAPIError("MATCH_INFO_QUERY_ERROR", "查询比赛信息时发生错误: {0}".format(str(e)))
