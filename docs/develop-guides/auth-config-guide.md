# 内网认证系统适配指南

本文档介绍如何配置和使用 fetch-url 接口的内网认证功能。

## 功能概述

`POST /knowledge/files/fetch-url` 接口现已支持自动认证配置，可根据 URL 域名自动匹配对应的认证方式，适用于需要鉴权的内网系统。

## 支持的认证类型

| 认证类型 | auth_type | 描述 |
|----------|-----------|------|
| 无认证 | `none` | 公开 URL，无需认证 |
| HTTP Basic | `basic` | HTTP Basic Auth |
| Bearer Token | `bearer` | Bearer Token 认证 |
| 静态 Cookie | `cookie` | 使用已有 session cookie |
| Cookie 登录 | `cookie_login` | 先登录获取 cookie，再访问 |
| 自定义 | `custom` | 完全自定义配置 |

## API 接口

### 创建认证配置

```http
POST /knowledge/auth-configs
Content-Type: application/json
Authorization: Bearer <admin_token>

{
  "domain_pattern": "*.example.com",
  "auth_type": "basic",
  "credentials": {
    "username": "admin",
    "password": "secret"
  },
  "description": "内网 Wiki 系统"
}
```

### 获取认证配置列表

```http
GET /knowledge/auth-configs
Authorization: Bearer <admin_token>
```

### 更新认证配置

```http
PUT /knowledge/auth-configs/{config_id}
Content-Type: application/json
Authorization: Bearer <admin_token>

{
  "auth_type": "bearer",
  "credentials": {
    "token": "new_token_here"
  }
}
```

### 删除认证配置

```http
DELETE /knowledge/auth-configs/{config_id}
Authorization: Bearer <admin_token>
```

## 配置示例

### 1. HTTP Basic Auth

适用于使用 HTTP Basic 认证的内网系统：

```json
{
  "domain_pattern": "wiki.internal.com",
  "auth_type": "basic",
  "credentials": {
    "username": "admin",
    "password": "password123"
  },
  "description": "公司 Wiki 系统"
}
```

### 2. Bearer Token

适用于 API Token 认证的系统：

```json
{
  "domain_pattern": "api.service.internal",
  "auth_type": "bearer",
  "credentials": {
    "token": "ghp_xxxxxxxxxxxxxxxxxxxx"
  },
  "description": "内部 API 服务"
}
```

### 3. 静态 Cookie + 工号

适用于已有 session cookie 且需要传递工号的系统：

```json
{
  "domain_pattern": "docs.internal.com",
  "auth_type": "cookie",
  "credentials": {
    "session_id": "abc123xyz",
    "employee_id": "12345"
  },
  "request_modifiers": {
    "cookies": {
      "sessionid": "{session_id}"
    },
    "headers": {
      "X-User-ID": "{employee_id}",
      "X-Auth-Source": "yuxi-system"
    }
  },
  "description": "内部文档系统"
}
```

### 4. Cookie 登录（自动获取 session）

适用于需要先登录获取 session 的系统：

```json
{
  "domain_pattern": "secure.internal.com",
  "auth_type": "cookie_login",
  "credentials": {
    "login_url": "https://secure.internal.com/api/login",
    "username": "user123",
    "password": "pass456",
    "employee_id": "12345"
  },
  "request_modifiers": {
    "headers": {
      "X-User-ID": "{employee_id}"
    }
  },
  "description": "安全文档系统"
}
```

### 5. 自定义认证

适用于特殊认证需求的系统：

```json
{
  "domain_pattern": "custom.service.com",
  "auth_type": "custom",
  "credentials": {
    "api_key": "xxx",
    "tenant_id": "yyy",
    "employee_id": "12345"
  },
  "request_modifiers": {
    "headers": {
      "X-API-Key": "{api_key}",
      "X-Tenant-ID": "{tenant_id}",
      "X-User-ID": "{employee_id}",
      "X-Custom-Sign": "{api_key}-{tenant_id}"
    }
  },
  "description": "自定义认证服务"
}
```

## 域名匹配规则

- **完全匹配**：`wiki.internal.com` 只匹配该域名
- **通配符匹配**：`*.internal.com` 匹配 `api.internal.com`、`docs.internal.com` 等
- **最具体匹配原则**：同时匹配时，选择最具体的配置（通配符最少的）

## 使用说明

### fetch-url 接口调用

配置好认证后，调用 `fetch-url` 接口时无需额外参数，系统会自动根据 URL 域名匹配认证配置：

```http
POST /knowledge/files/fetch-url
Content-Type: application/json
Authorization: Bearer <admin_token>

{
  "url": "https://wiki.internal.com/page/123",
  "db_id": "kb_abc123"
}
```

响应中会包含 `auth_used` 字段，指示使用了哪种认证方式：

```json
{
  "status": "success",
  "auth_used": "basic",
  "content_hash": "...",
  "file_path": "...",
  ...
}
```

## 安全说明

1. **凭据加密**：认证凭据可通过 `AUTH_ENCRYPTION_KEY` 环境变量配置加密存储
2. **脱敏返回**：API 返回的凭据信息会被脱敏（显示为 `***`）
3. **管理员权限**：认证配置的增删改查需要管理员权限
4. **日志安全**：日志中不会记录敏感凭据信息

## 扩展开发

### 注册自定义认证器

```python
from yuxi.plugins.auth import AuthenticatedFetcher, AuthFetcherRegistry

class MyCustomFetcher(AuthenticatedFetcher):
    async def prepare(self, context):
        # 注入认证信息
        context.headers["X-Custom-Auth"] = "..."
        return context
    
    async def fetch(self, url):
        # 执行请求
        ...

# 注册
AuthFetcherRegistry.register("my_custom", MyCustomFetcher)
```

## 故障排查

### 问题：认证配置不生效

1. 检查域名 pattern 是否匹配目标 URL
2. 检查 auth_type 是否为有效值
3. 查看日志确认认证配置加载状态

### 问题：Cookie 登录失败

1. 检查 `login_url` 是否正确
2. 检查 `username` 和 `password` 是否正确
3. 确认登录接口返回的 cookie 格式

### 问题：自定义 headers 未生效

检查 `request_modifiers` 配置格式是否正确，变量替换语法为 `{credential_key}`。
