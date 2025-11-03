# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RedAlert AI is an intelligent game assistant for the Red Alert game (OpenRA), built on LangGraph and MCP (Model Context Protocol). It provides a complete asynchronous architecture with multi-modal AI control capabilities for automated gameplay.

The system uses a dual-architecture approach:
1. **LangGraph workflow** (in `/graph`) - Original implementation using LangGraph state machines
2. **MOFA agent hub** (in `/agent-hub`) - Agent-based system using the MOFA framework

Both systems interact with the game through MCP servers that provide tools for unit control, production management, camera control, information gathering, and AI assistance.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Running the Application

**Start MCP Servers (Required First):**
```bash
cd mcp_tools
python start.py
```

**Start the AI Assistant:**
```bash
# Standard stdio mode (default)
python main.py --mode stdio

# With debug logging
python main.py --mode stdio --log-level DEBUG

# SSE streaming mode
python main.py --mode sse

# HTTP API mode
python main.py --mode http

# Gradio UI mode
python main.py --mode gradio
```

**Exit the application:**
Type `/bye` in stdio mode or use Ctrl+C

### Validation
```bash
# Validate configuration
python validate_config.py

# Validate LLM and MCP server configs
python config/config.py
```

## Architecture Overview

### System Components

1. **Graph Workflow (`/graph`)** - LangGraph-based state machine system:
   - `graph.py` - Main workflow orchestrator
   - `state.py` - Global state and workflow type definitions
   - `classify.py` - Intent classification node
   - `camera.py` - Camera/viewport control node
   - `production.py` - Production management node
   - `unit_control.py` - Unit control node
   - `intelligence.py` - Information gathering node
   - `ai_assistant.py` - AI assistant node
   - `base_node.py` - Base class for all nodes with LLM + MCP tool integration
   - `mcp_manager.py` - MCP client manager using MultiServerMCPClient
   - `token_logger.py` - Token usage tracking and cost analysis

2. **MCP Tools (`/mcp_tools`)** - MCP servers that expose game control tools:
   - `camera_mcp_server.py` (port 8000) - Camera control
   - `fight_mcp_server.py` (port 8001) - Combat operations
   - `info_mcp_server.py` (port 8002) - Game state queries
   - `produce_mcp_server.py` (port 8003) - Production management
   - `unit_mcp_server.py` (port 8004) - Unit control
   - `start.py` - Unified launcher for all MCP servers

3. **Agent Hub (`/agent-hub`)** - MOFA framework-based agents:
   - `ra-classify` - Command classification agent
   - `ra-camera` - Camera control agent
   - `ra-produce` - Production agent
   - `ra-unit` - Unit control agent
   - `ra-info` - Information query agent
   - `ra-ai_assistant` - AI assistant agent
   - `ra-terminal-input` - Terminal input handler
   - `ra-show` - Output display agent

4. **Task Scheduler (`/task_scheduler`)** - Asyncio-based concurrent task management

5. **Configuration (`/config`)** - Centralized configuration system:
   - LLM configs per workflow type
   - MCP server configs
   - Prompt configs with file paths
   - Environment variable management

6. **Prompts (`/prompt`)** - System prompts for each workflow node (markdown files)

7. **Logging (`/logs`)** - Structured logging system with performance monitoring

### Key Architecture Patterns

**BaseNode Pattern:**
All graph nodes inherit from `BaseNode` which provides:
- LLM initialization from config
- MCP tool binding via `mcp_manager`
- Tool calling loop with `execute_with_tools()`
- Token usage tracking
- Abstract methods: `_get_node_tools()`, `_get_system_prompt()`

**MCP Tool Integration:**
- Each node gets specific tools via `mcp_manager.get_tools_by_server()`
- Tools are bound to LLM using `model.bind_tools()`
- Tool execution handled by LangGraph's `ToolNode`
- Tool filtering based on patterns in `config.SERVER_TOOL_PATTERNS`

**Workflow Routing:**
1. User input → `ClassifyNode` determines workflow type
2. State graph routes to appropriate node (camera/production/unit/intelligence/ai_assistant)
3. Node executes with LLM + tools loop
4. Returns to classify node for next command

**Dual Transport Support:**
- Graph nodes use `MultiServerMCPClient` with streamable_http transport
- Agent hub nodes have their own `mcp_cli.py` with the same pattern

## Configuration System

### Environment Variables (.env)

The system uses per-node LLM configuration to allow different models for different tasks:

```bash
# Classification node (fast, low temperature)
CLASSIFY_API_KEY=
CLASSIFY_API_BASE=
CLASSIFY_MODEL=
CLASSIFY_MODEL_PROVIDER=openai

# Production management node
PRODUCTION_API_KEY=
PRODUCTION_API_BASE=
PRODUCTION_MODEL=
PRODUCTION_MODEL_PROVIDER=openai

# Unit control node
UNIT_CONTROL_API_KEY=
UNIT_CONTROL_API_BASE=
UNIT_CONTROL_MODEL=
UNIT_CONTROL_MODEL_PROVIDER=openai

# Camera control node
CAMERA_API_KEY=
CAMERA_API_BASE=
CAMERA_MODEL=
CAMERA_MODEL_PROVIDER=openai

# Intelligence node
INTELLIGENCE_API_KEY=
INTELLIGENCE_API_BASE=
INTELLIGENCE_MODEL=
INTELLIGENCE_MODEL_PROVIDER=openai

# AI assistant node
AI_ASSISTANT_API_KEY=
AI_ASSISTANT_API_BASE=
AI_ASSISTANT_MODEL=
AI_ASSISTANT_MODEL_PROVIDER=openai
```

