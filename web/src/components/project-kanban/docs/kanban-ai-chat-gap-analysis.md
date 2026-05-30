# 看板 AI 对话功能 — 与主项目差异分析及修复报告

> **范围**：看板 AI 侧边栏（`AISidepanel.vue`）内嵌对话 vs 主项目对话框（`AgentChatComponent.vue`）
> **日期**：2026-04-28（更新）
> **状态**：@提及(Mention)功能已修复 ✅ | Agent/Config 选择逻辑已修复 ✅ | Run 模式 SSE 已通过 feature gate 接入 ✅ | 其余差异待确认优先级

---

## 一、文件架构总览

### 1.1 组件调用链

```
主项目对话框                          看板 AI 对话
=================                    ================
App.vue                              ProjectKanbanView.vue
 └─ AgentChatComponent.vue (81KB)     └─ AISidepanel.vue (50KB, Teleport→body)
      ├─ ChatSidebarComponent.vue          ├─ KanbanChatArea.vue (6.5KB)
      ├─ MessageInputComponent.vue (904行) │   ├─ AgentMessageComponent.vue [复用]
      ├─ AgentMessageComponent.vue         │   ├─ ToolCallsGroupComponent [复用]
      ├─ AgentInputArea.vue               │   └─ RefsComponent [复用]
      └─ RefsComponent.vue                ├─ AgentInputArea.vue [复用]
                                           │   └─ MessageInputComponent.vue [复用, :mention]
                                           └─ 数据概览区(雷达图/进度/风险)
                                               
核心 composable:                      核心 composable:
- useAgentStore                       - useKanbanChat.js (72.7KB→~60KB)
- useAgentMentionConfig              - useAISidepanel.js (面板数据/折叠)
- useAgentThreadState                 - useAgentStreamHandler [复用]
- useAgentStreamHandler               - useStreamSmoother [复用]
```

### 1.2 关键文件路径

| 文件 | 行数 | 职责 |
|------|------|------|
| `src/components/project-kanban/common/AISidepanel.vue` | ~650 | 侧边栏主组件（Teleport+布局+数据概览+对话区） |
| `src/components/project-kanban/common/KanbanChatArea.vue` | ~200 | 消息渲染区域（复用 AgentMessageComponent） |
| `src/components/project-kanban/composables/useKanbanChat.js` | ~415 | **对话核心逻辑**（线程管理+S流处理+mention配置） |
| `src/components/AgentChatComponent.vue` | ~810 | 主项目聊天容器（参考基准） |
| `src/components/MessageInputComponent.vue` | ~904 | 底层输入框（@提及 UI 实现） |
| `src/composables/useAgentMentionConfig.js` | ~161 | Mention 配置推导（主项目使用，看板已绕过） |
| `src/stores/agent.js` | ~300 | Agent 状态管理（含 fetchMentionResources） |

---

## 二、功能差异总表（26 项）

### 2.1 完全缺失的功能（11 项）

