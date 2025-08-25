import asyncio
from typing import Any, Dict, List, Tuple
from datetime import datetime
from collections import deque

import gradio as gr
from dotenv import load_dotenv

from graph.graph import Graph
from task_scheduler.task_manager import TaskManager, TaskStatus

# Load .env
load_dotenv()

# Global graph instance (initialized lazily)
_graph: Graph | None = None
# Recent runs history for robust UI listing across Gradio workers
_recent_runs: deque[Dict[str, Any]] = deque(maxlen=50)

def _recent_upsert(record: Dict[str, Any]) -> None:
    """Insert or update a record in _recent_runs by id."""
    rid = record.get("id")
    if not rid:
        return
    for i, r in enumerate(_recent_runs):
        if r.get("id") == rid:
            _recent_runs[i] = {**r, **record}
            return
    _recent_runs.append(record)


def _ensure_graph() -> Graph:
    global _graph
    if _graph is None:
        # mode is irrelevant for Gradio; we drive the compiled graph directly
        _graph = Graph(mode="http")
    return _graph


def _format_steps(classify_plan_cmds: List[Any]) -> List[str]:
    steps: List[str] = []
    for i, cmd in enumerate(classify_plan_cmds or []):
        try:
            assistant = getattr(cmd, "assistant", None) or (cmd.get("assistant") if isinstance(cmd, dict) else str(cmd))
            task = getattr(cmd, "task", None) or (cmd.get("task") if isinstance(cmd, dict) else "")
        except Exception:
            assistant, task = str(cmd), ""
        steps.append(f"{i+1}. [{assistant}] {task}")
    return steps


def _render_state_md(state: Dict[str, Any]) -> str:
    if not isinstance(state, dict):
        return "执行完成，但无可展示的状态"
    result = state.get("result") or ""
    steps_md = "\n".join([f"- {s}" for s in _format_steps(state.get("classify_plan_cmds", []))])
    parts = []
    parts.append("### 执行结果\n" + (result if isinstance(result, str) else str(result)))
    if steps_md:
        parts.append("\n### 计划步骤\n" + steps_md)
    meta = []
    if state.get("state"):
        meta.append(f"状态: {getattr(state['state'], 'value', state['state'])}")
    if state.get("cmd_type"):
        meta.append(f"类型: {getattr(state['cmd_type'], 'value', state['cmd_type'])}")
    if meta:
        parts.append("\n> " + " | ".join(meta))
    return "\n\n".join(parts)


async def _render_all_tasks_md() -> str:
    """Render a markdown listing of all tasks and their statuses."""
    tm = await TaskManager.get_instance()
    infos = list(tm.get_all_tasks_info() or [])

    # Merge with recent runs (fallback entries when TaskManager view is limited)
    # Prefer TaskManager entries by id; only add missing recent ones
    known_ids = {it.get("id") for it in infos}
    for r in list(_recent_runs):
        if r.get("id") not in known_ids:
            infos.append(r)

    # Normalize to comparable float timestamp to avoid mixed-type sorting issues
    def _parse_ts(s: Any) -> float:
        if not s:
            return float("-inf")
        try:
            dt = datetime.fromisoformat(str(s))
            return float(dt.timestamp())
        except Exception:
            return float("-inf")

    # Sort by start_time desc, then by id
    infos_sorted = sorted(
        infos,
        key=lambda x: (-_parse_ts(x.get("start_time")), str(x.get("id"))),
    )

    # Counts by status
    counts: Dict[str, int] = {}
    for it in infos:
        counts[it.get("status", "unknown")] = counts.get(it.get("status", "unknown"), 0) + 1

    header = [
        "### 所有任务",
        "",
        f"总数: {len(infos)} | "
        + " | ".join([f"{k}:{v}" for k, v in sorted(counts.items())])
    ]

    # Limit to most recent 50 to keep UI fast
    lines = []
    for i, it in enumerate(infos_sorted[:50], 1):
        name = it.get("name") or it.get("id")
        status = it.get("status")
        st = it.get("start_time") or "-"
        et = it.get("end_time") or "-"
        err = it.get("error")
        extra = f" | 错误: {err}" if err else ""
        tid = it.get('id')
        # 以任务名称/命令为主，ID 作为备注
        lines.append(f"{i}. {name} [{status}]\n> 备注: id={tid} | 开始: {st} | 结束: {et}{extra}")

    if not lines:
        lines = ["(暂无任务)"]

    return "\n".join(header + [""] + lines)


