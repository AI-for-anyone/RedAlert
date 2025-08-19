"""
简单的LLM token使用记录器
"""
from typing import Dict
import time
import json
from datetime import datetime
from pathlib import Path
from logs import get_logger

logger = get_logger("token_logger")

class SimpleTokenLogger:
    """简单的Token记录器"""
    
    def __init__(self):
        self.log_file = Path("graph/logs/token_usage.log")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.session_total = 0
        self.node_total: Dict[str, int] = {}
    
    def log_usage(self, node_name: str, model_name: str, tokens: int, duration_ms: float = 0):
        """记录token使用"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.session_total += tokens
        if node_name in self.node_total:
            self.node_total[node_name] += tokens
        else:
            self.node_total[node_name] = tokens
        log_entry = f"{timestamp} | {node_name} | {model_name} | {tokens} tokens | {duration_ms:.0f}ms"
        
        # 写入文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
        
        # 控制台输出
        logger.info(f"Token使用: {node_name} - {tokens} tokens，[{node_name}]累计 {self.node_total[node_name]} tokens, 会话总计 {self.session_total} tokens")
    
    def get_session_total(self) -> int:
        """获取会话总token数"""
        return self.session_total
    
    def show_recent(self, lines: int = 10):
        """显示最近的使用记录"""
        if not self.log_file.exists():
            print("暂无使用记录")
            return
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        print(f"=== 最近 {len(recent_lines)} 条记录 ===")
        for line in recent_lines:
            print(line.strip())
        print(f"会话总计: {self.session_total} tokens")

# 全局实例
token_logger = SimpleTokenLogger()
