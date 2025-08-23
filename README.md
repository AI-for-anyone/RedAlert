# RedAlert AI 智能游戏助手

基于 LangGraph 和 MCP (Model Context Protocol) 的红色警戒智能游戏助手，提供完整的异步架构和多模态AI控制能力。

## 🎯 项目特色

- **🤖 智能决策系统**: 基于 LangGraph 的状态图工作流，支持复杂的游戏策略决策
- **⚡ 异步架构**: 完全异步化设计，支持高并发任务处理和实时响应
- **🔧 MCP 工具集**: 丰富的游戏控制工具，包括单位控制、生产管理、情报收集等
- **📊 Token 追踪**: 完整的 LLM Token 使用统计和成本分析系统
- **📈 任务调度**: 智能任务管理和并发控制系统

## 🏗️ 系统架构

```
RedAlert/
├── graph/                 # LangGraph 工作流核心
│   ├── base_node.py      # 基础节点类
│   ├── classify.py       # 意图分类节点
│   ├── camera.py         # 视觉识别节点
│   ├── production.py     # 生产管理节点
│   ├── unit_control.py   # 单位控制节点
│   ├── intelligence.py   # 情报收集节点
│   └── token_tracker.py  # Token 使用追踪
├── mcp_tools/            # MCP 工具服务器
│   ├── fight_mcp_server.py    # 战斗控制工具
│   ├── produce_mcp_server.py  # 生产管理工具
│   ├── unit_mcp_server.py     # 单位管理工具
│   ├── info_mcp_server.py     # 信息查询工具
│   └── camera_mcp_server.py   # 视觉识别工具
├── task_scheduler/       # 任务调度系统
├── config/              # 配置管理
└── logs/                # 日志系统
```

## ⚙️ 环境要求

- **Python**: 3.10+
- **操作系统**: Windows (支持 OpenRA 游戏)
- **内存**: 建议 8GB+
- **GPU**: 可选，用于视觉识别加速

## 🚀 快速开始

### 前置要求

