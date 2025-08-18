#!/usr/bin/env python3
"""
配置验证脚本
用于验证RedAlert项目的配置是否正确
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config.config import config, get_mcp_server_status, check_mcp_servers
from logs import get_logger

logger = get_logger("validate_config")

def main():
    """主函数"""
    print("🔍 验证 RedAlert 配置...")
    
    # 1. 基础配置验证
    print("\n📋 基础配置验证:")
    errors = config.validate_config()
    if errors:
        print("❌ 发现配置错误:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ 基础配置验证通过")
    
    # 2. LLM配置
    print("\n🤖 LLM 配置:")
    for workflow_type, llm_config in config.llm_configs.items():
        api_key_status = "✅ 已配置" if llm_config.api_key else "❌ 未配置"
        print(f"  {workflow_type.value:15} | {llm_config.model:20} | temp={llm_config.temperature:3.1f} | {api_key_status}")
    
    # 3. MCP服务器连接测试
    print("\n🔗 MCP 服务器连接测试:")
    server_status = get_mcp_server_status()
    
    all_online = True
    for name, status in server_status.items():
        status_icon = "✅" if status["online"] else "❌"
        print(f"  {name:8} | {status['url']:25} | {status['description']:20} | {status_icon}")
        if not status["online"]:
            all_online = False
    
    if all_online:
        print("✅ 所有MCP服务器在线")
    else:
        print("⚠️  部分MCP服务器离线，请检查服务器状态")
    
    # 4. 提示词文件检查
    print("\n📄 提示词文件检查:")
    for workflow_type, prompt_config in config.prompt_configs.items():
        file_exists = prompt_config.file_path.exists()
        status_icon = "✅" if file_exists else "❌"
        print(f"  {workflow_type.value:15} | {str(prompt_config.file_path):50} | {status_icon}")
    
    # 5. 项目结构检查
    print("\n📁 项目结构检查:")
    required_dirs = ["graph", "mcp_tools", "config", "prompt", "logs"]
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        exists = dir_path.exists() and dir_path.is_dir()
        status_icon = "✅" if exists else "❌"
        print(f"  {dir_name:15} | {status_icon}")
    
    # 6. MCP工具文件检查
    print("\n🔧 MCP 工具文件检查:")
    mcp_files = [
        "camera_mcp_server.py",
        "fight_mcp_server.py", 
        "info_mcp_server.py",
        "produce_mcp_server.py",
        "unit_mcp_server.py"
    ]
    
    for mcp_file in mcp_files:
        file_path = Path("mcp_tools") / mcp_file
        exists = file_path.exists()
        status_icon = "✅" if exists else "❌"
        print(f"  {mcp_file:25} | {status_icon}")
    
    # 总结
    print("\n" + "="*60)
    
    offline_servers = check_mcp_servers()
    missing_prompts = [wt.value for wt, pc in config.prompt_configs.items() if not pc.file_path.exists()]
    missing_api_keys = [wt.value for wt, llm in config.llm_configs.items() if not llm.api_key]
    
    issues = len(errors) + len(offline_servers) + len(missing_prompts) + len(missing_api_keys)
    
    if issues == 0:
        print("🎉 所有配置验证通过！系统可以正常运行。")
        return True
    else:
        print(f"⚠️  发现 {issues} 个问题需要解决:")
        
        if errors:
            print(f"  - {len(errors)} 个基础配置错误")
        if offline_servers:
            print(f"  - {len(offline_servers)} 个MCP服务器离线")
        if missing_prompts:
            print(f"  - {len(missing_prompts)} 个提示词文件缺失")
        if missing_api_keys:
            print(f"  - {len(missing_api_keys)} 个API Key未配置")
            
        print("\n请解决这些问题后重新运行验证。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)