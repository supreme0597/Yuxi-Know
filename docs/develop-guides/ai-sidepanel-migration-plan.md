# AI 侧边栏功能迁移计划

> HTML 原版 (`project-manager2`) → Vue 重写版 (`project-kanban`)
>
> 生成时间：2026-04-22

## 文档说明

本文档记录 HTML 原版与 Vue 重写版 AI 侧边栏功能的完整差异，并为每项差异提供代码级改动方案。

**涉及核心文件**：

| 文件 | 路径 | 职责 |
|------|------|------|
| useAISidepanel.js | `web/src/components/project-kanban/composables/useAISidepanel.js` | 所有 builder 逻辑（25 项中 23 项涉及） |
| AISidepanel.vue | `web/src/components/project-kanban/common/AISidepanel.vue` | 侧边栏 UI 组件 |
| ProjectKanbanView.vue | `web/src/views/ProjectKanbanView.vue` | 事件处理函数 |
| deptData.js | `web/src/components/project-kanban/data/deptData.js` | 部门级 Mock 数据 |
| 各 dept/ 组件 | `web/src/components/project-kanban/dept/` | 部门级卡片组件 |

---

## 🔴 部门级差异（16 项）

---

### A. `budget-dept` 子项点击缺少「焦点问题」

**严重度**：🟡 中

**HTML 原版**（`dashboard-renderer.js:2800-2818`）：

```js
window.openBudgetProjectDetail = function(idx) {
    var project = (window._budgetProjects && window._budgetProjects[idx]) || {};
    var deviation = project.deviation || 0;
    var projectName = project.name || '项目';

    // ✅ 动态生成焦点文本：根据 deviation 正负判断"超支"或"结余"
    var focusText = projectName + ' 费用执行' + (deviation > 0 ? '超支' : '结余') + Math.abs(deviation) + '%';
    var focusLevel = Math.abs(deviation) > 20 ? 'danger' : (Math.abs(deviation) > 10 ? 'warning' : 'safe');

    openSidebarWithContext('budget-project', {
        focus: focusText,          // 如 "208.11-208.12开发项目 费用执行超支15%"
        focusLevel: focusLevel,
        sentence: focusText,
        raw: { project: project }
    });
};
```

侧边栏处理（`sidebar.js:1129-1144`）：

```js
case 'budget-project': {
    // ...
    if (focus) {
        progressItems.push({ label: '焦点问题', value: focus, status: focusLevel === 'danger' ? 'danger' : 'warning' });
    }
    progressItems.push({ label: '预算总额', value: ... });
    progressItems.push({ label: '已执行', value: ... });
    progressItems.push({ label: '执行率', value: ... });
}
```

**Vue 现版**（`useAISidepanel.js:668-684`）：

```js
if (extra?.project) {
    const proj = extra.project
    const rate = proj.budget > 0 ? Math.round((proj.executed || 0) / proj.budget * 100) : 0
    const projRisks = proj.risks || []
    return {
        title: `费用执行 · ${proj.name || ''}`,
        subtitle: '部门级',
        progress: [
            // ❌ 缺少「焦点问题」
            { label: '预算', value: `${proj.budget || 0}M`, status: 'normal' },
            { label: '已执行', value: `${proj.executed || 0}M`, status: 'normal' },
            { label: '执行率', value: `${rate}%`, status: rate < 70 ? 'warning' : 'normal' }
        ],
        // ...
    }
}
```

**数据来源**：`deptData.js` 中 `budget.projects[].deviation` 字段已存在（如 `-15`, `5`, `-3`, `-12`）。

**改动方案**：

| 文件 | 改动 |
|------|------|
| `useAISidepanel.js:668-684` | 在 `extra.project` 分支动态计算焦点问题 |

```js
// 改动位置：useAISidepanel.js 第 669 行之后
if (extra?.project) {
    const proj = extra.project
    const rate = proj.budget > 0 ? Math.round((proj.executed || 0) / proj.budget * 100) : 0
    const projRisks = proj.risks || []

    // ✅ 新增：动态生成焦点问题
    const deviation = proj.deviation || 0
    const focusText = `${proj.name || '项目'} 费用执行${deviation > 0 ? '超支' : '结余'}${Math.abs(deviation)}%`
    const focusLevel = Math.abs(deviation) > 20 ? 'danger' : (Math.abs(deviation) > 10 ? 'warning' : 'normal')

    const progressItems = []
    if (Math.abs(deviation) > 10) {
        progressItems.push({ label: '焦点问题', value: focusText, status: focusLevel })
    }
    progressItems.push({ label: '预算', value: `${proj.budget || 0}M`, status: 'normal' })
    progressItems.push({ label: '已执行', value: `${proj.executed || 0}M`, status: 'normal' })
    progressItems.push({ label: '执行率', value: `${rate}%`, status: rate < 70 ? 'warning' : 'normal' })

    return {
        title: `费用执行 · ${proj.name || ''}`,
        subtitle: '部门级',
        progress: progressItems,
        reasoning: proj.aiSummary || budget.aiSummary || '',
        risks: formatRisks(projRisks),
        quickQuestions: proj.quickQuestions || budget.quickQuestions || []
    }
}
```

**其他文件无需改动**：`handleDeptBudgetProjectClick(project)` 已传完整 project 对象，builder 内可直接用 `proj.deviation`。

---

### B. `ahb` 子项点击缺少「焦点问题」

**严重度**：🟡 中

**HTML 原版**（`sidebar.js:696-741`）：

```js
case 'ahb-category': {
    var catData = raw.catData || {};
    var catLabel = catData.label || raw.catName || '';
    var deviation = catData.deviation || 0;
    // ...
    if (focus) {
        progressItems.push({ label: '焦点问题', value: focus, status: focusLevel === 'danger' ? 'danger' : 'warning' });
    }
    progressItems.push({ label: '工作量', value: workload + '人月', status: 'normal' });
    // ...
}
```

HTML 入口（`dashboard-renderer.js` 中 ahb 子卡片 click）动态生成 focus：
```js
focusText = catLabel + ' 人力缺口' + Math.abs(deviation) + '人月';
```

**Vue 现版**（`useAISidepanel.js:592-618`）：

```js
if (extra?.category) {
    const cat = extra.category
    // ...
    return {
        progress: [
            // ❌ 缺少焦点问题
            { label: '工作量', value: `${cat.workload || 0}人月`, status: 'normal' },
            { label: '人力', value: `${cat.total || 0}人月`, status: 'normal' },
            // ...
        ],
    }
}
```

**数据来源**：`deptData.js` 中 `ahb.categories[].deviation` 已存在。

**改动方案**：

| 文件 | 改动 |
|------|------|
| `useAISidepanel.js:592-618` | 在 `extra.category` 分支动态计算焦点问题 |

```js
if (extra?.category) {
    const cat = extra.category
    const catUtil = cat.total > 0 ? Math.round((cat.workload || 0) / cat.total * 100) : 0
    const catRisks = cat.risks || []

    // ✅ 新增：动态生成焦点问题
    const deviation = cat.deviation || 0
    const focusText = deviation < 0
        ? `${cat.label || ''} 人力缺口${Math.abs(deviation)}人月`
        : `${cat.label || ''} 人力富余${deviation}人月`
    const focusLevel = Math.abs(deviation) > 10 ? 'danger' : (Math.abs(deviation) > 5 ? 'warning' : 'normal')

    const progressItems = []
    if (Math.abs(deviation) > 5) {
        progressItems.push({ label: '焦点问题', value: focusText, status: focusLevel })
    }
    progressItems.push({ label: '工作量', value: `${cat.workload || 0}人月`, status: 'normal' })
    progressItems.push({ label: '人力', value: `${cat.total || 0}人月`, status: 'normal' })
    progressItems.push({ label: '利用率', value: `${catUtil}%`, status: catUtil > 100 ? 'danger' : (catUtil > 90 ? 'warning' : 'normal') })
    progressItems.push({ label: '偏差', value: `${deviation > 0 ? '+' : ''}${deviation}人月`, status: Math.abs(deviation) > 10 ? 'danger' : (Math.abs(deviation) > 5 ? 'warning' : 'normal') })

    // ... keyPoints, reasoning, risks, quickQuestions 不变
}
```