| # | 功能 | 主项目 | 看板 | 影响 | 建议 |
|---|------|--------|------|------|------|
| F1 | **对话历史侧边栏** | ChatSidebarComponent（新建/选择/删除/重命名/置顶/分页加载） | ❌ 无 | 用户无法查看历史对话、切换线程 | P1：空间有限，可考虑简化版（仅最近N条列表） |
| F2 | **Agent 选择器** | 可切换不同 Agent | ❌ 固定 defaultAgent，不可切换 | 功能限制（设计如此，非 Bug） | 无需修复——设计意图就是固定 Agent |
| F3 | **人工审批流程** | processApprovalInStream 允许人工介入确认操作 | ❌ `processApprovalInStream: () => false` 显式禁用 | Agent 无法请求用户确认 | P2：看板场景可能不需要审批 |
| F4 | **Run 模式 SSE** | 支持 Run Mode 流式 API | ✅ 已接入 Run/Legacy 双路径 | `VITE_USE_RUNS_API === 'true'` 且 `localStorage.force_legacy_stream !== 'true'` 时走 Run，否则回退 Legacy | 保持 feature gate，审批 UI 仍未启用 |
| F5 | **AgentPanel / Artifacts 卡片** | 文件系统浮动面板 + 产物展示卡片 | ❌ 已移除（侧边栏空间有限） | 无法浏览工作区文件/查看生成产物 | P3：已有独立浮动面板入口 |
| F6 | **模型选择器** | 可切换 LLM 模型 | ❌ 使用 defaultAgent 默认模型 | 灵活性受限 | 同 F2，设计如此 |
| F7 | **多轮对话上下文窗口** | 完整对话历史滚动 | ⚠️ 仅显示最近消息，无独立侧边栏 | 历史消息不易回溯 | P2：与 F1 相关 |
| F8 | **消息引用/回复** | 支持引用某条消息回复 | ❌ 无 | 对话深度受限 | P3 |
| F9 | **对话导出** | 导出对话为文件 | ❌ 无 | 无法存档 | P3 |
| F10 | **Token 计数/费用显示** | 显示 Token 用量 | ❌ 无 | 用户无用量感知 | P3 |
| F11 | **系统提示词编辑** | 可编辑 system_prompt | ❌ 固定 defaultAgent 提示词 | 无法自定义行为 | P2 |

### 2.2 简化/削弱的功能（15 项）

| # | 功能 | 主项目 | 看板 | 差异详情 | 建议 |
|---|------|--------|------|----------|------|
| S1 | **@提及资源范围** | 通过 configurableItems 过滤，只展示 agent 已选中的 KB/MCP/Skills | ✅ **已修复**：展示 store 全量可用资源（绕过过滤） | 原因：defaultAgent 的 knowledges/mcps/skills 为空数组 → 过滤后全为 null | — |
| S2 | **文件提及(@files)** | 展示工作区文件 + 附件 | ❌ files 始终为空数组（看板暂无文件上传上下文） | useKanbanChat 中 currentThreadFiles/currentThreadAttachments 取值有限 | P2：集成文件面板后可补充 |
| S3 | **子智能体提及(@subagents)** | 从 configurableItems 的 subagents kind 推导 | ❌ subagents 始终为空数组 | 同 S1，defaultAgent 未配置 subagents | 低优先级 |
| S4 | **SSE 流式处理** | Legacy + Run 双模式 | ✅ Run + Legacy 双模式 | Run 分支使用 `createAgentRun` + `startRunStream` + 共享 `useAgentRunStream`，Legacy 分支保留原有 stream | 已补充 focused unit tests |
| S5 | **错误重试机制** | 完整的重试 UI 和逻辑 | ⚠️ 有基础实现但未完全对齐 | 需验证错误提示和重试按钮是否生效 | P2 |
| S6 | **消息工具调用展示** | ToolCallsGroupComponent 完整展示 | ✅ 复用同一组件，`:hide-tool-calls="true"` 隐藏 | 故意隐藏以节省空间 | 设计合理 |
| S7 | **消息引用栏(RefsComponent)** | copy/sources/点赞/点踩/重新生成/模型名 | ⚠️ 仅对最后一条完成消息显示 `['copy', 'sources']` | 精简了可用操作 | 设计合理 |
| S8 | **隐藏上下文注入** | 无 | ✅ 看板独有：通过 `<context>` 标签注入数据概览 | 将 panelData 序列化后作为隐藏上下文发送 | 看板增强功能 |
| S9 | **输入框功能按钮** | 完整工具栏（附件/图片/语音等） | ⚠️ 仅保留发送按钮 + 文件上传 | 根据supportsFileUpload条件显示 | 设计合理 |
| S10 | **自动创建线程** | 手动/自动均可 | ✅ 首条消息自动用 defaultAgent 创建线程 | 简化交互 | 设计合理 |
| S11 | **数据概览区** | 无 | ✅ 看板独有（雷达图/进度条/风险列表） | 打开侧边栏时展示，对话激活后折叠 | 看板增强功能 |
| S12 | **拖拽调整宽度** | 无 | ✅ 看板独有 | 4px×64px 把手，右侧锚定 | 看板增强功能 |
| S13 | **响应式适配** | 独立页面布局 | ✅ 看板独有：移动端从底部弹出 | 高度 50vh→展开85vh | 看板增强功能 |
| S14 | **滚动容器管理** | 聊天组件自行管理 | ✅ 统一滚动：header(fixed) + body(数据+消息) + input-bar(fixed) | setScrollContainer 注册 | 看板架构需要 |
| S15 | **z-index 层级管理** | Modal z-index 标准 | ✅ Modal 弹窗 1010 > 面板 1002 > 输入弹窗 1000 | `.ant-modal-wrap` 覆盖 | 多层浮层需要 |

