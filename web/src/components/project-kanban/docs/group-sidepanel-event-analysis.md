# 项目群级侧边栏事件缺失分析

## 问题概述

项目群级视图的4个侧边栏交互点均无法正常打开侧边栏：

| # | 交互点 | 用户操作 | 预期行为 | 实际行为 |
|---|--------|---------|---------|---------|
| 1 | 卡片 AI 一句话总结 | 点击紫色渐变文字区域 | 打开该项目群的分析侧边栏 | 无响应 |
| 2 | 卡片 AI 按钮 | 点击卡片底部 AI 按钮 | 打开该项目群的分析侧边栏 | 无响应 |
| 3 | AI 智能评估第一栏文字 | 点击底部总结条的"AI 智能评估"文字 | 打开项目群汇总分析侧边栏 | 无响应 |
| 4 | 猜你想问 | 点击底部总结条的猜你想问按钮 | 打开侧边栏并自动发送问题 | 无响应 |

## 根因分析

**核心问题：`ProjectKanbanView.vue` 中引用了两个未定义的变量 `groupMeta` 和 `groupSummary`，导致所有依赖它们的 handler 函数运行时抛出 `ReferenceError` 而静默失败。**

### 具体问题

#### 问题1：`groupMeta` 未定义

```js
// 第336行 - handleGroupAIClick 使用了未定义的 groupMeta
function handleGroupAIClick(groupKey) {
  const meta = groupMeta[groupKey]  // ❌ ReferenceError: groupMeta is not defined
  if (!meta) return
  sidepanel.open('group', meta, { summary: groupSummary, groupCount: groupKeys.length })
}
```

影响范围：
- **问题1** 卡片 AI 一句话总结点击 → `$emit('ai-click', groupKey)` → `handleGroupAIClick(groupKey)` → ❌ `groupMeta` 未定义
- **问题2** 卡片 AI 按钮点击 → `$emit('ai-click', groupKey)` → `handleGroupAIClick(groupKey)` → ❌ `groupMeta` 未定义

#### 问题2：`groupSummary` 未定义

```js
// 第338行、第377行、第381行 - 多个 handler 使用了未定义的 groupSummary
sidepanel.open('group', meta, { summary: groupSummary, ... })      // 第338行 ❌
sidepanel.open('groupSummary', groupSummary, { ... })               // 第377行 ❌
sidepanel.open('groupSummary', groupSummary, { ... })               // 第381行 ❌
```

影响范围：
- **问题1+2** handleGroupAIClick 中传 `summary: groupSummary` → ❌
- **问题3** AI 智能评估文字点击 → `handleGroupSummaryClick()` → ❌ `groupSummary` 未定义
- **问题4** 猜你想问点击 → `handleGroupQuestionClick(question)` → ❌ `groupSummary` 未定义

## 与设计稿对比

### 设计稿的事件绑定

| 交互点 | 设计稿 HTML/JS | 设计稿行为 |
|--------|---------------|-----------|
| 卡片一句话总结 | `sentenceEl.onclick = function() { openSidebarWithContext('group-' + groupId, { focus, focusLevel, sentence, raw: { groupData } }) }` | 打开项目群分析，传入 sentence 作为焦点上下文 |
| 卡片 AI 按钮 | `onclick="event.stopPropagation(); handleCardClick('project-group:V2')"` | 打开项目群分析（与一句话相同 builder，但无焦点上下文） |
| AI 智能评估文字 | `onclick="handleCardClick('ai-summary-group')"` → `openSidebarWithContext('group-summary', ...)` | 打开项目群汇总分析 |
| 猜你想问 | `onclick="handleIntentClick('${q}')"` | 打开聊天侧边栏 + 自动发送问题 |

### Vue 实现差异

| 交互点 | Vue 组件层 emit | Vue handler | 问题 |
|--------|----------------|-------------|------|
| 卡片一句话总结 | `$emit('ai-click', groupKey)` ✅ | `handleGroupAIClick(groupKey)` | ❌ `groupMeta`/`groupSummary` 未定义 |
| 卡片 AI 按钮 | `$emit('ai-click', groupKey)` ✅ | `handleGroupAIClick(groupKey)` | ❌ `groupMeta`/`groupSummary` 未定义 |
| AI 智能评估文字 | `$emit('summary-click')` ✅ | `handleGroupSummaryClick()` | ❌ `groupSummary` 未定义 |
| 猜你想问 | `$emit('question-click', q)` ✅ | `handleGroupQuestionClick(q)` | ❌ `groupSummary` 未定义 |

