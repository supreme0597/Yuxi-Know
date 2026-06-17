# MCP 动态鉴权开发手册

本文面向维护 MCP 运行链路的开发者，说明动态鉴权、内部代理网关、连接池和缓存的职责边界。管理员配置方式见 [MCP 集成](../agents/mcp-integration.md)。

## 设计目标

MCP 动态鉴权解决的是多用户、多部门环境下的 HTTP MCP 调用问题：

- 运行时按 `user_id`、`work_id`、`department_id` 解析鉴权上下文。
- 长期敏感凭据只保存在 `mcp_connections`，不写入 Agent 配置。
- 动态 access token 由服务端获取、缓存、刷新和重试。
- 工具列表和长连接 session 按连接范围隔离，避免跨用户或跨部门复用。
- 动态 HTTP MCP 不把真实上游 token 固化在 MCP tool 对象或长期 client config 中。

## 核心数据

`mcp_servers.auth_config_json` 保存鉴权编排配置，字段模型在 `MCPAuthConfig` 中定义：

| 字段 | 说明 |
|------|------|
| `provider` | 鉴权方式：`bound_secret`、`custom_http_token`、`client_credentials`、`authorization_code`、`stdio_env` 等 |
| `binding_scope` | 连接绑定范围：`inline`、`system`、`department`、`user` |
| `manifest_scope` | 工具清单缓存隔离方式：`server` 或 `binding` |
| `inject` | 把 token、secret 或 context 注入到 headers/env |
| `refresh_policy` | 提前刷新秒数和 401 后是否重试一次 |
| `token_request` | 动态 provider 的 token 获取或刷新请求描述 |

`mcp_connections` 保存长期连接和敏感凭据：

| 字段 | 说明 |
|------|------|
| `server_name` | 所属 MCP server |
| `scope_type` | `system`、`department` 或 `user` |
| `scope_id` | `system` 固定为 `global`，其他范围使用部门 ID 或用户 ID |
| `credential_blob` | 加密后的凭据 JSON 或兼容旧 token 字符串 |
| `status` | `active`、`disabled`、`reauth_required`、`invalid` |

## 连接强制规则

运行时配置解析和内部代理入口必须使用同一套规则：

- `binding_scope=inline` 不需要 `MCPConnection`。
- 非 `inline` 且 `auth_config` 引用了 `${secret.xxx}` 时，必须存在 active `MCPConnection`。
- 非 `inline` 但没有引用 `${secret.xxx}` 时，可以无连接运行，适合只依赖上下文的免密钥 token 网关。

当前统一判断在 `requires_bound_mcp_connection()` 中。新增 provider 或改变模板变量语义时，必须同步检查该规则和回归测试。

## 内部 MCP 鉴权网关

`YUXI_INTERNAL_MCP_PROXY_BASE_URL` 不是普通 HTTP 代理，而是动态 HTTP MCP 的内部鉴权网关地址。Docker 默认值：

```bash
YUXI_INTERNAL_MCP_PROXY_BASE_URL=http://api:5050
```

当 MCP 满足以下条件时，运行时配置会改写到内部网关：

- `transport` 是 `streamable_http` 或 `sse`
- `provider` 是 `custom_http_token`、`client_credentials` 或 `authorization_code`
- `YUXI_INTERNAL_MCP_PROXY_BASE_URL` 非空

改写后的 MCP URL 形如：

```text
http://api:5050/api/internal/mcp-proxy/{server_name}
```

同时会注入短期内部 JWT：

```text
X-Yuxi-MCP-Proxy-Token: <jwt>
```

该 JWT 只承载当前 `server_name`、`user_id`、`department_id` 和 `work_id`，用于代理入口还原上下文。真实上游 access token 仍在代理层按 `auth_config` 获取并注入。

## 调用链

智能体运行时加载 MCP 工具：

```text
RuntimeConfigMiddleware.get_tools_from_context()
  -> get_enabled_mcp_tools()
  -> get_runtime_mcp_server_config()
  -> build_proxy_runtime_config()
  -> get_mcp_tools()
  -> mcp_client_pool.get_session()
  -> MultiServerMCPClient 请求 /api/internal/mcp-proxy/{server_name}
```

管理端工具列表、刷新和连接测试也复用同一链路：

```text
/api/system/mcp-servers/{name}/tools
/api/system/mcp-servers/{name}/tools/refresh
/api/system/mcp-servers/{name}/test
/api/system/mcp-servers/{name}/connections/{connection_id}/test
  -> get_all_mcp_tools() 或 test_mcp_connection()
  -> get_runtime_mcp_server_config()
  -> get_mcp_tools()
```

代理入口内部链路：

```text
proxy_mcp_server_request()
  -> handle_mcp_proxy_request()
  -> decode_proxy_access_token()
  -> 查找 MCPServer 和 active MCPConnection
  -> _proxy_mcp_request_stream()
  -> resolve_runtime_mcp_config()
  -> 获取或刷新真实 access token
  -> 注入上游 headers/env
  -> httpx stream 转发到真实 MCP
```

## 关键文件