---

## 三、@提及(Mention)功能 — 完整排查与修复记录

### 3.1 问题现象

看板 AI 侧边栏输入框输入 `@` 字符后，不弹出知识库/MCP/Skills 选择列表；主项目对话框正常弹出。

### 3.2 Mention 系统完整链路

```
数据源                    Composable                 组件传递                   UI 渲染
======                    ==========               ========                  =======

agentStore                useKanbanChat             AISidepanel              MessageInput
├─ availableKnowledgeBases  └─ mentionConfig           :mention="mentionConfig"  ├─ mentionEnabled (computed)
├─ availableMcps             (computed)                  ↓                      ├─ checkMentionTrigger()
└─ availableSkills           ↓                         Vue 自动解包              ├─ updateMentionItems()
                                ↓                                                  └─ .mention-dropdown-wrapper
                           返回 { files,                                           v-if="mentionPopupVisible"
                             knowledgeBases,
                             mcps, skills,
                             subagents } 或 null
```

### 3.3 排查过程（6 轮迭代）

| 轮次 | 检查点 | 结果 | 结论 |
|------|--------|------|------|
| R1 | 组件链路是否断裂 | AISidepanel→AgentInputArea→MessageInputComponent 连通 | ✅ 链路完整 |
| R2 | CSS overflow 是否裁剪 | input-bar `overflow:visible`, wrapper `position:absolute; z-index:1000` | ✅ 无裁剪 |
| R3 | mentionConfig 是否为 null | **是！返回 null** | 🔴 进入深层排查 |
| R4 | useAgentMentionConfig 内部过滤日志 | configItems 有9个keys含knowledges/mcps/skills，但 val 全为空数组 `[]` | 📍 发现过滤层问题 |
| R5 | mock 数据注入验证 | API 空→注入 mock(KB:3,MCP:1,Skills:2)，mentionConfig 最终仍为 null | 确认过滤是根因 |
| R6 | 结构包装层排查 | `{ mentionConfig: ComputedRef }` 外层对象导致模板不解包 | 📍 发现解包问题 |

### 3.4 根因分析（三层叠加）

#### 根因 ①：useAgentMentionConfig 过滤逻辑（最根本）

`useAgentMentionConfig.js` L121-127：
```js
const knowledgeBases = availableKnowledgeBases.value.filter(kb => allowedKbNames.has(kb.name))
const mcps = availableMcps.value.filter(mcp => allowedMcpNames.has(mcp.name))
const skills = availableSkills.value.filter(skill => { ... })
```

allowed 集合来自 configurableItems 中 kind=knowledges/mcps/skills 的 agentConfig 值：
```json
{ "knowledges": [], "mcps": [], "skills": [] }
```

**defaultAgent 未预配置任何 KB/MCP/Skills → allowed 集合全空 → 全部被过滤 → 5类资源全空 → return null**

#### 根因 ②：storeToRefs + computed 双重包装（加剧）

