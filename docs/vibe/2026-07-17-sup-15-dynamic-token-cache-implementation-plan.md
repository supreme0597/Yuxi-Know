# SUP-15 Dynamic Token and Cache Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add dynamic MCP token providers, connection-scoped Redis token/manifest caches, refresh singleflight, and precise cache invalidation without implementing the PR5 proxy or client pool.

**Architecture:** Token lifecycle is isolated in `mcp_auth/token_service.py`; cache decisions live in `mcp/cache_policy.py`; Redis manifest/revision storage lives in `mcp/manifest_cache.py`. The orchestrator returns resolved runtime configuration plus a non-secret cache identity, while the tool registry uses partitioned keys and lazy manifest-backed tools for dynamic providers.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, httpx, redis.asyncio, LangChain MCP adapters, pytest/pytest-asyncio.

---

### Task 1: Validate dynamic auth configuration

**Files:**
- Modify: `backend/package/yuxi/services/mcp_auth/config_models.py`
- Test: `backend/test/unit/services/test_mcp_auth_config_models.py`

- [ ] Add failing tests for non-negative `pre_refresh_seconds`, required dynamic `token_request`, and `authorization_code` refresh-only configuration.
- [ ] Run `docker compose exec api uv run --group test pytest test/unit/services/test_mcp_auth_config_models.py -q`; expect the new validation tests to fail.
- [ ] Add typed request/response-map models only where they remove ambiguous dictionary access; keep the persisted JSON shape backward compatible.
- [ ] Re-run the focused test and confirm it passes.

### Task 2: Implement Redis token cache and provider fetching

**Files:**
- Create: `backend/package/yuxi/services/mcp_auth/token_service.py`
- Test: `backend/test/unit/services/test_mcp_auth_token_service.py`

- [ ] Add failing tests proving token cache keys contain only `connection_id`, TTL derives from `expires_at`/`expires_in`, valid tokens bypass refresh, expiring tokens refresh, and Redis failure falls back to request-local fetching.
- [ ] Add a 10-request concurrency test whose fake token endpoint is invoked once.
- [ ] Run the focused test; expect import/behavior failures.
- [ ] Implement `RedisTokenCache`, normalized absolute expiry, custom HTTP form/JSON requests, client credentials, refresh-token flow, authorization-code refresh-only rejection, and ownership-safe Redis lock release using a random lock value plus compare-and-delete.
- [ ] Re-run the focused test and confirm all cases pass.

### Task 3: Define cache policy and manifest storage

**Files:**
- Create: `backend/package/yuxi/services/mcp/cache_policy.py`
- Create: `backend/package/yuxi/services/mcp/manifest_cache.py`
- Test: `backend/test/unit/services/test_mcp_cache_policy.py`
- Test: `backend/test/unit/services/test_mcp_manifest_cache.py`

- [ ] Add failing policy tests for global static sharing, connection partitioning of bound credentials, department/user isolation, and disabled Tool-object caching for dynamic providers.
- [ ] Add failing manifest tests for revision round-trip, connection-scoped keys, sanitized serialized fields, Redis outage fallback, and server/partition invalidation.
- [ ] Run both test files and confirm they fail for missing modules.
- [ ] Implement immutable `MCPCachePolicy`/`MCPCacheIdentity` values and a Redis manifest store that never accepts runtime headers/env/token fields.
- [ ] Re-run both test files and confirm they pass.

### Task 4: Resolve dynamic runtime auth and cache identity

**Files:**
- Modify: `backend/package/yuxi/services/mcp_auth/orchestrator.py`
- Modify: `backend/package/yuxi/services/mcp_auth/__init__.py`
- Test: `backend/test/unit/services/test_mcp_auth_orchestrator.py`

