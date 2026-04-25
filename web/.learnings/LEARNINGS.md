# LEARNINGS.md - Project Kanban Visual Style Iteration

## [LRN-20260425-001] Visual Style: Remove Background Colors, Use Shadows/Separation

**Logged**: 2026-04-25T14:35:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
用户一致偏好去掉背景色块，改用阴影、留白或细线做空间分割。这是 project-kanban 模块的核心视觉原则。

### Details
今天对以下组件/区域进行了去背景色改造：
- 任务令泳道：去掉背景色 + box-shadow，改用虚线/留白分割
- 可信管理九宫格：去掉子卡片背景色，hover 只加深阴影
- AI 侧边栏风险列表：去掉渐变背景/边框/圆角，改用阴影卡片
- AI 侧边栏 OBP 里程碑节点：去掉背景和边框，改用阴影卡片
- AI 侧边栏关键数据条：去掉 gray-50 背景
- AI 侧边栏 AI 分析文本：去掉渐变背景
- 子卡片 5 维度标签：去掉背景色，改圆点+灰色文字
- TOP3 风险：去掉状态背景色，改圆点

### Suggested Action
后续对 project-kanban 的样式改造，默认先考虑去掉背景色，用阴影/留白/细线替代。除非用户明确要求保留背景色。

### Metadata
- Source: user_feedback
- Related Files: src/components/project-kanban/**/*.vue
- Tags: visual-style, background-color, shadow, separation
- Pattern-Key: style.remove_background
- Recurrence-Count: 8
- First-Seen: 2026-04-25
- Last-Seen: 2026-04-25

---

## [LRN-20260425-002] Status Indicator: Dot + Gray Text Over Badge/Label

**Logged**: 2026-04-25T14:35:00+08:00
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
用户偏好用状态色圆点 + 灰色文字来指示风险/状态，而不是带背景色的标签或徽章。

### Details
改造实例：
- 子卡片 5 维度标签：从背景色标签 → 5px 状态圆点 + 灰色文字
- AI 侧边栏风险级别：从文字徽章（高风险/中风险/低风险）→ 6px 状态圆点
- TOP3 风险列表：从序号数字+背景色 → 5px 状态圆点

圆点规格：
- 卡片内小标签：5px
- 侧边栏风险：6-8px，可加白色外环+微阴影增强存在感

### Suggested Action
所有风险/状态指示优先使用圆点+灰色文字方案。圆点尺寸根据场景调整。

### Metadata
- Source: user_feedback
- Related Files: src/components/project-kanban/common/AISidepanel.vue, src/components/project-kanban/common/RiskList.vue, src/components/project-kanban/group/SubProjectCard.vue
- Tags: status-indicator, dot, risk-level
- Pattern-Key: ui.status_dot_over_badge
- Recurrence-Count: 3
- First-Seen: 2026-04-25
- Last-Seen: 2026-04-25

---

## [LRN-20260425-003] User Feedback Pattern: Iterative Fuzzy Adjustment

**Logged**: 2026-04-25T14:35:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary
用户习惯用模糊描述（"再大一点""太大了""没怎么变""太原始了"）进行 UI 数值微调，而非一次性给出精确值。

### Details
今天页边距调整轨迹：
`clamp(80px, 8vw, 200px)` → `clamp(40px, 5vw, 120px)`（用户说增加）→ `clamp(120px, 10vw, 280px)`（用户说没怎么变）→ `clamp(160px, 14vw, 360px)`（用户说太大了）→ `clamp(140px, 12vw, 320px)`（最终）

类似的迭代调整：
- 泳道分割：实线 → 去线留白 → 虚线

### Suggested Action
遇到 UI 数值调整时，先给一个中等幅度的变化，根据用户反馈再微调。准备好快速来回调整的心理预期。

### Metadata
- Source: user_feedback
- Related Files: src/views/ProjectKanbanView.vue
- Tags: user-preference, ui-tuning, iterative
- Pattern-Key: workflow.fuzzy_ui_adjustment
- Recurrence-Count: 2
- First-Seen: 2026-04-25
- Last-Seen: 2026-04-25

---

## [LRN-20260425-004] Highlight Without Background: Left Border Accent

**Logged**: 2026-04-25T14:35:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: frontend

### Summary
用户接受不用背景色的突出显示方式：左侧细线（2px）标记 + 标题/图标变色，用于科技感强调。

### Details
应用实例：
- 消减建议：`border-left: 2px solid var(--pk-accent)` + 标题/图标改强调色
- OBP 里程碑 active/risk 状态：左侧 2px 竖线（warning/danger 色）

这满足了"突出但不要大色块和背景色"的要求。

### Suggested Action
后续需要在无背景色的前提下突出某个区块时，优先使用左侧细线标记方案。

### Metadata
- Source: user_feedback
- Related Files: src/components/project-kanban/common/AISidepanel.vue
- Tags: highlight, accent, left-border, no-background
- Pattern-Key: style.left_border_highlight
- Recurrence-Count: 2
- First-Seen: 2026-04-25
- Last-Seen: 2026-04-25

---