---

### C. `task-dept` 子项点击 progress 缺风险等级/延期状态

**严重度**：🟡 中

**HTML 原版**（`sidebar.js:744-762`）：

```js
case 'task-ring': {
    progressItems.push({ label: '任务令名称', value: taskName, status: 'normal' });
    progressItems.push({ label: '截止日期', value: deadline, status: overdue ? 'danger' : 'normal' });
    progressItems.push({ label: '完成进度', value: progress + '%', status: ... });
    progressItems.push({ label: '风险等级', value: risk === 'high' ? '高' : (risk === 'medium' ? '中' : '低'), status: ... });
    progressItems.push({ label: '延期状态', value: overdue ? '已延期' : '正常', status: overdue ? 'danger' : 'normal' });
}
```

**Vue 现版**（`useAISidepanel.js:726-746`）：

```js
if (extra?.taskOrder) {
    const to = extra.taskOrder
    // ...
    return {
        progress: [
            { label: '进度', value: `${to.progress || 0}%`, status: ... },
            { label: '行业', value: to.industry || '-', status: 'normal' },
            { label: '负责人', value: to.owner || '-', status: 'normal' },
            { label: '截止', value: to.deadline || '-', status: to.status === 'overdue' ? 'danger' : 'normal' }
            // ❌ 缺少：风险等级、延期状态
        ],
    }
}
```

**数据来源**：`deptData.js` 中 `task.taskOrders[].risk`（`'high'/'medium'/'none'`）和 `task.taskOrders[].status`（含 `'overdue'`）已存在。

**改动方案**：

| 文件 | 改动 |
|------|------|
| `useAISidepanel.js:726-746` | 在 `extra.taskOrder` 分支增加风险等级和延期状态 |

```js
if (extra?.taskOrder) {
    const to = extra.taskOrder
    const toRisks = to.risks || []
    const keyPoints = (to.phases || []).map(p => `${p.name}(${p.date}): ${p.status === 'completed' ? '已完成' : p.status === 'active' ? '进行中' : '待启动'}`)

    // ✅ 新增：风险等级映射
    const riskMap = { high: '高', medium: '中', low: '低', none: '低' }
    const riskLevel = to.risk || 'none'
    const isOverdue = to.status === 'overdue'

    return {
        title: `任务令 · ${to.name || ''}`,
        subtitle: to.project || '部门级',
        progress: [
            { label: '任务令名称', value: to.name || '-', status: 'normal' },
            { label: '截止日期', value: to.deadline || '-', status: isOverdue ? 'danger' : 'normal' },
            { label: '完成进度', value: `${to.progress || 0}%`, status: (to.progress || 0) >= 100 ? 'normal' : ((to.progress || 0) < 50 ? 'danger' : 'warning') },
            { label: '风险等级', value: riskMap[riskLevel] || '低', status: riskLevel === 'high' ? 'danger' : (riskLevel === 'medium' ? 'warning' : 'normal') },
            { label: '延期状态', value: isOverdue ? '已延期' : '正常', status: isOverdue ? 'danger' : 'normal' }
        ],
        keyPoints,
        reasoning: to.aiSummary || task.aiSummary || '',
        risks: formatRisks(toRisks),
        quickQuestions: to.quickQuestions || task.quickQuestions || []
    }
}
```

---

### D. 缺少 `online-dept` 独立 builder

**严重度**：🟡 中

**HTML 原版**（`sidebar.js:813-844`）：

```js
case 'online-dept': {
    var onlineData = qv.online || {};
    var onlineRisks = onlineData.risks || [];
    var progressItems = [];
    if (focus) {
        progressItems.push({ label: '焦点问题', value: focus, status: 'warning' });
    }
    progressItems.push({ label: '今年基线', value: (onlineData.yearlyBase || 0) + '个', status: 'normal' });
    progressItems.push({ label: '今年新增', value: (onlineData.yearlyNew || 0) + '个', status: onlineData.yearlyNew > 0 ? 'warning' : 'normal' });
    progressItems.push({ label: '本月新增', value: (onlineData.monthlyNew || 0) + '个', status: onlineData.monthlyNew > 0 ? 'warning' : 'normal' });
    // reasoning, risks, quickQuestions ...
}
```

**Vue 现版**：`groups-overview` builder 的 `extra.dimension` 分支（第 785-816 行）仅用 `dim.stats` 映射 progress，缺少独立的今年基线/今年新增/本月新增字段。

**改动方案**：

| 文件 | 改动 |
|------|------|
| `useAISidepanel.js` | 在 `groups-overview` builder 的 `dimKey === 'online'` 分支中，替换通用 `dim.stats` 为专用 progress 构建 |
| `ProjectKanbanView.vue` | 无需改动（`handleDeptDimClick` 已传 dimension 对象） |

```js
// useAISidepanel.js groups-overview builder 内，替换 dimKey === 'online' 分支
if (dimKey === 'online') {
    dimData = go.online || {}
    risks = dimData.risks || []
    const onlineData = dimData
    const progressItems = []
    if (dim.sentence) {
        progressItems.push({ label: '焦点问题', value: dim.sentence, status: 'warning' })
    }
    progressItems.push({ label: '今年基线', value: `${onlineData.yearlyBase || 0}个`, status: 'normal' })
    progressItems.push({ label: '今年新增', value: `${onlineData.yearlyNew || 0}个`, status: (onlineData.yearlyNew || 0) > 0 ? 'warning' : 'normal' })
    progressItems.push({ label: '本月新增', value: `${onlineData.monthlyNew || 0}个`, status: (onlineData.monthlyNew || 0) > 0 ? 'warning' : 'normal' })

    return {
        title: '网上表现详情分析',
        subtitle: '部门级',
        progress: progressItems,
        reasoning: onlineData.aiSummary || dim.sentence || '',
        risks: formatRisks(risks),
        quickQuestions: onlineData.quickQuestions || ['关键问题的修复进展如何？', '是否有回归风险？', '监控告警是否正常？']
    }
}
```

---

### E. 缺少 `downstream-dept` 独立 builder

**严重度**：🟡 中

**HTML 原版**（`sidebar.js:847-878`）：

```js
case 'downstream-dept': {
    var dsData = qv.downstream || {};
    var progressItems = [];
    if (focus) {
        progressItems.push({ label: '焦点问题', value: focus, status: 'danger' });
    }
    progressItems.push({ label: '今年基线', value: (dsData.yearlyBase || 0) + '个', status: 'normal' });
    progressItems.push({ label: '今年新增', value: (dsData.yearlyNew || 0) + '个', status: dsData.yearlyNew > 0 ? 'warning' : 'normal' });
    progressItems.push({ label: '本月新增', value: (dsData.monthlyNew || 0) + '个', status: dsData.monthlyNew > 0 ? 'danger' : 'normal' });
    // reasoning, risks, quickQuestions ...
}
```

**改动方案**：

| 文件 | 改动 |
|------|------|
| `useAISidepanel.js` | 在 `groups-overview` builder 的 `dimKey === 'downstream'` 分支中，替换通用 `dim.stats` 为专用 progress 构建 |

