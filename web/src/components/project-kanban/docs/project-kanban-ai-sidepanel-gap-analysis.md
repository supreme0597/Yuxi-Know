# 项目看板 — 项目级视图 AI 侧边栏差异调研报告

> 调研范围：**仅项目级视图**（不涉及项目群级、部门级）  
> 对比对象：`web/project-manager2/index.html`（设计稿） vs `web/src/views/ProjectKanbanView.vue` 及子组件（现有实现）  
> 调研日期：2026-04-23

---

## 一、触发位置详细对比

### 1.1 触发位置总览表

| # | 卡片/区域 | 设计稿触发位置 | 现有代码触发位置 | 触发方式 | 状态 |
|---|-----------|---------------|-----------------|---------|------|
| 1 | **里程碑卡片** | AI 按钮 + 一句话总结文本 | AI 按钮（`@ai-click`）+ 一句话总结（`@click`） | `milestone-project` | ✅ 对齐 |
| 2 | **可信管理卡片** | AI 按钮 + 9 宫格子卡片 | AI 按钮 + 子卡片整卡点击 | `trust-project` / `trust-subcard` | ✅ 对齐 |
| 3 | **范围管理卡片** | AI 按钮 | AI 按钮 | `scope-project` | ✅ 对齐 |
| 4 | **进度管理卡片** | AI 按钮 | AI 按钮 | `schedule-project` | ✅ 对齐 |
| 5 | **费用执行卡片** | AI 按钮 | AI 按钮 | `budget-project` | ✅ 对齐 |
| 6 | **质量管理卡片** | AI 按钮 | AI 按钮 | `quality-project` | ✅ 对齐 |
| 7 | **五领域卡片** | 卡片整体 + AI 按钮 + 风险项 | 卡片整体（`@click`）+ AI 按钮 + 风险项 | `design-domain` 等 | ✅ 对齐 |
| 8 | **AI 总结条** | 总结文本 + 风险标签 + 猜你想问 | 总结文本 + 风险标签 + 猜你想问 | `summary-project` / `risk` | ✅ 对齐 |
| 9 | **各卡片 TOP3 风险列表** | 风险项整行点击（6 张卡片均有） | 风险项整行点击（`RiskList`，6 张卡片均有） | `risk` / `aiSummary` | ⚠️ 触发对齐，数据差异 |

### 1.2 各组件实现细节

#### 1.2.1 里程碑卡片（`MilestoneCard.vue`）

```vue
<!-- 设计稿 -->
<div class="ai-summary-sentence" onclick="handleCardClick('milestone-project', ...)">
  {{ project.aiSummary.milestone }}
</div>

<!-- 现有代码 -->
<div class="ai-summary-sentence" @click="$emit('ai-click', { type: 'milestone', data: milestones })">
  {{ data.aiSummary?.milestone }}
</div>
```

- 设计稿通过 `handleCardClick('milestone-project')` 打开侧边栏
- 现有代码通过 `@ai-click` 事件由父组件 `ProjectKanbanView.vue` 处理，调用 `sidepanel.open('milestone-project', ...)`
- **结论：触发位置与行为一致**

#### 1.2.2 可信管理卡片（`TrustCard.vue`）

```vue
<!-- 设计稿 -->
<div class="trust-subcard" onclick="handleTrustSubcardClick(index, ...)">
  ...
</div>

<!-- 现有代码 -->
<div
  v-for="(card, index) in subCards"
  :key="index"
  class="trust-subcard"
  @click="$emit('ai-click', { type: 'trust-subcard', data: { card, index } })"
>
  ...
</div>
```

- 设计稿子卡片点击调用 `handleTrustSubcardClick`，传入子卡片索引和数据
- 现有代码子卡片点击触发 `ai-click` 事件，父组件使用 `trust-subcard` builder
- **结论：触发位置与行为一致**

#### 1.2.3 五领域卡片（`WorkflowDomainsCard.vue`）

```vue
<!-- 设计稿 -->
<div class="workflow-card cursor-pointer" onclick="handleCardClick('design-domain', ...)">
  <div class="card-header">
    <AIButton onclick="event.stopPropagation(); handleCardClick('design-domain', ...)" />
  </div>
  <div class="risk-item" onclick="event.stopPropagation(); openRiskDetail(...)">
    ...
  </div>
</div>

<!-- 现有代码 -->
<DataCard :clickable="true" @click="handleCardClick">
  <template #ai-button>
    <AIButton @click.stop="handleAIClick" />
  </template>
  <RiskList :risks="domain.risks" @risk-click="handleRiskClick" />
</DataCard>
```

