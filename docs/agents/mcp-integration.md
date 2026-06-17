# MCP 集成

MCP（Model Context Protocol）是扩展智能体能力的重要方式。系统支持通过管理界面动态配置 MCP 服务器，无需修改代码。

内置 MCP 服务器以代码为事实源：系统启动时会自动补齐缺失项，并用代码中的最新连接与展示字段覆盖数据库定义；是否“已添加”以及工具级禁用列表仍保留数据库状态。

## 支持的传输协议

| 协议 | 说明 | 适用场景 |
|------|------|----------|
| Streamable HTTP | 流式 HTTP 连接 | 远程 MCP 服务 |
| SSE | Server-Sent Events | 标准 HTTP 长连接 |
| Stdio | 标准输入输出 | 本地进程 |

## 配置示例

### 远程 MCP 服务

```json
{
    "name": "sequentialthinking",
    "transport": "streamable_http",
    "url": "https://remote.mcpservers.org/sequentialthinking/mcp"
}
```

### 本地 Python 进程

```json
{
    "name": "mysql-mcp-server",
    "transport": "stdio",
    "command": "uvx",
    "args": ["mysql_mcp_server"],
    "env": {
        "MYSQL_HOST": "localhost",
        "MYSQL_DATABASE": "your_database"
    }
}
```

## 服务器管理

管理界面使用“添加 / 移除”语义管理 MCP 服务器：

- 已添加：`enabled=true`，会加载到运行时缓存并可供 Agent 使用
- 可添加：`enabled=false`，记录保留但不会进入运行时

## 动态鉴权

MCP 支持在服务配置中声明 `auth_config`，由 Yuxi 在运行时按当前用户、部门或系统范围解析凭据，再把请求头或环境变量注入到 MCP 调用中。

常见模式：

| 模式 | provider | 适用场景 |
|------|----------|----------|
| 不启用动态鉴权 | 留空 | 无鉴权 MCP，或已经在 HTTP 请求头中配置固定 token |
| 绑定长期密钥 | `bound_secret` | API Key、长期 access token、租户密钥等固定凭据 |
| 接口换 Token | `custom_http_token` | 调用内部网关、IAM 或业务系统动态换取 token |
| Client Credentials | `client_credentials` | OAuth2 client credentials 风格的机器凭证换 token |
| Stdio 环境变量 | `stdio_env` | `stdio` MCP 进程需要从环境变量读取密钥 |
| Authorization Code | `authorization_code` | 已有 refresh token，需要按 OIDC issuer 刷新 access token |

管理界面的“认证配置”向导覆盖常见模式；更复杂的配置可以切换到“JSON 高级”直接编辑 `auth_config`。

### 绑定范围

`binding_scope` 决定连接页维护的凭据按什么范围生效：

| 范围 | scope_id | 说明 |
|------|----------|------|
| `system` | `global` | 全员共享同一组凭据 |
| `department` | 部门 ID | 同一部门共享凭据 |
| `user` | 用户 ID | 当前用户独占凭据 |
| `inline` | 无 | 不使用连接表绑定，通常仅兼容旧静态配置 |

对于 `department` 和 `user` 绑定，工具列表、工具调用和连接测试都会按当前运行上下文解析，不会跨部门或跨用户复用连接。

### 模板变量

`auth_config` 中的请求头、body 模板和注入项可以使用以下变量：

| 变量 | 含义 |
|------|------|
| `${secret.xxx}` | 当前连接的长期敏感凭据字段，例如 `${secret.client_secret}` |
| `${access_token}` | 动态换取到的 access token |
| `${token.xxx}` | token 响应或缓存中的字段，例如 `${token.refresh_token}` |
| `${context.user_id}` | 当前 Yuxi 用户 ID |
| `${context.work_id}` | 当前用户工号或登录 ID |
| `${context.department_id}` | 当前用户所属部门 ID |

