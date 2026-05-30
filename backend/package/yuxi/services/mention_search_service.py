from __future__ import annotations

import asyncio
import base64
import os
from pathlib import Path

import ormsgpack
from yuxi.agents.backends.sandbox.paths import (
    sandbox_outputs_dir,
    sandbox_uploads_dir,
    sandbox_workspace_dir,
)
from yuxi.config.app import config
from yuxi.services.run_queue_service import get_redis_client
from yuxi.utils.logging_config import logger

MENTION_EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".idea",
    ".vscode",
    "dist",
    "build",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}

MAX_MENTION_RESULTS = 50
MAX_ENTRIES_PER_DIR = 500
MAX_SEARCH_DEPTH = 15
CACHE_TTL = 60  # 缓存有效期 60 秒
MAX_CACHED_ENTRIES = 100000
REDIS_KEY_PREFIX = "yuxi:mention:cache:"


def _scan_pruned_files(root: Path, max_entries: int) -> list[tuple[str, str]]:
    """
    同步扫描磁盘文件目录并进行多重限额剪枝保护 (防止大文件仓库卡死)
    """
    results: list[tuple[str, str]] = []
    if not root.exists():
        return results

    root_str = str(root)
    for dirpath, dirnames, filenames in os.walk(root_str):
        # 1. 剪枝黑名单和隐藏目录 (直接在 dirnames 中修改，阻止 os.walk 深入)
        dirnames[:] = [d for d in dirnames if d not in MENTION_EXCLUDE_DIRS and not d.startswith(".")]

        # 2. 深度保护：限制最大搜索深度（root 本身为第 0 层，第 15 层时 rel.parts 长度恰好为 15）
        try:
            rel = Path(dirpath).relative_to(root)
            if len(rel.parts) >= MAX_SEARCH_DEPTH:
                dirnames.clear()
                continue
        except Exception:
            pass

        # 3. 宽度与全局限额保护下的合格“子目录实体”收集
        for dirname in dirnames:
            full_dir_path = Path(dirpath) / dirname
            rel_dir_path = full_dir_path.relative_to(root).as_posix()

            # 使用以 '/' 结尾的虚拟相对路径，代表这是一个目录
            virtual_dir_path = f"{rel_dir_path}/"
            results.append((dirname, virtual_dir_path))

            if len(results) >= max_entries:
                return results

        # 4. 宽度限额保护：单层目录限制最多只读取 500 个文件，防止扁平超宽目录卡死
        scan_filenames = filenames[:MAX_ENTRIES_PER_DIR]
        for filename in scan_filenames:
            full_path = Path(dirpath) / filename
            # 计算相对于根路径的相对路径
            rel_path = full_path.relative_to(root).as_posix()

            # 存为紧凑型元组 (filename, relative_path)
            results.append((filename, rel_path))

            # 5. 全局上限保护：如果总文件数已达上限，熔断退出
            if len(results) >= max_entries:
                return results

    return results


async def get_or_build_file_index(
    thread_id: str,
    user_id: str,
) -> list[tuple[str, str]]:
    """
    获取或构建当前 Workspace 和 Thread 的提及文件索引缓存 (使用 ormsgpack 二进制序列化)
    """
    redis = await get_redis_client()
    redis_key = f"{REDIS_KEY_PREFIX}{thread_id}"

    # NOTE: 项目全局 Redis 客户端配置了 decode_responses=True，
    # 为了在上面安全地存储 ormsgpack 产生的二进制 bytes，
    # 我们使用极速且无损的 latin1 (ISO-8859-1) 进行单字节字符互转。
    # 这在 Python 底层由 C 引擎执行，体积完全不膨胀，速度极快，且不需要新建不带 decode 限制的 Redis 连接。
    cached_str = await redis.get(redis_key)
    if cached_str:
        try:
            # NOTE: decode_responses=True 的 Redis 客户端只能存 str，
            # 使用 base64 对 ormsgpack 的二进制输出进行无损编码后存储。
            packed_bytes = base64.b64decode(cached_str)
            return ormsgpack.unpackb(packed_bytes)
        except Exception as e:
            logger.warning(f"Failed to unpack mention cache for thread {thread_id}: {e}")

    # 缓存未命中，在 asyncio.to_thread 线程池中执行阻塞的 os.walk 磁盘扫描
    roots_with_prefixes = [
        ("workspace", sandbox_workspace_dir(thread_id, user_id)),
        ("uploads", sandbox_uploads_dir(thread_id)),
        ("outputs", sandbox_outputs_dir(thread_id)),
    ]

    entries: list[tuple[str, str]] = []
    for prefix, root in roots_with_prefixes:
        needed = MAX_CACHED_ENTRIES - len(entries)
        if needed <= 0:
            break

        # 使用 to_thread 避免 os.walk 阻塞 FastAPI 事件循环
        scan_results = await asyncio.to_thread(_scan_pruned_files, root, needed)

        # 加上虚拟文件系统前缀，例如 "workspace/src/main.py"
        for name, rel_path in scan_results:
            virtual_rel_path = f"{prefix}/{rel_path}" if rel_path and rel_path != "." else prefix
            entries.append((name, virtual_rel_path))

    # 写入 Redis 缓存
    try:
        packed_bytes = ormsgpack.packb(entries)
        packed_str = base64.b64encode(packed_bytes).decode("ascii")
        await redis.set(redis_key, packed_str, ex=CACHE_TTL)
    except Exception as e:
        logger.warning(f"Failed to write mention cache for thread {thread_id}: {e}")

    return entries


