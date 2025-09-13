"""
实时语音识别模块
连接 audio_recorder.py 和 asr.py，实现麦克风实时语音识别
"""

import json
import base64
import hashlib
import hmac
import ssl
import time
import threading
import queue
import numpy as np
from datetime import datetime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
from time import mktime

import websocket
from audio_recorder import AudioRecorder


class RealtimeASR:
    """实时语音识别"""
    
    def __init__(self, app_id, api_key, api_secret, volume_threshold=500, silence_duration=0.5):
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        
        # 音频录制器
        self.recorder = AudioRecorder(sample_rate=16000, channels=1, chunk_size=1280)
        
        # WebSocket相关
        self.ws = None
        self.audio_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.is_running = False
        
        # 状态
        self.STATUS_FIRST_FRAME = 0
        self.STATUS_CONTINUE_FRAME = 1
        self.STATUS_LAST_FRAME = 2
        self.frame_status = self.STATUS_FIRST_FRAME
        
        # 音量检测相关
        self.volume_threshold = volume_threshold  # 音量阈值
        self.silence_duration = silence_duration  # 静音持续时间(秒)
        self.is_speaking = False  # 是否正在说话
        self.last_speech_time = 0  # 最后检测到语音的时间
        self.speech_buffer = []  # 语音缓冲区
        self.max_buffer_size = 50  # 最大缓冲区大小
        
    def create_url(self):
        """生成WebSocket连接URL"""
        url = 'ws://iat.xf-yun.com/v1'
        
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        
       # 拼接字符串
        signature_origin = "host: " + "iat.xf-yun.com" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v1 " + "HTTP/1.1"
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(self.api_secret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.api_key, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": "iat.xf-yun.com"
        }
        
        # 拼接鉴权参数，生成url
        url = url + '?' + urlencode(v)
        return url
    
    def on_message(self, ws, message):
        """处理WebSocket消息"""
        try:
            print(f"收到消息: {message}")  # 调试输出
            message_data = json.loads(message)

            code = message_data["header"]["code"]
            status = message_data["header"]["status"]
            
            # 检查是否是错误消息
            if code != 0:
                print(f"识别错误：{code} - {message_data.get('message', '')}")
                self.is_running = False
                self.ws.close()
                self.result_queue.put({"error": f"错误码: {message_data['code']}"})
                return
                
            payload = message_data.get("payload")
            
            # 处理识别结果
            if payload:
                if payload:
                    text = payload["result"]["text"]
                    text = json.loads(str(base64.b64decode(text), "utf8"))
                    text_ws = text['ws']
                    result = ''
                    for i in text_ws:
                        for j in i["cw"]:
                            w = j["w"]
                            result += w
                    print("识别结果:", result)
                    self.result_queue.put({
                        "text": result,
                        "is_final": False,
                        "timestamp": time.time()    
                    })
            
            if status == 2:
                print("识别结束，重置状态准备下一轮")
                # 识别结束，重置状态准备下一轮，但不关闭连接
                self.frame_status = self.STATUS_FIRST_FRAME
                # 短暂停顿，让服务器处理完当前会话
                time.sleep(0.1)
                
        except Exception as e:
            print(f"消息处理错误: {e}")
            print(f"原始消息: {message}")
            self.result_queue.put({"error": str(e)})
    
    def on_error(self, ws, error):
        """处理WebSocket错误"""
        print(f"WebSocket错误: {error}")
        self.result_queue.put({"error": str(error)})
    
    def on_close(self, ws, close_status_code, close_msg):
        """处理WebSocket关闭"""
        print("WebSocket连接已关闭")
    
    def on_open(self, ws):
        """WebSocket连接建立"""
        print("WebSocket连接已建立")
        # 启动音频发送线程
        threading.Thread(target=self.send_audio_data, daemon=True).start()
    
    def calculate_volume(self, audio_data):
        """计算音频数据的音量"""
        try:
            # 将字节数据转换为numpy数组
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            if len(audio_array) == 0:
                return 0
            # 计算RMS音量，避免除零和负数
            mean_square = np.mean(audio_array.astype(np.float64)**2)
            if mean_square <= 0:
                return 0
            rms = np.sqrt(mean_square)
            return rms
        except Exception as e:
            return 0
    
    def audio_callback(self, audio_data):
        """音频回调函数，带音量检测"""
        if not self.is_running:
            return
            
        # 计算当前音频块的音量
        volume = self.calculate_volume(audio_data)
        current_time = time.time()
        
        # 检查是否超过音量阈值
        if volume > self.volume_threshold:
            if not self.is_speaking:
                print(f"检测到语音开始 (音量: {volume:.0f})")
                self.is_speaking = True
                self.frame_status = self.STATUS_FIRST_FRAME
                # 清空之前的缓冲区
                self.speech_buffer.clear()
                # 新建ws连接
                self._create_connection()
            
            self.last_speech_time = current_time
            self.speech_buffer.append(audio_data)
            
            # 限制缓冲区大小
            if len(self.speech_buffer) > self.max_buffer_size:
                self.speech_buffer.pop(0)
                
        else:
            # 音量低于阈值
            if self.is_speaking:
                # 检查是否静音时间过长
                if current_time - self.last_speech_time > self.silence_duration:
                    print(f"检测到语音结束 (静音 {self.silence_duration}s)")
                    self.is_speaking = False
                else:
                    # 静音时间不够长，继续缓冲
                    self.speech_buffer.append(audio_data)
            
        if self.is_speaking and self.speech_buffer:
            # 发送缓冲区中的数据
            for buffered_data in self.speech_buffer:
                self.audio_queue.put(buffered_data)
            self.speech_buffer.clear()
    
    def _send_end_frame(self):
        """发送结束帧"""
        if self.ws and self.is_running:
            try:
                # 发送最后一帧数据
                iat_params = {
                    "domain": "slm", "language": "zh_cn", "accent": "mandarin","dwa":"wpgs", "result":
                        {
                            "encoding": "utf8",
                            "compress": "raw",
                            "format": "plain"
                        }
                }
                
                end_frame = {
                    "header": {
                        "status": 2,
                        "app_id": self.app_id
                    },
                    "parameter": {
                        "iat": iat_params
                    },
                    "payload": {
                        "audio": {
                            "audio": "",
                            "sample_rate": 16000,
                            "encoding": "raw"
                        }
                    }
                }
                
                self.ws.send(json.dumps(end_frame))
                self.ws.close()
                print("发送结束帧")
                
            except Exception as e:
                print(f"发送结束帧错误: {e}")

    
    def send_audio_data(self):
        """发送音频数据到WebSocket"""
        # iFlytek API 参数配置
        iat_params = {
            "domain": "slm", "language": "zh_cn", "accent": "mandarin","dwa":"wpgs", "result":
                {
                    "encoding": "utf8",
                    "compress": "raw",
                    "format": "plain"
                }
        }
        
        while self.is_running:
            try:
                # 从队列获取音频数据
                audio_data = self.audio_queue.get(timeout=1.0)
                
                # 编码音频数据
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                
                # 构造数据包 - 按照官方demo格式
                if self.frame_status == self.STATUS_FIRST_FRAME:
                    # 第一帧
                    d = {
                        "header": {
                            "status": 0,
                            "app_id": self.app_id
                        },
                        "parameter": {
                            "iat": iat_params
                        },
                        "payload": {
                            "audio": {
                                "audio": audio_base64,
                                "sample_rate": 16000,
                                "encoding": "raw"
                            }
                        }
                    }
                    self.frame_status = self.STATUS_CONTINUE_FRAME
                elif self.frame_status == self.STATUS_CONTINUE_FRAME:
                    # 中间帧
                    d = {
                        "header": {
                            "status": 1,
                            "app_id": self.app_id
                        },
                        "parameter": {
                            "iat": iat_params
                        },
                        "payload": {
                            "audio": {
                                "audio": audio_base64,
                                "sample_rate": 16000,
                                "encoding": "raw"
                            }
                        }
                    }
                elif self.frame_status == self.STATUS_LAST_FRAME:
                    # 最后一帧
                    d = {
                        "header": {
                            "status": 2,
                            "app_id": self.app_id
                        },
                        "parameter": {
                            "iat": iat_params
                        },
                        "payload": {
                            "audio": {
                                "audio": audio_base64,
                                "sample_rate": 16000,
                                "encoding": "raw"
                            }
                        }
                    }
                
                self.ws.send(json.dumps(d))
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"发送音频数据错误: {e}")
                break
    
    def _create_connection(self):
        """创建新的WebSocket连接"""
        try:
            # 如果已有连接，先关闭
            if self.ws:
                self.ws.close()
            
            # 创建新的WebSocket连接
            websocket.enableTrace(False)
            ws_url = self.create_url()
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            self.ws.on_open = self.on_open
            
            # 在新线程中启动连接
            import threading
            def run_ws():
                self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
            
            ws_thread = threading.Thread(target=run_ws, daemon=True)
            ws_thread.start()
            
            # 等待连接建立
            import time
            time.sleep(0.5)
            
        except Exception as e:
            print(f"创建WebSocket连接失败: {e}")

    def start_recognition(self):
        """开始实时语音识别"""
        try:
            self.is_running = True
            
            # 启动录音
            self.recorder.start_recording(callback=self.audio_callback)
            
            # 保持主线程运行，等待用户停止
            while self.is_running:
                import time
                time.sleep(0.1)
            
        except Exception as e:
            print(f"启动识别失败: {e}")
        finally:
            self.stop_recognition()
    
    def stop_recognition(self):
        """停止语音识别"""
        self.is_running = False
        
        # 停止录音
        if self.recorder:
            self.recorder.stop_recording()
        
        # 关闭WebSocket
        if self.ws:
            self.ws.close()
    
    def get_results(self):
        """获取识别结果（非阻塞）"""
        results = []
        while not self.result_queue.empty():
            print("获取识别结果")
            try:
                result = self.result_queue.get_nowait()
                results.append(result)
            except queue.Empty:
                break
        return results