async def _refresh_tasks_ui() -> str:
    """Return tasks_markdown for periodic UI refresh. Does NOT touch selector to avoid input interference."""
    try:
        return await _render_all_tasks_md()
    except Exception as e:
        print("[gradio_ui] _refresh_tasks_ui error:", e)
        return "### 所有任务\n(加载失败)"


async def _refresh_selector(selected_id: str | None = None):
    """Manually refresh dropdown choices. Keeps selection when possible."""
    tm = await TaskManager.get_instance()
    infos = list(tm.get_all_tasks_info() or [])

    known_ids = {it.get("id") for it in infos}
    for r in list(_recent_runs):
        if r.get("id") not in known_ids:
            infos.append(r)

    def _parse_ts(s: Any) -> float:
        if not s:
            return float("-inf")
        try:
            return float(datetime.fromisoformat(str(s)).timestamp())
        except Exception:
            return float("-inf")

    infos_sorted = sorted(
        infos,
        key=lambda x: (-_parse_ts(x.get("start_time")), str(x.get("id"))),
    )

    choices = [
        (f"{(it.get('name') or it.get('id'))} (id={it.get('id')})", str(it.get("id")))
        for it in infos_sorted[:50]
    ]
    values = [v for (_, v) in choices]
    value = selected_id if (selected_id in values) else (values[0] if values else None)
    return gr.update(choices=choices, value=value)


async def show_task_detail(task_id: str) -> str:
    """Render details for a specific task id."""
    try:
        if not task_id:
            return "(未选择任务)"
        tm = await TaskManager.get_instance()
        info = tm.get_task_info(task_id) or {}
        status = info.get("status")
        start = info.get("start_time") or "-"
        end = info.get("end_time") or "-"
        err = info.get("error")
        header = f"### 任务 {task_id}\n状态: {status} | 开始: {start} | 结束: {end}"
        if status == TaskStatus.COMPLETED.value:
            state = tm.get_task_result(task_id)
            return header + "\n\n" + _render_state_md(state)
        if status == TaskStatus.FAILED.value:
            return header + (f"\n\n错误: {err}" if err else "")
        return header + "\n\n(进行中或已排队，完成后可查看结果)"
    except Exception as e:
        print("[gradio_ui] show_task_detail error:", e)
        return f"### 任务 {task_id or '-'}\n(详情加载失败)"


async def run_graph_command(user_cmd: str) -> Tuple[str, str, str]:
    """Submit a graph task and return an immediate acknowledgement.

    Returns 3 outputs: (current_cmd_md, status_md, result_md)
    """
    graph = _ensure_graph()
    await graph.initialize()

    tm = await TaskManager.get_instance()
    task = await tm.create_task(graph._compiled_graph.ainvoke({"input_cmd": user_cmd}), name=f"cmd:{user_cmd}")
    _recent_upsert({
        "id": task.id,
        "name": task.name,
        "status": TaskStatus.PENDING.value,
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "error": None,
    })
    _ = await tm.submit_task(task.id)
    return (
        f"指令: {user_cmd}",
        "状态: 已提交",
        "(等待完成后在下方选择任务查看详情)"
    )


