# RedAlert 日志模块

RedAlert项目的统一日志记录模块，提供完整的日志功能，包括文件输出、控制台输出、彩色显示、性能监控等。

## 功能特性

- 🎯 **统一接口**: 提供一致的日志记录API
- 📁 **文件输出**: 支持日志轮转和文件大小限制
- 🎨 **彩色输出**: 控制台彩色日志显示
- ⚡ **性能监控**: 内置函数执行时间记录
- 🔧 **灵活配置**: 支持多种配置方式
- 📊 **模块化**: 支持不同模块使用独立配置

## 快速开始

### 基本使用

```python
from logs import get_logger

# 获取日志记录器
logger = get_logger("my_module")

# 记录日志
logger.info("应用启动")
logger.debug("调试信息")
logger.warning("警告信息")
logger.error("错误信息")
```

### 自定义配置

```python
from logs import setup_logging, LogConfig, LogLevel

# 创建自定义配置
config = LogConfig(
    level=LogLevel.DEBUG,
    enable_color=True,
    log_filename="my_app.log"
)

# 应用配置
setup_logging(config)
```

## 配置选项

### LogConfig 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `level` | LogLevel | INFO | 日志级别 |
| `format` | str | 标准格式 | 日志格式字符串 |
| `enable_file_logging` | bool | True | 是否启用文件输出 |
| `enable_console_logging` | bool | True | 是否启用控制台输出 |
| `enable_color` | bool | True | 是否启用彩色输出 |
| `log_dir` | str | "logs" | 日志文件目录 |
| `log_filename` | str | "redalert.log" | 日志文件名 |
| `max_file_size` | int | 10MB | 单个日志文件最大大小 |
| `backup_count` | int | 5 | 保留的备份文件数量 |

### 预定义配置

```python
from logs.config import DEV_CONFIG, PROD_CONFIG

# 开发环境配置
setup_logging(DEV_CONFIG)

# 生产环境配置  
setup_logging(PROD_CONFIG)
```

## 高级功能

### 性能监控装饰器

```python
from logs.utils import log_execution_time

@log_execution_time("performance")
def slow_function():
    # 函数执行时间会被自动记录
    pass
```

### 上下文管理器

```python
from logs.utils import LogContext

with LogContext("my_module", "数据处理"):
    # 操作开始和结束会被自动记录
    process_data()
```

### 异常记录

```python
try:
    risky_operation()
except Exception as e:
    logger.exception("操作失败")  # 自动记录异常堆栈
```

## 在RedAlert项目中的集成

### 1. 在main.py中初始化

```python
from logs import setup_logging, LogConfig, LogLevel

# 根据环境选择配置
if os.getenv("ENV") == "production":
    from logs.config import PROD_CONFIG
    setup_logging(PROD_CONFIG)
else:
    from logs.config import DEV_CONFIG
    setup_logging(DEV_CONFIG)
```

### 2. 在Graph模块中使用

```python
from logs import get_logger

class Graph:
    def __init__(self):
        self.logger = get_logger("graph")
        self.logger.info("Graph模块初始化")
    
    def run(self):
        self.logger.info("Graph开始运行")
        # ... 其他代码
```

### 3. 在MCP Server中使用

```python
from logs import get_logger

def main():
    logger = get_logger("mcp_server")
    logger.info("MCP Server启动")
    # ... 服务器代码
```

## 日志级别

- **DEBUG**: 详细的调试信息
- **INFO**: 一般信息
- **WARNING**: 警告信息
- **ERROR**: 错误信息
- **CRITICAL**: 严重错误

## 文件结构

```
logs/
├── __init__.py          # 模块入口
├── config.py           # 配置定义
├── logger.py           # 核心日志实现
├── utils.py            # 工具函数
├── examples.py         # 使用示例
└── README.md           # 文档
```

## 示例运行

```bash
# 运行示例代码
python -m logs.examples
```

## 注意事项

1. 日志文件会自动创建在 `logs/` 目录下
2. 当日志文件超过设定大小时会自动轮转
3. 彩色输出仅在支持的终端中生效
4. 建议在应用启动时就配置好日志系统

## 最佳实践

1. **模块化使用**: 每个模块使用独立的日志记录器
2. **合理的日志级别**: 开发时使用DEBUG，生产时使用INFO或WARNING
3. **异常记录**: 使用`logger.exception()`记录异常信息
4. **性能监控**: 对关键函数使用性能监控装饰器
5. **上下文信息**: 在日志中包含足够的上下文信息