def main():
    """测试主函数"""
    # 请填入您的讯飞配置
    import os
    APP_ID = os.getenv("APP_ID")
    API_KEY = os.getenv("API_KEY")
    API_SECRET = os.getenv("API_SECRET")
    
    if not all([APP_ID, API_KEY, API_SECRET]):
        print("请先配置讯飞语音识别的 APP_ID、API_KEY 和 API_SECRET")
        print("请检查 .env 文件中的配置:")
        print("APP_ID=your_app_id")
        print("API_KEY=your_api_key") 
        print("API_SECRET=your_api_secret")
        return
    
    # 创建ASR实例，设置音量阈值和静音时长
    asr = RealtimeASR(APP_ID, API_KEY, API_SECRET, volume_threshold=500, silence_duration=2.0)
    
    print("=== 实时语音识别测试 ===")
    print("开始录音识别，按 Ctrl+C 停止...")
    print("-" * 40)
    
    # 启动结果监听线程
    def result_listener():
        while asr.is_running:
            results = asr.get_results()
            for result in results:
                if "error" in result:
                    print(f"错误: {result['error']}")
                else:
                    status = "【最终】" if result.get('is_final') else "【临时】"
                    print(f"{status} {result['text']}")
            time.sleep(0.1)
    
    result_thread = threading.Thread(target=result_listener, daemon=True)
    result_thread.start()
    
    try:
        asr.start_recognition()
    except KeyboardInterrupt:
        print("\n用户停止识别")
    finally:
        asr.stop_recognition()
        print("识别已结束")


if __name__ == "__main__":
    #将.env导入环境变量
    from dotenv import load_dotenv
    load_dotenv()
    main()
