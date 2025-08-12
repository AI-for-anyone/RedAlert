# MCP 一键启动示例

本项目为 MCP 的简化演示版，提供一键启动的 MCP 服务端与 SSE 客户端。

## 📦 项目结构

```
mcp/
├── mcp_tools/
│   ├── mcp_server.py      # MCP 服务端（基于 FastAPI + SSE）
│   └── mcp_client.py      # MCP 客户端（基于 SSE + OpenAI/DeepSeek）
├── main.py                # ✅ 一键启动脚本：同时启动服务端和客户端
├── requirements.txt       # 所需依赖
└── README.md              # 使用说明
└── .env                   # 大模型接口
```

## ⚙️ 安装环境依赖

建议使用 Python 3.10+，并创建虚拟环境：

```bash
pip install -r requirements.txt
```

## 🔐 配置大模型接口

你需要手动配置自己的 API Key 和模型访问地址。

打开 `.env` 文件，填写你的大模型接口信息：
## 🚀 启动方式

直接运行 `main.py`，即可同时启动 MCP Server 与 Client：

```bash
python main.py
```

你会看到如下提示：

```
[启动] MCP Server
[✔] MCP Server 已就绪
[启动] MCP Client
MCP SSE 客户端已启动，输入 /bye 退出
>>> 
```

客户端将连接 `http://127.0.0.1:8000/sse`，并与大模型对话交互。

## 🛠 交互说明

客户端支持自然语言指令，自动解析为工具调用。示例输入：

```
>>> 生产一个电厂
>>> 查询当前状态
>>> 派出部队攻击敌人
```

每个输入都将通过 LLM 转换为 JSON 工具调用，服务端处理后返回结果。

## 🧼 清理与退出

- 输入 `/bye` 可退出客户端
- 按 `Ctrl+C` 可中断整个运行

## 📋 其他说明

- 如需单独运行服务端，请执行：

```bash
python mcp_tools/mcp_server.py
```

- 如需单独运行客户端：
```bash
python mcp_tools/mcp_client.py http://127.0.0.1:8000/sse
```

C:\Users\15964\AppData\Roaming\OpenRA\Logs