def launch():
    """Launch the Gradio UI."""
    with gr.Blocks(title="RedAlert 控制台", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # RedAlert 控制台
        请输入自然语言指令，我会自动分类并执行相应流程，然后将结果优雅地展示。
        """)

        # 动态任务列表 + 任务选择器 + 详情
        tasks_md = gr.Markdown("(任务列表加载中…)")
        with gr.Row():
            with gr.Column(scale=1):
                task_selector = gr.Dropdown(label="选择任务查看详情", choices=[], value=None, interactive=True)
                refresh_sel_btn = gr.Button("刷新列表", variant="secondary")
            with gr.Column(scale=3):
                task_detail = gr.Markdown("(选择任务查看详情)")

        # 最近一次提交的即时反馈（不再承载全部任务的流式输出，避免跳变）
        with gr.Row():
            current_cmd = gr.Markdown("指令: -")
            status = gr.Markdown("状态: 就绪")
        result_md = gr.Markdown("等待指令…")

        gr.Markdown("---")

        # 输入区始终位于底部
        with gr.Row():
            with gr.Column(scale=4):
                cmd = gr.Textbox(label="指令", placeholder="例如：移动相机到坐标(100, 200)")
            with gr.Column(scale=1):
                run_btn = gr.Button("执行", variant="primary")
        
        # 点击/回车：直接提交任务并清空输入
        def _clear_text() -> str:
            return ""
        run_btn.click(fn=run_graph_command, inputs=cmd, outputs=[current_cmd, status, result_md], show_progress=False)
        run_btn.click(fn=_clear_text, inputs=None, outputs=cmd, show_progress=False)
        cmd.submit(fn=run_graph_command, inputs=cmd, outputs=[current_cmd, status, result_md], show_progress=False)
        cmd.submit(fn=_clear_text, inputs=None, outputs=cmd, show_progress=False)

        # 选择器变化：更新 State 与详情（需在 Timer 使用前定义）
        selected_task_id = gr.State(value=None)
        def _id_passthrough(x):
            return x
        task_selector.change(fn=_id_passthrough, inputs=task_selector, outputs=selected_task_id)
        task_selector.change(fn=show_task_detail, inputs=task_selector, outputs=task_detail)

        # 手动刷新下拉列表 + 页面初次加载填充
        refresh_sel_btn.click(fn=_refresh_selector, inputs=task_selector, outputs=task_selector)
        try:
            demo.load(fn=_refresh_selector, inputs=task_selector, outputs=task_selector)
        except TypeError:
            demo.load(fn=_refresh_selector, inputs=task_selector, outputs=task_selector)

        # 页面加载和轮询：Timer 仅刷新任务列表与详情，不更新下拉，避免影响输入
        timer = None
        try:
            # 优先尝试 interval 参数（较老版本）
            timer = gr.Timer(interval=1.0, active=True)
        except TypeError:
            try:
                # 某些版本使用 every 参数
                timer = gr.Timer(every=1.0, active=True)
            except Exception:
                timer = None

        # 使用 Timer 与 demo.load(every=1) 双通道保障自动刷新
        if timer is not None:
            try:
                # 刷新任务列表 Markdown（无输入）
                timer.tick(fn=_refresh_tasks_ui, outputs=[tasks_md])
                # 刷新选中任务的详情：直接以下拉框当前值为输入，不会改变其值
                timer.tick(fn=show_task_detail, inputs=[task_selector], outputs=[task_detail])
                # 刷新下拉框的 choices，同时尽量保持当前 value 不变
                timer.tick(fn=_refresh_selector, inputs=[task_selector], outputs=[task_selector])
            except TypeError:
                timer.tick(fn=_refresh_tasks_ui, outputs=[tasks_md])
                timer.tick(fn=show_task_detail, inputs=[task_selector], outputs=[task_detail])
                timer.tick(fn=_refresh_selector, inputs=[task_selector], outputs=[task_selector])

        # 始终添加基于 load 的轮询（兼容某些环境 Timer 不触发的情况）
        try:
            demo.load(fn=_refresh_tasks_ui, outputs=[tasks_md], every=1)
            # 仅使用 Timer 来带输入刷新详情与下拉，避免某些版本对 load+inputs+every 的限制
        except TypeError:
            # 某些版本需要 outputs=[...]
            try:
                demo.load(fn=_refresh_tasks_ui, outputs=[tasks_md], every=1)
            except TypeError:
                # 如果不支持every参数，则只在加载时刷新一次
                try:
                    demo.load(fn=_refresh_tasks_ui, outputs=[tasks_md])
                except TypeError:
                    demo.load(fn=_refresh_tasks_ui, outputs=[tasks_md])
    # 允许并发执行，避免一次执行阻塞后续提交（兼容不同 gradio 版本的参数）
    q = demo
    try:
        # 旧版本 gradio（3.x）
        q = demo.queue(concurrency_count=8, max_size=64)
    except TypeError:
        try:
            # 新版本 gradio（4.x）
            q = demo.queue(default_concurrency_limit=8, max_size=64)
        except TypeError:
            # 兜底：启用队列但不设置并发参数
            q = demo.queue()

    # 启动时尽量显示错误与调试信息，若参数不被支持则降级
    try:
        q.launch(show_error=True, debug=True)
    except TypeError:
        try:
            q.launch(debug=True)
        except TypeError:
            q.launch()
