# 模型配置权限管控调研与设计方案

> 调研对象：Yuxi 平台 `ModelProvider` 模型供应商配置
> 参考对象：已实现权限管控的 `Agent` / `Skill` 资源
> 目标：让模型供应商在「创建 / 编辑 / 删除 / 可见 / 调用」五个维度上，与智能体一致地支持「全局 / 部门 / 指定人」三档权限。
> 文档版本：v0.1（待评审）

---

## 1. 背景与动机

### 1.1 现状一句话

模型供应商（`ModelProvider`）目前是「全平台共享」：任何管理员都能看见、改、删所有供应商；任何登录用户都能在聊天/智能体里选到任意 `model_spec`；这与平台内「Agent / Skill」已经具备的「可见性 + 管理权」双层权限模型完全脱节。

### 1.2 业务诉求

企业落地时常见的模型管理诉求：

1. **预算与配额**：每个部门用自己的供应商，避免「测试时调用昂贵的 GPT 跑批」这类事故。
2. **数据合规**：某些供应商仅允许内网使用，需要把它限制到指定部门。
3. **个人试用**：开发同学可以临时接入一个新供应商做 POC，但又不想对其他部门暴露。
4. **责任可追溯**：删除一个供应商前需要知道「被谁引用」，不能因为「这个模型没人用」就误删。

### 1.3 设计目标

让 `ModelProvider` 具备与 `Agent` 一致的权限模型，复用现有 `share_config` 抽象，保证改动最小、行为可预测。

---

## 2. 现状调研

### 2.1 `ModelProvider` 当前实现

| 维度 | 现状 |
|------|------|
| 表 | `model_providers`（`backend/package/yuxi/storage/postgres/models_business.py:673-731`） |
| 关键字段 | `provider_id`, `display_name`, `provider_type`, `base_url`, `api_key`, `enabled_models`, `is_enabled`, `is_builtin`, `created_by`（仅字符串） |
| 缺失字段 | `share_config`、`created_by_uid`、无外键 |
| 创建/更新/删除 | `model_provider_router.py:62-166`，全部走 `get_admin_user` 守卫 |
| 列表展示 | `GET /api/system/model-providers/models/v2`（`model_provider_router.py:204-240`）走 `get_required_user`，**任何登录用户**都能看到全部启用模型 |
| 缓存 | `ModelCache` (`models/providers/cache.py`) 用 `yuxi:model_cache` Redis key 存储所有 provider + 明文 `api_key` |
| 模型加载 | `select_model(model_spec)` (`models/chat.py:53-77`) 不验证调用方权限 |
| API Key | 明文入库，列表 API 完整回传给前端，缓存也明文存 Redis |
| 删除保护 | `ModelProviderManagePanel.vue:177-179` 仅前端校验"是否是默认模型" |

### 2.2 `Agent` 已实现的权限模型（参照样板）

#### 2.2.1 数据层 (`models_business.py:230-275`)

```python
class Agent(Base):
    share_config = Column(JSON, nullable=False, default=dict)  # ← 关键字段
    is_default = Column(Boolean, ...)
    is_subagent = Column(Boolean, ...)
    created_by = Column(String(64), nullable=True, index=True)
```

`share_config` 结构（来自 `utils/share_config.py:5-6`）：

```python
SHARE_ACCESS_LEVELS = {"global", "department", "user"}
EMPTY_SHARE_CONFIG = {"access_level": "global", "department_ids": [], "user_uids": []}
```

#### 2.2.2 工具层（`utils/share_config.py`）

| 函数 | 职责 |
|------|------|
| `normalize_share_config(...)` | 通用规整：补默认值、校验 access_level、把创建者 uid/部门追加到对应列表 |
| `_normalize_department_ids` / `_normalize_user_uids` | 类型规整（`int` / `str`） |

复用点：`Skill`、未来 `ModelProvider` 都直接调用。

#### 2.2.3 仓库层（`repositories/agent_repository.py`）

