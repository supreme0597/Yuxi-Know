# 项目看板配色治理方案

## 一、核心原则

1. **完全独立**：所有配色通过看板局部 CSS 变量 `--pk-*` 管理，不修改 Yuxi 主项目任何文件（`base.css`、`design.md` 等）。
2. **不考虑暗色模式**：只定义一套色值，无需 `.dark` 覆盖逻辑。
3. **同色收敛**：同一语义（成功/警告/危险/AI 强调）只保留一个色值，消灭当前"这里一个绿、那里另一个绿"的混乱。
4. **清爽明快**：状态色保持在 Tailwind 400–500 明亮区间，配合 100 级浅背景和 600 级深色文字，视觉降噪但不沉闷。

## 二、配色决策历史

| 轮次 | 用户反馈 | 调整结果 |
|------|---------|---------|
| 初版 | 与 Yuxi 设计系统冲突、暗色模式穿帮 | 决定完全独立，不兼容主项目 |
| 第二版 | 饱和度太高，颜色鲜艳刺眼 | 大幅降饱和 → 被否决 |
| 第三版 | 太灰暗沉闷 | 回调饱和度，保持 Tailwind 标准明亮色 |
| 第四版 | 警告/危险色太深 | 警告 `#d97706` → `#f59e0b`；危险 `#dc2626` → `#ef4444` |
| 第五版 | 红色太正 | 危险主色 `#ef4444` → 西瓜红 `#ff6b6b` |

## 三、完整 CSS 变量表

### 3.1 状态色（核心三色）

| 变量 | 值 | Tailwind 参考 | 用途 |
|------|-----|--------------|------|
| `--pk-success` | `#10b981` | emerald-500 | 成功态图标、圆环、进度条 |
| `--pk-success-light` | `#d1fae5` | emerald-100 | 成功标签背景 |
| `--pk-success-dark` | `#059669` | emerald-600 | 成功标签文字 |
| `--pk-warning` | `#f59e0b` | amber-500 | 警告态图标、圆环 |
| `--pk-warning-light` | `#fef3c7` | amber-100 | 警告标签背景 |
| `--pk-warning-dark` | `#d97706` | amber-600 | 警告标签文字 |
| `--pk-danger` | `#ff6b6b` | — | 危险态图标、圆环（西瓜红） |
| `--pk-danger-light` | `#fee2e2` | red-100 | 危险标签背景 |
| `--pk-danger-dark` | `#ef4444` | red-500 | 危险标签文字 |

### 3.2 AI 强调色

| 变量 | 值 | Tailwind 参考 | 用途 |
|------|-----|--------------|------|
| `--pk-accent` | `#6366f1` | indigo-500 | AI 按钮、图标、StatGrid 点击态 |
| `--pk-accent-light` | `#eef2ff` | indigo-50 | AI 总结卡片背景 |
| `--pk-accent-dark` | `#4f46e5` | indigo-600 | AI 按钮 hover、深色文字 |
| `--pk-accent-gradient-from` | `#eef2ff` | indigo-50 | AI 侧板头部渐变起点 |
| `--pk-accent-gradient-to` | `#e0e7ff` | indigo-100 | AI 侧板头部渐变终点 |

### 3.3 项目群标识色（设计文档规定）

| 变量 | 值 | Tailwind 参考 | 用途 |
|------|-----|--------------|------|
| `--pk-group-v2` | `#3b82f6` | blue-500 | 项目群 V2 圆点/标签 |
| `--pk-group-v3` | `#8b5cf6` | violet-500 | 项目群 V3 圆点/标签 |
| `--pk-group-mcu` | `#06b6d4` | cyan-500 | 项目群 MCU 圆点/标签 |

### 3.4 中性色

