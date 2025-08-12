"""
mcp_sse_client.py
-----------------
用法：
    uv run mcp_sse_client.py http://127.0.0.1:8000/sse
或：
    python mcp_sse_client.py http://127.0.0.1:8000/sse
"""
import asyncio
import os

import sys
from contextlib import AsyncExitStack
from typing import Optional

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client            # ← 核心差异：SSE 传输
from openai import AsyncOpenAI                   # DeepSeek 兼容的 async SDK

import re, json

load_dotenv()


def clean_json_string(raw: str) -> dict | None:
    """
    去掉 markdown 包裹，提取并解析 JSON。
    返回 dict，失败返回 None。
    """
    raw = raw.strip()

    # 移除两端引号（如果是字符串字面量）
    if (raw.startswith("'") and raw.endswith("'")) or (raw.startswith('"') and raw.endswith('"')):
        raw = raw[1:-1]

    # 解码 \n 等转义字符（如果存在）
    #raw = raw.encode().decode("unicode_escape")

    # 处理 markdown ```json 包裹
    if raw.startswith("```"):
        lines = raw.splitlines()

        # 去掉第一行 ```json 或 ```
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        # 如果最后一行是 ``` 或 ```
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]

        raw = "\n".join(lines).strip()

    # 正则提取第一个 {...} 块
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        # print("[清理失败] 无法匹配大括号内 JSON")
        return None

    json_str = match.group(0)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print("[解析失败]", e)
        return None


