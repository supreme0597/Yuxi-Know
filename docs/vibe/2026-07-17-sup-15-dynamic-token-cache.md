# SUP-15 动态 Token 与 MCP 缓存隔离设计

## 背景与目标

本次在 PR3 已支持 `bound_secret` / `stdio_env` 运行时注入的基础上，实现 PR4：

- 支持 `custom_http_token`、`client_credentials`，以及已有 `refresh_token` 的 `authorization_code` 后台刷新。
- access token 仅按 `connection_id` 缓存，并使用 Redis lock 保证同一连接并发刷新单飞。
- 明确静态、绑定凭据、动态 token 三类 MCP 缓存策略，避免不同用户、部门和 connection 复用错误 Tool。
- Redis 缓存脱敏 tool manifest，并按 server、partition、revision、config hash 隔离。
- server/connection 变更时精准失效相关 token、Tool 和 manifest 缓存。
- 无 `AuthContext` 的全局预热跳过所有需要运行时鉴权的 MCP；管理端测试/工具接口使用当前管理员身份。

不包含内部 proxy streaming、长连接池、proxy 401 retry、完整 OAuth authorization URL/callback/state/PKCE/consent，也不包含前端改动。

## 设计选择

采用“token 服务、缓存策略、tool registry 组合”的实现：

1. `mcp_auth/token_service.py` 负责 token 请求、过期判断、Redis token cache 和 refresh singleflight。
2. `mcp/cache_policy.py` 根据 provider、scope 和已解析 connection 生成 `cache_partition`，并决定是否允许缓存 Tool 对象。
3. `mcp/manifest_cache.py` 只存脱敏工具定义、revision 和 manifest，不存 header、env、secret、access token 或 refresh token。
4. `mcp_auth/orchestrator.py` 负责查找当前连接、调用 token 服务、注入 headers/env，并返回运行时配置及缓存身份。
5. `mcp/tool_registry_service.py` 使用缓存身份构建 `server_name:partition:revision:config_hash` key。动态 provider 不缓存包含短期 token 的 Tool 实例；manifest 命中时创建按调用懒连接的工具包装，加载阶段不重新发现 MCP 工具。

该方案避免把 token 生命周期塞进路由或 registry，同时不引入 PR5 的 client pool/proxy 架构。

## Token 生命周期

- 连接密文沿用 PR2 的结构：`{"secrets": {...}, "token": {...}}`；兼容顶层已有 token 字段。
- Redis key 仅由 `connection_id` 派生。
- token 的有效期优先读取 `expires_at`，其次读取 `expires_in`；写入 cache 时保存绝对 `expires_at`，Redis TTL 与其剩余寿命一致。
- 当剩余寿命不大于 `pre_refresh_seconds` 时进入刷新路径。
- 同一 connection 使用 Redis `SET NX EX` lock。未拿到锁的请求轮询 token cache，获取刷新后的 token；等待超时后仅执行本请求的本地加载，不写入跨用户共享缓存。
- Redis 不可用时记录脱敏告警，并退化为本请求内获取 token；不会使用 server/user/work 等其他维度替代 connection key。
- `authorization_code` 必须已有 `refresh_token`；缺失时将连接标记 `reauth_required` 并返回明确错误，不构造 OAuth callback。

## MCP 缓存策略

| 类型 | partition | Tool 对象缓存 | manifest 缓存 |
| --- | --- | --- | --- |
| 无 auth / inline legacy | `global` | 允许全局共享 | 允许 |
| `bound_secret` / `stdio_env` system | `connection:{id}` | 允许同 connection 共享 | 允许 |
| `bound_secret` / `stdio_env` department/user | `connection:{id}` | 仅该 connection 分区 | 允许 |
| 动态 token provider | `connection:{id}` | 禁止 | 允许 |

缓存 key 包含 `server_name + cache_partition + server_revision + partition_revision + config_hash`。`config_hash` 基于脱敏的服务配置与 auth 配置计算，不包含运行时 token、secret、注入后的敏感 headers/env。

动态 provider 的 manifest 命中后，registry 创建懒调用工具：工具加载阶段不连接 MCP；真正调用工具时重新解析当前 connection/token、连接 MCP、查找同名工具并执行。因此短期 token 不进入长期 Tool 对象，同时 manifest 仍能避免重复 discovery。

## 失效与错误处理

- MCP server 更新、启停、删除：递增 server revision，并清理该 server 的本地 Tool cache。
- MCP connection 更新、停用、删除：删除该 `connection_id` 的 token cache，递增该 connection partition revision，并清理对应本地 Tool cache。
- 缺少 AuthContext、绑定 connection 或有效 refresh token 时返回 `RuntimeMCPAuthError`，不回退到全局凭据。
- token endpoint 错误仅记录 provider、server/connection 和异常类型，不记录请求 body、响应 body、token 或 secret。
- PR4 不根据最终 MCP 401 修改连接状态；该闭环由 PR5 处理。仅 `authorization_code` 本身缺失 refresh token 时标记 `reauth_required`。

## 验收与测试

- token 即将过期时会刷新；有效 token 直接命中 cache。
- 同 connection 10 个并发请求仅触发一次 token 请求。
- 两个 connection 指向同一 server 时 Tool/manifest 不串用。
- 动态 provider 不写入本地 Tool 对象 cache。
- manifest 命中时加载工具不重新连接 MCP，调用时使用当前 connection/token。
- Redis 不可用时请求仍可本地获取 token，且不会跨身份共享。
- bound auth 缺 connection、authorization_code 缺 refresh token时返回明确错误。
- 无 AuthContext 的全局预热跳过运行时鉴权 MCP。
- 管理端 server test/tools endpoint 将当前管理员转换为 `AuthContext`。
- connection/server 更新、停用和删除触发对应 token、Tool、manifest 失效。

## Checklist

- [ ] Token provider、TTL、Redis cache 与 singleflight
- [ ] Cache policy、partition、revision 和 manifest
- [ ] Orchestrator 动态 token 注入与缓存身份
- [ ] Tool registry 分区缓存和 manifest 懒工具
- [ ] Server/connection 精准失效
- [ ] 管理端 AuthContext 与预热行为
- [ ] 单元、集成、lint、Docker 环境验证
- [ ] roadmap 更新
