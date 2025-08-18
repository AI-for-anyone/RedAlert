#!/bin/bash
source .venv/bin/activate
python mcp_tools/produce_mcp_server.py &
python mcp_tools/unit_mcp_server.py &
python mcp_tools/info_mcp_server.py &
python mcp_tools/camera_mcp_server.py &
python mcp_tools/fight_mcp_server.py &