| 变量 | 值 | 用途 |
|------|-----|------|
| `--pk-card-bg` | `#ffffff` | 卡片背景 |
| `--pk-page-bg` | `#f8fafa` | 看板页面背景 |
| `--pk-border` | `#eef0f4` | 卡片边框、分割线 |
| `--pk-text` | `#1e293b` | 主标题、正文 |
| `--pk-text-secondary` | `#64748b` | 辅助文字、时间戳 |

### 3.5 图表专用（映射状态色，保持语义直观）

| 变量 | 值 | 用途 |
|------|-----|------|
| `--pk-chart-green` | `#10b981` | 进度圆环-正常 |
| `--pk-chart-orange` | `#f59e0b` | 进度圆环-警告 |
| `--pk-chart-red` | `#ff6b6b` | 进度圆环-危险 |

## 四、隔离策略

1. **新建文件**：`web/src/components/project-kanban/styles/variables.css`
2. **作用域挂载**：`ProjectKanbanView.vue` 根元素添加 `class="project-kanban-view"`，所有 `--pk-*` 变量定义在该选择器下
3. **继承机制**：CSS 变量天然继承，子组件 DOM 树内自动可用，**不污染全局 `:root`**
4. **零侵入**：不改动 `base.css`、`design.md` 及看板以外的任何文件

## 五、治理文件清单（共 23 个）

| 类别 | 文件 | 主要改动点 |
|------|------|-----------|
| **壳层** | `ProjectKanbanView.vue` | 注入变量、header logo 渐变、tab 统计点 |
| **公共组件** | `common/StatusBadge.vue` | 状态标签收敛到 `--pk-success/warning/danger` |
| | `common/DonutChart.vue` | 圆环色收敛到 `--pk-chart-*` |
| | `common/StatGrid.vue` | 统计值状态色、点击态收敛 |
| | `common/DataCard.vue` | AI 总结渐变、边框、背景 |
| | `common/RiskList.vue` | 风险项背景/圆点色 |
| | `common/AIButton.vue` | 渐变按钮收敛到 `--pk-accent` |
| | `common/AISidepanel.vue` | 头部渐变、进度点、风险卡片、阶段图标 |
| **项目级卡片** | `project/MilestoneCard.vue` | 时间轴圆点、状态标签色 |
| | `project/WorkflowDomainsCard.vue` | 领域标签色 |
| | `project/TrustCard.vue` | 信任度指示色 |
| | `project/ScopeCard.vue` | 紫/橙/蓝背景块收敛到变量 |
| | `project/QualityCard.vue` | 质量指标色 |
| | `project/ScheduleCard.vue` | 进度条色 |
| | `project/BudgetCard.vue` | 预算偏差色 |
| | `project/AISummaryBar.vue` | AI 总结条背景/文字 |
| **部门级卡片** | `dept/DeptMilestoneCard.vue` | 圆弧、圆点、时间轴 |
| | `dept/DeptAHBCard.vue` | 圆环、人员构成条 |
| | `dept/DeptBudgetCard.vue` | 圆环、偏差指示条 |
| | `dept/DeptTaskCard.vue` | 泳道圆环 |
| | `dept/DeptGroupsOverviewCard.vue` | 综合统计色 |
| **项目群级** | `group/GroupCard.vue` | 项目群色圆点 |
| | `group/SubProjectCard.vue` | 子项目标签色 |

## 六、执行 TODO（6 阶段 / 29 任务）

### 阶段 1：基础设施

- [ ] **1.1** 新建 `web/src/components/project-kanban/styles/variables.css`，定义全套 `--pk-*` 变量（状态色 / AI 色 / 项目群色 / 中性色 / 图表色）
- [ ] **1.2** `ProjectKanbanView.vue` 引入 `variables.css`，根元素添加 `project-kanban-view` 类名作为作用域
- [ ] **1.3** `ProjectKanbanView.vue` 壳层替换：header logo 渐变色、tab 统计点颜色、AI 状态点颜色、全局背景色改为 `--pk-*`

### 阶段 2：公共组件（7 个）