```js
if (dimKey === 'downstream') {
    dimData = go.downstream || {}
    risks = dimData.risks || []
    const dsData = dimData
    const progressItems = []
    if (dim.sentence) {
        progressItems.push({ label: '焦点问题', value: dim.sentence, status: 'danger' })
    }
    progressItems.push({ label: '今年基线', value: `${dsData.yearlyBase || 0}个`, status: 'normal' })
    progressItems.push({ label: '今年新增', value: `${dsData.yearlyNew || 0}个`, status: (dsData.yearlyNew || 0) > 0 ? 'warning' : 'normal' })
    progressItems.push({ label: '本月新增', value: `${dsData.monthlyNew || 0}个`, status: (dsData.monthlyNew || 0) > 0 ? 'danger' : 'normal' })

    return {
        title: '下游依赖详情分析',
        subtitle: '部门级',
        progress: progressItems,
        reasoning: dsData.aiSummary || dim.sentence || '',
        risks: formatRisks(risks),
        quickQuestions: dsData.quickQuestions || ['关键阻塞问题的解决进展如何？', '有哪些依赖需要提前协调？', '是否需要升级到更高层协调？']
    }
}
```

---

### F. 缺少 `trust-dept` 独立 builder

**严重度**：🟡 中

**HTML 原版**（`sidebar.js:1441-1471`）：

```js
case 'trust-dept': {
    var trustData = qv.trustSummary || {};
    var progressItems = [];
    if (focus) {
        progressItems.push({ label: '焦点问题', value: focus, status: 'warning' });
    }
    progressItems.push({ label: '达标率', value: (trustData.overallRate || 0) + '%', status: ... });
    progressItems.push({ label: '预警项', value: (trustData.warningCount || 0) + '个', status: ... });
    progressItems.push({ label: '未达标', value: (trustData.failCount || 0) + '个', status: ... });
    // reasoning, risks, quickQuestions ...
}
```

**改动方案**：

| 文件 | 改动 |
|------|------|
| `useAISidepanel.js` | 在 `groups-overview` builder 的 `dimKey === 'trust'` 分支中，替换通用 `dim.stats` 为专用 progress 构建 |

```js
if (dimKey === 'trust') {
    dimData = go.trustSummary || {}
    risks = dimData.risks || []
    const trustData = dimData
    const progressItems = []
    if (dim.sentence) {
        progressItems.push({ label: '焦点问题', value: dim.sentence, status: 'warning' })
    }
    progressItems.push({ label: '达标率', value: `${trustData.overallRate || 0}%`, status: (trustData.overallRate || 0) < 80 ? 'danger' : 'normal' })
    progressItems.push({ label: '预警项', value: `${trustData.warningCount || 0}个`, status: (trustData.warningCount || 0) > 0 ? 'warning' : 'normal' })
    progressItems.push({ label: '未达标', value: `${trustData.failCount || 0}个`, status: (trustData.failCount || 0) > 0 ? 'danger' : 'normal' })

    return {
        title: '可信管理详情分析',
        subtitle: '部门级',
        progress: progressItems,
        reasoning: trustData.aiSummary || dim.sentence || '',
        risks: formatRisks(risks),
        quickQuestions: trustData.quickQuestions || []
    }
}
```

---

### G. `groups-overview` 默认视图缺风险等级排序/统计 progress

**严重度**：🟡 中

**HTML 原版**（`sidebar.js:1331-1348`）：

```js
// 按风险等级排序：critical > warning > normal
allRisks.sort(function(a, b) { return (levelOrder[a._rawLevel] || 3) - (levelOrder[b._rawLevel] || 3); });
var criticalCount = allRisks.filter(r => r._rawLevel === 'critical' || r._rawLevel === 'danger').length;
var warningCount = allRisks.filter(r => r._rawLevel === 'warning').length;
var normalCount = allRisks.filter(r => r._rawLevel === 'normal').length;

if (focus) {
    progressItems.push({ label: '焦点风险', value: focus, status: ... });
}
progressItems.push({ label: '项目群数', value: '3个', status: 'normal' });
progressItems.push({ label: '高风险', value: criticalCount + '个', status: ... });
progressItems.push({ label: '中风险', value: warningCount + '个', status: ... });
progressItems.push({ label: '正常', value: normalCount + '个', status: 'normal' });
```

**Vue 现版**（`useAISidepanel.js:837-854`）：已有 `criticalCount/warningCount/normalCount` 从 `pr` 数据中读取，但缺少焦点风险项，且风险未按等级排序（`formatRisks` 已做了排序，但 progress 中的统计是从 `pr` 静态字段读取而非动态计算）。

**改动方案**：

| 文件 | 改动 |
|------|------|
| `useAISidepanel.js:837-854` | 默认分支增加焦点风险 progress 项 |

```js
// 默认：整体综合风险分析
const pr = go.projectRisk || {}
const risks = pr.risks || []

const progressItems = []
// ✅ 新增：焦点风险
const topRisk = risks.find(r => normalizeLevel(r.level) === 'danger') || risks.find(r => normalizeLevel(r.level) === 'warning')
if (topRisk) {
    progressItems.push({ label: '焦点风险', value: topRisk.title || '', status: normalizeLevel(topRisk.level) === 'danger' ? 'danger' : 'warning' })
}
progressItems.push({ label: '项目群数', value: `${pr.groupCount || 0}个`, status: 'normal' })
progressItems.push({ label: '高风险', value: `${pr.criticalCount || 0}项`, status: (pr.criticalCount || 0) > 0 ? 'danger' : 'normal' })
progressItems.push({ label: '中风险', value: `${pr.warningCount || 0}项`, status: (pr.warningCount || 0) > 0 ? 'warning' : 'normal' })
progressItems.push({ label: '正常', value: `${pr.normalCount || 0}项`, status: 'normal' })
```

---

### H. `groups-overview` 中 group 点击缺焦点风险/子项目 progress

**严重度**：🟡 中

**HTML 原版**（`sidebar.js:881-914`）：

```js
case 'group-V2':
case 'group-V3':
case 'group-MCU': {
    if (focus) {
        progressItems.push({ label: '焦点风险', value: focus, status: ... });
    }
    progressItems.push({ label: '项目数', value: projectCount + '个', status: 'normal' });
    progressItems.push({ label: '整体进度', value: overallProgress + '%', status: ... });
    progressItems.push({ label: '状态', value: ..., status: ... });
    // ✅ 每个子项目单独一行 progress
    subProjects.forEach(function(p) {
        var pRiskCount = (p.risks || []).filter(...).length;
        progressItems.push({
            label: p.name || p.id,
            value: '进度' + (p.progress || 0) + '%' + (pRiskCount > 0 ? '（' + pRiskCount + '个风险）' : ''),
            status: pRiskCount > 0 ? 'danger' : 'normal'
        });
    });
}
```

**Vue 现版**（`useAISidepanel.js:874-891` `groupRisk` builder）：

```js
progress: [
    { label: '项目数', value: `${gc.projectCount || 0}个`, status: 'normal' },
    { label: '整体进度', value: `${gc.overallProgress || 0}%`, status: ... },
    { label: '风险数', value: `${risks.length}项`, status: ... }
    // ❌ 缺少：焦点风险、子项目逐项 progress
]
```

**改动方案**：

| 文件 | 改动 |
|------|------|
| `useAISidepanel.js:874-891` | `groupRisk` builder 增加焦点风险 + 子项目逐项 progress |