### 设计稿与 Vue 的逻辑差异

| 差异点 | 设计稿 | Vue 当前 |
|--------|--------|---------|
| 一句话总结 vs AI 按钮行为区分 | 一句话点击传入 `sentence/focus/focusLevel` 上下文，AI 按钮无上下文 | 两者都调用同一个 `handleGroupAIClick`，无区分 |
| builder 名称 | 一句话/AI 按钮使用 `openSidebarWithContext('group-V2')` → `group-V2` builder | 使用 `group` builder |
| 侧边栏数据来源 | `window.projectGroupsData[groupId]` | 应为 `groupData[groupKey]` |

## 修改方案

### 修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `web/src/views/ProjectKanbanView.vue` | 1. 添加 `groupMeta` computed 定义 2. 添加 `groupSummary` computed 定义 3. 修复 `handleGroupAIClick` 区分一句话 vs AI 按钮 4. 修复 `handleGroupQuestionClick` 使用 `groupSummaryData` |

### 具体修改点

#### 1. 定义 `groupMeta` 和 `groupSummary` computed（ProjectKanbanView.vue）

在第230行附近添加：

```js
// 项目群元数据映射（groupKey → groupData[key]）
const groupMeta = computed(() => {
  const map = {}
  groupKeys.value.forEach(key => {
    map[key] = groupData[key] || {}
  })
  return map
})

// 项目群汇总数据
const groupSummary = computed(() => groupData.summary || {})
```

#### 2. 修复 `handleGroupAIClick`（ProjectKanbanView.vue）

设计稿中，一句话点击传 `sentence/focus/focusLevel` 上下文，AI 按钮无上下文。当前两者都调用同一个 handler，需要区分：

**方案A（推荐）：** 保持共用 handler，一句话点击额外传 sentence 参数

GroupCard.vue 一句话区域：
```html
<!-- 当前：@click.stop="$emit('ai-click', groupKey)" -->
<!-- 修改为：@click.stop="$emit('summary-click', groupKey)" -->
```

新增 `handleGroupSummarySentenceClick(groupKey)` handler，传入 sentence 上下文（与设计稿一致）。

**方案B：** 仅修复变量引用，不区分行为

直接用 `groupData[groupKey]` 替代 `groupMeta[groupKey]`，用 `groupSummaryData.value` 替代 `groupSummary`。

#### 3. 修复 `handleGroupSummaryClick` 和 `handleGroupQuestionClick`

将 `groupSummary` 替换为 `groupSummaryData.value`。

### 推荐修改方案（方案B，最小改动）

| 修改点 | 文件 | 具体改动 |
|--------|------|---------|
| M1 | ProjectKanbanView.vue 第335-338行 | `handleGroupAIClick`: 用 `groupData[groupKey]` 替代 `groupMeta[groupKey]`，用 `groupSummaryData.value` 替代 `groupSummary` |
| M2 | ProjectKanbanView.vue 第375-378行 | `handleGroupQuestionClick`: 用 `groupSummaryData.value` 替代 `groupSummary` |
| M3 | ProjectKanbanView.vue 第380-382行 | `handleGroupSummaryClick`: 用 `groupSummaryData.value` 替代 `groupSummary` |
| M4（可选增强） | GroupCard.vue + ProjectKanbanView.vue | 新增 `@summary-click` emit 区分一句话点击 vs AI 按钮点击，一句话点击传 sentence 上下文（与设计稿一致） |

## TODO 列表

- [ ] **M1**: 修复 `handleGroupAIClick` 中的 `groupMeta` → `groupData[groupKey]`，`groupSummary` → `groupSummaryData.value`
- [ ] **M2**: 修复 `handleGroupQuestionClick` 中的 `groupSummary` → `groupSummaryData.value`
- [ ] **M3**: 修复 `handleGroupSummaryClick` 中的 `groupSummary` → `groupSummaryData.value`
- [ ] **M4**: （可选增强）GroupCard.vue 一句话区域 emit `summary-click` 事件，新增 `handleGroupSummarySentenceClick` handler 传入 sentence/focus 上下文（与设计稿行为一致）