原代码：
```js
function getAgentStoreData() {
  return storeToRefs(useAgentStore())  // 第1层：所有属性变为 Ref<T>
}
const _deps = computed(() => { ... })    // 第2层：computed 包裹 Ref
// 使用时：_deps.value.availableKnowledgeBases?.value  // 双重 .value ← 响应性丢失
```

双重 `.value?.value` 导致 Vue 依赖追踪不稳定，表现为有时有值、有时 undefined。

#### 根因 ③：外层对象阻止 Vue 模板解包（最终暴露）

原代码：
```js
const mentionConfig = { mentionConfig: computed(...) }  // 外层普通对象
// 模板：:mention="mentionConfig"
// 子组件 props.mention === { mentionConfig: ComputedRefImpl }  ← 拿到的是原始对象！
```

Vue 3 模板**仅对顶层 Ref/ComputedRef 自动解包**，嵌套在普通对象内的不会被解包。

### 3.5 修复方案

**修改文件**：`src/components/project-kanban/composables/useKanbanChat.js`

**改动前**（~30行，三重包装）：
```js
import { storeToRefs } from 'pinia'
import { useAgentMentionConfig } from '@/composables/useAgentMentionConfig'

function getAgentStoreData() {
  return storeToRefs(useAgentStore())
}
const _deps = computed(() => { const { kb, m, s } = getAgentStoreData(); return { kb, m, s } })
const mentionConfig = {
  mentionConfig: useAgentMentionConfig({
    configurableItems: computed(() => _deps.value.configurableItems?.value || {}),
    agentConfig: computed(() => _deps.value.agentConfig?.value || {}),
    availableKnowledgeBases: computed(() => _deps.value.kb?.value || []),
    // ... 更多双层 .value
  })
}
```

**改动后**（10行，单层直读）：
```js
// 看板场景：defaultAgent 固定，@提及应展示全部可用资源
const mentionConfig = computed(() => {
  const store = useAgentStore()
  const kb = store.availableKnowledgeBases || []
  const mcps = store.availableMcps || []
  const skills = store.availableSkills || []
  const hasAny = kb.length || mcps.length || skills.length
  return hasAny ? { files: [], knowledgeBases: kb, mcps, skills, subagents: [] } : null
})
```

**同时清理**：
- 移除 `storeToRefs` import（Pinia）— 不再需要
- 移除 `useAgentMentionConfig` import — 看板场景绕过
- 模板保持 `:mention="mentionConfig"` — 顶层 ComputedRef，Vue 自动解包 ✅

### 3.6 修复验证结果

```
[AISidepanel DEBUG] 强制求值结果:
  {files:[], knowledgeBases:[...3], mcps:[...1], skills:[...2], subagents:[]}
[MessageInput DEBUG] mentionEnabled: true
[MessageInput DEBUG] checkMentionTrigger 被调用!        ← 弹窗触发成功 ✅
```

### 3.7 @提及子功能完整性清单（13 项）

| # | 子功能 | 状态 | 备注 |
|---|--------|------|------|
| M1 | `@` 触发检测（正则 `/@(\S*)$/`） | ✅ 正常 | handleKeyUp + handleInput 双通道检测 |
| M2 | 弹窗定位（absolute + textarea 位置计算） | ✅ 正常 | mentionDropdownStyle computed |
| M3 | 知识库列表渲染 | ✅ 正常 | mock 验证通过，生产环境依赖 API |
| M4 | MCP 列表渲染 | ✅ 正常 | 同上 |
| M5 | Skills 列表渲染 | ✅ 正常 | 同上 |
| M6 | 文件列表渲染 | ⚠️ 空列表（设计如此） | 看板暂无文件上传上下文，未来可扩展 |
| M7 | 键盘导航（↑↓/Enter/Tab/Esc） | ✅ 正常 | handleMentionNavigation 复用主项目 |
| M8 | 搜索过滤（模糊匹配多字段） | ✅ 正常 | filterItems 复用主项目 |
| M9 | Token 插入（`@type:value` 格式） | ✅ 正常 | insertMention + formatMentionToken |
| M10 | 点击外部关闭 | ✅ 正常 | document click 监听 + contains 检查 |
| M11 | 文件类型搜索提示（空 query 时） | ✅ 正常 | showFileSearchPrompt 逻辑 |
| M12 | 子智能体列表 | ⚠️ 空列表（设计如此） | defaultAgent 未配置 subagents |
| M13 | 选中高亮（hover + keyboard active） | ✅ 正常 | CSS `.active` class |

