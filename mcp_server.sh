#!/usr/bin/env bash
set -euo pipefail

# Project root
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Ensure we always use the project's .venv (per user rule)
VENV_PY="$BASE_DIR/.venv/bin/python"
LOG_DIR="$BASE_DIR/logs/mcp_servers"
PID_FILE="$BASE_DIR/.mcp_servers.pids"

# Name:relative_script_path
SERVERS=(
  "produce:mcp_tools/produce_mcp_server.py"
  "unit:mcp_tools/unit_mcp_server.py"
  "info:mcp_tools/info_mcp_server.py"
  "camera:mcp_tools/camera_mcp_server.py"
  "fight:mcp_tools/fight_mcp_server.py"
)

ensure_venv() {
  if [[ ! -x "$VENV_PY" ]]; then
    echo "Error: .venv not found or Python not executable at: $VENV_PY" >&2
    echo "Create it and install requirements, e.g.:" >&2
    echo "  python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt" >&2
    exit 1
  fi
}

start_servers() {
  ensure_venv
  mkdir -p "$LOG_DIR"
  : > "$PID_FILE"

  local started=0
  for entry in "${SERVERS[@]}"; do
    local name="${entry%%:*}"
    local script_rel="${entry#*:}"
    local script="$BASE_DIR/$script_rel"

    if pgrep -f "$script" >/dev/null 2>&1; then
      echo "[$name] already running"
      continue
    fi

    nohup "$VENV_PY" "$script" >"$LOG_DIR/$name.out.log" 2>"$LOG_DIR/$name.err.log" &
    local pid=$!
    echo "$name:$pid" >> "$PID_FILE"
    echo "Started [$name] (pid $pid)"
    started=$((started + 1))
  done

  if (( started == 0 )); then
    echo "No servers started (all already running)."
  else
    echo "Logs: $LOG_DIR"
  fi
}

stop_servers() {
  local stopped_any=0

  # Try PID file first
  if [[ -f "$PID_FILE" ]]; then
    while IFS=: read -r name pid; do
      [[ -z "${pid:-}" ]] && continue
      if kill -0 "$pid" >/dev/null 2>&1; then
        kill "$pid" 2>/dev/null || true
        sleep 0.5
        if kill -0 "$pid" >/dev/null 2>&1; then
          kill -9 "$pid" 2>/dev/null || true
        fi
        echo "Stopped [$name] (pid $pid)"
        stopped_any=1
      fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
  fi

  # Ensure no stragglers by matching script path
  for entry in "${SERVERS[@]}"; do
    local name="${entry%%:*}"
    local script="$BASE_DIR/${entry#*:}"
    local pids
    pids=$(pgrep -f "$script" || true)
    if [[ -n "${pids:-}" ]]; then
      for pid in $pids; do
        kill "$pid" 2>/dev/null || true
        sleep 0.2
        kill -9 "$pid" 2>/dev/null || true
        echo "Killed stray [$name] (pid $pid)"
        stopped_any=1
      done
    fi
  done

  if [[ "$stopped_any" -eq 0 ]]; then
    echo "No servers were running."
  fi
}

usage() {
  cat <<EOF
Usage: $(basename "$0") {start|stop|restart}
  start   Start all MCP servers using .venv
  stop    Stop all MCP servers
  restart Stop then start
EOF
}

case "${1:-}" in
  start)
    start_servers
    ;;
  stop)
    stop_servers
    ;;
  restart)
    stop_servers
    start_servers
    ;;
  *)
    usage
    exit 1
    ;;
esac