- [ ] Add failing tests for custom HTTP token injection, client credentials, cached-token reuse, authorization-code missing refresh token marking `reauth_required`, and returned partition `connection:{id}`.
- [ ] Add tests proving missing bound connection remains a clear error and source server config is not mutated.
- [ ] Run the focused orchestrator test and confirm the new cases fail.
- [ ] Extend runtime resolution to return a `ResolvedMCPRuntime` carrying sanitized cache identity while preserving the existing `resolve_runtime_mcp_config()` dictionary API for callers.
- [ ] Inject tokens only after resolving the exact active connection and never include injected secrets in the cache hash payload.
- [ ] Re-run orchestrator/config/token tests and confirm they pass.

### Task 5: Partition Tool cache and consume manifest lazily

**Files:**
- Modify: `backend/package/yuxi/services/mcp/tool_registry_service.py`
- Modify: `backend/package/yuxi/services/mcp/__init__.py`
- Test: `backend/test/unit/services/test_mcp_tool_registry_auth_cache.py`
- Test: `backend/test/unit/services/test_mcp_service.py`

- [ ] Add failing tests proving different connection partitions never share Tool objects, dynamic providers never write `_mcp_tools_cache`, and a manifest hit returns tools without discovery connection.
- [ ] Add a failing lazy-call test proving the manifest-backed tool resolves current runtime auth and invokes the same named upstream tool.
- [ ] Run focused registry tests and confirm the new cases fail.
- [ ] Build cache keys from server, partition, revisions and sanitized config hash; replace per-server locks with per-cache-key locks.
- [ ] Serialize only name/id/description/JSON schema. On dynamic manifest hit, construct a LangChain-compatible lazy tool whose coroutine reconnects on invocation and calls the named upstream tool with current auth.
- [ ] Re-run registry tests and confirm they pass.

### Task 6: Wire precise invalidation

**Files:**
- Modify: `backend/package/yuxi/services/mcp/server_service.py`
- Modify: `backend/package/yuxi/services/mcp/connection_service.py`
- Test: `backend/test/unit/services/test_mcp_connection_service.py`
- Test: `backend/test/unit/services/test_mcp_service.py`

- [ ] Add failing tests proving server update/status/delete bumps server revision and connection update/status/delete clears token cache plus bumps `connection:{id}` revision.
- [ ] Run focused tests and confirm invalidation assertions fail.
- [ ] Add async invalidation entry points and invoke them only after successful database commits; preserve existing synchronous local-cache clearing behavior.
- [ ] Re-run focused tests and confirm they pass.

### Task 7: Verify router context and preload behavior

**Files:**
- Modify only if needed: `backend/server/routers/mcp_router.py`
- Test: `backend/test/unit/routers/test_mcp_router.py`
- Test: `backend/test/unit/services/test_mcp_service.py`

- [ ] Add/extend tests proving test/tools/refresh endpoints pass `AuthContext.from_current_user(current_user)` and global preload skips bound and dynamic runtime auth.
- [ ] Run focused router/preload tests and observe failures if any contract is missing.
- [ ] Make the minimum wiring changes needed; do not add frontend or OAuth callback endpoints.
- [ ] Re-run the focused tests and confirm they pass.

### Task 8: Documentation and full verification

**Files:**
- Modify: `docs/develop-guides/roadmap.md`

- [ ] Update the existing MCP 0.6.3 roadmap bullet to include dynamic token providers, refresh singleflight, and connection-partitioned Tool/manifest caches.
- [ ] Run targeted formatting/lint for touched files inside Docker.
- [ ] Run all MCP unit tests: `docker compose exec api uv run --group test pytest test/unit/services/test_mcp_* test/unit/routers/test_mcp_router.py test/unit/agents/test_mcp_auth_context_middlewares.py -q`.
- [ ] Run relevant integration tests under `backend/test/integration/api` and an MCP runtime smoke test against the running containers.
- [ ] Run `git diff --check` and review that no token, secret, or unrelated user changes are staged.
- [ ] Commit implementation using Chinese Conventional Commit messages; do not push any remote without coordinator approval.