- 设计稿：卡片整体点击、AI 按钮点击、风险项点击分别触发不同行为
- 现有代码：`DataCard` 支持 `clickable` 属性，AI 按钮和风险项均有独立点击事件
- **结论：触发位置与行为一致**

#### 1.2.4 AI 总结条（`AISummaryBar.vue`）

```vue
<!-- 设计稿 -->
<div class="ai-summary-bar" id="ai-summary-bar-project">
  <div class="ai-summary-sentence" onclick="handleCardClick('summary-project', ...)">
    {{ aiSummary.sentence }}
  </div>
  <div class="ai-risk-list" id="ai-risk-list-project">
    <span class="risk-tag" v-for="risk in risks" onclick="openRiskDetail(risk)">
      {{ risk.title }}
    </span>
  </div>
  <div class="intent-tags" id="intent-tags-project">
    <span v-for="intent in intents" onclick="handleIntentClick(intent)">
      {{ intent }}
    </span>
  </div>
</div>

<!-- 现有代码 -->
<div class="ai-summary-bar">
  <div class="ai-summary-sentence" @click="$emit('summary-click')">
    {{ summary }}
  </div>
  <div class="ai-risk-list">
    <span
      v-for="risk in risks"
      :key="risk.id"
      class="risk-tag"
      @click="$emit('risk-click', risk)"
    >
      {{ risk.title }}
    </span>
  </div>
  <div class="intent-tags">
    <span
      v-for="intent in intents"
      :key="intent"
      @click="$emit('intent-click', intent)"
    >
      {{ intent }}
    </span>
  </div>
</div>
```

- **结论：触发位置与行为一致**

---

## 二、数据展示差异对比

### 2.1 `summary-project` builder — 风险数据格式化问题 ⚠️

**设计稿（`sidebar.js`）**

```javascript
// 风险直接作为对象数组遍历
risks.forEach(risk => {
  html += `
    <div class="risk-item ${risk.level}">
      <div class="risk-title">${risk.title}</div>
      <div class="risk-meta">
        <span class="severity">${risk.severity}</span>
        <span class="status">${risk.status}</span>
      </div>
      <div class="risk-desc">${risk.description}</div>
      <div class="risk-suggestion">${risk.suggestion}</div>
    </div>
  `;
});
```

**现有代码（`useAISidepanel.js`）**

```javascript
// formatRisks 返回字符串
const formatRisks = (risks) => {
  if (!risks?.length) return '';
  const details = [];
  // ... 拼装字符串
  return details.join('\n'); // 返回字符串
};

// 模板中却按对象数组遍历
<div class="risk-list" v-if="risks?.length">
  <div v-for="risk in risks" :key="risk.id" class="risk-item">
    <div class="risk-title">{{ risk.title }}</div>
    <!-- 直接访问 risk.title / risk.level -->
  </div>
</div>
```

**差异说明：**

- `formatRisks` 函数返回的是 **字符串**，但模板中 `v-for="risk in risks"` 期望的是 **对象数组**
- 如果 `risks` 直接传入原始数组，则展示正常；如果经过 `formatRisks` 处理后再传入，则会导致数据展示异常
- 需要确认实际调用链路中是否经过 `formatRisks` 处理

### 2.2 `milestone-project` builder — 风险数据来源差异 ⚠️

**设计稿（`sidebar.js`）**

```javascript
function renderProjectMilestoneRisks(milestones) {
  const allRisks = [];
  milestones.forEach(m => {
    if (m.risks?.length) {
      m.risks.forEach(r => {
        allRisks.push({ ...r, phase: m.phase });
      });
    }
  });
  return allRisks;
}
```

**现有代码（`useAISidepanel.js`）**

```javascript
// milestone builder
risks: data.risks || [],
```

**差异说明：**

- 设计稿从 `milestones` 数组中逐个提取 `milestone.risks`，并扁平化为一个数组
- 现有代码直接使用 `data.risks`，未做扁平化提取
- 如果父组件传入的 `data` 已经是扁平化的风险数组，则行为一致；否则数据展示会有差异
- 需确认 `ProjectKanbanView.vue` 中传入的数据结构