- [ ] **2.1** `StatusBadge.vue`：替换成功/警告/危险三种标签的背景色和文字色，收敛为 `--pk-success/warning/danger` 系列
- [ ] **2.2** `DonutChart.vue`：替换圆环状态色为 `--pk-chart-green/orange/red`，中心文字色改为 `--pk-text`
- [ ] **2.3** `StatGrid.vue`：替换统计值状态色、点击态高亮色，收敛到 `--pk-success/warning/danger` 和 `--pk-accent`
- [ ] **2.4** `DataCard.vue`：替换 AI 总结渐变背景、卡片边框、阴影、图标色为 `--pk-accent` 系列
- [ ] **2.5** `RiskList.vue`：替换风险项背景色、左侧圆点色、风险文字色为 `--pk-danger/warning` 系列
- [ ] **2.6** `AIButton.vue`：替换渐变按钮背景色、hover 态、图标色为 `--pk-accent` 系列
- [ ] **2.7** `AISidepanel.vue`：替换头部渐变、进度点、风险卡片、阶段图标、产业进度条等所有硬编码色为 `--pk-*`

### 阶段 3：项目级卡片（8 个）

- [ ] **3.1** `MilestoneCard.vue`：替换时间轴圆点色、状态标签色为 `--pk-success/warning/danger`
- [ ] **3.2** `WorkflowDomainsCard.vue`：替换领域标签背景色和文字色为 `--pk-accent/info` 系列
- [ ] **3.3** `TrustCard.vue`：替换信任度指示色、状态文字色为 `--pk-success/warning/danger`
- [ ] **3.4** `ScopeCard.vue`：替换进行中/延期/完成三色背景块和文字色，收敛到 `--pk-accent/warning/info` 系列
- [ ] **3.5** `QualityCard.vue`：替换质量指标状态色为 `--pk-success/warning/danger`
- [ ] **3.6** `ScheduleCard.vue`：替换进度条状态色为 `--pk-success/warning/danger`
- [ ] **3.7** `BudgetCard.vue`：替换预算偏差状态色为 `--pk-success/warning/danger`
- [ ] **3.8** `AISummaryBar.vue`：替换 AI 总结条背景色、文字色、图标色为 `--pk-accent` 系列

### 阶段 4：部门级卡片（5 个）

- [ ] **4.1** `DeptMilestoneCard.vue`：替换圆弧仪表色、时间轴圆点/连线色、标签色为 `--pk-chart-*` 和 `--pk-success/warning/danger`
- [ ] **4.2** `DeptAHBCard.vue`：替换圆环状态色、人员构成条颜色为 `--pk-chart-*`
- [ ] **4.3** `DeptBudgetCard.vue`：替换圆环状态色、偏差指示条颜色为 `--pk-chart-*` 和 `--pk-danger`
- [ ] **4.4** `DeptTaskCard.vue`：替换泳道圆环状态色、泳道标签色为 `--pk-chart-*`
- [ ] **4.5** `DeptGroupsOverviewCard.vue`：替换综合统计状态色为 `--pk-success/warning/danger`

### 阶段 5：项目群级卡片（2 个）

- [ ] **5.1** `GroupCard.vue`：替换项目群色圆点、标签色为 `--pk-group-v2/v3/mcu`
- [ ] **5.2** `SubProjectCard.vue`：替换子项目状态标签色为 `--pk-success/warning/danger`

### 阶段 6：验证与收尾

- [ ] **6.1** 全局扫描：在 `project-kanban` 目录搜索所有残留硬编码 HEX 色值（`#` 开头），列出清单
- [ ] **6.2** 修复遗漏：按扫描清单逐个替换为对应 `--pk-*` 变量
- [ ] **6.3** 清理冗余：删除已废弃的硬编码色值注释、无用样式代码
- [ ] **6.4** 质量检查：运行 lint 确保无语法错误，确认所有组件正常引用 `--pk-*` 变量