```js
groupRisk(deptData, extra) {
    const gc = extra?.groupCard
    if (!gc) return { title: '项目群风险分析', reasoning: '暂无数据' }

    const risks = gc.risks || []
    const progressItems = []

    // ✅ 新增：焦点风险
    const topRisk = risks.find(r => normalizeLevel(r.level) === 'danger') || risks.find(r => normalizeLevel(r.level) === 'warning')
    if (topRisk) {
        progressItems.push({ label: '焦点风险', value: topRisk.title || '', status: normalizeLevel(topRisk.level) === 'danger' ? 'danger' : 'warning' })
    }
    progressItems.push({ label: '项目数', value: `${gc.projectCount || 0}个`, status: 'normal' })
    progressItems.push({ label: '整体进度', value: `${gc.overallProgress || 0}%`, status: (gc.overallProgress || 0) >= 60 ? 'normal' : 'warning' })
    progressItems.push({ label: '风险数', value: `${risks.length}项`, status: risks.some(r => r.level === 'critical') ? 'danger' : 'normal' })

    // ✅ 新增：子项目逐项 progress
    const subProjects = gc.subProjects || []
    subProjects.forEach(p => {
        const pRiskCount = (p.risks || []).filter(r => normalizeLevel(r.level) !== 'normal').length
        progressItems.push({
            label: p.name || p.id || '',
            value: `进度${p.progress || 0}%${pRiskCount > 0 ? `（${pRiskCount}个风险）` : ''}`,
            status: pRiskCount > 0 ? 'danger' : 'normal'
        })
    })

    return {
        title: `${gc.name || '项目群'}风险分析`,
        subtitle: gc.targetProject || '部门级',
        progress: progressItems,
        reasoning: gc.aiSummary || '',
        risks: formatRisks(risks),
        quickQuestions: gc.quickQuestions || []
    }
}
```

**注意**：需要确认 `deptData.js` 中 groupCard 数据是否包含 `subProjects` 字段。如果没有，需要补充数据。

---

### I. 缺少 `openMetricDetail` 指标点击

**严重度**：🟢 低

**HTML 原版**（`sidebar.js:76-86`）：

```js
function openMetricDetail(cardType, metricType, value) {
    const metricConfigs = {
        milestone: {
            metrics: {
                total: { label: 'Offering总数', desc: '当前管理的产品/服务总数' },
                danger: { label: '高风险', desc: '存在重大风险、可能影响交付的Offering' },
                // ...
            }
        },
        // ...
    };
    // 根据配置构建侧边栏数据
}
```

**改动方案**：

| 文件 | 改动 |
|------|------|
| `DeptBudgetCard.vue` | `StatGrid` 项添加 `@click` 事件 |
| `DeptAHBCard.vue` | 同上 |
| `DeptTaskCard.vue` | 同上 |
| `useAISidepanel.js` | 新增 `metric-detail` builder |
| `ProjectKanbanView.vue` | 新增 `handleMetricClick` handler |

此功能为增强型交互，优先级低。涉及多个组件改造，建议在核心数据差异修复后再实施。

---

### J. 缺少 `highlightOffering` 里程碑子卡片高亮

**严重度**：🟢 低

**HTML 原版**（`sidebar.js:2150-2293`）：

```js
function highlightOffering(offeringName) {
    // 1. 高亮该子卡片
    document.querySelectorAll('.milestone-sub-card').forEach(el => el.classList.remove('milestone-sub-card--active'));
    var target = document.querySelector('.milestone-sub-card[data-offering="' + offeringName + '"]');
    if (target) target.classList.add('milestone-sub-card--active');

    // 2. 构建侧边栏内容：展示 phases/objectives/riskReason 详情
    // ...
}
```

**改动方案**：

| 文件 | 改动 |
|------|------|
| `DeptMilestoneCard.vue` | 添加 `activeOffering` 状态 + `.pk-milestone-sub--active` class |
| `useAISidepanel.js` | `milestone-dept` builder 的 `extra.timelineItem` 分支增加 phases 详情渲染数据 |
| `ProjectKanbanView.vue` | `handleDeptMilestoneItemClick` 传高亮参数 |

---

### K. 缺少 `openMilestonePhase` 节点详情

**严重度**：🟢 低

**HTML 原版**（`sidebar.js:2297-2317`）：

```js
function openMilestonePhase(offeringName, phaseIndex) {
    var phase = item.phases[phaseIndex];
    // 展示 objectives[] + 风险原因
    // ...
}
```

**改动方案**：

| 文件 | 改动 |
|------|------|
| `DeptMilestoneCard.vue` | phase 节点添加 `@click` 事件 |
| `useAISidepanel.js` | 新增 `milestone-phase` builder |
| `ProjectKanbanView.vue` | 新增 `handleMilestonePhaseClick` handler |

---

### L. 缺少 `_openTaskOrderAIOverview` 全局概览

**严重度**：🟢 低

**HTML 原版**：任务令 AI 按钮展示按产业分组的统计面板。

**改动方案**：

| 文件 | 改动 |
|------|------|
| `DeptTaskCard.vue` | 新增 AI 概览按钮/事件 |
| `useAISidepanel.js` | 新增 `task-overview` builder（按产业分组统计） |
| `ProjectKanbanView.vue` | 新增 handler |

当前 `task-dept` builder 默认分支已有整体分析，此差异属于 UI 形式不同（独立面板 vs 整体分析），优先级低。

---

### M. 缺少 `_openTaskOrderGanttNode` 甘特图节点 ⏸ 暂缓

**严重度**：🟢 低

取决于甘特图组件是否已实现。若已有甘特图：

| 文件 | 改动 |
|------|------|
| `useAISidepanel.js` | 新增 `gantt-node` builder |
| 甘特图组件 | 添加节点点击事件 |

当前 `task-dept` builder 的 `extra.taskOrder` 分支已覆盖任务令详情，甘特图节点是额外交互入口。

**暂缓原因**：甘特图组件尚未实现，待组件就绪后补充。

---

### N. 缺少 `_highlightIndustry` 产业高亮

**严重度**：🟢 低

**HTML 原版**：点击产业名高亮对应任务令。

**改动方案**：

| 文件 | 改动 |
|------|------|
| `DeptTaskCard.vue` | 产业名添加 `@click` + 高亮 class |
| `ProjectKanbanView.vue` | 新增 `handleIndustryHighlight` handler |

---

### O. 缺少 `external-risk-dept` cardType 处理

**严重度**：🟢 低

**HTML 原版**（`dashboard-renderer.js:1527-1533`）：

```js
sentenceEl.onclick = function() {
    openSidebarWithContext('external-risk-dept', {
        focus: summaryText,
        focusLevel: summaryClass,
        sentence: summaryText
    });
};
```

HTML 中 `external-risk-dept` 走 `default` 分支，仅展示 sentence 作为 reasoning，无专用 progress。

**改动方案**：

| 文件 | 改动 |
|------|------|
| `useAISidepanel.js` | 新增 `external-risk-dept` builder |
| 需确认 Vue 版中哪个组件触发此事件（目前可能无对应组件） |

若 Vue 版暂无外部风险概览区，此 cardType 可暂不实现。

---

### P. `groups-overview` 默认视图缺焦点风险

**严重度**：🟡 中

已在 G 项中合并处理。G 项的改动已包含焦点风险 progress。

---

## 🔵 项目级差异（4 项）

---

### Q. 五领域缺 `:riskIndex` 精确风险导航

**严重度**：🟢 低

**HTML 原版**：支持 `dev-domain:0` 格式，精确展示/高亮某条风险。

**Vue 现版**（`useAISidepanel.js:253-276`）：

```js
workflow(project, extra) {
    const domain = extra.domain || 'dev'
    const data = wf[domain]
    // ...
    return {
        progress: [
            { label: '状态', value: statusText(data.status), status: ... }
            // ❌ 仅 1 项状态
        ],
        risks: formatRisks(risks),
        // risks 全部展示，无法精确定位某一条
    }
}
```

**改动方案**：

