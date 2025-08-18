from typing import Dict
import asyncio
import json
import time
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
                    if query_params.faction is not None and len(query_params.faction) > 0 and data["faction"] not in query_params.faction:
                        continue
                    actor = Actor(data["id"])
                    position = Location(
                        data["position"]["x"],
                        data["position"]["y"]
                    )
                    hp_percent = data["hp"] * 100 // data["maxHp"] if data["maxHp"] > 0 else -1
                    actor.update_details(
                        data["type"],
                        data["faction"],
                        position,
                        hp_percent
                    )
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