- `user_can_access_agent(user, agent) -> bool`：`superadmin` 永真；`created_by == uid` 永真；按 `share_config.access_level` 判定 global/department/user
- `user_can_manage_agent(user, agent) -> bool`：`role in {admin, superadmin}` 或 `created_by == uid`
- `list_visible(user)`：全表拉取后 Python 层过滤（`repositories/agent_repository.py:329-338`）
- `get_visible_by_slug(slug, user, kind)`：404 对不可见对象（安全：避免"探测"）
- `create(...)` / `update(...)`：调用 `normalize_agent_share_config(..., force_private=role not in ADMIN_ROLES)` —— 非管理员角色创建默认强制私有

#### 2.2.4 路由层（`routers/agent_router.py`）

| 端点 | 守卫 | 关键校验 |
|------|------|---------|
| `GET /agent` | `get_required_user` | `list_visible(user)` |
| `GET /agent/{id}` | `get_required_user` | `get_visible_by_slug` |
| `PUT /agent/{id}` | `get_required_user` | `get_visible_by_slug` + `user_can_manage_agent` |
| `DELETE /agent/{id}` | `get_required_user` | `get_visible_by_slug` + `user_can_manage_agent` + `is_builtin_agent` 保护 |

`create_agent_run`（提交对话）虽然不在 agent 路由里做校验，但**消费侧**只能选可见的 agent（前端列表已过滤，后端 `submit_run_command` 同样会触发 `get_visible_by_slug`）。

#### 2.2.5 前端层（`web/src/components/model-management/AgentManagePanel.vue` + `AgentEditModal.vue`）

- 共享组件 `web/src/components/ShareConfigForm.vue`：`access_level` 卡片切换 + `department_ids` / `user_uids` 多选
- `allowedAccessLevels` prop 控制可选范围（非管理员只能 `user`）
- `autoSelectUserDept`：选 department 时自动把当前用户部门加上（避免把自己排除）
- 触发 `update:modelValue` 向父组件回传规整后的 share_config

### 2.3 `Skill` 复用同一套模式

`Skill.share_config`（`models_business.py:296`）字段 + `SkillRepository.update_share_config`（`agents/skills/repository.py:136-142`）已经证明 `share_config` 模式可以零成本横向铺到第二类资源。

### 2.4 权限调用链总览

```
┌────────────┐  ┌─────────────────────────────┐  ┌──────────────────────┐
│  User      │  │  HTTP Route                  │  │  Repository / Service │
│            ├─►│  - auth dependency           ├─►│  - list_visible()     │
│  uid       │  │  - get_visible_by_*()        │  │  - get_visible_by_*() │
│  role      │  │  - user_can_manage_*()       │  │  - normalize_share_*()│
│  dept_id   │  │                             │  │                      │
└────────────┘  └─────────────────────────────┘  └──────────────────────┘
                                                          │
                                                          ▼
                                              ┌────────────────────────┐
                                              │  ModelProvider (new)   │
                                              │  share_config + 4 fn   │
                                              └────────────────────────┘
```

---

## 3. 设计方案

### 3.1 总体设计原则

1. **复用，不重写**：照搬 `Agent.share_config` + `user_can_access_*` / `user_can_manage_*` 模式，新增 `ModelProviderRepository` 与对应规整函数
2. **最小入侵**：仅在确实需要鉴权的地方加 `Depends(get_current_user)` 或传入 `current_user`；其余字段、路由签名、缓存协议保持不变
3. **缓存不变**：模型缓存（`yuxi:model_cache`）仍存全量模型元数据 + 必要凭据；可见性过滤**始终在路由层**做，避免缓存维度的 N 份拷贝
4. **API Key 保护升级**（顺手做）：响应中默认脱敏，只在管理员显式请求时返回明文
5. **保留系统默认模型**：`Config.default_model` 始终指 `global` 的 provider，缺位时报警
6. **删除保护**：引用计数（被 `Knowledge.embedding_model_spec` / `llm_model_spec` / `AgentConfig.context.model_spec` / `UserConfig` 引用）时拒绝删除
7. **LITE 模式保持兼容**：`LITE_MODE` 不依赖此能力，但 `share_config` 字段本身保持 nullable 即可