---

## 四、架构决策与技术要点

### 4.1 禁止模式（踩坑记录）

| # | 反模式 | 后果 | 正确做法 |
|---|--------|------|----------|
| 1 | `storeToRefs()` 结果再包进 computed | 双重 `.value?.value` 响应性丢失 | 直接读 `store.property` 利用 Pinia 自身响应性 |
| 2 | `{ inner: computed(...) }` 外层套对象 | Vue 模板不解包内层 ComputedRef | 直接返回顶层 computed |
| 3 | 共享 composable 不考虑受限场景 | 看板固定 agent 导致过滤全空 | 提供 skipFilter 参数或文档标注适用前提 |
| 4 | 调试时只打印对象引用 | console.log 不展开 Proxy/ComputedRef | 同时打印判空结论和各字段 length |

### 4.2 分层调试方法论（推荐）

排查 Vue 响应式数据流断裂时，每层一个日志点：

```
L1 数据源     → 原始 API/mock 数据是否存在
L2 Store       → storeToRefs 或直读是否正确传递
L3 Composable  → computed/filter 逻辑是否产出预期值
L4 结构包装    → 外层结构是否阻碍模板解包
L5 Props 传递  → 子组件收到的 prop 类型/值是否正确
L6 组件内部    → enabled/visible 等门控条件是否通过
L7 DOM/CSS     → 元素是否存在、定位/z-index/overflow 是否正确
```

### 4.3 未来改进建议

| 优先级 | 改进项 | 说明 |
|--------|--------|------|
| P1 | **useAgentMentionConfig 增加 skipFilter 选项** | 让下游消费者不必各自绕过（见 FEAT-20260428-001） |
| P2 | **补充文件提及上下文** | 集成文件面板后，将 workspace 文件注入 mentionConfig.files |
| P2 | **对话历史侧边栏（简化版）** | 至少提供最近 N 条对话列表供切换 |
| 已完成 | **Run 模式 SSE 支持** | 通过 feature gate 接入，关闭 gate 或设置 `localStorage.force_legacy_stream === 'true'` 时仍走 Legacy |
| P3 | **审批流程** | 看板场景可能需要简化的审批交互 |

---

## 四½、Agent/Config 选择逻辑修复（2026-04-28）

### 4½.1 问题背景

看板 AI 侧边栏需要使用特定的"项目管理"配置档案（Config），而非全局默认的"初始配置"。

**关键概念区分：**

| 概念 | API 接口 | 示例 |
|------|----------|------|
| **Agent**（智能体） | `GET /api/chat/agent` | `ChatbotAgent`(智能助手)、`DeepAgent`(深度分析) |
| **Config**（配置档案） | `GET /agent/{agentId}/configs` | `id:1 初始配置(default)`、`id:3 项目管理` |

### 4½.2 原始问题

- 原代码所有位置硬编码读 `agentStore.defaultAgentId` + `agentStore.selectedAgentConfigId`
- `selectedAgentConfigId` 由全局 store 管理，跟随用户在主项目对话框中的选择
- 看板侧边栏无法独立指定使用哪个 Config

### 4½.3 修复方案

**修改文件**：`src/components/project-kanban/composables/useKanbanChat.js`

#### 新增函数