| 文件 | 改动 |
|------|------|
| `useAISidepanel.js:253-276` | `workflow` builder 支持 `extra.riskIndex`，自动展开指定风险 |
| `WorkflowDomainsCard.vue` | `domain-click` 事件携带 `riskIndex` |
| `ProjectKanbanView.vue` | `handleDomainClick` 传递 `riskIndex` |

---

### R. 缺少 `summary-project` builder

**严重度**：🟡 中

**HTML 原版**（`sidebar.js:1223-1260`）：

```js
case 'summary-project': {
    var pData = raw.projectData || {};
    var riskFields = ['milestone', 'trustDetails', 'scope', 'schedule', 'resource', 'budget', 'quality'];
    // 各领域风险计数
    riskFields.forEach(function(f) {
        var fieldRisks = pData[f]?.risks || [];
        var criticalCount = fieldRisks.filter(r => r.level === 'critical').length;
        var warningCount = fieldRisks.filter(r => r.level === 'warning').length;
        if (fieldRisks.length > 0) {
            progressItems.push({ label: fieldLabels[f] + '风险', value: valStr, status: ... });
        }
    });
    // 展示全部风险列表 + 综合风险分析 reasoning
}
```

**Vue 现版**（`ProjectKanbanView.vue:312-314`）：

```js
function handleSummaryClick() {
    sidepanel.open('subProject', currentProject.value)  // ❌ 使用 subProject builder
}
```

`subProject` builder 展示全维度汇总（进度/里程碑/关键风险/关注风险），而 `summary-project` 侧重各领域风险统计+全部风险列表。

**改动方案**：

| 文件 | 改动 |
|------|------|
| `useAISidepanel.js` | 新增 `summary-project` builder |
| `ProjectKanbanView.vue:312` | `handleSummaryClick` 改为 `sidepanel.open('summary-project', currentProject.value)` |

```js
'summary-project'(project) {
    const fieldLabels = {
        milestone: '里程碑', trustDetails: '可信', scope: '范围',
        schedule: '进度', resource: '资源', budget: '费用', quality: '质量'
    }
    const riskFields = Object.keys(fieldLabels)

    const allRisks = []
    const progressItems = []

    // 焦点风险
    riskFields.forEach(f => {
        const fieldRisks = project[f]?.risks || []
        if (fieldRisks.length > 0) allRisks.push(...fieldRisks)
        const criticalCount = fieldRisks.filter(r => normalizeLevel(r.level) === 'danger').length
        const warningCount = fieldRisks.filter(r => normalizeLevel(r.level) === 'warning').length
        const label = fieldLabels[f] + '风险'
        let valStr = ''
        if (criticalCount > 0) valStr += `${criticalCount}严重 `
        if (warningCount > 0) valStr += `${warningCount}关注`
        if (!valStr) valStr = `${fieldRisks.length}项`
        progressItems.push({ label, value: valStr, status: criticalCount > 0 ? 'danger' : (warningCount > 0 ? 'warning' : 'normal') })
    })

    // 焦点风险
    const topRisk = allRisks.find(r => normalizeLevel(r.level) === 'danger')
        || allRisks.find(r => normalizeLevel(r.level) === 'warning')
    if (topRisk) {
        progressItems.unshift({ label: '焦点风险', value: topRisk.title || '', status: normalizeLevel(topRisk.level) === 'danger' ? 'danger' : 'warning' })
    }

    return {
        title: `${project.name || '项目'} 综合风险分析`,
        subtitle: project.name || '',
        progress: progressItems,
        reasoning: project.aiSummary || '',
        risks: formatRisks(allRisks),
        quickQuestions: project.intentQuestions?.risk || []
    }
}
```

---

### S. 五领域 builder progress 数据偏少

**严重度**：🟢 低

**改动方案**：与 Q、T 合并处理。在 `workflow` builder 中增加焦点问题/焦点风险 progress。

---

### T. 各项目级 builder 缺焦点问题/焦点风险

**严重度**：🟡 中

**HTML 原版**：各领域（milestone-project/schedule-project/budget-project/quality-project/scope-project/trust-project）都有 `if (focus) { progressItems.push({ label: '焦点风险', value: focus }) }` 逻辑。

**Vue 现版**：项目级 6 个 builder（`milestone`/`schedule`/`budget`/`quality`/`scope`/`trust`）均无焦点风险。

**改动方案**：

| 文件 | 改动 |
|------|------|
| `useAISidepanel.js` | 6 个项目级 builder 统一增加焦点风险 progress |

以 `milestone` 为例：

```js
milestone(project, extra) {
    const ms = project.milestone || {}
    const phases = ms.phases || []
    const risks = ms.risks || []

    const progressItems = []
    // ✅ 新增：焦点风险
    const topRisk = risks.find(r => normalizeLevel(r.level) === 'danger') || risks.find(r => normalizeLevel(r.level) === 'warning')
    if (topRisk) {
        progressItems.push({ label: '焦点风险', value: topRisk.title || topRisk.text || '', status: normalizeLevel(topRisk.level) === 'danger' ? 'danger' : 'warning' })
    }
    const completed = phases.filter(p => p.status === 'completed').length
    const active = phases.filter(p => p.status === 'active').length
    progressItems.push({ label: '总阶段', value: `${phases.length}个`, status: 'normal' })
    progressItems.push({ label: '已完成', value: `${completed}个`, status: completed > 0 ? 'normal' : 'warning' })
    progressItems.push({ label: '进行中', value: `${active}个`, status: active > 0 ? 'warning' : 'normal' })

    return {
        title: '里程碑分析',
        subtitle: project.name || '',
        progress: progressItems,
        reasoning: ms.aiSummary || '',
        risks: formatRisks(risks),
        quickQuestions: ms.quickQuestions || []
    }
}
```

其余 5 个 builder 同理：取 `risks` 中最高风险项，插入 progress 首位。

---

## 🟣 项目群级差异（2 项）

---

### U. 缺少 `project-group:{id}` 专用 builder

**严重度**：🟡 中

**HTML 原版**：`project-group:208.11.0` 走独立逻辑查找子项目→项目群映射，展示项目群分析数据。

**Vue 现版**（`ProjectKanbanView.vue:331-333`）：

```js
function handleSubProjectAIClick(subProject) {
    sidepanel.open('subProject', subProject)  // ❌ 使用通用 subProject builder
}
```

**改动方案**：

| 文件 | 改动 |
|------|------|
| `useAISidepanel.js` | 新增 `project-group` builder |
| `ProjectKanbanView.vue:331` | 判断是否为项目群，若是则用 `project-group` builder |

```js
'project-group'(groupData) {
    const risks = groupData.risks || []
    const subProjects = groupData.subProjects || []

    const progressItems = []
    const topRisk = risks.find(r => normalizeLevel(r.level) === 'danger') || risks.find(r => normalizeLevel(r.level) === 'warning')
    if (topRisk) {
        progressItems.push({ label: '焦点风险', value: topRisk.title || '', status: normalizeLevel(topRisk.level) === 'danger' ? 'danger' : 'warning' })
    }
    progressItems.push({ label: '子项目数', value: `${groupData.projectCount || subProjects.length}个`, status: 'normal' })
    progressItems.push({ label: '整体进度', value: `${groupData.overallProgress || 0}%`, status: (groupData.overallProgress || 0) >= 60 ? 'normal' : 'warning' })
    subProjects.forEach(p => {
        progressItems.push({ label: p.name || '', value: `进度${p.progress || 0}%`, status: (p.progress || 0) >= 60 ? 'normal' : 'warning' })
    })

    return {
        title: `${groupData.name || '项目群'}分析`,
        subtitle: groupData.name || '',
        progress: progressItems,
        reasoning: groupData.aiSummary || '',
        risks: formatRisks(risks),
        quickQuestions: groupData.quickQuestions || []
    }
}
```

---