async def search_mention_files_in_index(
    thread_id: str,
    user_id: str,
    query: str,
) -> list[dict]:
    """
    高效的基于文件名/目录名权重与排序的模糊搜索算法 (彻底消除纯路径抢占，置顶核心匹配项)
    """
    index = await get_or_build_file_index(thread_id, user_id)
    if not index:
        return []

    # NOTE: query 为空时不执行搜索，避免空字符串匹配所有条目（空串是任何字符串的子串）
    if not query:
        return []

    query_lower = query.lower()

    prefix = (config.sandbox_virtual_path_prefix or "/home/gem/user-data").rstrip("/")

    # 存储加权匹配结果
    name_matched = []  # 文件名/目录名直接匹配的项 (高分)
    path_matched = []  # 仅路径匹配的项 (低分，作为兜底)

    for name, virtual_path in index:
        name_lower = name.lower()
        path_lower = virtual_path.lower()
        is_dir = virtual_path.endswith("/")

        # 1. 优先判定名称是否包含关键字 (置顶)
        if query_lower in name_lower:
            if name_lower == query_lower:
                score = 1000.0  # 完全匹配
            else:
                score = 500.0  # 基础名称匹配分

                # 附加前缀优势
                if name_lower.startswith(query_lower):
                    score += 50.0

                # 附加后缀优势
                if name_lower.endswith(query_lower):
                    score += 20.0

                # 位置惩罚：匹配位置越靠后，给与轻微扣分 (最高扣 30 分)
                start_idx = name_lower.find(query_lower)
                if start_idx != -1:
                    score -= min(start_idx, 30.0)

                # 长度惩罚：文件名越长，扣分越多 (最高扣 50 分，以优先展示简短、高信息密度的核心文件)
                score -= min(len(name) * 0.5, 50.0)

            name_matched.append({"name": name, "path": f"{prefix}/{virtual_path}", "is_dir": is_dir, "score": score})

        # 2. 其次判定是否为纯路径匹配 (名称不匹配，但路径中包含)
        elif query_lower in path_lower:
            score = 10.0
            # 路径长度惩罚
            score -= min(len(virtual_path) * 0.1, 5.0)
            path_matched.append(
                {
                    "name": name,
                    "path": f"{prefix}/{virtual_path}",
                    "is_dir": is_dir,
                    "score": score,
                }
            )

    # 对名称直接匹配项按照打分降序进行精准排序 (打分已融合位置与长度惩罚)
    name_matched.sort(key=lambda x: -x["score"])

    # 智能融合：如果名称匹配项不足 MAX_MENTION_RESULTS，用路径匹配项兜底填补
    merged_results = name_matched
    if len(merged_results) < MAX_MENTION_RESULTS:
        # 对路径匹配项按路径长度进行升序排序 (通常短路径更直观)
        path_matched.sort(key=lambda x: len(x["path"]))
        needed = MAX_MENTION_RESULTS - len(merged_results)
        merged_results.extend(path_matched[:needed])

    # 截取前 MAX_MENTION_RESULTS 项并还原为前端格式，附加 is_dir 属性以识别目录
    return [
        {"name": item["name"], "path": item["path"], "is_dir": item["is_dir"]}
        for item in merged_results[:MAX_MENTION_RESULTS]
    ]


async def invalidate_mention_cache(thread_id: str) -> None:
    """
    轻量级缓存清理工具函数，主动清除指定 thread 的提及缓存
    """
    try:
        redis = await get_redis_client()
        redis_key = f"{REDIS_KEY_PREFIX}{thread_id}"
        await redis.delete(redis_key)
    except Exception as e:
        logger.warning(f"Failed to invalidate mention cache for thread {thread_id}: {e}")
