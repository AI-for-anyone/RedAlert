# PowerShell script to start MCP servers
Write-Host "Starting MCP Servers..." -ForegroundColor Green

# Activate virtual environment
if (Test-Path ".venv\Scripts\Activate.ps1") {
    & ".venv\Scripts\Activate.ps1"
} elseif (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
} else {
    Write-Host "Virtual environment not found, continuing without activation..." -ForegroundColor Red
}

# Start all MCP servers in background
Write-Host "Starting Produce MCP Server..." -ForegroundColor Yellow
Start-Process -FilePath "python" -ArgumentList "mcp_tools\produce_mcp_server.py" -WindowStyle Minimized

Write-Host "Starting Unit MCP Server..." -ForegroundColor Yellow
Start-Process -FilePath "python" -ArgumentList "mcp_tools\unit_mcp_server.py" -WindowStyle Minimized

Write-Host "Starting Info MCP Server..." -ForegroundColor Yellow
Start-Process -FilePath "python" -ArgumentList "mcp_tools\info_mcp_server.py" -WindowStyle Minimized

Write-Host "Starting Camera MCP Server..." -ForegroundColor Yellow
Start-Process -FilePath "python" -ArgumentList "mcp_tools\camera_mcp_server.py" -WindowStyle Minimized

Write-Host "Starting Fight MCP Server..." -ForegroundColor Yellow
Start-Process -FilePath "python" -ArgumentList "mcp_tools\fight_mcp_server.py" -WindowStyle Minimized

Write-Host "All MCP servers started successfully!" -ForegroundColor Green
Write-Host "Press any key to exit..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
