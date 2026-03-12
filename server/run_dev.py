"""
Windows 本地开发启动脚本

psycopg 异步模式不支持 Windows 默认的 ProactorEventLoop，
必须在 uvicorn 创建事件循环之前切换为 SelectorEventLoop。
使用 `python -m uvicorn` 方式启动时，事件循环在导入应用模块之前
就已创建，因此需要通过此包装脚本提前设置事件循环策略。
"""

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=5050,
        reload=True,
        reload_dirs=["server", "src"],
    )