### 3.2 数据层

#### 3.2.1 `ModelProvider` 新增字段

文件：`backend/package/yuxi/storage/postgres/models_business.py:673-731`

```python
class ModelProvider(Base):
    # ... 既有字段 ...
    share_config = Column(JSON, nullable=False, default=dict, comment="共享权限配置")
    # 注意：保留 created_by 字符串字段以兼容既有代码，但不作为权限判定依据
```

`share_config` 默认值建议使用 `EMPTY_SHARE_CONFIG`：

```python
from yuxi.utils.share_config import EMPTY_SHARE_CONFIG
# default=EMPTY_SHARE_CONFIG.copy()
```

#### 3.2.2 DDL 迁移

文件：`backend/package/yuxi/storage/postgres/manager.py:1130-1154`（既有的 `model_providers` 建表段后追加）

```sql
ALTER TABLE model_providers
    ADD COLUMN IF NOT EXISTS share_config JSONB NOT NULL DEFAULT '{"access_level":"global","department_ids":[],"user_uids":[]}'::jsonb;
```

- 兼容已有数据：所有历史 provider 视为 `global`（与改造前行为一致）
- 使用 `IF NOT EXISTS` 保证迁移可重入

#### 3.2.3 `UserConfig`（个人偏好）扩展（可选，本期建议**不做**）

`backend/package/yuxi/config/user.py:16-21` 当前只支持 `enable_memory`。本期不引入 `default_chat_model` 等用户级字段，保持单系统级 `Config.default_model`。如确需，把"我的偏好模型"作为 `ModelProvider.share_config={"access_level":"user", "user_uids":[<my_uid>]}` 的派生视图在前端展示即可，不破坏后端数据模型。

### 3.3 服务层

新建文件：`backend/package/yuxi/models/providers/share.py`

```python
from yuxi.repositories.agent_repository import ADMIN_ROLES
from yuxi.utils.share_config import EMPTY_SHARE_CONFIG, normalize_share_config

DEFAULT_PROVIDER_SHARE_CONFIG = EMPTY_SHARE_CONFIG.copy()


def normalize_provider_share_config(
    share_config: dict | None,
    *,
    user_uid: str | None = None,
    department_id: int | str | None = None,
    force_private: bool = False,
) -> dict:
    if force_private:
        if not user_uid:
            raise ValueError("私有模型供应商必须绑定创建用户")
        return {"access_level": "user", "department_ids": [], "user_uids": [str(user_uid)]}
    return normalize_share_config(
        share_config,
        default_config=DEFAULT_PROVIDER_SHARE_CONFIG,
        default_access_level="global",
        invalid_access_level_message="无效的模型供应商权限等级",
        user_uid=user_uid,
        department_id=department_id,
    )


def user_can_access_provider(user: "User", provider: "ModelProvider") -> bool:
    if user.role == "superadmin":
        return True
    user_uid = str(user.uid)
    if provider.created_by == user_uid:
        return True
    share_config = provider.share_config or DEFAULT_PROVIDER_SHARE_CONFIG.copy()
    access_level = share_config.get("access_level")
    if access_level == "global":
        return True
    if access_level == "department":
        if user.department_id is None:
            return False
        try:
            return int(user.department_id) in [int(v) for v in share_config.get("department_ids") or []]
        except (TypeError, ValueError):
            return False
    if access_level == "user":
        return user_uid in (share_config.get("user_uids") or [])
    return False


def user_can_manage_provider(user: "User", provider: "ModelProvider") -> bool:
    return user.role in ADMIN_ROLES or provider.created_by == str(user.uid)
```

### 3.4 仓库层

在 `backend/package/yuxi/models/providers/repository.py`（已有）增加：

| 方法 | 职责 |
|------|------|
| `list_visible(*, user) -> list[ModelProvider]` | 全表拉取 → 过滤 `user_can_access_provider`；`superadmin` 短路 |
| `get_visible_by_id(*, provider_id, user) -> ModelProvider \| None` | 不可见返回 `None`（路由层转 404） |
| `create(...)` | 接收 `share_config` 参数；调用 `normalize_provider_share_config(..., force_private=role not in ADMIN_ROLES)`；保存 `created_by=current_user.uid` |
| `update(provider, ...)` | 接受 `share_config` 更新；`is_builtin` 的 provider 强制 `global`；调用规整函数 |
| `delete(provider)` | 引用计数校验（见 3.7） |

