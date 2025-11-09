# RedAlert MoFA 智能游戏助手

RedAlert 现已全面基于 **MoFA (Modular Framework for Agents)** 重构，通过 Dora 流水线在多进程环境下连接所有 Agent 节点，并继续依托 MCP (Model Context Protocol) 与 OpenRA 游戏进行交互。

## ✨ 关键特性

- **模块化 Agent Hub**：`agent-hub/` 中的每个子项目都是一个独立的 MoFA 节点，涵盖分类、生产、单位控制、情报查询等核心能力。
- **Dora 实时流水线**：通过 `mofa-compose.yaml` 将所有节点串联，统一构建、启动和监控。
- **跨平台联动**：Windows 负责运行 OpenRA 游戏与 MCP 工具，WSL 负责运行 Dora 与 MoFA Agent Hub，充分利用双环境优势。
- **可观测性增强**：节点日志与终端输入输出解耦，便于排障与性能监控。

## 🧱 目录结构

```
RedAlert/
├── agent-hub/                 # MoFA Agent Hub（核心重构部分）
│   ├── ra-classify/           # 指令分类节点 (MoFA Agent)
│   ├── ra-produce/            # 生产管理节点
│   ├── ra-unit/               # 单位控制节点
│   ├── ra-info/               # 信息查询节点
│   ├── ra-camera/             # 视角与情报节点
│   ├── ra-ai_assistant/       # 对话/辅助节点
│   ├── ra-terminal-input/     # 终端输入节点（Dora Source）
│   └── show-result/           # 结果展示节点
├── mofa-compose.yaml          # Dora 流水线定义（连接所有 MoFA 节点）
├── mcp_tools/                 # MCP 工具服务器（运行在 Windows）
├── .venv/                     # Python 虚拟环境（推荐在 WSL 中创建）
├── requirements.txt           # 通用 Python 依赖
└── ...
```

## ⚙️ 环境要求

| 组件 | 说明 |
| --- | --- |
| 操作系统 | **Windows 11/10**（运行 OpenRA 与 MCP 服务） + **WSL2 (Ubuntu)**（运行 Dora + MoFA） |
| Python | 3.10+（在 WSL 中创建 `.venv` 并激活） |
| Rust 工具链 | 安装 `rustup`、`cargo`，用于构建 Dora 运行时 |
| MoFA CLI | 通过 `pip install mofa-core` 安装 |
| Dora CLI | 使用 `cargo install dora-cli` 安装 |
| OpenRA | Windows 环境中安装并可正常运行 |

> ⚠️ **重要：** 所有 Python 命令请在 `.venv` 虚拟环境内执行（遵循项目规范）。

## 🚀 快速开始

### 1. 克隆项目（Windows 和 WSL 均需要）

```bash
git clone <repository-url>
cd RedAlert
```

### 2. 在 WSL 和 windows 中创建并激活虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate        # WSL / Linux Shell
# 若在 Windows PowerShell： .\.venv\Scripts\Activate.ps1
```

### 3. 安装 Python 依赖

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. 安装 MoFA CLI（仍在 `.venv` 中）

```bash
pip install mofa-core
mofa --help    # 验证安装
```

### 5. 安装 Dora 运行时（建议在 WSL 内执行）

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
# 安装过程保持默认配置（直接按 Enter）
source "$HOME/.cargo/env"       # 安装完成后重新加载环境变量
cargo install dora-cli

rustc --version
cargo --version
dora --version                    # 确认全部安装成功
```

### 6. 配置 LLM 与游戏环境

```bash
cp .env_example .env
```

在 `.env` 中填写各类 API Key、OpenRA 日志路径等配置，MoFA 节点会通过环境变量读取这些信息。

### 7. 准备 OpenRA 游戏（Windows）

1. 启动 OpenRA 并选择 "Red Alert" 模组。
2. 进入任意对局、确保游戏界面处于运行状态。

## ▶️ 运行流程

1. **在 Windows 终端中启动 MCP Server**（确保游戏已运行）：
   ```bash
   cd <项目根目录>\mcp_tools
   python start.py
   ```
   该脚本会并行启动单位、生产、情报、视角等 MCP 工具，保持终端开启以便查看日志。

2. **切换到 WSL 终端（已激活 `.venv`）并启动 Dora**：
   ```bash
   dora up
   dora build mofa-compose.yaml       # 仅第一次或依赖变化时需要
   dora start mofa-compose.yaml
   ```
   Dora 会根据 `mofa-compose.yaml` 自动以可编辑模式安装并启动各个 MoFA 节点。

3. **开启终端指令输入节点**：
   ```bash
   ra-terminal-input
   ```
   在弹出的终端中输入自然语言指令（如“生产 5 个步兵”），数据会流入 `ra-classify` 节点并在流水线上依次处理。

4. **查看执行结果**：
   - `show-result` 节点会将指令输出至终端或写入日志。
   - 游戏内行为由各 MCP 工具与 OpenRA 交互完成，若无响应请检查对应节点日志。

> 提示：`dora start` 会阻塞当前终端；如需停止流程，按 `Ctrl+C` 结束 Dora，再停止 MCP Server。

## 🧩 Agent Hub 节点概览

| 节点 ID | 说明 |
| --- | --- |
| `ra-terminal-input` | Dora Source，读取终端输入并广播指令 |
| `ra-classify` | 使用 LLM 判定指令类型并指派至下一节点 |
| `ra-produce` | 生产管理（建筑/单位队列） |
| `ra-unit` | 单位调度与战术执行 |
| `ra-info` | 情报查询、状态汇报 |
| `ra-camera` | 地图视角与侦察控制 |
| `ra-ai_assistant` | 对话式辅助与分析反馈 |
| `show-result` | 汇总节点输出，方便调试 |

所有节点均基于 `mofa.agent_build.base.MofaAgent` 实现，可通过 `pip install -e ./agent-hub/<node>` 独立调试。

## 🔍 调试与排障

1. **节点日志**：每个 MoFA 节点会输出日志到其所属终端，可在 `agent.write_log` 中查看详细上下文。
2. **Dora 状态**：
   ```bash
   dora list pipelines
   dora stop <pipeline-id>
   ```
3. **常见问题**
   - *未找到 `mofa.agent_build`*：确认 `.venv` 已激活并安装 `mofa-core`。
   - *Dora 构建失败*：确保 Rust 工具链安装正确，必要时执行 `rustup update`。
   - *OpenRA 未响应*：确认 Windows 端 MCP Server 仍在运行且游戏处于前台。

## 🧪 开发建议

- 新增节点：在 `agent-hub/` 创建子包，遵循现有 `main.py` 模板编写 Agent，更新 `mofa-compose.yaml` 即可加入流水线。
- 调试单个节点：
  ```bash
  pip install -e ./agent-hub/ra-produce
  python -m produce.main
  ```
- 更新依赖后，重新执行一次 `dora build mofa-compose.yaml`。

## 📄 许可证

项目遵循 [MIT License](LICENSE)。

## 🙏 致谢

- [MoFA](https://github.com/mofa-framework) —— 模块化智能体框架
- [Dora](https://dora.incubator.apache.org/) —— 实时数据编排引擎
- [OpenRA](https://www.openra.net/) —— 开源即时战略游戏引擎
- [Model Context Protocol](https://modelcontextprotocol.io/) —— 上下文工具与模型互操作协议