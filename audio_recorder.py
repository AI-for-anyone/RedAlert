"""
简单的电脑音频录制模块
"""

import pyaudio
import wave
import threading
import time
from typing import Optional, Callable


class AudioRecorder:
    """简单的音频录制器"""
    
    def __init__(self, sample_rate=16000, channels=1, chunk_size=1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        
        self.audio = None
        self.stream = None
        self.frames = []
        self.is_recording = False
        self.record_thread = None
        
    def list_devices(self):
        """列出所有音频输入设备"""
        audio = pyaudio.PyAudio()
        print("可用音频输入设备:")
        for i in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"  {i}: {info['name']} (输入通道: {info['maxInputChannels']})")
        audio.terminate()
    
    def start_recording(self, device_index=None, callback: Optional[Callable] = None):
        """开始录音"""
        if self.is_recording:
            print("已在录音中")
            return
            
        self.audio = pyaudio.PyAudio()
        
        # 如果没指定设备，自动选择第一个有输入通道的设备
        if device_index is None:
            for i in range(self.audio.get_device_count()):
                info = self.audio.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    device_index = i
                    print(f"使用设备: {info['name']} (输入通道: {info['maxInputChannels']})")
                    break
        
        if device_index is None:
            print("错误: 未找到可用的音频输入设备")
            self.cleanup()
            return
        
        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk_size
            )
            
            self.is_recording = True
            self.frames = []
            
            # 启动录音线程
            self.record_thread = threading.Thread(target=self._record_audio, args=(callback,))
            self.record_thread.start()
            
            print("开始录音...")
            
        except Exception as e:
            print(f"录音启动失败: {e}")
            self.cleanup()
    
    def _record_audio(self, callback: Optional[Callable]):
        """录音线程函数"""
        while self.is_recording:
            try:
                data = self.stream.read(self.chunk_size)
                self.frames.append(data)
                
                # 如果有回调函数，调用它处理音频数据
                if callback:
                    callback(data)
                    
            except Exception as e:
                print(f"录音错误: {e}")
                break
    
    def stop_recording(self):
        """停止录音"""
        if not self.is_recording:
            return
            
        self.is_recording = False
        
        if self.record_thread:
            self.record_thread.join()
        
        self.cleanup()
        print("录音停止")
    
    def cleanup(self):
        """清理资源"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            
        if self.audio:
            self.audio.terminate()
            self.audio = None
    
    def save_to_file(self, filename="recording.wav"):
        """保存录音到文件"""
        if not self.frames:
            print("没有录音数据")
            return
            
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # paInt16 = 2 bytes
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(self.frames))
        
        print(f"录音已保存到: {filename}")
    
    def get_audio_data(self):
        """获取录音数据"""
        return b''.join(self.frames)


def simple_record_example():
    """简单录音示例"""
    recorder = AudioRecorder()
    
    # 列出设备
    recorder.list_devices()
    
    # 开始录音
    recorder.start_recording()
    
    try:
        # 录音5秒
        time.sleep(5)
    except KeyboardInterrupt:
        print("\n用户停止录音")
    
    # 停止录音并保存
    recorder.stop_recording()
    recorder.save_to_file("test_recording.wav")


def realtime_callback_example():
    """实时处理音频数据示例"""
    def audio_callback(data):
        # 这里可以实时处理音频数据
        # 比如发送给语音识别API
        print(f"收到音频数据: {len(data)} 字节")
    
    recorder = AudioRecorder()
    recorder.start_recording(callback=audio_callback)
    
    try:
        print("实时录音中，按Ctrl+C停止...")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n停止录音")
    
    recorder.stop_recording()


if __name__ == "__main__":
    print("选择测试模式:")
    print("1. 简单录音测试")
    print("2. 实时处理测试")
    
    choice = input("输入选择 (1 或 2): ").strip()
    
    if choice == "1":
        simple_record_example()
    elif choice == "2":
        realtime_callback_example()
    else:
        print("无效选择")