### V. `groupSummary` risks 被 `slice(0,5)` 截断

**严重度**：🟢 低

**Vue 现版**（`useAISidepanel.js:291`）：

```js
risks: formatRisks(risks.slice(0, 5))  // ❌ 只取前5条
```

**改动方案**：

| 文件 | 改动 |
|------|------|
| `useAISidepanel.js:291` | 移除 `.slice(0, 5)` 或改为分页展示 |

```js
// 方案1：展示全部风险
risks: formatRisks(risks)

// 方案2：如果风险过多影响性能，可以保留截断但增加"查看更多"
risks: formatRisks(risks.slice(0, 10))
```

---

## ⚪ 通用功能差异（3 项）

---

### W. 缺少 ECharts 雷达图 ✅ 已完成

**严重度**：🟢 低

**HTML 原版**：`initAIDashboard()` 渲染进度/质量/成本/风险四维雷达图。

**改动方案**：

| 文件 | 改动 |
|------|------|
| `AISidepanel.vue` | 添加雷达图区域（数据概览下方） |
| `useAISidepanel.js` | builder 增加 `radarData` 字段 + `computeRadarData()` 工具函数 |

已完成：在项目级 builder（subProject、summary-project）中增加 `radarData` 字段，AISidepanel.vue 使用 ECharts 按需引入渲染雷达图。

---

### X. 缺少 `openRiskDetail`/`openRiskDetailByType` 风险详情弹窗 — 无需实现

**严重度**：🟢 低

**HTML 原版**（`sidebar.js:2874-3052`）：

```js
function openRiskDetail(viewType, riskIndex) {
    // 获取当前视图的风险数据
    // 展示完整风险详情：根因/影响/建议/快捷问题
}

function openRiskDetailByType(projectId, riskKey) {
    // 按风险类型打开详情
}
```

**Vue 现版**：`AISidepanel.vue` 中的风险卡片已有三段式展示（根因/影响/建议），点击展开/折叠。功能上已覆盖 HTML 版的 `openRiskDetail`，无需额外添加弹窗。

---

### Y. 缺少侧边栏工具栏

**严重度**：🟢 低

**HTML 原版**：侧边栏有复制/导出/刷新工具按钮。

**改动方案**：

| 文件 | 改动 |
|------|------|
| `AISidepanel.vue` | 在 header 区域添加工具按钮（复制/导出/刷新） |

```html
<!-- 在 ai-sidepanel__header 中添加 -->
<div class="ai-sidepanel__toolbar">
    <button @click="handleCopy" title="复制分析内容"><Copy :size="14" /></button>
    <button @click="handleExport" title="导出"><Download :size="14" /></button>
    <button @click="handleRefresh" title="刷新"><RefreshCw :size="14" /></button>
</div>
```

---

## 实施优先级总结

### 第一优先级（🟡中，核心数据完整性）

| 编号 | 任务 | 涉及文件 | 改动量 |
|------|------|---------|--------|
| A | budget-dept 焦点问题 | `useAISidepanel.js` | 小 |
| B | ahb 焦点问题 | `useAISidepanel.js` | 小 |
| C | task-dept 风险等级/延期 | `useAISidepanel.js` | 小 |
| D | online-dept 独立 builder | `useAISidepanel.js` | 中 |
| E | downstream-dept 独立 builder | `useAISidepanel.js` | 中 |
| F | trust-dept 独立 builder | `useAISidepanel.js` | 中 |
| G+P | groups-overview 焦点风险 | `useAISidepanel.js` | 小 |
| H | groupRisk 焦点+子项目 | `useAISidepanel.js` | 中 |
| R | summary-project builder | `useAISidepanel.js` + `ProjectKanbanView.vue` | 中 |
| T | 项目级6个 builder 焦点风险 | `useAISidepanel.js` | 中 |
| U | project-group builder | `useAISidepanel.js` + `ProjectKanbanView.vue` | 中 |

### 第二优先级（🟢低，增强功能）

| 编号 | 任务 | 涉及文件 | 改动量 |
|------|------|---------|--------|
| I | openMetricDetail | 3 个 dept 组件 + `useAISidepanel.js` + `ProjectKanbanView.vue` | 大 |
| J | highlightOffering | `DeptMilestoneCard.vue` + `useAISidepanel.js` + `ProjectKanbanView.vue` | 中 |
| K | openMilestonePhase | `DeptMilestoneCard.vue` + `useAISidepanel.js` + `ProjectKanbanView.vue` | 中 |
| L | _openTaskOrderAIOverview | `DeptTaskCard.vue` + `useAISidepanel.js` + `ProjectKanbanView.vue` | 中 |
| M | _openTaskOrderGanttNode | 甘特图组件 + `useAISidepanel.js` | 中 |
| N | _highlightIndustry | `DeptTaskCard.vue` + `ProjectKanbanView.vue` | 小 |
| O | external-risk-dept | `useAISidepanel.js` | 小 |
| Q | :riskIndex 精确导航 | `useAISidepanel.js` + `WorkflowDomainsCard.vue` + `ProjectKanbanView.vue` | 中 |
| S | workflow progress 丰富 | `useAISidepanel.js` | 小（与 T 合并） |
| V | groupSummary risks 截断 | `useAISidepanel.js` | 极小 |
| W | ECharts 雷达图 | `AISidepanel.vue` + `useAISidepanel.js` | 大 |
| X | openRiskDetail 弹窗 | `AISidepanel.vue` | 中 |
| Y | 工具栏 | `AISidepanel.vue` | 小 |

### 建议实施顺序

1. **批次一**（纯 `useAISidepanel.js` 改动，无需改其他文件）：A → B → C → G → V → T
2. **批次二**（D/E/F 合并改造 `groups-overview` builder 的 dimension 分支）：D + E + F
3. **批次三**（需联动 `ProjectKanbanView.vue`）：R → U → H
4. **批次四**（低优先级增强功能）：按需实施

---

## 🔴 深度对比新增差异（2026-04-23 更新）

> 对 HTML 原版五个部门级卡片（里程碑、任务令、AHB人力、费用执行、项目群综合风险）不同点击位置的侧边栏内容进行逐项对比，发现以下之前遗漏的差异。每个差异项标注需要修改的文件。

---

### Z1. 任务令 AI 按钮走独立概览视图（非 task-dept builder）

**严重度**：🔴 高

**HTML 原版**（`sidebar.js:2758-2870`）：

任务令 AI 按钮调用 `_openTaskOrderAIOverview()`，**不走** `openSidebarWithData` 统一结构化模板，而是直接构建自定义 HTML：

- **概览统计**：已完成/进行中/待启动 三格大数字
- **各产业进展**：按产业分组卡片（完成数/总数、进度条、高/中风险计数）
- **关键风险项**：列出所有 critical/high 风险的任务令（名称+产业+进度+截止+负责人）
- **时间分布**：本月截止/下月截止数量

**Vue 现版**：AI 按钮走 `task-dept` builder 默认分支，与一句话总结点击完全相同。

**差异**：AI 按钮应该展示「综合概览」视角，而不是与一句话总结相同的结构化分析。

**改动方案**：

| 文件 | 改动 |
|------|------|
| `DeptTaskCard.vue:9` | AI 按钮 emit 改为 `'task-overview'` 而非 `'task-dept'` |
| `useAISidepanel.js:1214-1250` | 改进 `task-overview` builder：增加概览统计大数字、关键风险项详情、时间分布 |
| `AISidepanel.vue` | 新增概览统计区域渲染（`overviewStats` 字段：三格大数字 + 产业分组卡片列表） |
| `ProjectKanbanView.vue:381` | `handleDeptAIClick` 中 `'task-dept'` 改为 `'task-overview'`，或新增独立 handler |

---

