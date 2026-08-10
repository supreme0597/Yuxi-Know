# Sandbox Cookie 路径契约简化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 只通过系统提示词向 Agent 说明 Cookie Header 固定文件路径，移除重复的沙盒环境变量和仅为它服务的 Provisioner 迁移契约。

**Architecture:** 保留后端固定路径常量、运行期文件同步和 `instance_id`。Provider 不再把 Cookie 路径塞进创建沙盒的环境变量；提示词直接给出固定路径。Provisioner 保持实例 ID API，但删除 `runtime-contract-version=cookie-header-file-v1` 的 label/annotation、校验和旧实例重建。

**Tech Stack:** Python 3.12、FastAPI、pytest、ruff、Docker Compose。

## Global Constraints

- Cookie 仍是原始 Header 文件，绝不进入环境变量。
- 系统提示词是 Agent 获取文件路径的唯一说明；路径保持 `/home/gem/.yuxi-runtime/browser-cookie-header.txt`。
- 保留 `instance_id`，用于同一 run 内 idle reaper 重建实例后的重新同步。
- 不改线程级 sandbox 复用、run 退出文件清理、Cookie Redis 生命周期或域名授权策略。
- 不触碰 `Makefile`、`docker/web.Dockerfile` 及其它现有无关改动。

---

### Task 1: 去除 Cookie 路径环境变量并直写提示词路径

**Files:**
- Modify: `backend/package/yuxi/agents/backends/sandbox/provider.py`
- Modify: `backend/package/yuxi/agents/middlewares/sandbox_cookie.py`
- Test: `backend/test/unit/backends/test_sandbox_backends.py`
- Test: `backend/test/unit/middlewares/test_sandbox_cookie_middleware.py`

**Interfaces:**
- Consumes: `load_sandbox_env(uid) -> dict[str, str]`。
- Produces: 创建沙盒的环境变量不包含 `SANDBOX_COOKIE_HEADER_FILE` 或遗留 `SANDBOX_COOKIES_JSON`；仅 `SANDBOX_COOKIE_HEADER_FILE` 常量用于文件同步和提示词。

- [x] **Step 1: 写入红测**

将 Provider 环境断言更新为不含 `SANDBOX_COOKIE_HEADER_FILE`，并为 Cookie 提示词断言直接包含固定路径且不含 `环境变量`、`SANDBOX_COOKIE_HEADER_FILE`。

- [x] **Step 2: 运行红测**

Run: `docker exec api-dev uv run --group test pytest test/unit/backends/test_sandbox_backends.py test/unit/middlewares/test_sandbox_cookie_middleware.py -q`

Expected: 现有代码仍在注入环境变量且提示词仍引用环境变量，测试失败。

- [x] **Step 3: 写最小实现**

删除 `SANDBOX_COOKIE_HEADER_FILE_ENV` 和 `load_sandbox_env()` 中的路径赋值；保留路径常量。把提示词改为“Header 文件固定路径为 `<path>`”，不再引用环境变量。

- [x] **Step 4: 运行绿测**

Run: `docker exec api-dev uv run --group test pytest test/unit/backends/test_sandbox_backends.py test/unit/middlewares/test_sandbox_cookie_middleware.py -q`

Expected: 通过。

### Task 2: 移除仅用于路径环境变量的 Provisioner 契约迁移

**Files:**
- Modify: `docker/sandbox_provisioner/app.py`
- Test: `backend/test/unit/backends/test_sandbox_provisioner_config.py`

**Interfaces:**
- Consumes: Docker container ID、Kubernetes Pod UID。
- Produces: `SandboxResponse.instance_id` 和 `SandboxRecord.instance_id` 不变；Docker label/Kubernetes annotation 不再包含 `runtime-contract-version`，既有实例不会因 Cookie 路径升级而重建。

- [x] **Step 1: 写入红测**

断言新 Docker labels 与 Kubernetes annotations 不包含 `runtime-contract-version`，但 Docker/Kubernetes record 仍返回实例 ID。

- [x] **Step 2: 运行红测**

Run: `docker exec api-dev uv run --group test pytest test/unit/backends/test_sandbox_provisioner_config.py -q`

Expected: 当前 Cookie 契约 label/annotation 使新断言失败。

- [x] **Step 3: 写最小实现**

移除 `SANDBOX_RUNTIME_CONTRACT_VERSION` 及 Docker/Kubernetes 的写入、发现校验和重建分支；不改 `instance_id` 赋值或 API 响应。

- [x] **Step 4: 运行绿测**

Run: `docker exec api-dev uv run --group test pytest test/unit/backends/test_sandbox_provisioner_config.py -q`

Expected: 通过。

### Task 3: 文档、回归与提交

**Files:**
- Modify: `docs/agents/sandbox-architecture.md`
- Modify: `docs/develop-guides/changelog.md`
- Modify: `docs/superpowers/specs/2026-08-10-sandbox-cookie-lifecycle-fixes-design.md`
- Modify: `docs/superpowers/plans/2026-08-07-sandbox-cookie-runtime-file-inheritance.md`
- Create: `docs/superpowers/plans/2026-08-10-sandbox-cookie-path-contract-simplification.md`

- [x] **Step 1: 更新文档**

删除“路径环境变量指针”和 `cookie-header-file-v1` 迁移描述；说明系统提示词直接给出固定路径，`instance_id` 只用于同一 run 内实例重建后的重新同步。

- [x] **Step 2: 运行聚焦回归与静态检查**

Run:

```bash
docker exec api-dev uv run --group test pytest test/unit/backends/test_sandbox_backends.py test/unit/backends/test_sandbox_provisioner_config.py test/unit/middlewares/test_sandbox_cookie_middleware.py test/unit/services/test_run_worker.py test/integration/test_sandbox_runtime_cookie_header_file.py -q
docker exec api-dev uv run --group dev ruff check package/yuxi/agents/backends/sandbox/provider.py package/yuxi/agents/middlewares/sandbox_cookie.py package/yuxi/agents/backends/sandbox/backend.py
git diff --check
```

Expected: 全部通过。

- [x] **Step 3: 创建聚焦提交**

Run:

```bash
git add backend/package/yuxi/agents/backends/sandbox/provider.py backend/package/yuxi/agents/middlewares/sandbox_cookie.py backend/test/unit/backends/test_sandbox_backends.py backend/test/unit/backends/test_sandbox_provisioner_config.py backend/test/unit/middlewares/test_sandbox_cookie_middleware.py docker/sandbox_provisioner/app.py docs/agents/sandbox-architecture.md docs/develop-guides/changelog.md docs/superpowers/specs/2026-08-10-sandbox-cookie-lifecycle-fixes-design.md docs/superpowers/plans/2026-08-07-sandbox-cookie-runtime-file-inheritance.md docs/superpowers/plans/2026-08-10-sandbox-cookie-path-contract-simplification.md
git commit -m "refactor(sandbox): 简化 Cookie 文件路径契约"
```

Expected: 不包含已有无关改动。