```js
// Agent 选择：直接用 defaultAgent（不变）
function resolveKanbanAgentId(agentStore) {
  return agentStore.defaultAgentId || (agentStore.agents?.[0]?.id || null)
}

// Config 选择：按名称匹配「项目管理」→ is_default → configs[0]
function resolveKanbanConfigId(agentStore) {
  const agentId = resolveKanbanAgentId(agentStore)
  if (!agentId) return null
  const list = agentStore.agentConfigs?.[agentId] || []
  const matched = list.find((c) => c.name && c.name.includes('项目管理'))
  if (matched) return matched.id
  return list.find((c) => c.is_default)?.id || (list.length > 0 ? list[0].id : null)
}
```

#### 新增 computed

| 变量 | 用途 |
|------|------|
| `kanbanAgent` | 看板专用的 Agent 对象 |
| `kanbanAgentId` | 看板专用的 Agent ID（供 handleAgentResponse 等） |
| `kanbanConfigId` | **看板专用的 Config ID**（核心新增） |

#### 替换的引用（6 处 → 7 处）

| 位置 | 原逻辑 | 新逻辑 |
|------|--------|--------|
| `handleAgentResponse.currentAgentId` | `agentStore.defaultAgentId` | `kanbanAgentId.value` |
| `ensureActiveThread` agentId | `agentStore.defaultAgentId` | `kanbanAgentId.value` |
| `sendMessage` agentId | `agentStore.defaultAgentId` | `kanbanAgentId.value` |
| `sendMessage` configId guard | `agentStore.selectedAgentConfigId` | `kanbanConfigId.value` ✅新增 |
| `sendMessage` API 参数 | `agentStore.selectedAgentConfigId` | `configId` (kanbanConfigId) ✅新增 |
| `currentAgentName` | `agentStore.defaultAgent?.name` | `kanbanAgent.value?.name` |
| `currentAgentId` (导出) | `agentStore.defaultAgentId` | `kanbanAgentId.value` |
| `supportsFileUpload` | `agentStore.defaultAgent` | `kanbanAgent.value` |
| 导出 `selectedAgentConfigId` | `computed(() => agentStore.selectedAgentConfigId)` | `kanbanConfigId` ✅替换 |

### 4½.4 验证结果

```
[KanbanChat] Config 选择 — Agent ChatbotAgent 的全部 configs:
  [{ id: 1, name: "初始配置", is_default: true }, { id: 3, name: "项目管理", is_default: false }]
[KanbanChat] Config 选择 ✅ 命中「项目管理」: { id: 3, name: "项目管理" }
```

✅ 成功选中 id=3 的"项目管理"配置档案。

---

## 四¾、Run 模式 SSE 接入修复（2026-05-30）

### 4¾.1 问题背景

看板 AI 侧边栏原先只走 Legacy stream。主项目对话框已经支持 Run Mode 流式 API，看板侧边栏因此缺少新 runs 链路下的生命周期管理、恢复能力和统一 SSE 处理路径。

### 4¾.2 修复范围

**修改文件**：`src/components/project-kanban/composables/useKanbanChat.js`

`useKanbanChat.js` 现在使用 Run/Legacy 双路径，默认保持 Legacy 兼容，满足下面两个条件时才启用 Run 分支：

```js
import.meta.env.VITE_USE_RUNS_API === 'true'
localStorage.force_legacy_stream !== 'true'
```

这意味着生产环境可以通过环境变量逐步放量；排查问题时，也可以用 `localStorage.force_legacy_stream = 'true'` 强制回退旧链路。

### 4¾.3 Run 发送链路

Run 分支复用主项目的 runs API 与共享流处理 composable：

```text
sendMessage
  → createAgentRun(threadId, payload)
  → startRunStream(threadId, runId, 0)
  → useAgentRunStream 统一处理 SSE chunk
```

看板侧不新增自定义 SSE parser，流式 chunk 仍交给共享 `useAgentRunStream` 和既有消息处理逻辑，避免看板维护一套分叉协议。

### 4¾.4 停止与关闭语义