### 3.5 路由层

文件：`backend/server/routers/model_provider_router.py`

| 端点 | 改造前 | 改造后 |
|------|--------|--------|
| `GET /api/system/model-providers` | `get_admin_user` + 全量返回 | `get_required_user` + `list_visible(user)`；响应里增加 `can_manage: bool` |
| `POST /api/system/model-providers` | `get_admin_user` | `get_required_user`；非 admin 角色创建默认 `force_private=True` |
| `GET /api/system/model-providers/{id}` | `get_admin_user` | `get_required_user` + `get_visible_by_id`；命中后 `can_manage` |
| `PUT /api/system/model-providers/{id}` | `get_admin_user` | `get_required_user` + `get_visible_by_id` + `user_can_manage_provider` |
| `DELETE /api/system/model-providers/{id}` | `get_admin_user` | `get_required_user` + 可见 + `can_manage` + 引用计数；`is_builtin` 拒绝 |
| `GET /api/system/model-providers/{id}/remote-models` | `get_admin_user` | `get_required_user` + 可见 |
| `POST /api/system/model-providers/models/cache/refresh` | `get_admin_user` | 不变（仍 `admin`，但仅刷新缓存） |
| `GET /api/system/model-providers/models/v2` | `get_required_user` + 全量 | `get_required_user` + 按 `user_can_access_provider` 过滤后返回 |
| `GET /api/system/model-providers/models/status` | `get_admin_user` | `get_required_user` + 可见（管理员也要做可见性过滤） |

### 3.6 消费侧鉴权（核心安全点）

文件：`backend/package/yuxi/models/chat.py:53-77`（`select_model`）

```python
def select_model(model_spec: str, *, current_user: "User" | None = None, **kwargs):
    info = model_cache.get_model_info(model_spec)
    if current_user is not None:
        from yuxi.models.providers.repository import ModelProviderRepository
        # 这里需要一次 DB 查询；为了避免在高并发热路径上击穿数据库，
        # 建议在 ModelCache.rebuild 时一并缓存"可见性摘要"（user role + dept_id → set[provider_id]）
        ...
    # ... 既有逻辑 ...
```

> 备注：消费侧鉴权**不是简单地把 `current_user` 透传下去就完事**。每个请求都查 DB 不现实。建议：
>
> - **方案 A（推荐）**：在 `ModelCache` 旁边增加一个 `VisibilityCache`，键为 `user.uid`，值为 `set[provider_id]`；`list_visible` 后写入；TTL 30s 即可（变更时可强制失效）。`select_model` 命中即过。
> - **方案 B（兜底）**：`select_model` 仅在有 `current_user` 时做校验，未传则保持原行为（`superadmin` 与全 global 场景不受影响）。

实际改动还涉及：
- `yuxi/agents/models.py:load_chat_model` 调用栈 → 从 `run_submission_service` 透传 `current_user`
- `chat_service.py:194-198` 在 `input_context["model"] = model_spec` 之前做可见性校验
- `knowledge_router.py:220-271` 创建知识库时的 `embedding_model_spec` / `llm_model_spec` 同样校验（管理员的兜底）

### 3.7 删除保护

文件：`backend/package/yuxi/models/providers/repository.py` 新增 `count_references(provider_id)`

引用点来源：

1. `Knowledge.embedding_model_spec` / `llm_model_spec`（`models_knowledge.py`）
2. `Knowledge.query_llm_model_spec`（同上）
3. `Agent.config_json` → `context.model_spec` / `context.embedding_model_spec` / `context.reranker_model_spec`（JSON 字段需 JSONB 查询）
4. `ConfigOption.value` / `Config.value` 中保存的 `default_model` / `embed_model` / `reranker` / `content_guard_llm_model`（如指向本 provider，则只清字段，不阻止删除）
5. （可选）`Message.model_used` 历史记录