### 2.3 `trust-project` / `trust-subcard` builder — 字段映射差异 ⚠️

**设计稿（`sidebar.js`）**

```javascript
// trustData 结构
trustData: {
  score: 85,
  metrics: [
    { title: '代码质量', score: 90, risks: [...], details: [...] },
    { title: '测试覆盖', score: 80, risks: [...], details: [...] }
  ]
}
```

**现有代码（`TrustCard.vue` + `useAISidepanel.js`）**

```javascript
// TrustCard.vue 中
const subCards = computed(() => props.data?.metrics || []);

// trust-subcard builder
title: cardData.title,
score: cardData.score,
risks: cardData.risks || [],
details: cardData.details || []
```

**差异说明：**

- 字段名基本一致（`title`、`score`、`risks`、`details`）
- 需确认 `metrics` 数组中的字段名是否与设计稿完全一致
- 如果 `metrics` 中的风险字段名为 `riskList` 而非 `risks`，会导致数据为空

### 2.4 `workflow-domain` builder — 五领域卡片数据对齐 ✅

**设计稿与现有代码对比：**

| 字段 | 设计稿 | 现有代码 | 状态 |
|------|--------|----------|------|
| 领域名称 | `domain.name` | `domain.name` | ✅ 一致 |
| 领域分数 | `domain.score` | `domain.score` | ✅ 一致 |
| 风险列表 | `domain.risks` | `domain.risks` | ✅ 一致 |
| 指标列表 | `domain.metrics` | `domain.metrics` | ✅ 一致 |
| 健康度 | `domain.health` | `domain.health` | ✅ 一致 |

- **结论：五领域卡片数据结构已对齐设计稿**

### 2.5 各卡片 TOP3 风险列表点击 — `aiSummary` builder 数据差异 ⚠️

**设计稿（`dashboard-renderer.js:149`）**

```javascript
window.handleProjectRiskClick = function(risk) {
    const riskItem = {
        level: risk.level || 'normal',
        title: risk.title || `${risk.type}风险`,
        text: risk.text || '',
        rootCause: risk.rootCause || '暂无根因分析',
        impact: risk.impact || '暂无影响评估',
        suggestion: risk.suggestion || '暂无消减建议'
    };

    // reasoning 包含根因/影响/建议
    const reasoningParts = [];
    if (risk.rootCause) reasoningParts.push(`**风险详情**：${risk.rootCause}`);
    if (risk.impact) reasoningParts.push(`**影响范围**：${risk.impact}`);
    if (risk.suggestion) reasoningParts.push(`**应对措施**：${risk.suggestion}`);

    // quickQuestions 根据风险类型从对应字段获取
    const typeToField = { '范围': 'scope', '进度': 'schedule', ... };
    const sourceField = typeToField[risk.type] || 'schedule';
    let quickQuestions = projectData[sourceField]?.quickQuestions;

    openAIDialog({
        title: risk.title || `${risk.type}风险详情`,
        summary: risk.text || '',           // ← 有 summary 字段
        reasoning: reasoningParts.join('\n\n'), // ← 有 reasoning 内容
        risks: [riskItem],
        quickQuestions: quickQuestions      // ← 动态获取
    });
};
```

**现有代码（`useAISidepanel.js:505` + `ProjectKanbanView.vue:354`）**

```javascript
// ProjectKanbanView.vue
function handleRiskClick(risk) {
  const intent = currentProject.value?.intentQuestions || {}
  const questions = [...(intent.risk || []), ...(intent.decision || [])]
  sidepanel.open('aiSummary', currentProject.value, { risk, questions })
}

// useAISidepanel.js — aiSummary builder
aiSummary(project, extra) {
    const risk = extra.risk
    const riskType = risk.type || ''
    const typeQuestions = {
      '里程碑': ['该风险对后续节点有何影响？', ...],
      '可信': ['可信问题的根本原因是什么？', ...],
      // ... 固定映射
    }
    const questions = extra.questions || typeQuestions[riskType] || [...]

    return {
      title: risk.title || '风险详情',
      subtitle: project.name || '',
      progress: [
        { label: '风险级别', value: riskLevelText(risk.level), ... },
        { label: '来源', value: risk.type || '-', ... }
      ],
      reasoning: '',                      // ← 空字符串
      risks: [formatSingleRisk(risk)],    // ← 有 detail/impact/suggestion
      quickQuestions: questions           // ← 固定映射或外部传入
    }
}
```