class MCPClient:
    def __init__(self, model: str = "deepseek-chat"):
        self.messages = None
        self.tools = None
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

        # 从 .env 读取配置
        base_url = os.getenv("OPENAI_API_BASE", "https://api.deepseek.com")
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "deepseek-chat")

        if not api_key:
            raise ValueError("请在 .env 文件中设置 OPENAI_API_KEY")

        self.llm = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        self.model = model


    # ---------- 连接到 SSE 服务器 ----------
    async def connect(self, server_url: str):
        """
        server_url 形如 http://host:port/sse
        """
        # 建立 SSE 流
        self._streams_ctx = sse_client(url=server_url)
        streams = await self._streams_ctx.__aenter__()

        # 建立 MCP 会话
        self._session_ctx = ClientSession(*streams)
        self.session = await self._session_ctx.__aenter__()
        await self.session.initialize()

        # 列出可用工具
        tools = (await self.session.list_tools()).tools
        self.tools = {tool.name: tool for tool in tools}
        print("已连接，服务器可用工具：", [t.name for t in tools])

        def fmt(tool):
            args = tool.inputSchema.get("properties", {})
            required = set(tool.inputSchema.get("required", []))
            arg_lines = [
                f"- {name}{' (必需)' if name in required else ''}：{info.get('description', '')}"
                for name, info in args.items()
            ]
            return f"### {tool.name}\n{tool.description}\n参数:\n" + "\n".join(arg_lines)

        tools_doc = "\n\n".join(fmt(t) for t in tools)
        SYSTEM_PROMPT = f"""
    你是 OpenRA 实时指令助手。下面是你可以调用的工具列表 —— **只要需要执行游戏动作，就返回一个没有 markdown 的 JSON，字段固定为
    "tool" 和 "params"**；否则直接用自然语言回答。

    如果用户命令可以用工具完成，你必须：
    1. 选出最合适的工具名写到 "tool"。
    2. 在 "params" 里给出该工具需要的全部参数。
    3. 绝不能输出除 JSON 以外的任何内容；不要加反引号、不要加说明文字。
    4.每次回答只能包含 **一个** JSON 结构，格式如下：```json
    {{"tool": "工具名", "params": {{...}}}}
    5.不要模拟工具调用结果，也不要输出总结性文本。
    6.工具调用由外部系统执行，你只负责生成 JSON。生成完后，等待系统调用并反馈结果再继续。
    7.如果已完成所有操作，再输出自然语言的总结。

    可用工具：
    {tools_doc}
    你每次都先get_game_state来刷新状态，获取可以操作的actor_id。
    你只能调用工具并传入真实的 actor_id（整数），不能传入像 "MCV"、"actor_1" 这种字符串。
    如果你不知道 actor 的 ID，请先调用 get_game_state 获取玩家所有信息，得到目标的actor_id。
    你每次调用工具后，系统会返回其执行结果。你必须根据该结果判断是否已完成任务：
    - 如果结果满足目标，不要再重复调用工具。
    - 如果还未完成，再决定是否调用下一个工具。
    - 绝不能连续重复调用同一个工具。

    """
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    async def close(self):
        if self._session_ctx:
            await self._session_ctx.__aexit__(None, None, None)
        if self._streams_ctx:
            await self._streams_ctx.__aexit__(None, None, None)



    # ---------- 与 LLM 对话 ----------
    async def ask_llm(self, user_prompt: str) -> str:
        self.messages.append({"role": "user", "content": user_prompt})
        resp = await self.llm.chat.completions.create(
            model=self.model,
            messages=self.messages,
        )
        answer = resp.choices[0].message.content
        return answer

        # ---------- 通用的“解析 & 调用工具”逻辑 ----------

    async def handle_and_call_tool(self, llm_response: str):
        # 1. 预处理，拿到纯 JSON
        json_str = clean_json_string(llm_response)
        if not json_str:
            print("最终回答：", llm_response)
            return

        # 2. 解析
        try:
            spec = json_str
        except json.JSONDecodeError as e:
            print("解析 JSON 失败：", e, "\n内容：", llm_response)
            return

        # 3. 判断是否是工具调用
        tool_name = spec.get("tool")
        params = spec.get("params", {})
        if tool_name in self.tools:
            result = await self.session.call_tool(tool_name, params)
            print(f"[工具 {tool_name} 执行结果]:", result)

            # 反馈给 LLM
            # 工具执行结果（结构化 or 文本）
            tool_result = result.structuredContent or {"error": "no structuredContent"}

            # 加入明确说明（避免误解成只是输出）
            self.messages.append({
                "role": "user",
                "content": (
                    f"工具 `{tool_name}` 已执行完毕，返回结果如下：\n"
                    f"{json.dumps(tool_result, ensure_ascii=False)}\n\n"
                    "请根据这个结果判断是否还需要进一步调用工具，若不需要则给出最终答复。"
                     "如果需要进一步调用工具，请给出 {{\"tool\": \"工具名\", \"params\": {{...}}}} 的 JSON 格式。"
                )
            })

            resp = await self.llm.chat.completions.create(
                model=self.model,
                messages=self.messages,
            )
            next_llm = resp.choices[0].message.content
            self.messages.append({"role": "assistant", "content": next_llm})
            await self.handle_and_call_tool(next_llm)
        else:
            print("最终回答：", llm_response)

        # -------- REPL 主循环 ----------

    async def chat_loop(self):
        print("MCP SSE 客户端已启动，输入 /bye 退出\n")
        while True:
            prompt = input(">>> ").strip()
            if prompt.lower() == "/bye":
                break

            # 1. 用户问题加入上下文
            self.messages.append({"role": "user", "content": prompt})
            # 2. 调用 LLM
            resp = await self.llm.chat.completions.create(
                model=self.model,
                messages=self.messages,
            )
            llm_content = resp.choices[0].message.content
            # 先把 LLM 回复也追加上下文
            self.messages.append({"role": "assistant", "content": llm_content})

            # 3. 交给通用 handler 去看是否要调用工具
            await self.handle_and_call_tool(llm_content)


async def main(url: str = None):
    if not url:
        if len(sys.argv) < 2:
            print("用法: python mcp_sse_client.py http://127.0.0.1:8000/sse")
            sys.exit(1)
        url = sys.argv[1]

    client = MCPClient()
    try:
        await client.connect(url)
        await client.chat_loop()
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())