策略：返回引用列表，**任一非 0** 则 `HTTP 409 Conflict`，响应体带上 `references: [{kind, id, name}]` 给前端弹窗。

### 3.8 API Key 保护升级（顺手做）

文件：`backend/package/yuxi/storage/postgres/models_business.py:706-731`（`to_dict`）新增 `masked` 模式：

```python
def to_dict(self, *, include_api_key: bool = True) -> dict:
    api_key = self.api_key
    masked = _mask_api_key(api_key) if api_key else None
    return {
        ...
        "api_key": api_key if include_api_key else masked,
        "api_key_masked": masked,
        ...
    }

def _mask_api_key(key: str) -> str:
    if not key:
        return None
    if len(key) <= 8:
        return "***"
    return f"{key[:3]}***{key[-4:]}"
```

调用约定：
- 列表/详情默认 `include_api_key=False`（前端只展示 masked）
- `PUT /api/system/model-providers/{id}` 在 PATCH 成功时单独返回一次明文（前端回填输入框）
- `is_builtin` 字段继续明文（如果数据库里有）—— 改用 `masked` 也可，避免一次性发散

缓存层（`yuxi:model_cache`）保留明文 `api_key`，因为 worker 进程需要它调外部 API；这是**已存在的风险**，本设计不重做。

### 3.9 前端层

#### 3.9.1 共享组件

`web/src/components/ShareConfigForm.vue` **已经存在并通用**，无需新建；只在新页面 import。

#### 3.9.2 `ModelProviderManagePanel.vue` 改造

文件：`web/src/components/model-management/ModelProviderManagePanel.vue`

改造要点：
- 顶部加"全部 / 我创建的 / 部门共享 / 全局共享"四档 Tabs（对齐 `AgentManagePanel.vue`）
- "新建 provider" 弹窗里加 `<ShareConfigForm>`；`allowedAccessLevels` 按当前用户角色裁剪（与 agent 一致：非 admin 只能 `user`）
- 列表卡片显示可见范围 chip（"🌐 全局 / 🏢 部门：研发、运维 / 👤 指定人：3 人"）
- 操作按钮（编辑、删除、测试连接）按 `can_manage` 显隐
- API Key 输入框绑定 `provider.api_key_masked`，点"显示"按钮触发单独请求取明文

#### 3.9.3 `ModelSelectorComponent.vue` 改造

文件：`web/src/components/ModelSelectorComponent.vue`

- 调用 `getV2Models` 拿到的数据已经按 `list_visible` 过滤，前端只做展示分组与搜索
- 选中模型时把 `provider_id:model_id` 上抛，沿用 `select-model` 事件，不变
- 不再需要"配置模型"快捷入口对 admin 之外的展示（`/agent-manage?tab=providers` 入口继续 admin only）

#### 3.9.4 API 封装

文件：`web/src/apis/system_api.js:97-131`

`getV2Models` 不变（已走 `get_required_user`）。新增：

```js
modelProviderApi.getV2Models = (modelType = 'chat') => request.get('/system/model-providers/models/v2', { params: { model_type: modelType } })
```

---

## 4. 关键设计权衡（Why）

| 取舍 | 决策 | 理由 |
|------|------|------|
| 复用 `share_config` 抽象 vs 新建一套字段 | **复用** | 已经在 Agent / Skill 上跑通，再造一套会让前端组件、规整逻辑、UI 重复 |
| 缓存按用户维度拆分 vs 路由层过滤 | **路由层过滤** | 缓存一致性是难题；30s 内可见性变更延迟可接受；现状已用 Redis 做单一事实源 |
| 删除时硬拦截 vs 软删除 | **硬拦截 + 409 + 引用列表** | 避免"幽灵引用"；用户可显式处理依赖；与现有 `is_builtin` 拦截一致 |
| 内置 provider 强制 `global` | **强制** | 与 `Agent` 的"内置智能体必须 global" 一致；防止升级覆盖策略 |
| 是否做"用户级 default_model" | **暂不做** | 业务上不急需；如做会让"个人偏好" + "share_config" 两套机制重叠，先用 `user` 级别 share + 前端兜底 |
| API Key 是否落库前加密 | **不引入** | 已有明文；引入加密会涉及密钥管理，超出本次需求范围。但**响应脱敏**立即做 |
| 消费侧鉴权 | **方案 A（可见性缓存）+ 透传 current_user** | 简单透传会在 chat 热路径上加 N 次 DB 查询；用户维度缓存命中后是 O(1) |