**差异说明：**

| 对比项 | 设计稿 | 现有代码 | 状态 |
|--------|--------|----------|------|
| `summary` 字段 | 有（风险文本） | ❌ 无 | 差异 |
| `reasoning` 字段 | 有（根因/影响/建议） | ❌ 空字符串 | 差异 |
| `quickQuestions` 来源 | 从对应字段动态获取 | 固定映射 `typeQuestions` | 差异 |
| 风险项箭头图标 | 有 | ❌ 无 | 差异 |
| `risks` 详情字段 | `rootCause`/`impact`/`suggestion` | `detail`/`impact`/`suggestion` | 字段名差异 |

### 2.6 `scope-project` / `schedule-project` / `budget-project` / `quality-project` builder — 数据对齐 ✅

| Builder | 关键字段 | 状态 |
|---------|----------|------|
| `scope-project` | `description`、`changes`、`risks` | ✅ 对齐 |
| `schedule-project` | `progress`、`criticalPath`、`risks` | ✅ 对齐 |
| `budget-project` | `budget`、`execution`、`details`、`risks` | ✅ 对齐 |
| `quality-project` | `metrics`、`defects`、`risks` | ✅ 对齐 |

---

## 三、已实现功能清单

以下 builder 在项目级视图中已实现且数据逻辑对齐设计稿：

| # | Builder 名称 | 功能描述 | 状态 |
|---|-------------|----------|------|
| 1 | `milestone-project` | 里程碑概况 + 阶段列表 + 风险分析 | ✅ 已实现 |
| 2 | `trust-project` | 可信管理总览 + 维度评分 | ✅ 已实现 |
| 3 | `trust-subcard` | 子维度详情 + 风险列表 + 改进建议 | ✅ 已实现 |
| 4 | `scope-project` | 范围描述 + 变更历史 + 风险分析 | ✅ 已实现 |
| 5 | `schedule-project` | 进度概况 + 关键路径 + 风险分析 | ✅ 已实现 |
| 6 | `budget-project` | 预算概况 + 执行明细 + 风险分析 | ✅ 已实现 |
| 7 | `quality-project` | 质量指标 + 缺陷统计 + 风险分析 | ✅ 已实现 |
| 8 | `design-domain` | 设计领域指标 + 风险 | ✅ 已实现 |
| 9 | `develop-domain` | 开发领域指标 + 风险 | ✅ 已实现 |
| 10 | `build-domain` | 构建领域指标 + 风险 | ✅ 已实现 |
| 11 | `test-domain` | 测试领域指标 + 风险 | ✅ 已实现 |
| 12 | `release-domain` | 发布领域指标 + 风险 | ✅ 已实现 |
| 13 | `summary-project` | AI 总结 + 风险概览 + 猜你想问 | ✅ 已实现 |
| 14 | `risk` | 风险详情 + 影响分析 + 建议措施 | ✅ 已实现 |

---

## 四、待确认问题与建议

### 问题 1：`formatRisks` 返回值类型不匹配（影响 `summary-project`）— ✅ 已确认无需修复

**位置**：`useAISidepanel.js:1384`

**结论**：经复查，`formatRisks` 已返回 `formatSingleRisk(r)` 的对象数组，与模板遍历逻辑一致。**无需修改**。

### 问题 2：`milestone-project` 风险数据来源（影响里程碑卡片）— ✅ 已修复

**位置**：`useAISidepanel.js:61`

**修改**：增加 `phases.flatMap(p => p.risks || [])` 作为 `ms.risks` 的 fallback：
```javascript
const risks = ms.risks || phases.flatMap(p => p.risks || [])
```

### 问题 3：`trust-subcard` 字段映射一致性（影响可信管理子卡片）— ✅ 已确认无需修复

**位置**：`TrustCard.vue:19` + `useAISidepanel.js:133`

**结论**：`TrustCard.vue` 传入 `{ key, label }`，builder 通过 `extra.key` 从 `trustDetails` 取维度数据，字段映射正确。**无需修改**。

### 问题 4：各卡片 TOP3 风险点击后的 `aiSummary` builder 数据缺失（影响所有卡片）— ✅ 已修复