### Z2. 里程碑子卡片（highlightOffering）侧边栏内容不完整

**严重度**：🟡 中

**HTML 原版**（`sidebar.js:2152-2293`）：`highlightOffering` 展示该 offering 的**所有 phases 逐项**（名称+状态图标+日期+objectives+riskReason）。

**Vue 现版**（`useAISidepanel.js:547-569`）：只展示下一节点+偏差+当前阶段的 keyPoints。

**缺失**：各 phase 的 objectives 逐项、riskReason、状态图标+日期、当前阶段标记。

**改动方案**：

| 文件 | 改动 |
|------|------|
| `useAISidepanel.js:547-569` | `milestone-dept` builder 的 `timelineItem` 分支：将所有 phases 逐项展开为 keyPoints（含状态图标+日期+objectives+riskReason），并标记当前阶段 |

---

### Z3. 项目群综合风险卡片：风险列表项点击应展示 5W2H 详情，而非整个项目群

**严重度**：🟡 中

**HTML 原版**（`sidebar.js:2874-3052`）：

风险列表项点击 → `openRiskDetail('group-V3', riskIndex)` → 展示**该条风险**的完整 5W2H 详情：
- 风险级别标签 + 类型标签 + #序号
- 基本信息（who/when/where）
- 根因分析（why/rootCause）
- 影响范围（impact）
- 消减建议（how/suggestion/smart）
- 快捷问题（从对应项目群的 quickQuestions 获取）

**Vue 现版**（`DeptGroupsOverviewCard.vue:59` + `ProjectKanbanView.vue:391`）：

风险列表项点击 → `emit('risk-click', risk, gc)` → `handleDeptRiskClick` → `sidepanel.open('groups-overview', ..., { risk, groupCard })` → 展示**整个项目群**的分析（项目数+进度+风险数+全部 risks），不是该条风险的详情。

**差异**：点击单条风险项应展示该风险的 5W2H 详情，而非整个项目群概览。

**改动方案**：

| 文件 | 改动 |
|------|------|
| `DeptGroupsOverviewCard.vue:59` | 已有 `@click="$emit('risk-click', risk, gc)"`，无需改动 |
| `ProjectKanbanView.vue:391` | `handleDeptRiskClick` 改为 `sidepanel.open('group-risk-detail', deptData, { risk, groupCard })` |
| `useAISidepanel.js` | 新增 `group-risk-detail` builder：展示单条风险的 5W2H 详情（风险级别+类型标签+基本信息who/when/where+根因rootCause+影响impact+建议suggestion）+ 对应项目群的 quickQuestions |
| `AISidepanel.vue` | 新增 5W2H 详情渲染：风险级别标签、基本信息区、根因分析区、影响范围区、消减建议区 |

---

### Z4. ~~费用执行率指标区：仅「预警项目」可点击，其他指标不可点击~~ 无需改动

**严重度**：🟢 低 → ✅ 无需改动

**复核结论**：正式版 `dashboard-renderer.js` 中费用指标区只设 `textContent`，**没有**添加 `metric-clickable` 类和 `onclick` 事件。带 `metric-clickable` 的代码仅存在于 `.bak20260415` 备份文件中，不是最终设计。设计稿中指标区本就不可点击，Vue 现版行为一致。

**Vue 现版**（`DeptBudgetCard.vue`）：只有「预警项目」设置了 `clickable: true`，这是合理的额外增强，无需修改。

---

### Z5. ~~里程碑卡片 StatGrid 指标不可点击~~ 无需改动

**严重度**：🟡 中 → ✅ 无需改动

**复核结论**：正式版 `dashboard-renderer.js` 中里程碑指标区（787-798行）只设 `textContent`，**没有**添加 `metric-clickable` 类和 `onclick` 事件。设计稿中指标区不可点击，Vue 现版行为一致。

---

### Z6. 里程碑/AHB/任务令/费用卡片的一句话总结（aiSummary）没有独立点击事件

**严重度**：🟡 中

**HTML 原版**：每个卡片的一句话总结文本是可点击的，点击后调用 `openSidebarWithContext(cardType, context)` 打开**该卡片的结构化分析**侧边栏（含焦点风险、进度数据、风险列表）。与 AI 按钮不同，一句话总结携带 focus/focusLevel/sentence 上下文。

**Vue 现版**：`DataCard.vue` 的 `ai-summary` 文本只是展示，没有 `@click` 事件。点击 AI 按钮和点击一句话应该有不同行为：
- **AI 按钮**：打开卡片全量分析（无特定焦点）
- **一句话总结**：打开带焦点的分析（focus = 一句话中的高风险关键词）

**改动方案**：

| 文件 | 改动 |
|------|------|
| `DataCard.vue` | `ai-summary` 区域添加 `@click` 事件，emit `'summary-click'` |
| `DeptMilestoneCard.vue` | 传递 `@summary-click` 到 DataCard，emit 带卡片类型标识 |
| `DeptAHBCard.vue` | 同上 |
| `DeptBudgetCard.vue` | 同上 |
| `DeptTaskCard.vue` | 同上 |
| `useAISidepanel.js` | 各部门级 builder 在无 extra 时，从 data.aiSummary 提取 focus 文本（加粗标记的内容）作为焦点风险 |
| `ProjectKanbanView.vue` | 新增 `handleSummaryClick(section)` handler |

注意：此任务影响面广，可作为后续增强。当前 AI 按钮已可打开全量分析，一句话点击的差异仅在焦点定位上。

---

### Z12. 项目群综合风险 AI 按钮：侧边栏应从 V3/V2/MCU 汇总风险，而非只取 projectRisk.risks

**严重度**：🟡 中

**HTML 原版**（`sidebar.js:1301-1364`）：

AI 按钮 → `handleCardClick('groups-overview')` → `_openSidebarByCardType('groups-overview')` → 结构化模板，数据来源：

```js
// 从 V3/V2/MCU 三个项目群分别取 risks 汇总
['V3', 'V2', 'MCU'].forEach(function(gId) {
    var g = groupsData[gId];
    g.risks.forEach(function(r) {
        allRisks.push({
            level: riskLevel,
            title: (g.name || gId) + ' · ' + (r.title || ''),  // ← 带项目群名前缀
            text: r.title,
            rootCause: r.rootCause,
            impact: r.impact,
            suggestion: r.suggestion
        });
    });
});
```

- progress: 焦点风险 + 项目群数(3个) + 高风险数 + 中风险数 + 正常数
- risks: **V3/V2/MCU 三个项目群的所有 risks 合并**，每条带 "V3 · xxx" 前缀，按级别排序
- reasoning: 一句话总结 + 总体风险数量描述
- quickQuestions: 从 `prData.quickQuestions` 获取

**Vue 现版**（`useAISidepanel.js:984-1006`）：

AI 按钮 → `sidepanel.open('groups-overview', deptData)` → 默认分支，数据来源：

```js
const pr = go.projectRisk || {}
const risks = pr.risks || []  // ← 只取 projectRisk.risks（预聚合的 TOP3）
```

- progress: 焦点风险 + 项目群数 + 高/中/正常风险数（同设计稿）
- risks: 只从 `projectRisk.risks` 取，**缺少项目群名前缀**，且不是完整的三项目群合并
- reasoning: `pr.aiSummary`
- quickQuestions: `pr.quickQuestions`

**差异**：
1. 设计稿从 V3/V2/MCU 三个项目群**分别取 risks 合并**，带项目群名前缀（如 "V3 · TR5节点延误"）；Vue 版只取预聚合的 `projectRisk.risks`
2. 设计稿会展示**所有**项目群风险（V3 有 3 条 + V2 有 N 条 + MCU 有 N 条），Vue 版只有 TOP3 汇总
3. 目前 `projectRisk.risks` 的数据已包含了关键风险但缺少项目群名前缀

