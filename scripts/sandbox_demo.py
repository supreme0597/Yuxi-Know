import asyncio

from src.agents.common.toolkits.buildin.sandbox_tools import (
    bash_tool,
    ls_tool,
    read_file_tool,
    str_replace_tool,
    write_file_tool,
)
from langchain_core.runnables.config import RunnableConfig

def main():
    print("Testing Sandbox Tools locally...")
    
    config = RunnableConfig(
        configurable={"thread_id": "demo_thread_001"}
    )
    
    print("\n--- Testing bash_tool ---")
    result = bash_tool.invoke({"description": "Test bash", "command": "echo 'Hello from Bash Tool!'; pwd", "config": config})
    print(f"Result:\n{result}")

    print("\n--- Testing write_file_tool ---")
    result_write = write_file_tool.invoke({"description": "Test write", "path": "test_script.py", "content": "print('Hello from test_script.py')", "config": config})
    print(f"Result:\n{result_write}")

    print("\n--- Testing ls_tool ---")
    result_ls = ls_tool.invoke({"description": "Test ls", "path": "/", "config": config})
    print(f"Result:\n{result_ls}")

    print("\n--- Testing read_file_tool ---")
    result_read = read_file_tool.invoke({"description": "Test read", "path": "test_script.py", "config": config})
    print(f"Result:\n{result_read}")
    
    print("\n--- Testing bash_tool with python execution ---")
    result_python = bash_tool.invoke({"description": "Test python execution", "command": "python test_script.py", "config": config})
    print(f"Result:\n{result_python}")
    
    print("\n--- Cleaning up (Manual test of Middleware functionality) ---")
    from src.sandbox.provider import get_sandbox_provider
    provider = get_sandbox_provider()
    sandbox = provider.get("demo_thread_001")
    if sandbox:
        print(f"Sandbox demo_thread_001 found. Releasing...")
        provider.release("demo_thread_001")
        print("Done.")

if __name__ == "__main__":
    # Force use of local provider to bypass docker socket when running on raw host
    from src.config.app import config as app_config
    app_config.sandbox_mode = "local"
    
    main()