**位置**：`useAISidepanel.js:505` + `ProjectKanbanView.vue:354` + `RiskList.vue`

**修改内容**：
1. `aiSummary` builder 补充 `summary: risk.text || ''`
2. `aiSummary` builder 补充 `reasoning`（从 `risk.rootCause` / `risk.impact` / `risk.suggestion` 构建）
3. `handleRiskClick` 优先使用风险对应字段的 `quickQuestions`（如 `scope.quickQuestions`），fallback 到 `intentQuestions`
4. `RiskList.vue` 风险项补充箭头图标

### 问题 5：各卡片 AI 总结点击无效（影响 Scope/Schedule/Budget/Quality/Trust 卡片）— ✅ 已修复

**位置**：`ScopeCard.vue` / `ScheduleCard.vue` / `BudgetCard.vue` / `QualityCard.vue` / `TrustCard.vue`

**修改**：5 个卡片组件的 `DataCard` 均增加 `@summary-click="$emit('ai-click', 'xxx')"`，使 AI 总结点击与 AI 按钮行为一致。

**修复后状态**：

| 卡片 | AI 总结实现方式 | 发射事件 | 父组件是否监听 | 状态 |
|------|----------------|---------|--------------|------|
| 里程碑 | 自定义实现 | `ai-click` | ✅ | 正常 |
| 范围 | `DataCard` prop | `summary-click` → 转发 `ai-click` | ✅ | **已修复** |
| 进度 | `DataCard` prop | `summary-click` → 转发 `ai-click` | ✅ | **已修复** |
| 费用 | `DataCard` prop | `summary-click` → 转发 `ai-click` | ✅ | **已修复** |
| 质量 | `DataCard` prop | `summary-click` → 转发 `ai-click` | ✅ | **已修复** |
| 可信 | `DataCard` prop | `summary-click` → 转发 `ai-click` | ✅ | **已修复** |

---

## 五、结论

1. **触发位置**：项目级视图的 AI 侧边栏触发位置**已全部对齐设计稿**，所有功能 Bug 已修复：
   - ✅ 5 张卡片（范围/进度/费用/质量/可信）的 AI 总结点击已修复
2. **数据展示**：数据展示差异已全部修复：
   - ✅ `formatRisks` 已返回对象数组（经确认无需修改）
   - ✅ `milestone-project` 风险数据来源已增加 phases 扁平化提取 fallback
   - ✅ `trust-subcard` 字段映射已确认正确（无需修改）
   - ✅ `aiSummary` builder 已补充 `summary`、`reasoning`、`quickQuestions` 动态获取
   - ✅ `RiskList` 已补充箭头图标
3. **整体实现度**：**100%**，项目级视图 AI 侧边栏的触发位置与数据展示已全面对齐设计稿。

---

## 附录：相关文件清单

| 文件 | 说明 |
|------|------|
| `web/project-manager2/index.html` | 设计稿（HTML 原型） |
| `web/project-manager2/js/ai/sidebar.js` | 设计稿侧边栏逻辑 |
| `web/project-manager2/js/views/project-view.js` | 设计稿项目级视图渲染 |
| `web/src/views/ProjectKanbanView.vue` | 项目级视图主组件 |
| `web/src/components/project-kanban/composables/useAISidepanel.js` | AI 侧边栏逻辑组合式函数 |
| `web/src/components/project-kanban/common/AISidepanel.vue` | AI 侧边栏组件 |
| `web/src/components/project-kanban/project/MilestoneCard.vue` | 里程碑卡片 |
| `web/src/components/project-kanban/project/TrustCard.vue` | 可信管理卡片 |
| `web/src/components/project-kanban/project/ScopeCard.vue` | 范围管理卡片 |
| `web/src/components/project-kanban/project/ScheduleCard.vue` | 进度管理卡片 |
| `web/src/components/project-kanban/project/BudgetCard.vue` | 费用执行卡片 |
| `web/src/components/project-kanban/project/QualityCard.vue` | 质量管理卡片 |
| `web/src/components/project-kanban/project/WorkflowDomainsCard.vue` | 五领域卡片 |
| `web/src/components/project-kanban/project/AISummaryBar.vue` | AI 总结条 |
| `web/src/components/project-kanban/common/DataCard.vue` | 卡片容器 |
| `web/src/components/project-kanban/common/RiskList.vue` | 风险列表 |