---

## 5. 风险与回滚

| 风险 | 缓解 |
|------|------|
| 历史 provider 默认 `global` → 与现状一致 | ALTER TABLE 默认值设为 `global`；无须数据回填 |
| 缓存可见性不一致 | 任何 `ModelProvider` 写操作完成后 `_refresh_visibility_cache(user)`；TTL 兜底 |
| 非 admin 误删内置 provider | `is_builtin` 保护 + 路由层 `can_manage` 校验 |
| 引用计数遗漏 | e2e 测试覆盖：先建 KB/Agent 再尝试删除 provider |
| LITE_MODE 下没有 knowledge 引用源 | 引用计数函数 `count_references` 根据 `LITE_MODE` 短路 |
| API Key 脱敏影响"复制 key"工作流 | UI 提供"获取明文"二次确认按钮，仅创建者 + admin 可见 |

回滚：所有新字段都可空 / 默认 `global`；DDL `IF NOT EXISTS` 可重入；关闭 `share_config` 校验分支即可回到改造前。

---

## 6. 实施计划（待评审）

> 单元/集成测试放在 `backend/test/unit` 与 `backend/test/integration`，e2e 放 `backend/test/e2e`，命名遵循现有 `test_xxx.py` 风格。

### 6.1 后端（基础）

- [ ] **DDL**：`manager.py:1130-1154` 段后追加 `share_config` 字段（带默认值与 `IF NOT EXISTS`）
- [ ] **Model 字段**：`ModelProvider.share_config` Column + `to_dict` 新增 `api_key_masked`
- [ ] **share.py**：`normalize_provider_share_config` / `user_can_access_provider` / `user_can_manage_provider`
- [ ] **Repository**：`list_visible` / `get_visible_by_id` / `create` / `update` 接入 share_config 规整
- [ ] **路由**：9 个端点全部按 3.5 改造；新增 404/403/409 错误路径
- [ ] **单测**：`test_providers_share.py` —— 三档 access_level 行为、`is_builtin` 锁、`force_private` 兜底
- [ ] **集测**：`test_model_provider_router.py` —— 9 个端点的可见性矩阵

### 6.2 后端（消费侧）

- [ ] **`VisibilityCache`**：`yuxi/models/providers/cache.py` 增加 `visible_to(user) -> set[str]` + TTL
- [ ] **`select_model`** 接受 `current_user`，命中 `VisibilityCache` 校验；缺缓存时回退 DB
- [ ] **`run_submission_service`** 把 `current_user` 透传到 `input_context["model"]` 之前
- [ ] **`chat_service.py:194-198`** 在 set model 之前校验
- [ ] **`knowledge_router.py`** 创建/更新 KB 时校验 `embedding_model_spec` / `llm_model_spec` 可见
- [ ] **集测**：`test_consume_model_visibility.py` —— 非可见 provider 拒绝消费

### 6.3 后端（删除保护）

- [ ] **`count_references`**：扫 `Knowledge.*_model_spec` / `Agent.config_json->...->model_spec` / `ConfigOption.value` / `Config.value`
- [ ] **DELETE 端点** 校验并返回 `references`
- [ ] **e2e**：`test_model_provider_delete_e2e.py` —— 准备 KB/Agent 引用后删除应失败

### 6.4 前端

