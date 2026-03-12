"""ARQ worker entrypoint."""
import asyncio
import sys

# 1. 绝对的最高优先级：接管事件循环
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from src.services.run_worker import WorkerSettings

__all__ = ["WorkerSettings"]
