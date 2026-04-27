import { ref } from 'vue'

// 工具类型 -> 标题/副标题映射
const TOOL_META = {
  daily: { title: '项目日报', subtitle: '每日进展与关键事项汇总' },
  weekly: { title: '项目周报', subtitle: '本周进展、风险与下周计划' },
  review: { title: '项目复盘', subtitle: '阶段性回顾与经验总结' },
  aar: { title: 'AAR 复盘报告', subtitle: 'After Action Review 行动后回顾' },
  sandbox: { title: '风险沙盘推演', subtitle: '潜在风险场景模拟与应对策略' }
}

/**
 * Mock API：获取 Markdown 内容
 * 目前直接读取 src/components/project-kanban/data/README.md（通过 fetch）
 * 后续替换为真实接口即可
 */
export async function fetchMdContent(toolType, currentProjectId) {
  // 模拟网络延迟
  await new Promise(resolve => setTimeout(resolve, 300))

  // 尝试读取组件目录下的 README.md
  try {
    const response = await fetch(`/src/components/project-kanban/data/AIREPORT-${currentProjectId}-${toolType}`)
    if (response.ok) {
      const text = await response.text()
      // 如果 README 有内容就返回，否则返回 mock 内容
      if (text.trim().length > 10 && !text.includes('<!DOCTYPE html>')) {
        return wrapWithToolHeader(text, toolType)
      }
    }
  } catch (e) {
    console.warn('[useMdSidepanel] 读取 README.md 失败，使用 mock 数据:', e)
  }

  // 降级到 mock 数据
  return getMockContent(toolType)
}

/**
 * 在 README 内容前加上工具栏标题说明
 */
function wrapWithToolHeader(content, toolType) {
  // const meta = TOOL_META[toolType] || { title: '文档预览', subtitle: '' }
  // const header = `## ${meta.title}\n\n> ${meta.subtitle}\n\n---\n\n`
  return content
}

/**
 * Mock 数据：各工具类型的默认内容
 */
function getMockContent(toolType) {
  const meta = TOOL_META[toolType] || { title: '文档预览', subtitle: '' }

  const templates = {
    daily: `# ${meta.title}

> ${meta.subtitle}

## 📅 2026-04-27 日报

### 今日进展
- ✅ 完成前端组件 MdSidepanel 封装
- ✅ 集成甜点工具栏 5 个按钮事件
- 🔄 接口联调中（待后端提供真实数据）

### 关键风险
| 风险项 | 等级 | 负责人 | 状态 |
|--------|------|--------|------|
| 接口延迟 | 中 | 张三 | 跟进中 |
| 需求变更 | 低 | 李四 | 已确认 |

### 明日计划
1. 替换 mock 接口为真实请求
2. 联调测试
3. 代码评审

---
*由 AI 项目管理助手自动生成*
`,
    weekly: `# ${meta.title}

> ${meta.subtitle}

## 📊 本周概览（4.21 - 4.27）

### 总体进度
- 计划完成：12 项
- 实际完成：10 项
- 完成率：**83.3%**

### 各模块进展
| 模块 | 计划 | 完成 | 状态 |
|------|------|------|------|
| 前端开发 | 5 | 5 | 🟢 正常 |
| 后端接口 | 4 | 3 | 🟡 延迟 |
| 测试用例 | 3 | 2 | 🟡 延迟 |

### 下周计划
1. 完成后端接口联调
2. 补充测试用例
3. 准备上线文档

---
*由 AI 项目管理助手自动生成*
`,
    review: `# ${meta.title}

> ${meta.subtitle}

## 🎯 阶段复盘：项目级看板 v1.0

### 目标回顾
- **原定目标**：完成项目级、项目群级、部门级三视图
- **实际达成**：三视图框架已完成，AI 侧边栏已集成

### 过程分析
1. **做得好的**
   - 组件化设计清晰，复用性高
   - 响应式断点覆盖全面

2. **待改进**
   - 接口 mock 数据需尽快替换
   - 部分交互细节需打磨

### 经验沉淀
> 先跑通主流程，再迭代细节。

---
*由 AI 项目管理助手自动生成*
`,
    aar: `# ${meta.title}

> ${meta.subtitle}

## 🎖️ AAR - MdSidepanel 组件开发

### 预期目标
封装一个独立的 Markdown 侧边栏组件，支持甜点工具栏 5 个按钮点击打开。

### 实际结果
- ✅ 组件独立封装完成
- ✅ 支持拖拽调整宽度
- ✅ 支持 Markdown 渲染
- ⏳ 真实接口待替换

### 原因分析
| 维度 | 分析 |
|------|------|
| 技术 | Vue 3 + marked 渲染方案成熟，无技术障碍 |
| 协作 | 前后端接口约定清晰，mock 数据可快速替换 |
| 时间 | 开发周期符合预期 |

### 后续行动
1. 后端提供 /api/project/:id/daily 等 5 个接口
2. 前端替换 fetchMdContent 实现
3. 补充加载态/错误态交互

---
*由 AI 项目管理助手自动生成*
`,
    sandbox: `# ${meta.title}

> ${meta.subtitle}

## ⚠️ 风险沙盘推演

### 场景一：接口延迟上线
- **触发条件**：后端接口延期 3 天
- **影响范围**：前端联调、测试周期压缩
- **应对策略**：
  1. 延长 mock 数据使用周期
  2. 并行进行 UI 走查
  3. 预留 2 天缓冲期

### 场景二：需求变更
- **触发条件**：业务方新增报表维度
- **影响范围**：数据卡片需调整
- **应对策略**：
  1. 评估变更工作量
  2. 协商分期交付
  3. 预留扩展字段

### 场景三：性能瓶颈
- **触发条件**：部门级数据量 > 1000 条
- **影响范围**：页面加载缓慢
- **应对策略**：
  1. 引入虚拟滚动
  2. 分页加载
  3. 数据缓存

---
*由 AI 项目管理助手自动生成*
`
  }

  return templates[toolType] || `# ${meta.title}\n\n> ${meta.subtitle}\n\n内容加载中...`
}

/**
 * Composable：管理 MdSidepanel 状态
 */
export function useMdSidepanel() {
  const visible = ref(false)
  const toolType = ref('')

  const title = ref('')
  const subtitle = ref('')

  function open(type) {
    const meta = TOOL_META[type] || { title: '文档预览', subtitle: '' }
    toolType.value = type
    title.value = meta.title
    subtitle.value = meta.subtitle
    visible.value = true
  }

  function close() {
    visible.value = false
  }

  return {
    visible,
    toolType,
    title,
    subtitle,
    open,
    close
  }
}