Each workflow type can use a different model optimized for its task (e.g., fast model for classification, powerful model for unit control).

### MCP Server Configuration

Default MCP servers run on localhost:
- Camera: `http://127.0.0.1:8000/mcp`
- Fight: `http://127.0.0.1:8001/mcp`
- Info: `http://127.0.0.1:8002/mcp`
- Produce: `http://127.0.0.1:8003/mcp`
- Unit: `http://127.0.0.1:8004/mcp`

All use `streamable_http` transport. Configuration in `config/config.py`.

### Workflow Types

The system recognizes these workflow types (defined in `config.WorkflowType` and `graph.state.WorkflowType`):

- `CLASSIFY` - Intent classification (always runs first)
- `CAMERA_CONTROL` - Map viewport control
- `PRODUCTION` - Building and unit production
- `UNIT_CONTROL` - Unit movement and combat
- `INTELLIGENCE` - Game state queries and information gathering
- `AI_ASSISTANT` - Autonomous AI decision-making

## Important Implementation Details

### Asynchronous Architecture

The entire system is built on asyncio:
- All nodes must be initialized with `await node.initialize()`
- Model calls use `ainvoke()` not `invoke()`
- Tool calls use `await tool_node.ainvoke()`
- Main entry point is `asyncio.run(main_async())`

### Token Tracking

Token usage is automatically tracked per node:
```python
from graph.token_logger import token_logger

# Automatically logged in BaseNode._call_model()
# View stats programmatically or check logs/token_usage.jsonl
```

### Adding New Workflow Nodes

1. Create new file in `/graph` (e.g., `my_node.py`)
2. Inherit from `BaseNode`:
   ```python
   from graph.base_node import BaseNode
   from config.config import WorkflowType

   class MyNode(BaseNode):
       def __init__(self):
           super().__init__("my_node", WorkflowType.MY_TYPE)

       def _get_node_tools(self):
           return mcp_manager.get_tools_by_server("relevant_server")

       def _get_system_prompt(self):
           return config.load_prompt(WorkflowType.MY_TYPE)

       async def my_node_func(self, state):
           result = await self.execute_with_tools(state["input_cmd"])
           return {"result": result}
   ```
3. Add to `graph/graph.py` in `Graph._init_graph()`
4. Add prompt file to `/prompt`
5. Add LLM config to `config/config.py`

### MCP Tool Filtering

Tools are filtered by server name using patterns in `SERVER_TOOL_PATTERNS`:

```python
# In config/config.py
SERVER_TOOL_PATTERNS = {
    "camera": ("move_camera_to", "camera_move_dir", "camera_move_to"),
    "produce": ("produce", "can_produce", "deploy_mcv", ...),
    # ...
}
```

When a node needs tools, it calls:
```python
tools = mcp_manager.get_tools_by_server("camera")
```

This filters the global tool list to only those matching the patterns.

### Game Constants

Game entities are defined as constants in `config/config.py`:
- `ALL_BUILDINGS` - All buildable structures
- `ALL_UNITS` - All producible units
- `ALL_DIRECTIONS` - Map directions
- `ALL_GROUPS` - Unit group numbers (0-9)
- `ALL_ACTORS` - Actor types (enemy, friendly, neutral)

These are exposed as `PROMPT_PARAMS` for use in prompt templates.

### Error Handling

- MCP server connection is checked but not enforced (see `check_mcp_servers()`)
- Nodes gracefully handle missing tools
- Token logging failures are logged but don't break execution
- Each MCP server runs in separate process for isolation

## Common Development Tasks

### Modifying System Prompts

Prompts are in `/prompt` as markdown files. They're loaded dynamically:
```python
from config.config import config, WorkflowType

prompt = config.load_prompt(WorkflowType.PRODUCTION)
```

### Changing Model Per Node

Edit `.env` to change model for specific workflow:
```bash
# Use GPT-4 for unit control, GPT-3.5 for others
UNIT_CONTROL_MODEL=gpt-4
UNIT_CONTROL_API_BASE=https://api.openai.com/v1

CLASSIFY_MODEL=gpt-3.5-turbo
CLASSIFY_API_BASE=https://api.openai.com/v1
```

### Adding New MCP Tools

1. Add tool function to appropriate server in `/mcp_tools`
2. Register tool with MCP server decorator
3. Add tool name to `SERVER_TOOL_PATTERNS` in `config/config.py`
4. Tool will be available to nodes that use that server

### Debugging

Enable debug logging to see all LLM calls and tool invocations:
```bash
python main.py --log-level DEBUG
```

Check logs:
- System logs in `/logs` directory
- Token usage: `graph/logs/token_usage.jsonl`
- Each node logs its operations

## Project Structure Context

This is a competition/demonstration project for Red Alert AI gameplay. The dual architecture (LangGraph + MOFA) suggests experimentation with different approaches. The `mofa-compose.yaml` defines the MOFA agent pipeline, while `graph/` contains the LangGraph implementation.

The system is designed to:
1. Receive natural language commands
2. Classify intent
3. Execute using appropriate specialized node/agent
4. Track resource usage (tokens)
5. Handle concurrent tasks via task scheduler

Game interaction happens entirely through MCP servers which communicate with OpenRA via game logs and APIs (implementation details in `/mcp_tools`).