| 操作 | Run 行为 | 说明 |
|------|----------|------|
| 显式点击停止生成 | 取消当前 active Run | 用户明确要求中断，本轮生成停止 |
| 关闭 AI 侧边栏 | 不取消 Run | 关闭面板只是隐藏 UI，后续可继续或恢复 active Run |

该语义遵循看板交互决策：关闭侧边栏不等于停止任务，只有显式 Stop 才取消后端 Run。

### 4¾.5 隐藏上下文与 UI 展示

看板仍通过隐藏 `<context>` 块把数据概览注入给后端。Run 分支保留这条 backend-only 输入路径，但历史消息展示会清理隐藏上下文，用户可见 UI 不显示 `<context>` 内容。

### 4¾.6 测试覆盖

**新增测试文件**：`src/components/project-kanban/composables/__tests__/useKanbanChat.spec.js`

覆盖点：

| 场景 | 期望 |
|------|------|
| Run gate 开启 | 调用 `createAgentRun` 后交给 `startRunStream(threadId, runId, 0)` |
| Legacy 回退 | gate 关闭或 `force_legacy_stream` 为 `true` 时继续走旧 stream |
| 隐藏 context | 后端 payload 保留 `<context>`，可见历史不显示该块 |
| 显式 Stop | 取消 active Run |
| 关闭或恢复 | 不取消 active Run，可继续 resume |
| 缺少 run_id | 进入错误处理，不静默成功 |
| 项目管理配置 | 仍优先选择「项目管理」Config |

### 4¾.7 仍未纳入本次修复的范围

- 人工审批 UI 仍保持禁用，`processApprovalInStream: () => false` 的限制未改。
- 对话历史侧边栏、模型选择器、Artifacts 卡片仍是看板侧边栏的待办或设计外能力。
- AgentPanel、文件系统浮动面板和产物展示仍不在本次 Run SSE 修复范围内。

---

## 五、相关文件索引

### 5.1 看板 AI 对话相关（本次涉及）

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `src/components/project-kanban/composables/useKanbanChat.js` | **核心修复** | ① mentionConfig 重写（三重包装→单层直读）② Agent/Config 选择逻辑独立化（新增 resolveKanbanConfigId/kanbanConfigId）③ Run/Legacy 双路径流式发送 |
| `src/components/project-kanban/composables/__tests__/useKanbanChat.spec.js` | 单元测试 | 覆盖 Run/Legacy gate、隐藏上下文、取消、恢复、缺少 run_id 和项目管理配置 |
| `src/components/project-kanban/common/AISidepanel.vue` | prop 传递 | `:mention="mentionConfig"` 传参 |
| `src/stores/agent.js` | 数据源 | fetchMentionResources() 提供 KB/MCP/Skills 全量列表 |
| `src/composables/useAgentMentionConfig.js` | 参考基准 | 主项目 Mention 配置推导（看板已绕过） |
| `src/components/MessageInputComponent.vue` | UI 实现（只读） | @提及弹窗/键盘导航/Token插入 完整实现 |

### 5.2 主项目对话框（参考基准）

| 文件 | 说明 |
|------|------|
| `src/components/AgentChatComponent.vue` | 主聊天容器，mentionConfig 定义在 L525-534 |
| `src/components/AgentInputArea.vue` | 输入区封装层，透传 :mention |
| `src/components/AgentMessageComponent.vue` | 消息渲染（Markdown/推理过程/ToolCalls） |
| `src/components/ChatSidebarComponent.vue` | 对话历史侧边栏 |
| `src/components/RefsComponent.vue` | 引用栏（点赞/复制/重新生成等） |

### 5.3 流式处理相关

| 文件 | 说明 |
|------|------|
| `src/composables/useAgentStreamHandler.js` | SSE 流处理器（看板复用） |
| `src/composables/useAgentRunStream.js` | Run 模式 SSE 处理器（看板 Run 分支复用） |
| `src/composables/useStreamSmoother.js` | 流式平滑（看板复用） |
| `src/utils/messageProcessor.js` | 消息解析/格式化（看板复用） |