- [ ] **`ModelProviderManagePanel.vue`**：Tabs + 共享范围 chip + ShareConfigForm 接入；非 admin 隐藏"新建"按钮（按角色裁剪 allowedAccessLevels）
- [ ] **`ModelSelectorComponent.vue`**：可见性由后端保证，前端只展示
- [ ] **`system_api.js`**：`getV2Models` 接口不变；新增 `getProvider`、`getV2Models`（按 type 过滤已支持）
- [ ] **测试**：组件级 vitest + Playwright 跑通 admin/department/user 三档场景

### 6.5 文档与 changelog

- [ ] `docs/develop-guides/changelog.md` 记录本特性
- [ ] `docs/.vitepress/config.mts` 在「进阶」分组加 `model-provider-permission.md`
- [ ] `docs/develop-guides/design.md` 同步更新（如有相关章节）

### 6.6 验收清单

- [ ] 非 admin 用户登录 → 模型选择器只看到 global 或自己可见的 provider
- [ ] 普通 user 创建私有 provider → 其他用户看不到
- [ ] 部门共享 → 同部门可见，跨部门不可见
- [ ] admin 修改别人的私有 provider → 403
- [ ] admin 删除被 KB 引用的 provider → 409 + 引用列表
- [ ] 内置 provider 的 share_config 不可改为非 global
- [ ] `LITE_MODE` 下引用计数不报错
- [ ] API Key 列表默认脱敏，只有显式请求才返回明文

---

## 7. 参考资料

| 文件 | 行号 | 说明 |
|------|------|------|
| `backend/package/yuxi/utils/share_config.py` | 1-54 | `share_config` 通用规整 |
| `backend/package/yuxi/repositories/agent_repository.py` | 117-167, 329-348 | 权限判定与可见列表模板 |
| `backend/package/yuxi/storage/postgres/models_business.py` | 230-275, 673-731 | Agent / ModelProvider 模型定义 |
| `backend/server/routers/agent_router.py` | 133-251 | 路由层权限校验模板 |
| `backend/package/yuxi/models/providers/cache.py` | 23-82, 138-179 | `ModelCache` + Redis 序列化 |
| `backend/server/routers/model_provider_router.py` | 62-254 | 待改造的 9 个端点 |
| `backend/package/yuxi/models/chat.py` | 53-77 | 消费侧 `select_model` |
| `web/src/components/ShareConfigForm.vue` | 全文 | 通用共享范围 UI 组件 |
| `web/src/components/model-management/ModelProviderManagePanel.vue` | 全文 | 待改造 |
| `web/src/components/model-management/AgentManagePanel.vue` | 全文 | 改造参考（已实现） |
| `web/src/components/ModelSelectorComponent.vue` | 246-273 | v2 模型选择器 |
| `docs/ARCHITECTURE.md` | 全文 | 架构不变量的最终参考 |

---

## 8. 已确认决策（2026-08-03）

1. **本期不引入"用户级 default_model"**。用 `user` 级别 `share_config` + 前端兜底视图。
2. **不对 API Key 做库内加密**。仅做响应脱敏（默认 masked，仅创建者/admin 显式请求返回明文）。
3. **`/api/system/model-providers/models/cache/refresh` 保留 admin only**。其他 8 个端点按 3.5 节矩阵改造。
4. **删除时引用列表暴露 `id` + `name`**，方便用户定位。响应结构：`{ detail, references: [{kind, id, name}] }`。
5. **`/api/system/model-providers/models/v2` 仍由 `get_required_user` 守护**，但服务端按 `user_can_access_provider` 过滤后返回。
6. **`Config.default_model` 等系统级配置"必须指向 global provider"的校验**：仅前端提示 + 后端 `logger.warning`，不强行 raise。

## 9. 实施记录

| Task | Commit | 备注 |
|------|--------|------|
| 1. DDL + share_config 字段 | 50b09a4a + 5d4f79a9 | 含 ORM default 修复 |
| 2. share.py 工具 | 10105410 | |
| 3. Repository | 2bf3d479 | |
| 4. Service | 9654ef65 | |
| 5. 路由矩阵 | 98fa90f5 | |
| 6. 消费侧鉴权 | c12467a4 | |
| 7. 删除保护 + knowledge | 1e8cc2b2 | |
| 8. 前端 | 7e6c4bff | |