| 文件 | 职责 |
|------|------|
| `backend/package/yuxi/services/mcp_auth/config_models.py` | `auth_config` Pydantic 模型和 `${secret.xxx}` 提取 |
| `backend/package/yuxi/services/mcp_auth/orchestrator.py` | 模板解析、credential 解密、token 获取、token 缓存读写、最终 runtime config 注入 |
| `backend/package/yuxi/services/mcp_auth/proxy_service.py` | 内部代理 URL 改写、短期 JWT、代理入口、HTTP/SSE 转发、401 重试 |
| `backend/package/yuxi/services/mcp/connection_service.py` | MCP connection CRUD、scope 解析、连接测试上下文 |
| `backend/package/yuxi/services/mcp/server_service.py` | MCP server CRUD、runtime config 解析、内部代理触发 |
| `backend/package/yuxi/services/mcp/tool_registry_service.py` | 工具加载、manifest 缓存、工具对象缓存策略 |
| `backend/package/yuxi/services/mcp/client_pool.py` | 长连接 MCP session 池和动态请求头注入 |
| `backend/package/yuxi/services/mcp/cache_policy.py` | 静态、绑定凭据、动态代理的缓存隔离策略 |
| `backend/server/routers/mcp_internal_router.py` | `/api/internal/mcp-proxy/*` 路由层入口 |

## 缓存和连接池

动态 MCP 涉及三类缓存：

- access token 缓存：由 `RedisTokenCache` 按 connection 缓存，支持提前刷新和刷新锁。
- tool manifest 缓存：由 `RedisMcpToolCache` 按 server 或 connection 分区缓存。
- 长连接 session 池：由 `MCPClientPool` 按 `(server_name, partition_key)` 复用。

`MCPClientPool._calculate_config_hash()` 必须忽略会变化的临时 token header，包括：

- `Authorization`
- `X-Yuxi-MCP-Proxy-Token`

否则同一个动态 HTTP MCP 会因为短期代理 JWT 变化被误判为配置变更，导致 session 频繁重建。

## 上下文约定

`AuthContext` 包含：

| 字段 | 来源 |
|------|------|
| `user_id` | Yuxi 数据库用户 ID |
| `work_id` | 用户登录 ID 或工号 |
| `department_id` | 当前用户部门 ID |

Agent 运行态由 `chat_service` 写入 context，管理端接口由 `mcp_router._auth_context_from_user()` 构造。连接测试没有完整用户对象，user scope 下使用 connection 的 `scope_id` 同时作为 `user_id` 和 `work_id` 来模拟运行态。

## Provider 维护约束

新增动态 provider 时需要同时考虑：

1. `MCPAuthConfig.provider` 枚举。
2. `TokenFetcherFactory` 的分发。
3. 是否属于 `_DYNAMIC_HTTP_PROVIDERS`，即是否需要走内部代理。
4. `CachePolicyFactory` 的缓存隔离策略。
5. 前端 `McpAuthConfigBuilder` 是否需要向导支持。
6. 单元测试覆盖 runtime config、代理入口、token 获取、缓存失效和连接测试。

如果 provider 会请求上游 token 接口，`token_request.response_map` 应映射到标准字段：

```json
{
  "access_token": "data.access_token",
  "refresh_token": "data.refresh_token",
  "expires_in": "data.expires_in",
  "expires_at": "data.expires_at",
  "scope": "data.scope",
  "token_type": "data.token_type"
}
```

至少需要能解析出 `access_token`。`expires_in` 或 `expires_at` 用于预刷新判断。

## 测试要求

修改 MCP 动态鉴权链路时，至少补充或运行相关单元测试：

```bash
docker exec api-dev uv run --group test pytest \
  test/unit/services/test_mcp_auth_runtime.py \
  test/unit/services/test_mcp_auth_proxy_service.py \
  test/unit/services/test_mcp_client_pool.py \
  test/unit/services/test_mcp_connection_service.py -q
```

涉及管理端接口时补跑 router 或 e2e 测试；涉及前端向导时补跑前端 lint，并手动验证生成的 `auth_config` JSON。

重点回归场景：

- no-secret 动态 HTTP MCP 在代理模式下无 active connection 也能运行。
- 引用了 `${secret.xxx}` 的非 `inline` 配置缺少 active connection 时必须失败。
- user scope 连接测试会带上 `work_id`。
- 代理 JWT 变化不会改变 MCP client pool config hash。
- 401 且 `retry_once_on_401=true` 时会清理 token 缓存并重试一次。

## 排障

| 现象 | 检查方向 |
|------|----------|
| 工具列表 403 | 检查 `binding_scope`、当前用户/部门、是否引用 `${secret.xxx}`、是否存在 active connection |
| 工具调用 424 `reauth_required` | 上游 MCP 或 token 接口持续返回 401，需要更新连接凭据或 refresh token |
| 工具列表跨用户不一致 | 检查 `manifest_scope`、cache partition 和 connection id |
| HTTP MCP 频繁重连 | 检查 config hash 是否包含临时 token header |
| 免密钥配置仍要求连接 | 确认 `auth_config` 中没有 `${secret.xxx}`，并确认代理入口复用 `requires_bound_mcp_connection()` |
| Docker 内请求内部代理失败 | 检查 `YUXI_INTERNAL_MCP_PROXY_BASE_URL` 是否指向容器网络中的 API 地址，默认应为 `http://api:5050` |