只要配置中引用了 `${secret.xxx}`，非 `inline` 范围就必须在连接页创建 active 连接。未引用 `${secret.xxx}` 的动态鉴权配置不强制绑定连接，适合只依赖用户上下文、部门上下文或无密钥网关的场景。

### 示例：绑定长期 API Key

服务配置中的 `auth_config`：

```json
{
  "version": 1,
  "provider": "bound_secret",
  "binding_scope": "department",
  "manifest_scope": "binding",
  "inject": {
    "target": "headers",
    "entries": [
      {
        "name": "X-Api-Key",
        "value_template": "${secret.api_key}"
      }
    ]
  }
}
```

然后在 MCP 连接页为对应部门创建连接，凭据填写：

```json
{
  "secrets": {
    "api_key": "your-api-key"
  }
}
```

### 示例：接口换 Token

服务配置中的 `auth_config`：

```json
{
  "version": 1,
  "provider": "custom_http_token",
  "binding_scope": "department",
  "manifest_scope": "binding",
  "inject": {
    "target": "headers",
    "entries": [
      {
        "name": "Authorization",
        "value_template": "Bearer ${access_token}"
      }
    ]
  },
  "refresh_policy": {
    "pre_refresh_seconds": 300,
    "retry_once_on_401": true
  },
  "token_request": {
    "url": "http://gateway.internal/api/token",
    "method": "POST",
    "body_type": "json",
    "headers": {
      "Content-Type": "application/json"
    },
    "body_template": {
      "client_id": "${secret.client_id}",
      "client_secret": "${secret.client_secret}",
      "user_id": "${context.user_id}",
      "work_id": "${context.work_id}",
      "department_id": "${context.department_id}"
    },
    "response_map": {
      "access_token": "data.access_token",
      "refresh_token": "data.refresh_token",
      "expires_in": "data.expires_in"
    }
  }
}
```

连接页凭据：

```json
{
  "secrets": {
    "client_id": "client-id",
    "client_secret": "client-secret"
  }
}
```

Yuxi 会缓存 access token，接近过期时提前刷新；如果上游 MCP 返回 401 且启用了 `retry_once_on_401`，会清理缓存并自动重试一次。

### 示例：免密钥动态鉴权

如果 token 网关只依赖 Yuxi 用户上下文，不需要长期密钥，可以不引用 `${secret.xxx}`：

```json
{
  "version": 1,
  "provider": "custom_http_token",
  "binding_scope": "user",
  "manifest_scope": "binding",
  "inject": {
    "target": "headers",
    "entries": [
      {
        "name": "Authorization",
        "value_template": "Bearer ${access_token}"
      }
    ]
  },
  "token_request": {
    "url": "http://gateway.internal/api/token/by-user",
    "method": "POST",
    "body_type": "json",
    "headers": {
      "Content-Type": "application/json"
    },
    "body_template": {
      "user_id": "${context.user_id}",
      "work_id": "${context.work_id}",
      "department_id": "${context.department_id}"
    },
    "response_map": {
      "access_token": "access_token",
      "expires_in": "expires_in"
    }
  }
}
```

这类配置无需创建 MCP 连接即可测试和加载工具；运行时仍会按当前用户上下文生成 token。

### 操作流程

1. 管理员进入扩展管理中的 MCP 页面，创建或编辑 MCP 服务。
2. 填写传输协议、URL 或 stdio 命令。
3. 在“认证配置”中选择认证模式，或用“JSON 高级”粘贴 `auth_config`。
4. 如果配置引用了 `${secret.xxx}`，在连接页按 `system`、`department` 或 `user` 创建对应连接。
5. 点击“测试连接”确认可以拉取工具列表。
6. 在 Agent 配置或运行时选择该 MCP 服务。

## 工具管理

MCP 工具支持粒度控制：管理员可以单独启用或禁用某个 MCP 服务器下的特定工具，实现精细化的权限管理。

## 开发与排障

动态 HTTP MCP 的内部代理、连接池和缓存策略见 [MCP 动态鉴权开发手册](../develop-guides/mcp-dynamic-auth.md)。