- **OpenRA 游戏**: 确保已安装并能正常运行 [OpenRA](https://www.openra.net/)
- **Python 3.10+**: 推荐使用 Python 3.11
- **API 密钥**: 至少需要一个 LLM 服务的 API 密钥

### 1. 克隆项目

```bash
git clone <repository-url>
cd RedAlert
```

### 2. 创建虚拟环境

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
.venv\Scripts\activate  # Windows
# 或
source .venv/bin/activate  # Linux/macOS
```

### 3. 安装依赖

```bash
# 升级 pip
python -m pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt
```

### 4. 配置环境变量

复制示例配置文件并编辑：

```bash
copy .env_example .env  # Windows
# 或
cp .env_example .env    # Linux/macOS
```

编辑 `.env` 文件，配置你的 API 密钥：

```env
# OpenAI API 配置 (推荐)
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# DeepSeek API 配置 (经济实惠的选择)
DEEPSEEK_API_KEY=your-deepseek-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 模型配置
MODEL_NAME=gpt-4o-mini  # 或 deepseek-chat

# 游戏配置 (可选)
OPENRA_LOG_PATH=C:\Users\YourName\AppData\Roaming\OpenRA\Logs
```

### 5. 启动 OpenRA 游戏

1. 启动 OpenRA 游戏
2. 选择 "Red Alert" 模组
3. 开始一局游戏（单人或多人）

### 6. 启动mcp服务器和AI助手

启动mcp服务器
```bash
cd mcp_tools
python start.py
```

启动助手
```bash
# 标准模式启动 (推荐新手)
python main.py

# 或指定启动模式
python main.py --mode stdio --log-level INFO
```

### 7. 首次使用

启动成功后,可以尝试输入一些基础指令：

```
>>> 查看当前游戏状态
>>> 建造一个电厂
>>> 生产5个步兵
>>> 帮我分析当前局势
```

### 🎯 启动模式说明

```bash
# 标准输入输出模式 (默认，适合开发和调试)
python main.py --mode stdio

# SSE 流式模式 (适合 Web 集成)
python main.py --mode sse

# HTTP API 模式 (适合外部调用)
python main.py --mode http

# 调试模式 (显示详细日志)
python main.py --log-level DEBUG
```

### ⚠️ 常见启动问题

**问题 1**: `ModuleNotFoundError`
```bash
# 确保虚拟环境已激活
.venv\Scripts\activate
pip install -r requirements.txt
```

**问题 2**: API 密钥错误
```bash
# 检查 .env 文件配置
python validate_config.py
```

**问题 3**: OpenRA 连接失败
- 确保 OpenRA 游戏正在运行
- 检查游戏日志路径配置是否正确

**问题 4**: 权限错误
```bash
# 以管理员身份运行 (Windows)
# 或检查文件权限 (Linux/macOS)
```

## 🎮 功能模块

### 🧠 智能决策系统
- **意图分类**: 自动识别用户指令类型（生产、战斗、侦察等）
- **状态管理**: 基于 LangGraph 的全局状态跟踪
- **工作流编排**: 复杂任务的自动分解和执行

### ⚔️ 战斗控制
- **单位编组**: 智能单位分组和阵型管理
- **战术执行**: 攻击、防守、撤退等战术指令
- **目标识别**: 自动识别和优先攻击目标

### 🏭 生产管理
- **建筑建造**: 自动选择最优建造位置
- **单位生产**: 智能生产队列管理
- **资源优化**: 基于当前资源状况的生产决策

### 👁️ 视觉识别
- **屏幕分析**: 实时游戏画面识别
- **单位检测**: 自动识别友军和敌军单位
- **地图分析**: 地形和资源点识别

### 📊 数据分析
- **Token 统计**: 详细的 LLM 使用统计和成本分析
- **性能监控**: 系统性能和响应时间监控
- **日志记录**: 完整的操作日志和错误追踪

## 🛠️ 使用示例

### 基础指令
```
>>> 建造一个电厂
>>> 生产5个步兵
>>> 攻击敌人基地
>>> 查看当前资源状况
>>> 侦察地图右上角
```

### 高级功能
```
>>> 创建一个攻击编组，包含坦克和步兵
>>> 在主基地周围建立防御阵地
>>> 分析当前战场形势
>>> 制定经济发展策略
```

## 📈 Token 使用统计

系统内置完整的 Token 追踪功能：

```python
from graph.token_stats import show_session_summary, show_cost_analysis

# 查看会话统计
show_session_summary()

# 查看成本分析
show_cost_analysis()

# 导出详细报告
export_report()
```

## 🔧 技术栈

- **核心框架**: LangGraph, LangChain
- **异步处理**: asyncio, aiohttp
- **MCP 协议**: Model Context Protocol
- **AI 模型**: OpenAI GPT, DeepSeek, Claude 等
- **游戏接口**: OpenRA Game API
- **日志系统**: 结构化日志和性能监控

## 📝 开发说明

### 添加新的 MCP 工具
1. 在 `mcp_tools/` 目录创建新的服务器文件
2. 继承 `BaseNode` 类实现业务逻辑
3. 在 `config/config.py` 中注册新工具

### 扩展工作流节点
1. 在 `graph/` 目录创建新节点类
2. 实现 `process` 方法定义节点逻辑
3. 在 `graph.py` 中添加到状态图

## 🐛 故障排除

### 常见问题
- **MCP 连接失败**: 检查 MCP 服务器是否正常启动
- **API 调用错误**: 验证 `.env` 文件中的 API 密钥配置
- **游戏连接问题**: 确保 OpenRA 游戏正在运行

### 日志查看
```bash
# 查看系统日志
tail -f logs/system.log

# 查看 Token 使用日志
tail -f graph/logs/token_usage.jsonl
```

## 🤝 贡献指南

1. Fork 项目仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [LangGraph](https://github.com/langchain-ai/langgraph) - 工作流编排框架
- [OpenRA](https://www.openra.net/) - 开源即时战略游戏引擎
- [MCP](https://modelcontextprotocol.io/) - 模型上下文协议