**改动方案**：

| 文件 | 改动 |
|------|------|
| `useAISidepanel.js:984-1006` | `groups-overview` builder 默认分支改为：从 `go.V3/V2/MCU` 分别取 risks 合并，每条加项目群名前缀，按级别排序；progress 数据保持从 `projectRisk` 取 |

---

### Z13. 侧边栏头部多了「复制」「刷新」工具栏按钮，设计稿中没有

**严重度**：🟡 中

**HTML 原版**（`index.html:47-62` + `main.css:3321-3336`）：

侧边栏头部只有：
- 左侧：💡 灯泡 SVG 图标 + 标题（h2）+ 副标题（p）
- 右侧：关闭按钮（32x32 白色圆角按钮）
- **没有**复制、刷新等工具栏按钮

```html
<div class="ai-sidebar-header">
    <div>
        <h2 id="sidebar-title"><svg>💡</svg> AI 分析</h2>
        <p id="sidebar-subtitle">综合风险分析</p>
    </div>
    <button class="ai-sidebar-close" onclick="closeSidebar()">✕</button>
</div>
```

**Vue 现版**（`AISidepanel.vue:10-30`）：

头部多了工具栏：
```html
<div class="ai-sidepanel__toolbar">
    <button class="ai-sidepanel__tool-btn" title="复制分析内容" @click="handleCopy">
        <Copy :size="14" />
    </button>
    <button class="ai-sidepanel__tool-btn" title="刷新" @click="handleRefresh">
        <RefreshCw :size="14" />
    </button>
</div>
```

**差异**：设计稿头部只有「关闭」按钮，Vue 版额外增加了「复制」和「刷新」工具栏按钮，不符合设计稿。

**改动方案**：

| 文件 | 改动 |
|------|------|
| `AISidepanel.vue:22-29` | 删除工具栏 `<div class="ai-sidepanel__toolbar">` 整块（含复制和刷新按钮） |
| `AISidepanel.vue:239` | 删除 `Copy, RefreshCw` 的 import |
| `AISidepanel.vue:537-566` | 删除 `handleCopy()` 和 `handleRefresh()` 函数 |
| `AISidepanel.vue:640-663` | 删除 `.ai-sidepanel__toolbar` 和 `.ai-sidepanel__tool-btn` CSS |

---

### Z7. 任务令圆环节点：HTML 走 `task-ring` 独立 cardType，Vue 复用 `task-dept` 的 taskOrder 分支

**严重度**：🟢 低

**HTML 原版**（`sidebar.js:744-811`）：任务令圆环点击走 `openSidebarWithContext('task-ring', context)`，有独立的 cardType 处理逻辑，展示：
- 任务令名称 + 截止日期 + 完成进度 + 风险等级 + 延期状态（5项 progress）
- 该任务令的 risks 详情
- 独立快捷问题

**Vue 现版**（`ProjectKanbanView.vue:403`）：圆环点击 → `sidepanel.open('task-dept', deptData, { taskOrder })`，走 `task-dept` builder 的 taskOrder 分支。

**差异**：功能上已等价（Vue 的 taskOrder 分支已包含任务令名称+截止+进度+风险等级+延期状态+risks），只是 cardType 名不同。无需改动。

---

### Z8. ~~AHB 人力指标区：仅「总偏差」可点击，其他指标不可点击~~ 无需改动

**严重度**：🟢 低 → ✅ 无需改动

**复核结论**：正式版 `dashboard-renderer.js` 中 AHB 指标区（1217-1237行）只设 `textContent`，**没有**添加 `metric-clickable` 类和 `onclick` 事件。设计稿中 AHB 指标区不可点击，Vue 现版行为一致。

---

### Z9. ~~任务令指标区：仅「高风险」可点击，其他指标不可点击~~ 无需改动

**严重度**：🟢 低 → ✅ 无需改动

**复核结论**：正式版 `dashboard-renderer.js` 中任务令指标区（920-931行）只设 `textContent`，**没有**添加 `metric-clickable` 类和 `onclick` 事件。设计稿中任务令指标区不可点击，Vue 现版行为一致。

---

### Z10. 项目群综合风险：维度卡片点击时，HTML 根据 sentence 文本走 `openLineDetail`，Vue 走 `groups-overview` builder

**严重度**：🟢 低

**HTML 原版**：维度卡片中的 sentence 文本可点击，调用 `openLineDetail(cardType, lineText)` 展示该行文字的详细分析。

**Vue 现版**：整个维度卡片是一个点击区域，emit `dim-click` → `handleDeptDimClick` → `sidepanel.open('groups-overview', ..., { dimension })`。已有的 dimension 分支处理已覆盖了 D/E/F 任务的独立 builder，功能上等价。

**差异**：HTML 版是分两次点击（卡片 + sentence），Vue 版合并为一次点击。当前行为可接受，无需改动。

---

### Z11. 项目群综合风险：项目群标签(V3/V2/MCU)点击，HTML 跳转到项目群视图，Vue 打开侧边栏

**严重度**：🟢 低

**HTML 原版**：项目群标签点击 → `switchLegacyView('group'); switchGroup('V3')` → 跳转到项目群级视图。

**Vue 现版**（`DeptGroupsOverviewCard.vue:45`）：整个项目群卡片点击 → `emit('group-click', gc)` → `sidepanel.open('groupRisk', ...)` → 打开侧边栏展示项目群风险分析。

**差异**：HTML 版是视图跳转，Vue 版是侧边栏分析。这是设计差异而非缺陷，Vue 版的行为更合理（在侧边栏中分析而非跳转页面）。无需改动。

---

## 实施优先级（深度对比新增）

| 编号 | 任务 | 严重度 | 涉及文件 | 改动量 |
|------|------|--------|---------|--------|
| Z1 | 任务令 AI 按钮走独立概览视图 | 🔴 高 | `DeptTaskCard.vue` + `useAISidepanel.js` + `AISidepanel.vue` + `ProjectKanbanView.vue` | 大 |
| Z2 | 里程碑子卡片侧边栏补全 phases 逐项 | 🟡 中 | `useAISidepanel.js` | 中 |
| Z3 | 项目群风险列表项点击展示 5W2H 详情 | 🟡 中 | `ProjectKanbanView.vue` + `useAISidepanel.js` + `AISidepanel.vue` | 中 |
| Z12 | 项目群综合风险 AI 按钮改为从 V3/V2/MCU 汇总风险 | 🟡 中 | `useAISidepanel.js` | 小 |
| Z13 | 侧边栏头部删除多余的工具栏按钮（复制/刷新） | 🟡 中 | `AISidepanel.vue` | 小 |
| Z6 | 一句话总结独立点击（焦点定位） | 🟡 中 | `DataCard.vue` + 4个 Dept 组件 + `useAISidepanel.js` + `ProjectKanbanView.vue` | 大 |
| Z4 | ~~费用指标区全部 clickable~~ | ✅ 无需改动 | 正式版设计稿指标区本就不可点击 | — |
| Z5 | ~~里程碑 StatGrid 指标可点击~~ | ✅ 无需改动 | 同上 | — |
| Z7 | task-ring vs task-dept cardType | ✅ 无需改动 | 功能等价 | — |
| Z8 | ~~AHB 指标区 clickable 修复~~ | ✅ 无需改动 | 正式版设计稿指标区本就不可点击 | — |
| Z9 | ~~任务令指标区全部 clickable~~ | ✅ 无需改动 | 同上 | — |
| Z10 | 维度卡片 sentence 点击方式差异 | ✅ 无需改动 | 功能等价 | — |
| Z11 | 项目群标签点击行为差异 | ✅ 无需改动 | 设计差异可接受 | — |
